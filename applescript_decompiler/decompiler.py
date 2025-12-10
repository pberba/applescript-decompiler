import struct
import sys
import argparse

from jinmo_applescript_disassembler.engine.util import opcodes, comments
from jinmo_applescript_disassembler.engine.fasparser import Loader

from applescript_decompiler.ast import *

# Some hardcoded offset in apple script binary
# root -> (<function index> -> (name, ..., literal, code))
ROOT_OFFSET = -1

# function object
NAME_OFFSET = 0
ARGS_OFFSET = 2
LITERAL_OFFSET = 5
CODE_OFFSET = 6


def cli():
    args = parse_args()

    path = args.scpt
    add_comments = args.comments

    f = Loader()
    f = f.load(path)

    root = f[ROOT_OFFSET]

    # assert code['kind'] == 'untypedPointerBlock'  # I think it doesn't matter
    def decompile(function_offset, add_comments=False):  # function number
        state = {"pos": 0, "tab": 0}
        function = root[function_offset]

        print("-- === data offset %d ===" % function_offset)

        if type(function) is not list:
            print("-- <not a function>")
            return
        if len(function) < 7:
            print("-- <maybe binding?>", function)
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

        handler = Handler(
            name=name.decode() if isinstance(name, bytes) else name,
            parameters=[e.decode() if isinstance(e, bytes) else str(e) for e in _args],
            body=[],
        )

        handler_stack = [handler]

        code = bytearray(function[CODE_OFFSET + 1].value)

        def word():
            r = struct.unpack(">H", code[state["pos"] : state["pos"] + 2])[0]
            state["pos"] += 2
            return r - 0x10000 if r & 0x8000 else r

        def literal(x):
            if x >= len(literals):
                return "[L%d]" % x
            return literals[x]

        def variable(x, local=False):
            if local and len(_args) > x:
                _x = _args[x]
                return "[var_%d (%r)]" % (
                    x,
                    _x.decode() if isinstance(_x, bytes) else str(_x),
                )
            return "[var_%d]" % x

        _stack = []
        _var = None
        _prev_op = None

        while state["pos"] < len(code):
            _curr_pos = state["pos"]
            _comment = " " * state["tab"] * 4 + " " + "%05x" % state["pos"] + " "
            c = code[state["pos"]]
            state["pos"] += 1
            op = opcodes[c]

            _comment += op + " "
            _state = []

            if _stack and (
                isinstance(handler_stack[-1], AndOp)
                or isinstance(handler_stack[-1], OrOp)
            ):
                if _curr_pos == handler_stack[-1].right_end_pos:
                    handler_stack[-1].right = _stack.pop()
                    _op = handler_stack.pop()
                    _stack.append(BinaryOp(op=_op.op, left=_op.left, right=_op.right))

            if op == "Jump":
                _address = _curr_pos + 1 + word()
                _comment += hex(_address) + " "
                # Assume repeat blocks follow proper jump
                # Use Jump address to infer `else` block for `if-then-else`
                curr_index = -1
                while (
                    isinstance(handler_stack[curr_index], IfStatement)
                    and handler_stack[curr_index].end_if_pos is not None
                ):
                    curr_index -= 1
                _handler = handler_stack[curr_index]
                if isinstance(_handler, IfStatement):
                    _handler.end_if_pos = _address
                    if _stack:
                        if _var is not None:
                            _state.append(
                                SetStatement(
                                    # TODO: handle generic values
                                    target=LValue(obj=_var),
                                    value=_stack.pop(),
                                )
                            )
                            _var = None
                        else:
                            _state.append(ExprStatement(expr=_stack.pop()))
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
                    _stack.append(VariableRef(name=v.decode()))
                else:
                    _stack.append(convert_literal(v))
                _comment += str(v) + " "
            elif op in ["PopGlobal", "PopGlobalExtended"]:
                v = word() if "Extended" in op else (c & 0xF)
                _comment += str(literal(v))
                _var = VariableRef(literal(v).decode())
            elif op in ["PopVariable", "PopVariableExtended"]:
                v = variable(word() if "Extended" in op else (c & 0xF))
                _comment += str(v) + " "
                _var = VariableRef(v)
            elif op == "Dup" and _stack:
                curr_index = len(handler_stack) - 1
                # Find enclosing `RepeatStatement`
                while curr_index > 0 and not isinstance(
                    handler_stack[curr_index], RepeatStatement
                ):
                    curr_index -= 1

                _handler = handler_stack[curr_index]
                if (
                    isinstance(_handler, RepeatStatement)
                    and _handler.kind != RepeatKind.FOREVER
                ):
                    pass
                else:
                    _stack.append(_stack[-1])
            elif op in BINARY_OP_MAPPING:
                r = _stack.pop()
                l = _stack.pop()
                _op = BinaryOp(op=BINARY_OP_MAPPING[op], left=l, right=r)
                _stack.append(_op)
            elif op in UNARY_OP_MAPPING:
                exp = _stack.pop()
                _op = UnaryOp(op=UNARY_OP_MAPPING[op], operand=exp)
                _stack.append(_op)

            elif op == "Exit":
                _handler = handler_stack[-1]
                # Maybe check current block is repeat?
                # Should only be during repeat
                _state.append(ExitRepeat())
            elif op == "Tell":
                _comment += str(word()) + " "
                state["tab"] += 1

                _target = _stack.pop()
                _handler = TellBlock(target=_target, body=[])
                handler_stack.append(_handler)
            elif op == "EndTell":
                state["tab"] -= 1
                # Look for the containing TellBlock
                curr_index = -1
                while not isinstance(handler_stack[curr_index], TellBlock):
                    curr_index -= 1

                handler_stack[curr_index].is_done = True

                if _stack and not (
                    isinstance(handler_stack[curr_index].target, Keyword)
                    and handler_stack[curr_index].target.value == "misccura"
                ):
                    _curr = _stack.pop()
                    if _var is not None:
                        _state.append(
                            SetStatement(
                                # TODO: handle generic values
                                target=LValue(obj=_var),
                                value=_curr,
                            )
                        )
                        _var = None
                    else:
                        _state.append(ExprStatement(expr=_curr))

            elif op in ("MakeObjectAlias", "MakeComp"):
                t = c - 23
                sub_operation = comments.get(t, "<Unknown>")
                _comment += sub_operation
                if sub_operation == "GetPositionEnd":
                    operand = _stack.pop()
                    _stack.append(UnaryOp(op=UnaryOpKind.END_OF, operand=operand))
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

                    l = BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=l, right=target)

                    _stack.append(
                        BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=r, right=l)
                    )
                elif "GetKeyFrom" in sub_operation:
                    # Also not sure if this is correct
                    l = _stack.pop()
                    r = _stack.pop()
                    if l.value == "kfrmID  ":
                        _type = _stack.pop()
                        _stack.pop()
                        l.value += _type.value
                    _stack.append(
                        BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=l, right=r)
                    )
                elif "GetRange" in sub_operation:
                    _comment += str(_stack)
                    _to = _stack.pop()
                    _from = _stack.pop()
                    _prop = _stack.pop()
                    _stack.pop()
                    _var = _stack.pop()
                    _stack.pop()
                    _range = BinaryOp(op=BinaryOpKind.THRU, left=_from, right=_to)

                    _range_of = BinaryOp(
                        op=BinaryOpKind.GET_PROPERTY, left=_range, right=_var
                    )
                    _stack.append(
                        BinaryOp(
                            op=BinaryOpKind.GET_PROPERTY, left=_prop, right=_range_of
                        )
                    )
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
                    handler_stack.append(AndOp(left=_left, right_end_pos=_next))
                else:
                    handler_stack.append(OrOp(left=_left, right_end_pos=_next))

            elif op == "TestIf":
                _else_pos = _curr_pos + 1 + word()
                _comment += hex(_else_pos)
                _cond = _stack.pop()
                _handler = IfStatement(
                    condition=_cond, else_pos=_else_pos, then_block=[], else_block=[]
                )
                handler_stack.append(_handler)
            elif op == "MessageSend":
                v = word()
                _comment += str(v) + " # " + str(literal(v))

                event_code = number_to_code(
                    literal(v).value.identifier[0]
                ) + number_to_code(literal(v).value.identifier[1])
                args_count = _stack.pop().value
                if args_count == 0:
                    args = []
                else:
                    args = _stack[-args_count:]
                    _stack = _stack[:-args_count]

                _command = CommandCall(
                    command_name=event_code, arguments=[_stack.pop()] + args
                )
                _stack.append(_command)
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
                    if _target.name == "__it__":
                        _target = None
                else:
                    _target = None

                _curr = HandlerCall(
                    handler_name=literal(v).decode(), arguments=args, target=_target
                )
                _stack.append(_curr)
            elif op == "StoreResult" and _stack:
                _curr = _stack.pop()
                if _var is not None:
                    _state.append(
                        SetStatement(
                            # TODO: handle generic values
                            target=LValue(obj=_var),
                            value=_curr,
                        )
                    )
                    _var = None
                else:
                    _state.append(ExprStatement(expr=_curr))
            elif op == "LinkRepeat":
                v = word() + _curr_pos + 1
                _comment += hex(v) + " "
                _handler = RepeatStatement(
                    kind=RepeatKind.FOREVER, end_repeat_pos=v  # By default
                )
                handler_stack.append(_handler)
                state["tab"] += 1
            elif op == "RepeatNTimes":
                _stack.pop()  # remove PushOne
                N = _stack.pop()

                _handler = handler_stack[-1]
                _handler.kind = RepeatKind.TIMES
                _handler.times = N
            elif op == "RepeatWhile":
                cond = _stack.pop()
                _handler = handler_stack[-1]
                _handler.kind = RepeatKind.WHILE
                _handler.condition = cond
            elif op == "RepeatUntil":
                cond = _stack.pop()
                _handler = handler_stack[-1]
                _handler.kind = RepeatKind.UNTIL
                _handler.condition = cond
            elif op == "RepeatInCollection":
                v = variable(word())
                _stack.pop()  # Push1
                _stack.pop()  # Result of len(_arr)
                _arr = _stack.pop()
                _handler.kind = RepeatKind.WITH_IN
                _handler.counter_var = VariableRef(v)
                _handler.in_expr = _arr
            elif op == "RepeatInRange":
                v = variable(word())
                _comment += v

                _by = _stack.pop()
                _to = _stack.pop()
                _from = _stack.pop()

                _handler = handler_stack[-1]
                _handler.kind = RepeatKind.WITH_COUNTER
                _handler.from_expr = _from
                _handler.to_expr = _to
                _handler.by_expr = _by
                _handler.counter_var = VariableRef(v)
            elif op == "Return":
                # TODO Make Return Robust
                if _stack and (
                    isinstance(_stack[-1], CommandCall)
                    or isinstance(_stack[-1], HandlerCall)
                ):
                    _state.append(ExprStatement(expr=_stack.pop()))
                elif _stack:
                    _state.append(ReturnStatement(value=_stack.pop()))
                elif op != _prev_op:
                    _state.append(ReturnStatement())

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
                state["tab"] += 1
                handler_stack.append(TryStatement(try_block=[], on_error_block=[]))
            elif op == "EndErrorHandler":
                v = _curr_pos + 1 + word()
                _comment += " " + hex(v)
                state["tab"] -= 1
                if _stack and (
                    isinstance(_stack[-1], CommandCall)
                    or isinstance(_stack[-1], HandlerCall)
                ):
                    _state.append(ExprStatement(expr=_stack.pop()))
                    handler_stack[-1].try_block.extend(_state)
                    _state = []
                handler_stack[-1].end_try_pos = v
            elif op == "HandleError":
                _comment += " " + variable(word()) + " " + variable(word())
            elif op == "PushParentVariable":
                v = "[parent]" + variable(word())
                _comment += " " + str(word()) + " " + v + " "
                _stack.append(VariableRef(v))
            elif op == "PopParentVariable":
                v = "[parent]" + variable(word())
                _comment += " " + str(word()) + " " + v + " "
                _var = VariableRef(v)

            # elif op == 'Quotient':
            #     pass
            # elif op == 'GetResult':
            #     pass
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

            if _comment is not None and add_comments:
                handler_stack[0].body.append(Comment(comment=_comment))

            _handler = handler_stack[-1]

            _prev_op = op
            while True:
                while True:
                    _handler = handler_stack[-1]
                    if isinstance(_handler, TellBlock):
                        if _state:
                            _handler.body.extend(_state)
                            _state = []
                        # If we have encountered an end tell
                        if _handler.is_done:
                            # Special case to handle (ASCII character X) & (ASCII character X) ... etc
                            # For some reason, this is handled internally as a tell/endtellx
                            if not (
                                isinstance(_handler.target, Keyword)
                                and _handler.target.value == "misccura"
                            ):
                                _state.append(_handler)
                            handler_stack.pop()
                            continue
                    elif isinstance(_handler, TryStatement):
                        if _state:
                            if _handler.end_try_pos is not None:
                                _handler.on_error_block.extend(_state)
                            else:
                                _handler.try_block.extend(_state)
                            _state = []
                        # If we've reached the end address of the try block
                        if (
                            _handler.end_try_pos is not None
                            and _curr_pos >= _handler.end_try_pos
                        ):
                            _state.append(handler_stack.pop())
                            continue
                    elif isinstance(_handler, RepeatStatement):
                        if _state and (_curr_pos <= _handler.end_repeat_pos):
                            _handler.body.extend(_state)
                            _state = []
                        # If we've reached the end address of the repeat block
                        if (
                            _handler.end_repeat_pos is not None
                            and _curr_pos >= _handler.end_repeat_pos
                        ):
                            _state.append(handler_stack.pop())
                            continue
                    elif isinstance(_handler, IfStatement):
                        # We need to keep track the end of the if block, from address in TestIf
                        # and the end of the else block, from the address in Jump
                        if _state and (_curr_pos < _handler.else_pos):
                            _handler.then_block.extend(_state)
                            _state = []
                        elif _handler.end_if_pos is not None:
                            if _state and (_curr_pos <= _handler.end_if_pos):
                                _handler.else_block.extend(_state)
                                _state = []
                            if _curr_pos == _handler.end_if_pos and _stack:
                                _handler.else_block.append(_stack.pop())
                            if _curr_pos == _handler.end_if_pos:
                                _state.append(handler_stack.pop())
                                continue
                    else:
                        if _state:
                            _handler.body.extend(_state)
                    break

                # If we are at the end of the decompilation, we should
                # attach all handlers back to the root handler
                if state["pos"] >= len(code) and len(handler_stack) > 1:
                    _state.append(handler_stack.pop())
                else:
                    break

        return handler_stack[0]

    sources = []
    for cur_function_offset in range(2, len(root)):
        try:
            ret = decompile(cur_function_offset, add_comments=add_comments)
            if ret is not None:
                sources.append(ret.to_source())
        except:
            print("-- Failed to decompile")
    print("-----")
    print("\n\n".join(sources))


def parse_args():
    parser = argparse.ArgumentParser(
        prog="applescript_decompile", description="AppleScript .scpt decompiler"
    )

    parser.add_argument("scpt", help="Path to a compiled AppleScript .scpt file")

    parser.add_argument(
        "--comments",
        action="store_true",
        help="Include comments in the decompiled output",
    )

    # Show help when no arguments at all are passed
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()


if __name__ == "__main__":
    cli()
