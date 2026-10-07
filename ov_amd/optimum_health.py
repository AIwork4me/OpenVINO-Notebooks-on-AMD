"""Optimum CLI health contract.

A recurring pre-closure failure cluster (11+ workloads: ernie-image, qwen-image,
text-to-speech-genai, flux.2-klein, glm-ocr, z-image-turbo, ltx-video,
langchain-genai twins, flux-fill, flux.1-kontext, glm4.1-v-thinking ...) was
'optimum-cli broken/missing in environment': notebooks %pip-install optimum
from git (transport-blocked on the reference network) and later shell out to
`optimum-cli export openvino ...`, which then fails — surfacing far from the
root cause.

The health contract makes the CLI a first-class preflight: before a workload
that uses optimum-cli runs, the runner records a machine-readable health
snapshot and applies bounded remediation (install optimum-intel from PyPI into
the workload's own venv, then re-check). The same check is reusable
standalone: python -m ov_amd.optimum_health <python-binary>.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

NOTEBOOK_OPTIMUM_CLI_RE = re.compile(r"optimum-cli|optimum\.intel|OVModelFor|optimum\.exporters")

KEY_PACKAGES = ("openvino", "optimum", "optimum-intel", "transformers", "huggingface_hub")


def notebook_uses_optimum_cli(nb_path: Path) -> bool:
    try:
        return bool(NOTEBOOK_OPTIMUM_CLI_RE.search(nb_path.read_text(errors="replace")))
    except OSError:
        return False


def _pip_show(python: str, pkg: str) -> dict[str, Any]:
    r = subprocess.run(
        [python, "-m", "pip", "show", pkg], capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        return {"installed": False}
    out: dict[str, Any] = {"installed": True}
    for line in (r.stdout or "").splitlines():
        if line.startswith("Version:"):
            out["version"] = line.split(":", 1)[1].strip()
    return out


def check_health(python: str) -> dict[str, Any]:
    """Health snapshot of the optimum CLI stack inside one environment."""

    result: dict[str, Any] = {"python": python, "packages": {}, "cli": {}}
    for pkg in KEY_PACKAGES:
        result["packages"][pkg] = _pip_show(python, pkg)
    cli = shutil.which("optimum-cli") or str(Path(python).parent / "optimum-cli")
    probe_rc = 127
    if Path(cli).exists() or shutil.which("optimum-cli"):
        try:
            probe = subprocess.run([cli, "--help"], capture_output=True, text=True, timeout=120)
            probe_rc = probe.returncode
        except (OSError, subprocess.TimeoutExpired):
            probe_rc = 127
    result["cli"] = {
        "path": cli if probe_rc == 0 else None,
        "help_exit_code": probe_rc,
        "help_ok": probe_rc == 0,
    }
    missing_cli = not result["cli"]["help_ok"]
    missing_pkgs = [p for p in ("optimum", "optimum-intel") if not result["packages"][p]["installed"]]
    if missing_cli and not missing_pkgs:
        result["diagnosis"] = "CLI_ENTRYPOINT_BROKEN"  # packages present, console script dead
    elif missing_pkgs:
        result["diagnosis"] = "OPTIMUM_PACKAGES_MISSING"
    elif missing_cli:
        result["diagnosis"] = "OPTIMUM_CLI_UNAVAILABLE"
    else:
        result["diagnosis"] = "HEALTHY"
    return result


def remediate(python: str, health: dict[str, Any]) -> tuple[bool, str]:
    """Bounded remediation: single targeted install from PyPI into the SAME
    environment, one re-check. Never a combinatorial resolver search."""

    target = "optimum-intel" if health["diagnosis"] != "CLI_ENTRYPOINT_BROKEN" else "optimum-intel"
    r = subprocess.run(
        [python, "-m", "pip", "install", "--no-input", target],
        capture_output=True,
        text=True,
        timeout=1800,
    )
    log = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        return False, log[-2000:]
    after = check_health(python)
    return after["diagnosis"] == "HEALTHY", json.dumps(after["packages"], indent=2)[-2000:]


def health_contract(python: str, evidence_dir: Path | None = None) -> dict[str, Any]:
    """Check + bounded remediation + evidence record. Returns the final health
    snapshot (post-remediation when remediation ran)."""

    health = check_health(python)
    health["remediation"] = None
    if health["diagnosis"] != "HEALTHY":
        ok, log = remediate(python, health)
        health = check_health(python)
        health["remediation"] = {"attempted": True, "ok": ok, "log_tail": log[-1000:]}
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "optimum-cli-health.json").write_text(json.dumps(health, indent=2))
    return health


if __name__ == "__main__":  # standalone: python -m ov_amd.optimum_health <python>
    import sys

    print(json.dumps(check_health(sys.argv[1]), indent=2))
