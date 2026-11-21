import struct
import sys
import argparse

from jinmo_applescript_disassembler.engine.util import opcodes, comments
from jinmo_applescript_disassembler.engine.fasparser import Loader

from applescript_decompiler.ast import *
from applescript_decompiler.utils import load_object
from applescript_decompiler.jxa import extract_jxa_source, is_jxa, resolve_script_path
import jinmo_applescript_disassembler.engine.runtimeobjects as rto

# Labels of the variables in `on error msg number n from f partial result p to t`
ERROR_LABELS = {"errn": "number", "erob": "from", "ptlr": "partial result", "errt": "to"}

# Some hardcoded offset in apple script binary
# root -> (<function index> -> (name, ..., literal, code))
ROOT_OFFSET = -1

# function object
NAME_OFFSET = 0
ARGS_OFFSET = 2
LABELED_OFFSET = 3  # labeled parameters (`given name:n`), a Binding chain
LOCALS_OFFSET = 4  # local variable names; kept even in run-only scripts
LITERAL_OFFSET = 5
CODE_OFFSET = 6


def run_decompiler(f, add_comments=False, force=False, analyzer=None, debug=False):
    script = decompile_script(f[ROOT_OFFSET], [], add_comments, force, debug)
    print("-----")
    print(script.to_source(analyzer=analyzer))


def script_from_init(statements, init_locals):
    """Rebuild a script object from the statements of its `init` closure."""
    names = {n.decode() for n in init_locals if isinstance(n, bytes)}
    script = Script(properties=[], handlers=[], body=[])
    for stmt in statements:
        if isinstance(stmt, PropertyDecl):
            script.properties.append(stmt)
        elif (
            isinstance(stmt, SetStatement)
            and isinstance(stmt.target.obj, VariableRef)
            and stmt.target.obj.name in names
        ):
            script.properties.append(PropertyDecl(name=stmt.target.obj.name, initial_value=stmt.value))
        elif isinstance(stmt, Handler) and isinstance(stmt.name, rto.Object):
            script.body.extend(stmt.body)  # the script's run handler
        elif isinstance(stmt, Handler):
            script.handlers.append(stmt)
        elif not isinstance(stmt, VariableDeclaration):
            script.body.append(stmt)
    return script


def decompile_script(
    root, outer_scopes, add_comments=False, force=False, debug=False, scope_names=None
):
    """Decompile a script body: [outer scope, names, value 0, value 1, ...].

    `outer_scopes` are the name lists of the enclosing scripts, used to
    resolve PushParentVariable. `scope_names` overrides the names handlers
    see at depth 1 (for scripts defined inside handlers).
    """
    if scope_names is None:
        scope_names = root[1] if isinstance(root[1], list) else []
    scopes = [scope_names] + outer_scopes

    # assert code['kind'] == 'untypedPointerBlock'  # I think it doesn't matter
    def decompile(function_offset, add_comments=False):  # function number
        state = {"pos": 0}
        function = root[function_offset]

        print("-- === data offset %d ===" % function_offset)

        names = root[1] if isinstance(root[1], list) else []
        member = names[function_offset - 2] if function_offset - 2 < len(names) else None
        if (
            isinstance(member, rto.Object)
            and isinstance(member.value, rto.Constant)
            and number_to_code(member.value.value) == "pimr"
        ):
            print("-- use clauses")
            uses.extend(use_clauses(function))
            return

        if type(function) is not list:
            print("-- <not a function>")
            # A script-level value that isn't a handler is a property. Kept
            # in declaration order among the handlers: the order of the
            # script's members is part of the compiled script.
            names = root[1] if isinstance(root[1], list) else []
            if function_offset - 2 < len(names) and isinstance(names[function_offset - 2], bytes):
                handlers.append(
                    PropertyDecl(
                        name=names[function_offset - 2].decode(),
                        initial_value=convert_literal(function),
                    )
                )
            return

        # A script object: [15, name, ?, parent script, script body]
        if function[0] == 15 and len(function) > 4 and isinstance(function[4], list):
            print(f"-- {function[NAME_OFFSET + 1]} is a script object")
            parent = function[3]
            parent_name = None
            if isinstance(parent, list) and len(parent) > 1 and isinstance(parent[1], bytes):
                parent_name = parent[1].decode()  # `property parent : Base`
            return ScriptBlock(
                name=function[NAME_OFFSET + 1].decode(),
                parent=parent_name,
                script=decompile_script(function[4], scopes, add_comments, force, debug),
            )

        if len(function) < 7:
            print("-- <maybe binding?>", function)
            # A property whose value is a string, list, ...
            if function_offset - 2 < len(names) and isinstance(names[function_offset - 2], bytes):
                handlers.append(
                    PropertyDecl(
                        name=names[function_offset - 2].decode(),
                        initial_value=convert_literal(function),
                    )
                )
            return

        literals = function[LITERAL_OFFSET + 1]
        name = function[NAME_OFFSET + 1]
        args = function[ARGS_OFFSET + 1]

        print("-- Function name :", name)
        print("-- Function arguments: ", end=" ")

        _args = []
        if isinstance(args, list) and len(args) >= 3 and isinstance(args[2], list):
            print(args[2][1:])
            _args = args[2][1:]
        else:
            print("-- <empty or unknown>")

        _labeled = []
        _binding = function[LABELED_OFFSET + 1]
        while isinstance(_binding, rto.Binding) and isinstance(_binding.b, bytes):
            _labeled.append((convert_literal(_binding.a), _binding.b.decode()))
            _binding = _binding.next

        _bound = set()  # locals bound by loops, `on error` and `script` blocks
        handler = Handler(
            name=name.decode() if isinstance(name, bytes) else name,
            parameters=[e.decode() if isinstance(e, bytes) else str(e) for e in _args],
            body=[],
            labeled=_labeled,
        )

        code = bytearray(function[CODE_OFFSET + 1].value)

        def word_at(pos):
            return struct.unpack(">H", code[pos : pos + 2])[0]

        def word():
            r = struct.unpack(">H", code[state["pos"] : state["pos"] + 2])[0]
            state["pos"] += 2
            return r - 0x10000 if r & 0x8000 else r

        def literal(x):
            if x >= len(literals):
                return "[L%d]" % x
            return literals[x]

        local_names = function[LOCALS_OFFSET + 1]
        if not isinstance(local_names, list):
            local_names = []

        def use_global(v):
            # Globals used outside the run handler need a `global` declaration
            if isinstance(name, bytes) and isinstance(v, bytes) and v not in globals_used:
                globals_used.append(v)

        def parent_variable(depth, x):
            # Operands are (depth, index): depth 1 is the enclosing script,
            # whose names (properties, handlers, script objects) are root[1].
            names = scopes[depth - 1] if 1 <= depth <= len(scopes) else []
            if 0 <= x < len(names) and isinstance(names[x], bytes):
                return names[x].decode()
            return "parent_%d_%d" % (depth, x)

        def variable(x, local=False):
            if 0 <= x < len(local_names) and isinstance(local_names[x], bytes):
                return local_names[x].decode()
            return "var_%d" % x

        # Runtime stack
        _stack = []

        # Stack that keeps track of the current block we are writing on.
        # Maintain as stack to represent things that are "block-ish" like
        # handlers, if/else, try, repeat, etc
        block_stack = [handler]

        _var = None
        _prev_op = None
        _closed_value = None  # value that ended the last closed else branch
        _pattern = []  # targets of a pending `set {a, b} to ...`

        def ending_statement(value):
            # a statement that ends without StoreResult (last of a handler or
            # branch): `value`, or the pending assignment of it
            nonlocal _var, _pattern
            if _pattern:
                target, _pattern = ListLiteral(elements=_pattern), []
            elif _var is not None:
                target, _var = _var, None
            else:
                return ExprStatement(expr=value)
            return SetStatement(target=LValue(obj=target), value=value)

        while state["pos"] < len(code):
            _curr_pos = state["pos"]
            _comment = " " + "%05x" % state["pos"] + " "
            c = code[state["pos"]]
            state["pos"] += 1
            op = opcodes[c]

            _comment += op + " "
            _statements = []

            if debug: 
                print(_stack)
                print(_comment, end = ' ')

            # AndOp/OrOp special cases since they have some control flow
            # but are actuall expressions
            if _stack and (
                isinstance(block_stack[-1], AndOp) or isinstance(block_stack[-1], OrOp)
            ):
                if _curr_pos == block_stack[-1].right_end_pos:
                    _right = _stack.pop()
                    # The compiler coerces the right operand: `b as boolean`
                    if (
                        isinstance(_right, BinaryOp)
                        and _right.op is BinaryOpKind.COERCE
                        and isinstance(_right.right, Keyword)
                        and _right.right.value == "bool"
                    ):
                        _right = _right.left
                    block_stack[-1].right = _right
                    _op = block_stack.pop()
                    _stack.append(BinaryOp(op=_op.op, left=_op.left, right=_op.right))

            if op == "Jump":
                _address = _curr_pos + 1 + word()
                _comment += hex(_address) + " "
                if _address < _curr_pos:
                    # Jump back to the top of a loop: the body's last value
                    # was Dup'ed for the loop result; drop what's left over.
                    _loop = next(
                        (b for b in reversed(block_stack) if isinstance(b, RepeatStatement)), None
                    )
                    if _loop is not None:
                        del _stack[_loop.stack_depth :]
                # Assume repeat blocks follow proper jump
                # Use Jump address to infer `else` block for `if-then-else`
                curr_index = len(block_stack) - 1
                while curr_index > 0 and (
                    not isinstance(block_stack[curr_index], IfStatement)
                    or block_stack[curr_index].end_if_pos is not None
                ):
                    curr_index -= 1
                _block = block_stack[curr_index]

                # (a backward jump is a loop's, even when the loop is in an if)
                if isinstance(_block, IfStatement) and _address > _curr_pos:
                    _block.end_if_pos = _address
                    if _stack:
                        _statements.append(ending_statement(_stack.pop()))
            elif op in ["PushLiteral", "PushLiteralExtended"]:
                v = word() if "Extended" in op else (c & 0xF)
                _comment += (
                    str(v)
                    + " # "
                    + str(convert_literal(literal(v)))
                    + " "
                    + str(literal(v))
                )
                _lit = convert_literal(literal(v))
                _stack.append(_lit)
            elif op in ["Push0", "Push1", "Push2", "Push3"]:
                _stack.append(NumberLiteral(value=int(op[-1])))
            elif op == "PushMinus1":
                _stack.append(NumberLiteral(value=int(-1)))
            elif op in ["PushTrue", "PushFalse"]:
                _stack.append(BooleanLiteral(value=op == "PushTrue"))
            elif op in ["PushIt", "PushMe", "PushUndefined"]:
                if "Me" in op:
                    _stack.append(VariableRef("my"))
                elif "It" in op:
                    _stack.append(VariableRef("__it__"))
            elif op in ["PushVariable", "PushVariableExtended"]:
                v = variable(
                    word() if "Extended" in op else (c & 0xF), "Extended" not in op
                )
                _comment += v + " "
                _stack.append(VariableRef(v))
            elif op in ["PushGlobal", "PushGlobalExtended"]:
                v = literal(word() if "Extended" in op else (c & 0xF))
                if isinstance(v, bytes):
                    use_global(v)
                    _stack.append(VariableRef(name=v.decode()))
                else:
                    _stack.append(convert_literal(v))
                _comment += str(v) + " "
            elif op in ["PopGlobal", "PopGlobalExtended"]:
                v = word() if "Extended" in op else (c & 0xF)
                _comment += str(literal(v))
                use_global(literal(v))
                _var = VariableRef(literal(v).decode())
            elif op in ["PopVariable", "PopVariableExtended"]:
                v = variable(word() if "Extended" in op else (c & 0xF))
                _comment += str(v) + " "
                _var = VariableRef(v)
            elif op == "Dup" and _stack:
                _stack.append(_stack[-1])
            elif op == "GCSwap" and len(_stack) >= 2:
                _stack[-1], _stack[-2] = _stack[-2], _stack[-1]
            elif op == "Pop" and _stack and _prev_op != "PushUndefined":
                # (PushUndefined pushes nothing here, so its Pop is skipped)
                _popped = _stack.pop()
                if (
                    _var is not None
                    and isinstance(_popped, BinaryOp)
                    and _popped.op is BinaryOpKind.GET_PROPERTY
                    and _stack
                    and _popped.right is _stack[-1]
                ):
                    # `set {a, b} to L`: each target is assigned `item i of`
                    # a Dup of L and popped; StoreResult then pops L itself
                    _pattern.append(_var)
                    _var = None
            elif op in BINARY_OP_MAPPING:
                r = _stack.pop()
                l = _stack.pop()
                _stack.append(BinaryOp(op=BINARY_OP_MAPPING[op], left=l, right=r))
            elif op in UNARY_OP_MAPPING:
                exp = _stack.pop()
                _stack.append(UnaryOp(op=UNARY_OP_MAPPING[op], operand=exp))
            elif op == "Exit":
                # Maybe check current block is repeat?
                # Should only be during repeat
                _statements.append(ExitRepeat())
            elif op == "Tell":
                _comment += str(word()) + " "
                _target = _stack.pop()
                block_stack.append(TellBlock(target=_target, body=[]))
            elif op == "Consider":
                _comment += str(word()) + " "
                _ignoring = _stack.pop()
                _considering = _stack.pop()
                block_stack.append(
                    ConsideringBlock(
                        target=None,
                        body=[],
                        considering=_considering.elements,
                        ignoring=_ignoring.elements,
                    )
                )
            elif op == "Clone":
                _stack.append(Copied(value=_stack.pop()))
            elif op == "ObjectAliasQuote":
                _stack.append(UnaryOp(op=UnaryOpKind.REFERENCE_TO, operand=_stack.pop()))
            elif op == "BeginTimeout":
                block_stack.append(TimeoutBlock(target=None, body=[], timeout=_stack.pop()))
            elif op == "PushEmpty":
                _stack.append(ListLiteral(elements=[]))
            elif op in ("EndTell", "EndConsider", "EndTimeout"):
                # Look for the containing TellBlock / ConsideringBlock / TimeoutBlock
                _kind = {"EndTell": TellBlock, "EndConsider": ConsideringBlock}.get(op, TimeoutBlock)
                curr_index = -1
                while not isinstance(block_stack[curr_index], _kind):
                    curr_index -= 1

                block_stack[curr_index].is_done = True

                if _stack and not (
                    isinstance(block_stack[curr_index].target, Keyword)
                    and block_stack[curr_index].target.value == "misccura"
                ):
                    _curr = _stack.pop()
                    if _var is not None:
                        _statements.append(
                            SetStatement(
                                # TODO: handle generic values
                                target=LValue(obj=_var),
                                value=_curr,
                            )
                        )
                        _var = None
                    else:
                        _statements.append(ExprStatement(expr=_curr))

            elif op in ("MakeObjectAlias", "MakeComp"):
                t = c - 23
                sub_operation = comments.get(t, "<Unknown>")
                _comment += sub_operation
                if sub_operation == "GetPositionEnd":
                    operand = _stack.pop()
                    _stack.append(UnaryOp(op=UnaryOpKind.END_OF, operand=operand))
                elif sub_operation == "GetPositionBeginning":
                    operand = _stack.pop()
                    _stack.append(UnaryOp(op=UnaryOpKind.BEGINNING_OF, operand=operand))
                elif sub_operation == "GetMiddle":
                    # `middle item of L`
                    _cls = _stack.pop()
                    _obj = _stack.pop()
                    _middle = BinaryOp(
                        op=BinaryOpKind.GET_INDEXED, left=VariableRef("middle"), right=_cls
                    )
                    _stack.append(
                        BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=_middle, right=_obj)
                    )
                elif sub_operation == "GetProperty":
                    l = _stack.pop()
                    r = _stack.pop()
                    _stack.append(
                        BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=l, right=r)
                    )
                elif sub_operation == "GetEvery":
                    r = _stack.pop()
                    l = _stack.pop()
                    _stack.append(BinaryOp(op=BinaryOpKind.EVERY, left=l, right=r))
                elif "GetIndexed" in sub_operation:
                    # Treat GetIndexed similar to GetProperty?
                    # content X of Y
                    # I'm not really sure if this is correct

                    l = _stack.pop()
                    r = _stack.pop()

                    target = _stack.pop()

                    l = BinaryOp(op=BinaryOpKind.GET_INDEXED, left=r, right=l)
                    _stack.append(
                        BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=l, right=target)
                    )
                elif "GetKeyFrom" in sub_operation:
                    # stack: container, class, key, key form
                    # (`window id 5`, `character id 65`, `file named "x"`)
                    _form = _stack.pop()
                    _key = _stack.pop()
                    _cls = _stack.pop()
                    _obj = _stack.pop()
                    _kind = {"kfrmID  ": BinaryOpKind.BY_ID, "kfrmname": BinaryOpKind.BY_NAME}.get(
                        getattr(_form, "value", None), BinaryOpKind.GET_INDEXED
                    )
                    _stack.append(
                        BinaryOp(
                            op=BinaryOpKind.GET_PROPERTY,
                            left=BinaryOp(op=_kind, left=_cls, right=_key),
                            right=_obj,
                        )
                    )
                elif sub_operation == "GetSome":
                    # `some item of L`
                    _cls = _stack.pop()
                    _obj = _stack.pop()
                    _some = BinaryOp(op=BinaryOpKind.GET_INDEXED, left=VariableRef("some"), right=_cls)
                    _stack.append(BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=_some, right=_obj))
                elif t in (28, 29):
                    # `item before X` / `item after X`; stack: container, class
                    _cls = _stack.pop()
                    _obj = _stack.pop()
                    _kind = BinaryOpKind.BEFORE if t == 28 else BinaryOpKind.AFTER
                    _stack.append(BinaryOp(op=_kind, left=_cls, right=_obj))
                elif "GetRange" in sub_operation:
                    _comment += str(_stack)
                    # stack: container, class, from, to (GCSwap/Pop already
                    # removed the container copies used to evaluate from/to)
                    _to = _stack.pop()
                    _from = _stack.pop()
                    _prop = _stack.pop()
                    _range_of = _stack.pop()
                    _range = BinaryOp(op=BinaryOpKind.THRU, left=_from, right=_to)
                    # `item 2 thru 4 of L`
                    _stack.append(
                        BinaryOp(
                            op=BinaryOpKind.GET_PROPERTY,
                            left=BinaryOp(op=BinaryOpKind.GET_INDEXED, left=_prop, right=_range),
                            right=_range_of,
                        )
                    )
                elif t == 26:
                    # `<container> whose <test>`
                    _test = _stack.pop()
                    _container = _stack.pop()
                    _stack.append(BinaryOp(op=BinaryOpKind.WHOSE, left=_container, right=_test))
                elif t == 44:
                    # whose-clause `not`
                    _stack.append(UnaryOp(op=UnaryOpKind.NOT, operand=_stack.pop()))
                elif op == "MakeComp" and opcodes[t - 33] in BINARY_OP_MAPPING:
                    # whose-clause comparison: sub-operation = 33 + comparison opcode
                    r = _stack.pop()
                    l = _stack.pop()
                    _stack.append(BinaryOp(op=BINARY_OP_MAPPING[opcodes[t - 33]], left=l, right=r))
                elif op == "MakeComp" and opcodes[t - 33] in ("And", "Or"):
                    r = _stack.pop()
                    l = _stack.pop()
                    _kind = BinaryOpKind.AND if opcodes[t - 33] == "And" else BinaryOpKind.OR
                    _stack.append(BinaryOp(op=_kind, left=l, right=r))
                else:
                    print(f"-- Warning {op}:{sub_operation} is not implemented")
                    _comment += " (not implemented)"
                    _stack.pop()
            elif op == "SetData":
                _var = _stack.pop()
            elif op == "GetData":
                pass
            elif op in ["And", "Or"]:
                _next = _curr_pos + 1 + word()
                _comment += hex(_next) + " "
                _left = _stack.pop()

                if op == "And":
                    block_stack.append(AndOp(left=_left, right_end_pos=_next))
                else:
                    block_stack.append(OrOp(left=_left, right_end_pos=_next))

            elif op == "TestIf":
                _else_pos = _curr_pos + 1 + word()
                _comment += hex(_else_pos)
                _cond = _stack.pop()
                _block = IfStatement(
                    condition=_cond, else_pos=_else_pos, then_block=[], else_block=[]
                )
                block_stack.append(_block)
            elif op == "MessageSend" and isinstance(literal(word_at(state["pos"])), bytes):
                # A user handler called with labeled parameters:
                # `greet given name:"bob"` (stack: target, label/value pairs, count)
                v = word()
                _comment += str(v) + " # " + str(literal(v))
                args_count = _stack.pop().value
                args = _stack[len(_stack) - args_count:]
                _stack = _stack[: len(_stack) - args_count]
                _target = _stack.pop()
                if isinstance(_target, VariableRef) and _target.name == "__it__":
                    _target = None
                _stack.append(
                    HandlerCall(
                        handler_name=literal(v).decode(),
                        arguments=[],
                        target=_target,
                        labeled=[(args[i], args[i + 1]) for i in range(0, len(args) - 1, 2)],
                    )
                )
            elif op == "MessageSend":
                v = word()
                event_code = number_to_code(
                    literal(v).value.identifier[0]
                ) + number_to_code(literal(v).value.identifier[1])
                _comment += str(v) + " (" + event_code  + ") # " + str(literal(v))

               
                args_count = _stack.pop().value
                if args_count == 0:
                    args = []
                else:
                    args = _stack[-args_count:]
                    _stack = _stack[:-args_count]

                _stack.append(
                    CommandCall(
                        command_name=event_code, arguments=[_stack.pop()] + args
                    )
                )
            elif op in ("Continue", "PositionalContinue"):
                # `continue name(args)`; stack: me, args, count, next, it
                # (PushNext pushes nothing here)
                v = word()
                _comment += str(v) + " # " + str(literal(v))
                _stack.pop()  # it
                args_count = _stack.pop().value
                args = _stack[len(_stack) - args_count:]
                _stack = _stack[: len(_stack) - args_count]
                _stack.pop()  # me
                _name = "continue " + literal(v).decode()
                if op == "Continue" and args:
                    _call = HandlerCall(
                        handler_name=_name,
                        arguments=[],
                        labeled=[(args[i], args[i + 1]) for i in range(0, len(args) - 1, 2)],
                    )
                else:
                    _call = HandlerCall(handler_name=_name, arguments=args)
                _stack.append(_call)
            elif op == "DefineActor":
                # `script Name ... end script` inside a handler. Stack: name,
                # syntax tree (unused). The literal is an `init` closure that
                # builds the script: property initialisations (assignments to
                # its locals, DefineProperty for `parent`), DefineProcedure for
                # each handler, the run handler last.
                v = word()
                _comment += str(v) + " "
                _stack.pop()
                _script_name = _stack.pop()
                _bound.add(_script_name.name)
                _closure = literal(v)
                _init = decompile_script(
                    [None, [b"init"], _closure], scopes, add_comments, force, debug,
                    scope_names=local_names,
                ).handlers[0]
                _stack.append(
                    ScriptBlock(
                        name=_script_name.name,
                        script=script_from_init(_init.body, _closure[LOCALS_OFFSET + 1]),
                    )
                )
            elif op in ("DefineProcedure", "DefineClosure"):
                # a handler of a script being built by an `init` closure
                v = word()
                _comment += str(v) + " "
                _fn = literal(v)
                _stack.append(
                    decompile_script(
                        [None, [_fn[NAME_OFFSET + 1]], _fn], scopes, add_comments, force, debug,
                        scope_names=local_names,
                    ).handlers[0]
                )
            elif op == "DefineProperty":
                # `property parent : X` in an `init` closure; literal = name
                v = word()
                _comment += str(v) + " "
                _prop = literal(v)
                _prop = _prop.decode() if isinstance(_prop, bytes) else "parent"
                _stack.append(PropertyDecl(name=_prop, initial_value=_stack.pop()))
            elif op == "EndDefineActor":
                pass
            elif op == "PositionalMessageSend":
                v = word()
                _comment += str(v) + " # " + str(literal(v))
                args_count = _stack.pop().value

                if args_count == 0:
                    args = []
                else:
                    args = _stack[-args_count:]
                    _stack = _stack[:-args_count]

                if _stack:
                    _target = _stack.pop()
                    if getattr(_target, "name", None) == "__it__":
                        _target = None
                else:
                    _target = None

                _stack.append(
                    HandlerCall(
                        handler_name=literal(v).decode(), arguments=args, target=_target
                    )
                )
            elif op == "StoreResult" and _stack:
                _curr = _stack.pop()
                if _pattern:
                    _statements.append(
                        SetStatement(target=LValue(obj=ListLiteral(elements=_pattern)), value=_curr)
                    )
                    _pattern = []
                elif _curr is _closed_value:
                    # a Dup'ed copy of the value that ended an else branch,
                    # already emitted there (the Dup ran before the if closed)
                    pass
                elif isinstance(_curr, (ScriptBlock, Handler, PropertyDecl)):
                    # `script Adder ... end script` inside a handler, or a
                    # handler/property of a script being built
                    _statements.append(_curr)
                    _var = None
                elif _var is not None:
                    _statements.append(
                        SetStatement(
                            # TODO: handle generic values
                            target=LValue(obj=_var),
                            value=_curr,
                        )
                    )
                    _var = None
                else:
                    _statements.append(ExprStatement(expr=_curr))
            elif op == "LinkRepeat":
                v = word() + _curr_pos + 1
                _comment += hex(v) + " "
                _repeat = RepeatStatement(kind=RepeatKind.FOREVER, end_repeat_pos=v)  # By default
                _repeat.stack_depth = len(_stack)
                block_stack.append(_repeat)
            elif op == "RepeatNTimes":
                _stack.pop()  # remove PushOne
                N = _stack.pop()
                _comment += str(N)
                _block = block_stack[-1]
                _block.kind = RepeatKind.TIMES
                _block.times = N
            elif op == "RepeatWhile":
                cond = _stack.pop()
                _block = block_stack[-1]
                _block.kind = RepeatKind.WHILE
                _block.condition = cond
            elif op == "RepeatUntil":
                cond = _stack.pop()
                _block = block_stack[-1]
                _block.kind = RepeatKind.UNTIL
                _block.condition = cond
            elif op == "RepeatInCollection":
                v = variable(word())
                _bound.add(v)
                _comment += v
                _stack.pop()  # Push1
                _stack.pop()  # Result of len(_arr)
                _arr = _stack.pop()
                _block = block_stack[-1]
                _block.kind = RepeatKind.WITH_IN
                _block.counter_var = VariableRef(v)
                _block.in_expr = _arr
            elif op == "RepeatInRange":
                v = variable(word())
                _bound.add(v)
                _comment += v

                _by = _stack.pop()
                _to = _stack.pop()
                _from = _stack.pop()

                _block = block_stack[-1]
                _block.kind = RepeatKind.WITH_COUNTER
                _block.from_expr = _from
                _block.to_expr = _to
                _block.by_expr = _by
                _block.counter_var = VariableRef(v)
            elif op == "Return":
                if _stack and (_var is not None or _pattern):
                    # The handler's last statement is an assignment: the
                    # implicit Return follows Pop*/SetData with no StoreResult.
                    _statements.append(ending_statement(_stack.pop()))
                elif _stack and state["pos"] >= len(code):
                    # The handler's final, implicit Return: the value is the
                    # result of the last statement, not an explicit `return`.
                    _curr = _stack.pop()
                    if _prev_op == "GetResult":
                        # A blank line after a trailing block compiles to
                        # StoreResult; GetResult (an empty statement)
                        _statements.append(EmptyStatement())
                    elif isinstance(_curr, (ScriptBlock, Handler, PropertyDecl)):
                        _statements.append(_curr)
                    else:
                        _statements.append(ExprStatement(expr=_curr))
                elif _stack:
                    _statements.append(ReturnStatement(value=_stack.pop()))
                elif op != _prev_op and state["pos"] < len(code):
                    # (a bare final Return is implicit; printing `return`
                    # would discard the last statement's result)
                    _statements.append(ReturnStatement())

            elif op == "MakeVector":
                vector_length = _stack.pop().value
                if vector_length == 0:
                    _list = ListLiteral(elements=[])
                else:
                    _list = ListLiteral(elements=_stack[-vector_length:])
                    _stack = _stack[:-vector_length]
                _stack.append(_list)
            elif op == "MakeRecord":
                record_length = _stack.pop().value
                if record_length == 0:
                    _rec = RecordLiteral(fields=[])
                else:
                    vals = _stack[-record_length:]
                    result = [
                        RecordField(label=vals[i], value=vals[i + 1])
                        for i in range(0, len(vals), 2)
                    ]
                    _rec = RecordLiteral(fields=result)
                _stack = _stack[:-record_length]
                _stack.append(_rec)
                pass
            elif op == "ErrorHandler":
                _comment += " " + hex(_curr_pos + 1 + word())
                block_stack.append(TryStatement(try_block=[], on_error_block=[]))
            elif op == "EndErrorHandler":
                v = _curr_pos + 1 + word()
                _comment += " " + hex(v)

                curr_index = len(block_stack) - 1
                while curr_index > 0 and not isinstance(
                    block_stack[curr_index], TryStatement
                ):
                    curr_index -= 1

                if _stack and (_var is not None or _pattern):
                    _statements.append(ending_statement(_stack.pop()))
                elif _stack and (
                    isinstance(_stack[-1], CommandCall)
                    or isinstance(_stack[-1], HandlerCall)
                ):
                    _statements.append(ExprStatement(expr=_stack.pop()))

                block_stack[curr_index].try_block.extend(_statements)
                _statements = []

                block_stack[curr_index].end_try_pos = v
            elif op == "HandleError":
                # Operands are literal indices: the message variable name, and
                # a Binding chain of labeled variables (number, from, ...).
                _msg = literal(word())
                _labeled = literal(word())
                _vars = []
                if isinstance(_msg, bytes):
                    _vars.append(_msg.decode())
                    _bound.add(_msg.decode())
                while isinstance(_labeled, rto.Binding) and isinstance(_labeled.b, bytes):
                    _label = number_to_code(_labeled.a.value.value)
                    _vars.append(ERROR_LABELS.get(_label, _label) + " " + _labeled.b.decode())
                    _bound.add(_labeled.b.decode())
                    _labeled = _labeled.next
                curr_index = len(block_stack) - 1
                while curr_index > 0 and not isinstance(block_stack[curr_index], TryStatement):
                    curr_index -= 1
                if _vars and isinstance(block_stack[curr_index], TryStatement):
                    block_stack[curr_index].on_error_var = " ".join(_vars)
                _comment += " " + " ".join(_vars)
            elif op == "PushParentVariable":
                v = parent_variable(word(), word())
                _comment += " " + v + " "
                _stack.append(VariableRef(v))
            elif op == "PopParentVariable":
                v = parent_variable(word(), word())
                _comment += " " + v + " "
                _var = VariableRef(v)
            elif op == "Error":
                # Stack: target, label/value pairs, count, message. A bare
                # `error` pushes PushUndefined as the message, which pushes
                # nothing here; otherwise the message is on top (it may be a
                # number itself, e.g. `error 5`).
                if _prev_op == "PushUndefined":
                    _s = None
                else:
                    _s = _stack.pop()
                args_count = _stack.pop().value

                if args_count == 0:
                    args = []
                else:
                    args = _stack[-args_count:]
                    _stack = _stack[:-args_count]

                if _s is not None:
                    args = [_s] + args
                _stack.pop()
                _statements.append(CommandCall(command_name="error", arguments=args))

            # elif op == 'Quotient':
            #     pass
            elif op == "GetResult":
                _stack.append(Keyword(value="rslt"))  # `result`
            # elif op == 'StartsWith':
            #     pass
            # elif op == 'EndsWith':
            #     pass
            # elif op == 'Pop':
            #     pass
            # elif op == 'DefineActor':
            #     print(hex(word()), end=' ')
            # elif op == 'EndDefineActor':
            #     pass
            else:
                _comment += "<disassembler not implemented> " + op

            _block = block_stack[-1]

            if _comment is not None and add_comments:
                _statements = [Comment(comment=_comment)] + _statements
                
            if debug: print(' '.join(_comment.split(' ')[2:]))

            _prev_op = op
            while True:
                while True:
                    _curr_index = -1
                    while isinstance(block_stack[_curr_index], AndOp) or isinstance(
                        block_stack[_curr_index], OrOp
                    ):
                        _curr_index -= 1

                    _block = block_stack[_curr_index]
                    if isinstance(_block, TellBlock):
                        if _statements:
                            _block.body.extend(_statements)
                            _statements = []
                        # If we have encountered an end tell
                        if _block.is_done:
                            # Special case to handle (ASCII character X) & (ASCII character X) ... etc
                            # For some reason, this is handled internally as a tell/endtellx
                            if not (
                                isinstance(_block.target, Keyword)
                                and _block.target.value == "misccura"
                            ):
                                _statements.append(_block)
                            block_stack.pop()
                            continue
                    elif isinstance(_block, TryStatement):
                        if _statements:
                            if _block.end_try_pos is not None:
                                _block.on_error_block.extend(_statements)
                            else:
                                _block.try_block.extend(_statements)
                            _statements = []
                        # If we've reached the end address of the try block
                        if (
                            _block.end_try_pos is not None
                            and _curr_pos >= _block.end_try_pos
                        ):
                            if (
                                _curr_pos == _block.end_try_pos
                                and _stack
                                and _stack[-1] is not _closed_value
                            ):
                                # the on-error part's last statement (no StoreResult)
                                _closed_value = _stack.pop()
                                _block.on_error_block.append(ending_statement(_closed_value))
                            _statements.append(block_stack.pop())
                            continue
                    elif isinstance(_block, RepeatStatement):
                        if _statements and (_curr_pos <= _block.end_repeat_pos):
                            _block.body.extend(_statements)
                            _statements = []
                        # If we've reached the end address of the repeat block
                        if (
                            _block.end_repeat_pos is not None
                            and _curr_pos >= _block.end_repeat_pos
                        ):
                            _statements.append(block_stack.pop())
                            continue
                    elif isinstance(_block, IfStatement):
                        # We need to keep track the end of the if block, from address in TestIf
                        # and the end of the else block, from the address in Jump
                        if _statements and (_curr_pos < _block.else_pos):
                            _block.then_block.extend(_statements)
                            _statements = []
                        elif _block.end_if_pos is not None:
                            if _statements and (_curr_pos <= _block.end_if_pos):
                                _block.else_block.extend(_statements)
                                _statements = []
                            if (
                                _curr_pos == _block.end_if_pos
                                and _stack
                                and _stack[-1] is not _closed_value  # else-if chain
                            ):
                                # the else branch's last statement (no StoreResult)
                                _closed_value = _stack.pop()
                                _block.else_block.append(ending_statement(_closed_value))
                            if _curr_pos == _block.end_if_pos:
                                _statements.append(block_stack.pop())
                                continue
                    elif isinstance(_block, Handler):
                        if _statements:
                            _block.body.extend(_statements)

                    break

                # If we are at the end of the decompilation, we should
                # attach all handlers back to the root handler
                if state["pos"] >= len(code) and len(block_stack) > 1:
                    _statements.append(block_stack.pop())
                else:
                    break

            # if _comment is not None and add_comments:
            #     block_stack[0].body.append(Comment(comment=_comment))

        if isinstance(name, rto.Object):  # run (event) handler
            # Undeclared variables in the run handler are globals; locals
            # other than loop/error variables and scripts were declared.
            _declared = [
                n.decode()
                for n in local_names
                if isinstance(n, bytes) and n.decode() not in _bound and n not in _args
            ]
            if _declared:
                block_stack[0].body.insert(0, VariableDeclaration(names=_declared))
        return block_stack[0]

    handlers = []
    uses = []
    properties = []
    globals_used = []
    for cur_function_offset in range(2, len(root)):
        try:
            ret = decompile(cur_function_offset, add_comments=add_comments)
            if ret is not None:
                handlers.append(ret)
        except Exception as e:
            print("-- Failed to decompile")
            if not force:
                raise e
    names = root[1] if isinstance(root[1], list) else []
    globals_used = [g for g in globals_used if g not in names]
    if globals_used:
        properties.insert(
            0, VariableDeclaration(names=[g.decode() for g in globals_used], is_global=True)
        )
    return Script(properties=uses + properties, handlers=handlers)


USE_CLASSES = {"frmk": "framework", "scpt": "script"}


def use_clauses(value):
    """`use` clauses are stored in the `pimr` property as a list of
    one-field records: `vers` (AppleScript version) or `cobj` (a stored
    reference such as framework "Foundation", or every scripting addition).
    """
    uses = []
    items = value[2][1:] if isinstance(value, list) and len(value) > 2 else []
    for b in items:
        if not isinstance(b, rto.Binding):
            continue
        label = number_to_code(b.a.value.value) if isinstance(b.a, rto.Object) else None
        ref = b.b
        if label == "vers":
            text = "AppleScript version " + convert_literal(ref).to_source()
        elif isinstance(ref, list) and len(ref) > 1 and ref[0] == 20 and isinstance(ref[1], list):
            spec = ref[1]
            if spec[0] == 22 and number_to_code(spec[2].value.value) == "osax":
                text = "scripting additions"
            elif spec[0] == 24 and len(spec) > 3:
                cls = number_to_code(spec[2].value.value)
                text = USE_CLASSES.get(cls, cls) + " " + convert_literal(spec[3]).to_source()
            else:
                continue
        else:
            text = convert_literal(ref).to_source()  # e.g. application "Finder"
        uses.append(UseStatement(text=text))
    return uses


def cli():
    args = parse_args()

    path = args.scpt
    add_comments = args.comments

    analyzer = None
    analyzer_mapping = {
        'OSAMinerDecryptAnalyzer': 'applescript_decompiler.OSAMinerDecryptAnalyzer',
        'NaiveStringAnalyzer': 'applescript_decompiler.NaiveStringAnalyzer'

    }

    if args.analyzer:
        analyzer = load_object(analyzer_mapping.get(args.analyzer, args.analyzer))

    if is_jxa(path):
        # JavaScript for Automation: the source is stored as text
        print(f'// {path}')
        print('// JavaScript for Automation (JXA): source stored in the script, not compiled')
        print('-----')
        print(extract_jxa_source(path))
        return

    print(f'-- {path}')
    print('--')
    f = Loader()
    f = f.load(resolve_script_path(path))
    run_decompiler(f, add_comments=args.comments, force=args.force, analyzer=analyzer, debug=args.debug)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="applescript_decompile",
        description="AppleScript .scpt decompiler (also extracts the source of JXA scripts)",
    )

    parser.add_argument(
        "scpt", help="Path to a compiled .scpt file (AppleScript or JXA), or a .scptd/.app bundle"
    )
    parser.add_argument(
        "-c",
        "--comments",
        action="store_true",
        help="Include comments in the decompiled output",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Ignore errors and keep decompiling the remaining handlers",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Prints out the disassembled code while decompiling",
    )
    parser.add_argument(
        "--analyzer",
        default=None,
        help="It can be OSAMinerDecryptAnalyzer or NaiveStringAnalyzer or a full dotted path to analyzer class like applescript_decompiler.OSAMinerDecryptAnalyzer, applescript_decompiler.NaiveStringAnalyzer, or  local.MyAnalyzer (for a file in local.py)",
    )

    try:
        return parser.parse_args()
    except Exception:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
