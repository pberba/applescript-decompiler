"""Loader (FasLoadTable) behaviour on hand-built object streams (any OS).

osacompile doesn't produce these streams, so the input is built in memory:
an object header is an index byte, a signed 16-bit RefID and a 16-bit
"inlined" field.
"""

import contextlib
import io
import struct

from jinmo_applescript_disassembler.engine import fasparser as F


def table(data):
    loader = F.Loader()
    loader.f = io.BytesIO(data)
    loader.bigEndian = True
    loader.stack = F.Stack()
    t = F.FasLoadTable.__new__(F.FasLoadTable)
    t.loader = loader
    t.depth = 0
    t.refTable = [(F.NIL, 2)] * 32
    with loader.context(t) as context:
        context.reuseHeader = False
        context.refErrors = []
    return t


def header(index, ref, inlined=0):
    return struct.pack(">BhH", index, ref, inlined)


def test_refid_errors_go_to_stderr():
    # the stream holds RefID 7 where RefID 5 is expected
    t = table(header(3, 7, 1))
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        t.loadObject(5)
    assert out.getvalue() == ""  # stdout carries the decompiled source
    assert "RefID doesn't match" in err.getvalue()
