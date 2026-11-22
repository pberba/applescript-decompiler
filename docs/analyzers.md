# Writing an analyzer

An **analyzer** rewrites the printed output without touching the decompiler.
It is the hook for deobfuscation and post-processing: folding
`ASCII character` string obfuscation, decrypting string literals, defanging
IOCs, and so on.

An analyzer is a subclass of `analyzer.AbstractAnalyzer` that defines
`visit_<NodeClass>` methods. When `AppleScriptPrinter.visit()` is about to
print a node, it first checks whether the analyzer has a method named
`visit_` + the node's class name; if so, it calls that **instead** of its
own. The analyzer gets the printer as `self.printer`, so a method can defer
to the default rendering (`self.printer.visit_<NodeClass>(node, indent)`) or
to any child (`self.printer.visit(child, 0)`) and rewrite the result.

```python
# local.py, in the directory you run the command from
from applescript_decompiler.analyzer import AbstractAnalyzer
from applescript_decompiler.ast import NumberLiteral


class MyAnalyzer(AbstractAnalyzer):
    def visit_NumberLiteral(self, node: NumberLiteral, indent=0):
        # render printable byte values as characters
        if 32 <= node.value <= 126:
            return f'"{chr(node.value)}"'
        return self.printer.visit_NumberLiteral(node, indent)
```

Run it with a dotted path:

```shell
applescript_decompile -x --analyzer local.MyAnalyzer script.scpt
```

`--analyzer` takes the two built-ins by name (`NaiveStringAnalyzer`,
`OSAMinerDecryptAnalyzer`, in `analyzer.py`) or any dotted path. A path
like `local.MyAnalyzer` imports `MyAnalyzer` from `local.py` in the current
directory, so you can keep one-off analyzers out of the package.

> **Keep the AST and its printed output stable.** Analyzers, and the
> library consumer [AEMonitor](https://github.com/pberba/AEMonitor), are
> coupled to the AST: the node class names (which select `visit_*` methods),
> the node fields, the `BinaryOpKind`/`UnaryOpKind` values (they appear in
> node reprs), and the exact strings the printer returns. Renaming a node,
> changing a `visit_*` method's output, or reordering an enum **silently
> breaks** every analyzer and downstream user — nothing in this repo will
> fail. `tests/test_ast_api.py` pins this surface; run it after any AST or
> printer change, add new enum members at the end, and treat a diff in its
> expected output as a breaking change, not a test to update lightly.
