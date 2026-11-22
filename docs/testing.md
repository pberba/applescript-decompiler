# Testing and debugging

## Tests

```shell
uv run --with pytest pytest            # everything
uv run --with pytest pytest -k c15     # tests whose id matches
```

pytest settings are in `pyproject.toml`:

- `testpaths = ["tests"]`;
- `pythonpath` adds the checkout and `jinmo_applescript_disassembler/`, so
  nothing needs to be installed.

### `tests/test_roundtrip.py`: bytecode equivalence (macOS)

For each `tests/fixtures/*.applescript`:

1. compile it run-only: `osacompile -x`;
2. decompile it with `run_decompiler`;
3. recompile the decompiled source run-only, which must succeed;
4. compare both builds through `canonical_script()`:
   - per handler: code bytes, literals, local names, positional and labeled
     parameters, and name;
   - per script: member names and values, script objects and their parents.

The compiler does the normalising, so the test doesn't depend on output
formatting: equivalent spellings and extra parentheses compile identically.
The decompiled output does have to keep variable names, since run-only
files keep them.

**Scripts are never executed.** Fixtures may do anything, such as
`do shell script` or controlling apps, because they are only compiled.

Fixture groups:

| Prefix | Contents |
| --- | --- |
| `c01`–`c25` | one language feature each (if/else, repeat forms, try, considering, script objects, …) |
| `x01`–`x25` | regressions for specific decompiler bugs; `x22` is the demo script |
| `objc_use_*` | AppleScriptObjC (`use framework`, `current application's NSString`) |
| `e2e_*` | large realistic scripts (nested script objects, closures, ObjC, error handling); their run-only `.scpt` builds are checked in |

Markers: a fixture whose first lines are `-- test: …` gets per-fixture
options. `-- test: xfail <reason>` is a known gap. The xfail is strict, so the
test fails once the gap is fixed; remove the marker then.

Adding a fixture:

1. Write the script. It should exercise the bug and fail before the fix.
2. Format it with AppleScript's own formatter, so the fixture is what
   Script Editor would show:

   ```shell
   osacompile -o /tmp/f.scpt f.applescript && osadecompile /tmp/f.scpt > tests/fixtures/xNN_name.applescript
   ```

### `tests/test_ast_api.py`: library API (any OS)

[AEMonitor](https://github.com/pberba/AEMonitor) builds AST nodes directly
(`CommandCall`, `BinaryOp`, `Keyword`, …) and calls `.to_source()` to print
Apple Events as AppleScript. These tests pin that usage:

- constructor signatures;
- printed output;
- enum values (`BinaryOpKind.GET_INDEXED == 16`, …).

New enum members go at the end.

### `tests/test_jxa.py`: JXA extraction

- The checked-in run-only build `tests/fixtures/jxa/*.scpt` must yield its
  `.js` source (any OS).
- Fresh `.scpt` and `.scptd` builds, and the CLI output, are checked on macOS.

## Debugging

- `applescript_decompile -d script.scpt` prints the disassembly while
  decompiling. `-c` adds per-instruction comments to the output.
- `applescript_disassemble script.scpt` prints the disassembler's listing.
- The decompiled source goes to stdout; warnings go to stderr.
  `-v`/`--verbose` also prints header comments to stderr: the path, each
  handler's signature (`-- Function: name(args)`) and properties, which
  show how far decompiling got. `applescript_decompile -v x.scpt >
  x.applescript` writes only the source; add `2> diag.txt` to keep the
  diagnostics.
- To find what a decompiled script gets wrong, recompile it with
  `osacompile -x`. Then compare the two disassemblies handler by handler;
  the first differing instruction is usually the bug.
- `-f`/`--force` keeps decompiling the remaining handlers after an error.
