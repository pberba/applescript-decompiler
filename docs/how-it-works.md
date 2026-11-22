# How decompiling works

```
.scpt ──Loader──> object tree ──decompile_script──> AST ──AppleScriptPrinter──> source
       (disassembler)            (decompiler.py)          (ast.py, + analyzer)
```

1. **Load.** `jinmo_applescript_disassembler.engine.fasparser.Loader().load(path)`
   parses the file into nested Python lists and runtime objects. The result
   is the top-level script object; its last element is the script body.
2. **Decompile** (`decompiler.py`):
   - `decompile_script()` walks the script body:
     - a handler becomes a `Handler`;
     - another value becomes a `PropertyDecl`;
     - a script object becomes a `ScriptBlock`, decompiled recursively;
     - the `pimr` value becomes the `use` clauses.
   - The inner `decompile()` symbolically executes one handler's bytecode:
     - Push opcodes put expressions on a stack.
     - Operators and object specifiers build `BinaryOp`/`UnaryOp` nodes.
     - `StoreResult`, `Pop*`/`Pop*Variable` and branch ends turn the stack top
       into statements.
     - Block opcodes (`Tell`, `TestIf`, `ErrorHandler`, `Repeat*`, `Consider`,
       `BeginTimeout` and their ends or jump targets) open and close entries on
       a `block_stack`.
   - Assignments are tracked through `_var`, the pending target of the next
     statement, and `_pattern`, the pending targets of `set {a, b} to …`.
   - A statement that ends without `StoreResult` goes through
     `ending_statement()`. This happens to the last statement of a handler,
     branch or `try` body.
3. **Print** (`ast.py`). `AppleScriptPrinter` turns the AST into AppleScript:
   - Four-character codes become terms, using `EVENT_CODES` (Apple's
     terminology table in `utils.DATA`) and the bundled `.sdef`
     dictionaries in `applescript_decompiler/data/` (`SDEFS`, `ENUMERATORS`).
   - `convert_literal()` maps loaded literal values to AST nodes.
4. **Analyzers** (`analyzer.py`, `--analyzer`). An analyzer class can define
   `visit_<NodeClass>` methods. The printer calls those before its own, which
   lets an analyzer rewrite output; for example, `NaiveStringAnalyzer` folds
   `ASCII character` obfuscation. See [analyzers.md](analyzers.md).

JXA scripts skip all of this: `jxa.py` reads the source text straight out
of the file.

## Reconstructing the source

Run-only strips the syntax tree but keeps the bytecode, the literal table
and the variable names. The decompiler
rebuilds the source from those. The approach, and the write-up it follows,
are in the blog post
[Decompiling run-only AppleScripts](https://pberba.github.io/security/2025/12/14/decompiling-run-only-applescripts/).

The core idea is a **symbolic stack machine**. `decompile()` runs each
handler's bytecode the way the AppleScript VM would, but instead of
computing values it builds AST nodes:

- **Expressions.** A push puts a value on the stack; `PushLiteral` resolves
  it through the literal table. An operator pops its operands and pushes a
  node (`BinaryOp`, `UnaryOp`, `CommandCall`, …) rather than a result, so
  the whole expression is retained as a tree. Lists and records are built
  from their pushed elements and a count (`MakeVector`, `MakeRecord`).
- **Statements.** `StoreResult` ends a statement: if a `Pop*Variable` set
  the pending target just before it, the statement is a `SetStatement`,
  otherwise the top-of-stack expression stands on its own. The last
  statement of a handler or branch ends without `StoreResult`, handled by
  `ending_statement()`.
- **Blocks and control flow.** The structure of `if`/`else`, `repeat`,
  `try` and `tell` isn't stored, so it is recovered from jump and
  error-handler targets. Open blocks are tracked on a `block_stack` and
  closed when the instruction pointer reaches their end address. Because a
  `Jump` serves both loops (backward) and `if`/`else` (forward), the
  direction and the enclosing block decide which it is; `if`-`else if`-`else`
  is read as an `if` nested in the `else` branch.
- **Terminology.** Commands, parameter keywords, classes and enumerators
  are stored as four-character codes. The printer maps them back to readable
  terms with Apple's terminology table and the bundled scripting
  dictionaries (see [scripting-dictionaries.md](scripting-dictionaries.md)).

Control-flow recovery is the least certain part: when a decompiled script
recompiles to different bytecode, the mismatch is almost always here. See
[Debugging](testing.md#debugging) for how to find it.
