# Changelog

## 0.2.1 (2026-11-24)

Bug fixes needed by the decompiler (`applescript_decompiler`).

### Loader (`engine`)

- **RefID errors go to stderr.** `FasLoadTable.loadObject()` printed
  "RefID doesn't match" to stdout, mixing it into the decompiled source
  and into tools that write results to stdout.
- **Back-references to immediates and identifiers resolve.** Integers,
  reals, booleans, styled text, code identifiers and user identifiers
  (object types 3, 7, 8, 9, 10, 11, 12) were never put in the ref table, so
  a later reference to one of them by RefID missed: the loader read the
  next object instead, reported "RefID doesn't match" and used `nil`
  (`delay 0.1` decompiled as `(delay )`, or the load failed with "Too many
  RefID errors"). `loadObjectBody()` now registers any object that carries
  a RefID and isn't registered yet.

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
- **Literal indices are unsigned.** AppleScript reads index operands with
  an unsigned 16-bit load, but `word()` sign-extends (as branch offsets
  need), so an index of 0x8000 or more wrapped to the wrong literal.
  Upstream [c360685](https://github.com/Jinmo/applescript-disassembler/commit/c360685)
  prints such indices as `[L-n]`; here they resolve to their literal.

## 0.1.0

- Clone of [Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler),
  packaged so it can be imported (`jinmo_applescript_disassembler`) and
  installed with an `applescript_disassemble` command.
