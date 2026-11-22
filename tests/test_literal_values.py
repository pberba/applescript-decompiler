"""Literal values osacompile can't produce here (any OS): built in memory.

Office apps define enumerators whose code isn't text, and old Script Editor
files store styled text; neither can be compiled without those apps.
"""

import jinmo_applescript_disassembler.engine.runtimeobjects as rto
from jinmo_applescript_disassembler.engine.util import opcodes

from applescript_decompiler.decompiler import decompile_script


def returns(literal):
    """Decompile `return <literal>` (the literal is literal 0)."""
    code = bytes([opcodes.index("PushLiteral"), opcodes.index("Return")])
    handler = [16, b"f", rto.NIL, rto.NIL, rto.NIL, [], [literal], rto.String(code)]
    return decompile_script([rto.NIL, [b"f"], handler], []).to_source()


def test_enumerator_with_binary_code():
    # an Office save-format enumerator: enumeration 'e188', value 0x02BC0039
    value = int.from_bytes(b"e188\x02\xbc\x00\x39", "big")
    source = returns(rto.Object(rto.Constant(value)))
    assert "«constant e188 0x02BC0039»" in source, source  # no raw control bytes


def test_styled_text_literal():
    # old Script Editor files store text as styled text: MacRoman bytes + a style
    source = returns(rto.Object(rto.UnicodeText(b"caf\x8e /tmp/example", b"\x00\x00")))
    assert '"café /tmp/example"' in source, source  # (a final `return x` prints as `x`)
