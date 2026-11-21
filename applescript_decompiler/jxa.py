"""JavaScript for Automation (JXA) scripts.

A compiled JXA script is not bytecode: it is the JavaScript source text in
a binary plist ({"script": <source>}) between a 16-byte header and the OSA
trailer:

    "JsOsaDAS1.001.00" | bplist | "jscr" 00 01 <u16 trailer size> FA DE DE AD

The trailer size includes any padding before "jscr". Compiling run-only
(`osacompile -l JavaScript -x`) produces the same file, so the source can
always be recovered.
"""

import os
import plistlib
import struct

JXA_MAGIC = b"JsOsaDAS"
OSA_TRAILER_END = b"\xfa\xde\xde\xad"


def resolve_script_path(path):
    """Return the compiled script inside a .scptd/.app bundle, or `path`."""
    if os.path.isdir(path):
        main = os.path.join(path, "Contents", "Resources", "Scripts", "main.scpt")
        if os.path.isfile(main):
            return main
    return path


def is_jxa(path):
    with open(resolve_script_path(path), "rb") as f:
        return f.read(len(JXA_MAGIC)) == JXA_MAGIC


def extract_jxa_source(path):
    """Return the JavaScript source of a compiled JXA script."""
    with open(resolve_script_path(path), "rb") as f:
        data = f.read()
    if not data.startswith(JXA_MAGIC):
        raise ValueError("not a compiled JXA script")
    end = len(data)
    if data.endswith(OSA_TRAILER_END) and len(data) >= 16 + 8:
        (trailer_size,) = struct.unpack(">H", data[-6:-4])
        end -= trailer_size
    plist = plistlib.loads(data[16:end])
    return plist["script"]
