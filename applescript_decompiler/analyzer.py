from applescript_decompiler.ast import *


class AbstractAnalyzer:
    printer: AppleScriptPrinter = None

    def __init__(self, printer: AppleScriptPrinter):
        self.printer = printer


class NaiveStringAnalyzer(AbstractAnalyzer):

    # This looks for numbers that are ASCII printable and converts them into characters
    # Also converts (ASCII Character X ) to character
    def visit_NumberLiteral(self, node: NumberLiteral, indent=0):
        n = node.value
        if 32 <= n <= 126:
            return f'"{chr(n)}"'
        return self.printer.visit_NumberLiteral(node, indent)

    # If all elements in the list are 1 character strings, then concat
    def visit_ListLiteral(self, node: ListLiteral, indent=0):
        elems = [self.printer.visit(e, 0) for e in node.elements]

        if all([('"' in e and len(e.strip('"') == 1) for e in elems)]):
            elems = "".join(e.strip('"') for e in elems)
            return '{ "' + elems + '" }'

        elems = ", ".join(elems)
        return "{" + elems + "}"

    # Parse out ASCII character (which is implemented as a command call)
    def visit_CommandCall(self, node: CommandCall, indent=0):
        # Use built-in resolver to convert codes to readable strings
        ret = self.printer.visit_CommandCall(node, indent)
        if "ASCII character" in ret and '"' in ret:
            # Example: (ASCII character "/")
            # Note that because we already converted the number
            # literal, we are now dealing with just characters
            return '"' + ret.split('"')[1] + '"'
        return ret

    # If both left and right parts of the CONCAT look kinda like strings
    # just concatenate the strings ?
    def visit_BinaryOp(self, node: BinaryOp, indent=0):
        if node.op != BinaryOpKind.CONCAT:
            return self.printer.visit_BinaryOp(node, indent)

        l = self.printer.visit(node.left, 0)
        r = self.printer.visit(node.right, 0)

        # Naive string checking
        def is_string(s):
            return s[0] == '"' and s[-1] == '"' and " & " not in s

        if is_string(l) and is_string(r):
            return f'"{l.strip('"')}{r.strip('"')}"'

        return f"{l} & {r}"


class OSAMinerDecryptAnalyzer(AbstractAnalyzer):
    # This looks for non printable strings and assumes that this needs to be
    # decrypted with the `d` function
    def visit_StringLiteral(self, node: StringLiteral, indent=0):
        if node.value.isascii():
            return self.printer.visit_StringLiteral(node, indent=indent)
        return "\"" + "".join(chr(ord(ch) - 100) for ch in node.value) + "\""
