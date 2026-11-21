# Changelog

## 0.2.0 (2026-11-21)

Bug fixes needed by the decompiler (`applescript_decompiler`).

### Loader (`engine/fasobjects`)

- **Scripts with script objects load without "RefID doesn't match"
  errors.** A script object's parent slot points back at its enclosing
  script. Value blocks (`valueblock.py`) and untyped pointer blocks
  (`untyped_pointer_block.py`) were only registered in the ref table after
  their children loaded, so that back-reference couldn't be resolved and
  the script's handlers were lost. The container is now registered first,
  and `TInferiorRefList.doLoad()` (`util.py`) fills the registered list
  in place.

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
