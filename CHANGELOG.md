# Changelog

## 2.0.1 (2026-11-24)

Bug fixes. Each fix has a test script that failed before it.

### Fixed

Output that compiled to a different script, or didn't compile:

- **Event handlers.** `on run argv` and `on open theFiles` keep their
  direct parameter. Standard Additions handlers are named
  (`on open location theURL`, `on adding folder items to f after
  receiving theItems`) instead of printed as raw codes.
- **Handler labels.** Prepositional labels are written directly
  (`on rangeSum from a thru b`, `rangeSum from 1 thru 4`), not after
  `given`.
- **Terminology.** `running` and the `progress` properties are named;
  enumerators are named by their enumeration (`path to desktop folder
  from user domain`), including codes written in hex (`with icon
  caution`); `make … at end` works for apps whose dictionary doesn't
  define `make` (System Events).
- **Values.** References the compiler builds from constants
  (`class of "x"`) and styled text literals from old Script Editor files
  are no longer dropped.
- **Crashes** on `set result to …` and on enumerator codes that aren't
  text (Office's `'e188' + 0x02BC0039`). With no dictionary for such a
  code it prints as `«constant e188 0x02BC0039»`, which AppleScript can't
  compile; add the app's sdef to `APPLESCRIPT_DECOMPILER_SDEF_DIR` to get
  the term.

### Disassembler

The vendored disassembler is now 0.2.1: RefID errors go to stderr, and
back-references to integers, reals, booleans, styled text and
identifiers resolve. See
[jinmo_applescript_disassembler/CHANGELOG.md](jinmo_applescript_disassembler/CHANGELOG.md).
The dependency on it is pinned to the `v2.0.1` tag.

## 2.0.0 (2026-11-21)

Decompiled run-only AppleScripts now compile, and recompile to the same
bytecode as the original.

- **Valid AppleScript.** Statements, precedence, string escapes,
  terminology and declarations are reconstructed so the output compiles
  as is.
- **Round-trip tested.** 57 test scripts, from single language features
  to large AppleScriptObjC programs, are compiled run-only, decompiled and
  recompiled; both builds must have the same bytecode, literals and names.
  Test scripts are only compiled, never run.
- **Real variable names.** Run-only scripts still store their variable
  names, and the output now uses them instead of `[var_N]`.
- **AppleScriptObjC.** `use framework` clauses, `current application's …`
  calls, ObjC method calls, and script objects with inheritance.
- **JXA.** Compiled JavaScript for Automation keeps its source, even when
  compiled run-only, so it is extracted rather than decompiled.
- **Docs.** `AGENTS.md` and a `docs/` folder for contributors and library
  users.

### Breaking changes

- **stdout is only the decompiled source.** The header comments (path,
  handler signatures, properties, the `-----` separator) are hidden by
  default; `-v`/`--verbose` prints them to stderr. Warnings and the `-d`
  trace also go to stderr. `applescript_decompile x.scpt > x.applescript`
  writes a script that compiles as is. Tooling that split stdout on
  `-----` should read stdout directly, or call `run_decompiler()`, which
  now returns the source.
- **`--force` only means "ignore errors".** It used to also make the
  decompiler recurse into script objects; script objects are now always
  decompiled.
- **`convert_literal()` returns `VariableRef` for identifiers.** Record
  labels and property names (stored as bytes) were returned as
  `StringLiteral`, which printed them as quoted strings.

### Added

- **JXA scripts.** Compiled JavaScript for Automation files (even
  run-only) store their source, which is now printed as is.
- **Bundles.** `.scptd` and `.app` paths are accepted for both languages.
- **Script objects**: top level, nested, and defined inside handlers,
  including their properties, run code and `property parent`.
- **Language features** that were dropped, crashed or printed wrongly:
  - blocks: `considering`/`ignoring`, `with timeout`, `use` clauses
    (AppleScriptObjC frameworks), `continue name(...)`
  - handlers: labeled parameters (`on greet given name:n` and
    `greet given name:"bob"`), the variables of
    `on error msg number n from f partial result p to t`
  - declarations: `property`, `global` (for globals used outside `run`)
    and `local`, in declaration order
  - specifiers: `whose` clauses, `beginning of`, `middle`, `some`,
    `before`/`after`, `id`/`named` key forms, `item 2 thru 4 of L`
  - operators: `div`, `starts with`, `ends with`
  - values: negative and long integers, reals, booleans, records, empty
    lists, `copy x to y`, `a reference to`, stored references,
    destructuring (`set {a, b} to L`), raw data (`«data rdat01020304»`)
- **Terminology:** enumerated values (`rounding as taught in school`) and
  Standard Additions terms (`port`) are named instead of printed as raw
  codes.
- **`APPLESCRIPT_DECOMPILER_SDEF_DIR`:** directories of extra `.sdef`
  files, loaded after the bundled dictionaries.
- **Tests:** round-trip bytecode tests (macOS), AST library API tests,
  and JXA extraction tests. Fixtures are only compiled, never run.
- **Docs:** `AGENTS.md`, and `docs/` covering setup, how decompiling
  works, library usage, analyzers, scripting dictionaries and testing.

### Fixed

Output that compiled to a different script, or didn't compile:

- **Names.** Variables keep the names stored in the script instead of
  `[var_N]`; parent variables resolve to properties; identifiers that
  aren't plain or clash with terms are barred (`|weird name|`, `|length|`,
  in definitions too); `me`, `my` and `its` are printed where each
  applies.
- **Lost statements.** A handler's, `else` branch's, `try` body's or
  `on error` block's last assignment; the implicit result of a handler,
  no longer turned into `return`; the value of an explicit `return f()`;
  the `else` branch and everything after an `if` whose then-branch ends
  in a loop; expressions inside loops that use `Dup` (e.g.
  `items i thru (i + 2) of L`).
- **Precedence and syntax.** Nested operators, `thru` bounds and `of`
  containers are parenthesised; the compiler's own `as boolean` in
  `and`/`or` is dropped; `error` is printed as a statement; handlers
  without parameters get `()`; a labeled call used as an argument is
  parenthesised.
- **Literals.** Strings use AppleScript's escapes (`\"`, `\\`, `\n`, `\t`,
  `\r`) instead of JSON's `\uXXXX`; application literals print as
  `application "Name"`, including names with spaces.
- **Terminology.** The first definition of a code wins (not a plural or
  synonym); commands use their own parameter names (`make new folder at
  x`, not `make each folder to x`); Standard Additions parameter names no
  longer leak into other contexts.
- **Crashes** on `error 5`, bare `error`, `error "msg" number n`, labeled
  handler calls, handler calls on an object specifier, `whose` clauses,
  record values and data over 64 KB.
- **Malformed files.** Literal and variable indices of 0x8000 and above
  are read as unsigned, as AppleScript does; they were read as negative
  and silently resolved to the wrong literal.
- **Diagnostics** are readable: one `-- Function: name(args)` line per
  handler, `-- property name` for properties.

### Disassembler

The vendored disassembler is now 0.2.0: it loads scripts that contain
script objects, and its listing no longer goes out of step on opcodes
with operands. See
[jinmo_applescript_disassembler/CHANGELOG.md](jinmo_applescript_disassembler/CHANGELOG.md).

The dependency on it is now pinned to the `v2.0.0` tag. It used to follow
`main`, so an install of any other revision could pair the decompiler with
a disassembler it doesn't work with.

## 1.0.2 and earlier

See the `v1.0.1` and `v1.0.2` tags.
