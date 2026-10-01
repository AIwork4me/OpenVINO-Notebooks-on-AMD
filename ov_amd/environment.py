"""Execution environment handling: venv discovery, env vars, pip installs.

Network resilience: all installs go through bounded retries with backoff.
HF_ENDPOINT defaults to a reachable mirror because huggingface.co is not
reachable from this network (recorded in docs/engineering-decisions.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CPU_VENV = REPO_ROOT / ".venv-cpu"
GPU_VENV = REPO_ROOT / ".venv-gpu"

# Deterministic, resumable download env for notebook kernels.
BASE_KERNEL_ENV = {
    "HF_ENDPOINT": os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"),
    "HF_HUB_DOWNLOAD_TIMEOUT": "60",
    "HF_HUB_DISABLE_XET": "1",  # xet CAS endpoint is unreachable on this network
    "GRADIO_ANALYTICS_ENABLED": "False",
    "DO_NOT_TRACK": "1",
    "NO_COLOR": "1",
    "TERM": "dumb",
    "PYTHONUNBUFFERED": "1",
    "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "32"),
    # OpenVINO CPU behaviour on AMD: make device selection explicit/inspectable.
    "OPENVINO_LOG_LEVEL": "3",
}

# GPU kernels additionally get the ROCm userspace on PATH.
GPU_KERNEL_ENV_EXTRA = {"PYTORCH_TUNABLEOP_ENABLED": "0", "TORCH_BLAS_PREFER_HIPBLASLT": "1"}


def venv_python(backend: str = "cpu") -> Path:
    v = CPU_VENV if backend == "cpu" else GPU_VENV
    return v / "bin" / "python"


def ensure_ipv4_first(backend: str = "cpu") -> None:
    """Install/refresh the network-safety hook in a venv.

    A plain sitecustomize.py gets shadowed by /usr/lib/python3.12/sitecustomize.py
    (stdlib dir precedes site-packages on sys.path), so the hook is wired via a
    .pth file, which site.py executes unconditionally at startup. The module
    file is refreshed from source on every call so hook updates propagate.
    """

    v = CPU_VENV if backend == "cpu" else GPU_VENV
    if not v.exists():
        return
    src = Path(__file__).resolve().parent / "ipv4_first.py"
    site = next((v / "lib").glob("python*/site-packages"), None)
    if site is None:
        return
    (site / "ov_amd_ipv4_first.py").write_text(src.read_text())
    pth = site / "ov_amd_net_fix.pth"
    if not pth.exists():
        pth.write_text("import ov_amd_ipv4_first\n")


def venv_exists(backend: str = "cpu") -> bool:
    return venv_python(backend).exists()


def kernel_env(backend: str = "cpu") -> dict[str, str]:
    env = dict(os.environ)
    env.update(BASE_KERNEL_ENV)
    # notebooks shell out to console scripts (optimum-cli, ovc, ...); the venv
    # bin dir must be on PATH or those cells fail with FileNotFoundError
    venv_bin = (CPU_VENV if backend == "cpu" else GPU_VENV) / "bin"
    if venv_bin.exists():
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    if backend == "gpu":
        env.update(GPU_KERNEL_ENV_EXTRA)
        rocm_bin = Path("/opt/rocm/bin")
        if rocm_bin.exists():
            env["PATH"] = f"{rocm_bin}:{env['PATH']}"
    return env


def pip_install(packages: list[str], backend: str = "cpu", retries: int = 3) -> tuple[bool, str]:
    """Install packages into the shared venv with bounded retries and backoff."""

    py = venv_python(backend)
    last = ""
    for attempt in range(retries):
        r = subprocess.run(
            [str(py), "-m", "pip", "install", "--no-input", *packages],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        last = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True, last
        time.sleep(10 * (attempt + 1))
    return False, last


def pip_freeze(backend: str = "cpu") -> str:
    try:
        r = subprocess.run([str(venv_python(backend)), "-m", "pip", "freeze"], capture_output=True, text=True, timeout=180)
        return r.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def disk_free_mb(path: str = "/") -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize // (1024 * 1024)


def ram_available_mb() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def upstream_root() -> Path | None:
    """Local pinned upstream snapshot dir (see scripts/fetch_upstream.py)."""

    meta_path = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    if not meta_path.exists():
        return None
    try:
        root = Path(json.loads(meta_path.read_text()).get("local_path", ""))
    except (OSError, ValueError):
        return None
    return root if root and root.exists() else None
