# AppleScript Decompiler

This decompiles run-only applescript. This is built on top of [Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler). See my [blog post for more details](https://pberba.github.io/security/2025/12/14/decompiling-run-only-applescripts/)

### Installation

#### pip

```shell
pip install git+https://github.com/pberba/applescript-decompiler
```

#### uv

```shell
git clone https://github.com/pberba/applescript-decompiler
cd applescript-decompiler

uv run sync
# uv run applescript_decompile ...
```

### Usage

#### Decompiler

```shell
usage: applescript_decompile [-h] [-c] [-f] [-d] [--analyzer ANALYZER] scpt

AppleScript .scpt decompiler (also extracts the source of JXA scripts)

positional arguments:
  scpt                 Path to a compiled .scpt file (AppleScript or JXA), or a .scptd/.app bundle

options:
  -h, --help           show this help message and exit
  -c, --comments       Include comments in the decompiled output
  -f, --force          Ignore errors and keep decompiling the remaining handlers
  -d, --debug          Prints out the disassembled code while decompiling
  --analyzer ANALYZER  Dotted path to analyzer class like applescript_decompiler.OSAMinerDecryptAnalyzer, applescript_decompiler.NaiveStringAnalyzer, or local.MyAnalyzer (for a file in local.py)

```

#### JXA

A compiled JavaScript for Automation script (`osacompile -l JavaScript`, even
with `-x`) is not bytecode: the file stores the original JavaScript source as
text. Nothing needs to be decompiled, so the tool reads the source directly
from the file and prints it as is. The AppleScript options (`--analyzer`,
`--comments`, `--force`, `--debug`) don't apply to JXA scripts. `.scptd` and
`.app` bundles are accepted for both languages (the script is
`Contents/Resources/Scripts/main.scpt`).

#### Demo

Compile demo script to be run-only
```
osacompile -x -o demo/demo_runonly.scpt demo/demo_source.applescript
```

Validate that there is no source
```
osadecompile demo/demo_runonly.scpt
# osadecompile: demo/demo_runonly.scpt: errOSASourceNotAvailable (-1756).
```

Decompile output
```
applescript_decompile demo/demo_runonly.scpt > demo/demo_output.out
```


### Tests

The tests need macOS (`osacompile`). Each script in `tests/fixtures` is
compiled run-only and decompiled; the decompiled source, recompiled run-only,
must produce the same bytecode, literals and names as the original (comments,
formatting and parentheses don't matter). Nothing is executed, so fixtures may
have side effects.

```
uv run --with pytest pytest
```

A fixture can start with `-- test: xfail <reason>` (known decompiler gap;
remove the marker once fixed).
Format new fixtures with AppleScript's own formatter:
`osacompile -o /tmp/f.scpt f.applescript && osadecompile /tmp/f.scpt > f.applescript`.
