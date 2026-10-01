"""Integration test: execute a synthetic notebook through _nbexec.py.

Requires the CPU validation venv (.venv-cpu) — skipped when absent so CI
without the full environment still passes.
"""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv-cpu" / "bin" / "python"

pytestmark = pytest.mark.skipif(not VENV_PY.exists(), reason="validation venv not provisioned")


def make_nb(path: Path, cells: list[str]) -> None:
    nb = {
        "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None,
                   "outputs": [], "source": src} for src in cells],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb))


def run_nbexec(nb: Path, out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(VENV_PY), str(ROOT / "ov_amd" / "_nbexec.py"), str(nb), str(out), "60", *extra],
        capture_output=True, text=True, timeout=180,
    )


def test_simple_execution(tmp_path):
    nb, out = tmp_path / "n.ipynb", tmp_path / "o.ipynb"
    make_nb(nb, ["x = 21 * 2\nprint(x)"])
    r = run_nbexec(nb, out)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout.strip().splitlines()[-1].removeprefix("NBEXEC_RESULT="))
    assert res["ok"] is True and res["n_cells"] == 1


def test_failing_cell(tmp_path):
    nb, out = tmp_path / "n.ipynb", tmp_path / "o.ipynb"
    make_nb(nb, ["raise ValueError('boom')"])
    r = run_nbexec(nb, out)
    assert r.returncode == 1
    assert "boom" in r.stderr


def test_skip_re(tmp_path):
    nb, out = tmp_path / "n.ipynb", tmp_path / "o.ipynb"
    make_nb(nb, ["import gradio as gr\ndemo.launch()", "print('core ok')"])
    r = run_nbexec(nb, out, "--skip-re", "gradio")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout.strip().splitlines()[-1].removeprefix("NBEXEC_RESULT="))
    assert res["n_skipped"] == 1 and res["ok"] is True


def test_sub_patch(tmp_path):
    nb, out = tmp_path / "n.ipynb", tmp_path / "o.ipynb"
    make_nb(nb, ["device = 'AUTO'\nprint(device)"])
    r = run_nbexec(nb, out, "--sub", "device\\s*=\\s*['\\\"]AUTO['\\\"]:device = 'CPU'")
    assert r.returncode == 0, r.stderr
    executed = json.loads(out.read_text())
    src = executed["cells"][0]["source"]
    src = "".join(src) if isinstance(src, list) else src
    assert "device = 'CPU'" in src


def test_stop_after(tmp_path):
    nb, out = tmp_path / "n.ipynb", tmp_path / "o.ipynb"
    make_nb(nb, ["print('a')", "print('STOP_MARKER')", "raise RuntimeError('must not run')"])
    r = run_nbexec(nb, out, "--stop-after-re", "STOP_MARKER")
    assert r.returncode == 0, r.stderr
