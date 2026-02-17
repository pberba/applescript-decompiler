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

AppleScript .scpt decompiler

positional arguments:
  scpt                 Path to a compiled AppleScript .scpt file

options:
  -h, --help           show this help message and exit
  -c, --comments       Include comments in the decompiled output
  -f, --force          Recursively traverse to find handlers to force handlers to come out and ignore errors
  -d, --debug          Prints out the disassembled code while decompiling
  --analyzer ANALYZER  Dotted path to analyzer class like applescript_decompiler.OSAMinerDecryptAnalyzer, applescript_decompiler.NaiveStringAnalyzer, or local.MyAnalyzer (for a file in local.py)

```

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

