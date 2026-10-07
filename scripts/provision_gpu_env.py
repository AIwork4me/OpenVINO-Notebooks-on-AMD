#!/usr/bin/env python3
"""Provision the ROCm GPU validation environment (.venv-gpu), runner-agnostic.

Strategy (recorded in .venv-gpu/provision-meta.json):
1. If .venv-gpu already exists with a working ROCm torch — done (warm runner).
2. Else, if the system python already imports a ROCm torch
   (torch.version.hip is not None): create .venv-gpu with
   --system-site-packages so it inherits the vendor ROCm stack, then ensure
   the twin runtime deps (ultralytics etc.) via uv.
3. Else: create an isolated venv and install torch from the official ROCm
   extra index for the detected ROCm release.

Every path records what it did; nothing is silently assumed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ov_amd.environment import GPU_VENV  # noqa: E402

# ultralytics/diffusers pull "torch" as a dependency; in the bridged-venv
# strategy uv cannot see the bridged ROCm torch and would re-resolve a pypi
# torch on top of it. Deps are therefore installed explicitly, without
# resolution, and only the ones not already provided by the bridge.
TWIN_DEPS = ["ultralytics>=8.0", "ultralytics-thop", "diffusers>=0.30"]
TWIN_DEPS_BRIDGED_EXTRA = ["tqdm", "huggingface_hub", "safetensors", "regex", "filelock"]


def run(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd[:6]), "..." if len(cmd) > 6 else "", flush=True)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def gpu_torch_ok(python: str) -> dict:
    code = (
        "import json\n"
        "try:\n"
        "    import torch\n"
        "    print(json.dumps({'torch': torch.__version__, 'hip': torch.version.hip,"
        " 'cuda_available': torch.cuda.is_available()}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'error': str(e)[:200]}))\n"
    )
    try:
        r = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=180)
        for line in (r.stdout or "").splitlines():
            if line.startswith("{"):
                return json.loads(line)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"error": "probe failed"}


def main() -> int:
    meta: dict = {"strategy": None, "system_torch": None, "venv_torch": None}
    py = GPU_VENV / "bin" / "python"

    if py.exists():
        info = gpu_torch_ok(str(py))
        meta["venv_torch"] = info
        if info.get("hip") and info.get("cuda_available"):
            meta["strategy"] = "existing .venv-gpu with working ROCm torch"
            (GPU_VENV / "provision-meta.json").write_text(json.dumps(meta, indent=2))
            print("GPU env already provisioned:", info)
            return 0

    sys_py = sys.executable
    info = gpu_torch_ok(sys_py)
    meta["system_torch"] = info
    if info.get("hip"):
        outer_cfg = Path(sys_py).parent.parent / "pyvenv.cfg"
        if outer_cfg.exists():
            # torch lives in an outer *venv* (vendor ROCm session env);
            # --system-site-packages would only expose the true system
            # interpreter's packages, so bridge via .pth instead. Twin deps
            # still install into .venv-gpu itself (isolated from the session).
            r = run(["uv", "venv", "--seed", "--python", "3.12", str(GPU_VENV)], timeout=600)
            if r.returncode != 0:
                print(r.stderr[-1500:], file=sys.stderr)
                return 1

            outer_site = None
            for lib in (Path(sys_py).parent.parent / "lib").glob("python*/site-packages"):
                outer_site = lib
            if outer_site is None:
                print("cannot locate outer venv site-packages", file=sys.stderr)
                return 1
            site = next((GPU_VENV / "lib").glob("python*/site-packages"))
            (site / "ov_amd_rocm_bridge.pth").write_text(f"{outer_site}\n")
            meta["strategy"] = f"isolated venv bridged via .pth to ROCm site-packages ({outer_site})"
        else:
            r = run([sys_py, "-m", "venv", "--system-site-packages", str(GPU_VENV)], timeout=600)
            if r.returncode != 0:
                print(r.stderr[-1500:], file=sys.stderr)
                return 1
            meta["strategy"] = "system-site-packages venv over vendor ROCm torch"
    else:
        # isolated venv + ROCm extra index
        rocm_rel = "6.4.2"
        r = run(
            [
                "uv", "venv", "--seed", "--python", "3.12", str(GPU_VENV),
            ],
            timeout=600,
        )
        if r.returncode != 0:
            print(r.stderr[-1500:], file=sys.stderr)
            return 1
        idx = f"https://download.pytorch.org/whl/rocm{rocm_rel}"
        r = run(
            ["uv", "pip", "install", "--python", str(py), "--index-url", idx, "torch", "torchvision"],
            timeout=3600,
        )
        if r.returncode != 0:
            print(r.stderr[-1500:], file=sys.stderr)
            return 1
        meta["strategy"] = f"isolated venv, torch from ROCm {rocm_rel} extra index"

    # twin runtime deps. Bridged venv: --no-deps (uv must not re-resolve a
    # pypi torch over the bridged ROCm stack); the non-torch extras are
    # listed explicitly. Isolated venv: normal resolution is safe.
    if "bridged" in str(meta.get("strategy")):
        run(["uv", "pip", "install", "--python", str(py), "--no-deps", *TWIN_DEPS], timeout=3600)
        run(["uv", "pip", "install", "--python", str(py), *TWIN_DEPS_BRIDGED_EXTRA], timeout=3600)
    else:
        run(["uv", "pip", "install", "--python", str(py), *TWIN_DEPS], timeout=3600)
    final = gpu_torch_ok(str(py))
    meta["venv_torch"] = final
    (GPU_VENV / "provision-meta.json").write_text(json.dumps(meta, indent=2))
    print("provisioned:", json.dumps(meta, indent=2))
    if not (final.get("hip") and final.get("cuda_available")):
        print("WARNING: ROCm torch not functional after provisioning", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
