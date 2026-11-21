"""JXA (JavaScript for Automation) scripts store their source as text, so
"decompiling" is extracting it. Never runs the scripts."""

import subprocess
import sys
from pathlib import Path

import pytest

from applescript_decompiler.jxa import extract_jxa_source, is_jxa

FIXTURES = Path(__file__).parent / "fixtures"
JXA_SOURCES = sorted((FIXTURES / "jxa").glob("*.js"))
on_macos = pytest.mark.skipif(sys.platform != "darwin", reason="needs osacompile")


@pytest.mark.parametrize("src", JXA_SOURCES, ids=lambda p: p.stem)
def test_checked_in_runonly_build(src):
    # no macOS needed: a run-only build is kept next to each source
    scpt = src.with_suffix(".scpt")
    assert is_jxa(scpt)
    assert extract_jxa_source(scpt) == src.read_text()


@on_macos
@pytest.mark.parametrize("bundle", [False, True], ids=["scpt", "scptd"])
@pytest.mark.parametrize("src", JXA_SOURCES, ids=lambda p: p.stem)
def test_fresh_runonly_build(src, bundle, tmp_path):
    out = tmp_path / ("script.scptd" if bundle else "script.scpt")
    subprocess.run(["osacompile", "-l", "JavaScript", "-x", "-o", str(out), str(src)], check=True)
    assert is_jxa(out)
    assert extract_jxa_source(out) == src.read_text()


def test_applescript_is_not_jxa():
    assert not is_jxa(Path(__file__).parent.parent / "demo" / "demo_runonly.scpt")


@on_macos
def test_cli_prints_jxa_source(tmp_path):
    src = JXA_SOURCES[0]
    out = tmp_path / "script.scpt"
    subprocess.run(["osacompile", "-l", "JavaScript", "-x", "-o", str(out), str(src)], check=True)
    from applescript_decompiler.decompiler import cli
    import contextlib
    import io

    buf = io.StringIO()
    argv = sys.argv
    sys.argv = ["applescript_decompile", str(out)]
    try:
        with contextlib.redirect_stdout(buf):
            cli()
    finally:
        sys.argv = argv
    assert buf.getvalue().split("\n-----\n", 1)[1] == src.read_text() + "\n"
