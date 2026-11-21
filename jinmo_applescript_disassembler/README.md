# AppleScript disassembler

A disassembler for run-only (compiled) AppleScript files. It is
[Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler)
by Jinmo, vendored here as the loader and opcode table for
[applescript-decompiler](https://github.com/pberba/applescript-decompiler).

## Changes from upstream

This copy:

- **is packaged** as `jinmo_applescript_disassembler`, so it can be imported
  and installed, with an `applescript_disassemble` command;
- **fixes loader bugs**: scripts that contain script objects (whose parent
  refers back to the enclosing script) failed with "RefID doesn't match"
  and lost their handlers;
- **fixes disassembly bugs**: several opcodes' 2-byte operands were not
  consumed, which threw the rest of the listing out of sync.

See [CHANGELOG.md](CHANGELOG.md) for details.

## Usage

```shell
applescript_disassemble path/to/script.scpt
```

```python
from jinmo_applescript_disassembler.engine.fasparser import Loader

root = Loader().load("script.scpt")  # the top-level script object
```

The opcode names are in `engine/util.py` (`opcodes`, indexed by opcode
byte). The decompiler's `docs/file-formats.md` describes the file format and
the loaded object tree.
