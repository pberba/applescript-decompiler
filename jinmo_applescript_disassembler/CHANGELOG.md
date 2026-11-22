# Changelog

## 0.2.0 (2026-11-21)

Bug fixes needed by the decompiler (`applescript_decompiler`).

### Loader (`engine`)

- **Scripts with script objects load without "RefID doesn't match"
  errors.** A script object's parent slot points back at its enclosing
  script. Value blocks (`valueblock.py`) and untyped pointer blocks
  (`untyped_pointer_block.py`) were only registered in the ref table after
  their children loaded, so that back-reference couldn't be resolved and
  the script's handlers were lost. The container is now registered first,
  and `TInferiorRefList.doLoad()` (`util.py`) fills the registered list
  in place.
- **Raw data values load.** A literal such as `«data rdat01020304»`, or
  any data block that isn't an application alias, crashed: the `@value`
  decorator (`runtimeobjects.py`) registered itself instead of the class,
  and there was no class for raw data. Ported from upstream
  [eea89bc](https://github.com/Jinmo/applescript-disassembler/commit/eea89bc),
  which also makes an unknown type raise a clear `ValueError`.
- **Data over 64 KB loads.** Long data blocks (object type 18) crashed
  with `NameError`: `long_data_block.py` called `parse_value` without
  importing it (upstream has the same bug).

### Disassembler (`disassembler.py`)

- **The listing no longer goes out of sync.** These opcodes have a 2-byte
  operand that was not consumed, so the operand bytes were decoded as
  instructions: `RepeatInCollection`, `Consider`, `Of`, `MatchLiteral`,
  `BeginTransaction`, `DefineProcedure`, `DefineClosure`,
  `DefineProperty`, `Continue` and `PositionalContinue`. The `Define*` and
  `Continue` operands are literal indices and are printed with their
  literal.
- Branch targets (`Jump`, `TestIf`, `And`, `Or`, `ErrorHandler`,
  `EndErrorHandler`) are computed explicitly as `opcode position + 1 +
  offset`.

## 0.1.0

- Clone of [Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler),
  packaged so it can be imported (`jinmo_applescript_disassembler`) and
  installed with an `applescript_disassemble` command.
