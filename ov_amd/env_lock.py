"""Dependency lock metadata for validation environments (evidence-side).

`environment.lock.json` records the resolved dependency profile of the exact
environment a workload ran in — python, OpenVINO stack, model-framework
versions and the full installed-package list when the environment is live.
For historical evidence whose venv was not retained, a partial lock is derived
from the recorded software snapshots and explicitly labeled as such (never
invented).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

KEY_PACKAGES = (
    "openvino",
    "openvino-genai",
    "openvino-tokenizers",
    "optimum",
    "optimum-intel",
    "transformers",
    "diffusers",
    "huggingface_hub",
    "protobuf",
    "torch",
    "nncf",
    "onnx",
)


def _live_packages(python: str) -> dict[str, str]:
    script = (
        "import importlib.metadata as md, json\n"
        "out = {}\n"
        "try:\n"
        "    for d in md.distributions():\n"
        "        n = d.metadata['Name']\n"
        "        if n:\n"
        "            out[n] = d.version\n"
        "except Exception:\n"
        "    pass\n"
        "print(json.dumps(out))\n"
    )
    try:
        r = subprocess.run([python, "-c", script], capture_output=True, text=True, timeout=180)
        return json.loads(r.stdout.strip() or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def write_lock(
    evidence_dir: Path,
    env_python: str | None = None,
    recorded: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write environment.lock.json. Live environments get the full package
    list; recorded-only snapshots get an honest partial lock."""

    lock: dict[str, Any] = {"schema_version": 2}
    if env_python and Path(env_python).exists():
        pkgs = _live_packages(env_python)
        lock.update(
            {
                "source": "live",
                "python_bin": str(env_python),
                "key_packages": {k: pkgs.get(k) for k in KEY_PACKAGES},
                "packages": pkgs,
            }
        )
    else:
        rec = recorded or {}
        ov = rec.get("openvino") or {}
        torch = rec.get("torch_rocm") or {}
        lock.update(
            {
                "source": "recorded-snapshot (venv not retained; partial — never reconstructed)",
                "python": rec.get("python"),
                "key_packages": {
                    "openvino": ov.get("version"),
                    "torch": torch.get("torch"),
                },
            }
        )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "environment.lock.json").write_text(json.dumps(lock, indent=2))
    return lock
