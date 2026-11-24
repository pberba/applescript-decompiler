# AGENTS.md

A decompiler for run-only (compiled, source-stripped) AppleScript `.scpt`
files, written in Python. It also extracts the source of JXA (JavaScript for
Automation) scripts, which keep it in the file.

More detail:

- [docs/development.md](docs/development.md): setup and an index to the rest
  of the docs (how it works, library usage, analyzers, scripting
  dictionaries, testing).

## Layout

```
applescript_decompiler/        the decompiler (package: applescript-decompiler)
  decompiler.py                bytecode -> AST, CLI (`applescript_decompile`)
  ast.py                       AST nodes, AppleScript printer, literal conversion
  analyzer.py                  optional printer overrides (deobfuscation helpers)
  jxa.py                       JXA detection/extraction, .scptd/.app bundle paths
  utils.py                     Apple event code tables, .sdef loading
  data/*.sdef                  bundled app dictionaries (command/parameter names)
jinmo_applescript_disassembler/ vendored FAS loader + opcode table (own package,
                               own CHANGELOG.md and setup.py version)
tests/                         pytest suite; fixtures in tests/fixtures
demo/                          demo source, its run-only build, decompiled output
```

## Setup and commands

Python 3.10+. Most tests and anything that compiles AppleScript need macOS
(`osacompile`, `osadecompile`).

```shell
uv run --with pytest pytest                      # all tests
uv run --with pytest pytest -k x24               # one fixture
uv run applescript_decompile demo/demo_runonly.scpt
```

Without uv: `pip install -e ./jinmo_applescript_disassembler -e . pytest`.
pytest needs no install: `pyproject.toml` puts the checkout and the vendored
package on `sys.path`.

## Tests

- `tests/test_roundtrip.py` (macOS): each `tests/fixtures/*.applescript` is
  compiled run-only, decompiled, recompiled, and compared **as bytecode**
  (code bytes, literals, local names, parameters, properties) with the
  original. Comments, whitespace and parentheses don't matter; a wrong
  operator, a lost statement or a renamed variable does.
- **Never run fixtures or decompiled scripts.** Fixtures may have side
  effects; the tests only compile.
- **No malware-like content in tests, fixtures or docs**, not even inert or
  encoded: EDR on the machine of anyone who clones or tests the repo could
  flag it. Test obfuscation techniques (ciphers, `character id`, text item
  delimiters, decoder handlers, `run script` stages) with harmless payloads
  (`echo`, `/tmp` paths, `.invalid` URLs). No password prompts, credential or
  keychain access, uploads, download-and-run, persistence or sandbox checks.
  Keep real samples outside the repo.
- `tests/test_ast_api.py`: the AST is used as a library
  ([AEMonitor](https://github.com/pberba/AEMonitor) builds nodes and calls
  `.to_source()`). Keep that API and its printed output stable.
- `tests/test_jxa.py`: JXA extraction from checked-in and fresh builds.

Every decompiler fix gets a fixture that fails without it. Format new
fixtures with AppleScript's own formatter:

```shell
osacompile -o /tmp/f.scpt f.applescript && osadecompile /tmp/f.scpt > tests/fixtures/f.applescript
```

A known, not yet fixed gap is marked with a first line
`-- test: xfail <reason>`. It is strict, so remove the marker once the gap
is fixed.

## Conventions

- **Keep changes minimal.** Fix bugs as small patches on the existing code
  structure. Don't reorganise or rewrite functions unless the fix needs it.
  Make one commit per fix, with its fixture.
- **Keep enum values stable.** Add new `BinaryOpKind`/`UnaryOpKind` members at
  the end; their values appear in node reprs used by library users.
- **Disassembler changes** go in `jinmo_applescript_disassembler/CHANGELOG.md`.
  Bump its `setup.py` version on release.
- **Regenerate the demo** after output changes:
  `applescript_decompile demo/demo_runonly.scpt > demo/demo_output.out`.
  The output must still recompile to the original bytecode.
- **Print valid AppleScript.** The output must compile. Bar identifiers that
  clash with terms (`|name|`, `|count|`) and parenthesise where AppleScript's
  parser would bind differently.
