# Library usage (advanced)

Besides the `applescript_decompile` CLI, the package can be used as a Python
library. There are two independent entry points: decompiling a compiled
file, and using the AST and its printer on their own.

## Decompile a file

`decompile_script()` returns a `Script` AST node; `.to_source()` renders it
as AppleScript.

```python
from jinmo_applescript_disassembler.engine.fasparser import Loader
from applescript_decompiler.decompiler import decompile_script

tree = Loader().load("script.scpt")   # the top-level script object
script = decompile_script(tree[-1], [])   # tree[-1] is the script body
source = script.to_source()           # -> AppleScript as a string
```

- `Loader().load(path)` parses the compiled file into the nested object
  tree. The last
  element of the top-level object is the script body, which is what
  `decompile_script()` takes; the second argument is the list of enclosing
  scopes, empty for a top-level script.
- Pass `analyzer=MyAnalyzer` to `to_source()` to post-process the output
  (see [analyzers.md](analyzers.md)).
- `decompile_script()` prints only warnings (to stderr) as it runs;
  `to_source()` returns the reconstructed source. `run_decompiler(tree)`
  does both steps, prints the source to stdout and returns it. To also get
  the header comments the CLI's `-v` prints (handler signatures,
  properties), set `applescript_decompiler.decompiler.VERBOSE = True`.

For JavaScript for Automation, there is no bytecode to decompile — read the
stored source directly:

```python
from applescript_decompiler.jxa import is_jxa, extract_jxa_source

if is_jxa("script.scpt"):
    source = extract_jxa_source("script.scpt")   # the JavaScript source
```

Both accept a `.scptd`/`.app` bundle as well as a bare `.scpt`.

## Use the AST to render Apple Events

The AST (`applescript_decompiler.ast`) and its printer are useful on their
own, without decompiling anything: build nodes and call `.to_source()` to
turn a raw Apple Event into readable AppleScript.
[AEMonitor](https://github.com/pberba/AEMonitor), which observes Apple
Events at runtime, uses the package this way — it constructs `CommandCall`,
`BinaryOp`, `Keyword`, … nodes from the events it sees and prints them.

```python
from applescript_decompiler.ast import (
    BinaryOp, BinaryOpKind, CommandCall, Keyword, StringLiteral, VariableRef,
)

# `get name extension of document file "a.png" of folder "Downloads"
#  of startup disk`, sent to Finder (four-character codes as captured)
def indexed(cls, key, container):
    node = BinaryOp(op=BinaryOpKind.GET_INDEXED, left=Keyword(cls), right=key)
    return BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=node, right=container)

ref = BinaryOp(
    op=BinaryOpKind.GET_PROPERTY,
    left=Keyword("nmxt"),
    right=indexed("docf", StringLiteral("a.png"),
                  indexed("cfol", StringLiteral("Downloads"), Keyword("sdsk"))),
)
src = CommandCall(
    target=VariableRef(name="Finder"), command_name="coregetd", arguments=[ref]
).to_source()
# '(tell application "Finder" coregetd (name extension of (document file
#   "a.png" of (folder "Downloads" of startup disk))))'
```

The printer resolves four-character codes to terms through the bundled
scripting dictionaries, so the `target` name must match an app with a known
dictionary (see [scripting-dictionaries.md](scripting-dictionaries.md)); an
unknown app prints the raw codes.

> This AST surface is a supported API. Its node classes, fields, enum values
> and printed output are pinned by `tests/test_ast_api.py`; see the stability
> note in [analyzers.md](analyzers.md#writing-an-analyzer) before changing
> any of them.
