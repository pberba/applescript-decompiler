"""Index operands are unsigned 16-bit words (any OS).

AppleScript's bytecode handlers (BCPushLiteralExtended, BC*VariableExtended,
...) read index operands with an unsigned load, so 0x8000 is literal 32768.
osacompile overflows long before a handler has that many literals, so the
handler is built in memory instead of compiled from a fixture.
"""

import jinmo_applescript_disassembler.engine.runtimeobjects as rto
from jinmo_applescript_disassembler.engine.util import opcodes

from applescript_decompiler.decompiler import decompile_script


def text(s):
    return [177, rto.String(s.encode("utf-16-be"))]  # Unicode text literal


def test_extended_literal_index_is_unsigned():
    literals = [text("wrong")] * 0x8001
    # read as signed, 0x8000 is -32768, i.e. index 1 of 0x8001 literals
    literals[0x8000] = text("right")
    code = bytes([opcodes.index("PushLiteralExtended"), 0x80, 0x00, opcodes.index("Return")])
    handler = [16, b"f", rto.NIL, rto.NIL, rto.NIL, [], literals, rto.String(code)]

    source = decompile_script([rto.NIL, [b"f"], handler], []).to_source()

    assert '"right"' in source, source
    assert '"wrong"' not in source, source
