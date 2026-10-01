"""Execution environment handling: venv discovery, env vars, pip installs.

Network resilience: all installs go through bounded retries with backoff.
HF_ENDPOINT defaults to a reachable mirror because huggingface.co is not
reachable from this network (recorded in docs/engineering-decisions.md).
"""

from __future__ import annotations

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
    "GRADIO_ANALYTICS_ENABLED": "False",
    "DO_NOT_TRACK": "1",
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


def venv_exists(backend: str = "cpu") -> bool:
    return venv_python(backend).exists()


def kernel_env(backend: str = "cpu") -> dict[str, str]:
    env = dict(os.environ)
    env.update(BASE_KERNEL_ENV)
    if backend == "gpu":
        env.update(GPU_KERNEL_ENV_EXTRA)
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
