# Development

## Setup

The project is two Python packages in one repository:

| Package | Directory | Purpose |
| --- | --- | --- |
| `applescript-decompiler` | `applescript_decompiler/` | decompiler, printer, CLI |
| `jinmo-applescript-disassembler` | `jinmo_applescript_disassembler/` | FAS file loader, opcode table, disassembler CLI |

The disassembler is a vendored copy of
[Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler)
with bug fixes (see its `CHANGELOG.md`). `pyproject.toml` installs it from
this repository's subdirectory. Under uv, `[tool.uv.sources]` points at the
local directory instead.

```shell
# uv
uv run applescript_decompile path/to/script.scpt
uv run --with pytest pytest

# pip
pip install -e ./jinmo_applescript_disassembler -e . pytest
applescript_decompile path/to/script.scpt
python -m pytest
```

Requirements:

- Python 3.10 or later.
- macOS for anything that compiles AppleScript (`osacompile`, `osadecompile`),
  which includes most of the tests.
- Decompiling an existing file works on any OS.

## Documentation

| Document | Covers |
| --- | --- |
| [how-it-works.md](how-it-works.md) | the decompilation pipeline: load, decompile, print; how the source is reconstructed from bytecode |
| [library-usage.md](library-usage.md) | using the package as a Python library (and AEMonitor as an example consumer) |
| [analyzers.md](analyzers.md) | writing an analyzer to rewrite the output, and the AST-stability contract |
| [scripting-dictionaries.md](scripting-dictionaries.md) | adding your own `.sdef` so an app's terms resolve |
| [testing.md](testing.md) | the test suite, fixtures, and debugging a wrong decompilation |
