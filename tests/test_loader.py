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


def immediate_then_backref(index, ref, inlined, body=b""):
    """An object with RefID `ref`, then nothing: a second lookup of `ref`
    must come from the ref table, not from the (empty) rest of the stream."""
    t = table(header(index, ref, inlined) + body)
    t.findObject(ref)
    first = t.loader.stack.pop()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        t.findObject(ref)
    return first, t.loader.stack.pop()


def test_back_reference_to_integer():
    first, again = immediate_then_backref(3, 5, 7)
    assert repr(again) == repr(first)  # not NIL


def test_back_reference_to_boolean():
    first, again = immediate_then_backref(9, 6, 1)
    assert again is True and first is True


def test_back_reference_to_real():
    first, again = immediate_then_backref(8, 9, 8, struct.pack(">d", 0.1))
    assert again == first == 0.1


def test_back_reference_to_class_constant():
    # code identifier, kind 10: a 4-byte class code ('ctxt')
    first, again = immediate_then_backref(10, 11, 4, bytes([10]) + b"ctxt")
    assert repr(again) == repr(first)
