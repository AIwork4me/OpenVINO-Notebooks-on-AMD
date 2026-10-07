"""Optimum CLI health contract: preflight, diagnosis, bounded remediation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ov_amd.optimum_health import check_health, health_contract, notebook_uses_optimum_cli


def _nb(tmp_path: Path, src: str) -> Path:
    p = tmp_path / "nb.ipynb"
    p.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [src]}]}))
    return p


def test_detects_optimum_cli_usage(tmp_path) -> None:
    assert notebook_uses_optimum_cli(_nb(tmp_path, "get_ipython().system('optimum-cli export openvino --model x y')"))
    assert notebook_uses_optimum_cli(_nb(tmp_path, "from optimum.intel import OVModelForCausalLM"))
    assert not notebook_uses_optimum_cli(_nb(tmp_path, "import openvino as ov"))


def test_check_health_uses_real_python() -> None:
    import sys

    h = check_health(sys.executable)
    assert set(h["packages"]) == {"openvino", "optimum", "optimum-intel", "transformers", "huggingface_hub"}
    assert h["diagnosis"] in ("HEALTHY", "OPTIMUM_PACKAGES_MISSING", "OPTIMUM_CLI_UNAVAILABLE", "CLI_ENTRYPOINT_BROKEN")


def test_diagnosis_logic(monkeypatch) -> None:
    import ov_amd.optimum_health as oh

    class R:
        returncode = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(oh.subprocess, "run", lambda *a, **k: R())
    monkeypatch.setattr(oh.shutil, "which", lambda _: None)
    h = oh.check_health("python")
    assert h["diagnosis"] in ("OPTIMUM_PACKAGES_MISSING", "OPTIMUM_CLI_UNAVAILABLE")


def test_health_contract_records_evidence(tmp_path, monkeypatch) -> None:
    import ov_amd.optimum_health as oh

    calls = {"n": 0}

    def fake_check(python: str):
        calls["n"] += 1
        return {"python": python, "packages": {}, "cli": {"help_ok": True}, "diagnosis": "HEALTHY"}

    monkeypatch.setattr(oh, "check_health", fake_check)
    ev = tmp_path / "ev"
    h = oh.health_contract("python", ev)
    assert h["diagnosis"] == "HEALTHY"
    assert (ev / "optimum-cli-health.json").exists()
    assert json.loads((ev / "optimum-cli-health.json").read_text())["diagnosis"] == "HEALTHY"
    assert calls["n"] == 1  # healthy: no remediation attempted


@pytest.mark.skipif(not Path(".venv-cpu/bin/python").exists(), reason="validation venv not provisioned")
def test_health_contract_end_to_end_on_venv() -> None:
    """Real end-to-end proof on the validation venv: the contract must reach a
    HEALTHY (or explicitly diagnosed) state with evidence recorded."""
    import shutil
    from pathlib import Path

    py = str(Path(".venv-cpu/bin/python"))
    ev = Path("results/optimum-health-proof")
    if ev.exists():
        shutil.rmtree(ev)
    h = health_contract(py, ev)
    assert h["diagnosis"] in ("HEALTHY", "OPTIMUM_PACKAGES_MISSING", "OPTIMUM_CLI_UNAVAILABLE", "CLI_ENTRYPOINT_BROKEN")
    assert (ev / "optimum-cli-health.json").exists()
    # the seed venv ships optimum-free: after remediation the contract must
    # either be HEALTHY or record the bounded failure honestly
    if h.get("remediation"):
        assert isinstance(h["remediation"].get("ok"), bool)
