# AppleScript Decompiler

This decompiles run-only applescript. This is built on top of [Jinmo/applescript-disassembler](https://github.com/Jinmo/applescript-disassembler)

### Installation

```shell
git clone https://github.com/pberba/applescript-decompiler
cd applescript-decompiler

python3 -m venv venv
venv/bin/pip install .
```

### Usage

#### Decompiler

```shell
applescript_decompile <scpt> [--comments]
```

`--comments`: adds the disassembled code as comments

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