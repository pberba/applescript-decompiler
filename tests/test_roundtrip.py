"""Round-trip tests for the run-only decompiler (macOS only).

For every fixture in tests/fixtures:

1. compile it run-only (`osacompile -x`) and decompile it;
2. **bytecode equivalence**: recompile the decompiled source run-only and
   compare both scripts handler by handler (code bytes, literals, local
   names, parameters, properties). The compiler does the normalising, so
   comments, whitespace, parentheses and equivalent spellings don't matter,
   while a wrong operator, a lost statement or a renamed variable does;
3. **run output**: run the original and the decompiled script with
   `osascript` and compare what they print.

The e2e_* fixtures are larger, realistic scripts (AppleScriptObjC, nested
script objects, closures, error handling); their run-only builds are kept
next to them as .scpt files for manual use.

Fixtures can start with marker lines:
  -- test: no-run           skip the run-output test (talks to other apps,
                            shows dialogs)
  -- test: xfail <reason>   known decompiler gap. Strict for the bytecode
                            test: remove the marker once the gap is fixed.
"""

import contextlib
import io
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="needs osacompile/osascript")

import jinmo_applescript_disassembler.engine.runtimeobjects as rto  # noqa: E402
from jinmo_applescript_disassembler.engine.fasobjects.data_block import Descriptor  # noqa: E402
from jinmo_applescript_disassembler.engine.fasparser import Loader  # noqa: E402

from applescript_decompiler.decompiler import run_decompiler  # noqa: E402

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.applescript"))


def markers(src: Path) -> dict:
    found = {}
    for line in src.read_text().splitlines():
        if not line.startswith("-- test: "):
            break
        key, _, reason = line[len("-- test: "):].partition(" ")
        found[key] = reason
    return found


def cases(strict, runnable_only=False):
    out = []
    for src in FIXTURES:
        m = markers(src)
        if runnable_only and "no-run" in m:
            continue
        marks = [pytest.mark.xfail(reason=m["xfail"], strict=strict)] if "xfail" in m else []
        out.append(pytest.param(src, id=src.stem, marks=marks))
    return out


def osacompile_runonly(src: Path, out: Path) -> Path:
    r = subprocess.run(["osacompile", "-x", "-o", str(out), str(src)], capture_output=True, text=True)
    assert r.returncode == 0, f"osacompile failed for {src.name}:\n{r.stderr}"
    return out


def decompile(scpt: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_decompiler(Loader().load(str(scpt)))
    # Everything before the "-----" separator is diagnostic comments.
    return buf.getvalue().split("\n-----\n", 1)[1]


def osascript(path: Path) -> str:
    r = subprocess.run(["osascript", str(path)], capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else "ERROR: " + r.stderr.strip().split(": ", 1)[-1]


# ---- canonical form of a loaded script ---------------------------------


def is_handler(v):
    return isinstance(v, list) and len(v) >= 8 and v[0] in (16, 17) and hasattr(v[7], "value")


def is_actor(v):
    return isinstance(v, list) and len(v) > 4 and v[0] == 15 and isinstance(v[4], list)


def canon(v, depth=0):
    """A comparable, acyclic representation of a loaded value."""
    if depth > 12:
        return "..."
    if is_handler(v):
        return canon_handler(v, depth + 1)
    if is_actor(v):
        # name, parent's name and body; the parent pointer itself is cyclic
        parent = v[3][1] if is_actor(v[3]) else None
        return ("script", canon(v[1]), canon(parent), canon_body(v[4], depth + 1))
    if isinstance(v, list):
        return tuple(canon(x, depth + 1) for x in v)
    if isinstance(v, rto.Statement):
        return "<syntax tree>"  # leftover tree stubs; not part of the program
    if isinstance(v, rto.Binding):
        return ("binding", canon(v.a, depth + 1), canon(v.b, depth + 1), canon(v.next, depth + 1))
    if isinstance(v, rto.EmptyPair):
        return ("pair",)
    if isinstance(v, rto.Pair):
        return ("pair", canon(v.first, depth + 1), canon(v.second, depth + 1))
    if isinstance(v, Descriptor):
        return ("descriptor", v.type, v.content)
    if isinstance(v, (rto.Value, rto.Reference)):
        return repr(v)
    return v


def canon_handler(fn, depth=0):
    return {
        "name": canon(fn[1], depth),
        "positional": canon(fn[3], depth),
        "labeled": canon(fn[4], depth),
        "locals": canon(fn[5], depth),
        "literals": canon(fn[6], depth),
        "code": bytes(bytearray(fn[7].value)),
    }


def canon_body(body, depth=0):
    """A script body: [outer scope, names, value 0, value 1, ...]."""
    names = canon(body[1], depth)
    return {"names": names, "values": [canon(v, depth) for v in body[2:]]}


def canonical_script(scpt: Path):
    return canon_body(Loader().load(str(scpt))[-1])


# ---- the tests -----------------------------------------------------------


@pytest.fixture(scope="module")
def roundtrip(tmp_path_factory):
    """Decompile each fixture once; returns paths of the intermediate files."""
    cache = {}

    def get(src: Path):
        if src not in cache:
            d = tmp_path_factory.mktemp(src.stem)
            original = osacompile_runonly(src, d / "original.scpt")
            decompiled = d / "decompiled.applescript"
            decompiled.write_text(decompile(original))
            cache[src] = (original, decompiled, d)
        return cache[src]

    return get


@pytest.mark.parametrize("src", cases(strict=True))
def test_bytecode_equivalent(src, roundtrip):
    original, decompiled, d = roundtrip(src)
    r = subprocess.run(
        ["osacompile", "-x", "-o", str(d / "recompiled.scpt"), str(decompiled)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"decompiled source does not compile:\n{r.stderr}\n{decompiled.read_text()}"
    assert canonical_script(d / "recompiled.scpt") == canonical_script(original), decompiled.read_text()


@pytest.mark.parametrize("src", cases(strict=False, runnable_only=True))
def test_same_output(src, roundtrip):
    _, decompiled, _ = roundtrip(src)
    assert osascript(decompiled) == osascript(src), decompiled.read_text()
