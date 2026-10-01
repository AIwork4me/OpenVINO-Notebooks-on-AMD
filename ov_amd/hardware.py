"""Sanitized hardware/software discovery.

Never exposes hostname, username, IP, SSH config or credentials.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

_REDACT_KEYS = {"hostname", "username", "user", "ip", "address", "token", "key"}


def _run(cmd: list[str], timeout: int = 20) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if not any(x in k.lower() for x in _REDACT_KEYS)}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def cpu_model() -> str:
    out = _run(["lscpu"])
    m = re.search(r"Model name:\s*(.+)", out)
    return m.group(1).strip() if m else platform.processor() or "unknown"


def gpu_info() -> dict:
    info: dict = {"available": False}
    out = _run(["rocminfo"])
    m = re.search(r"^\s*Marketing Name:\s*(.+)$", out, re.M)
    g = re.search(r"^\s*Name:\s*(gfx\S+)$", out, re.M)
    if g:
        info["available"] = True
        info["arch"] = g.group(1)
        info["marketing_name"] = m.group(1).strip() if m else "AMD Radeon"
    smi = _run(["rocm-smi", "--showmeminfo", "vram", "--csv"])
    vm = re.search(r"(\d+)", smi.splitlines()[-1]) if smi else None
    if vm:
        info["vram_total_bytes_reported"] = int(vm.group(1))
    return info


def torch_rocm(python_bin: str | None = None) -> dict:
    py = python_bin or shutil.which("python3")
    code = (
        "import json,torch\n"
        "print(json.dumps({'torch': torch.__version__, 'hip': torch.version.hip,"
        " 'cuda_available': torch.cuda.is_available(),"
        " 'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))\n"
    )
    try:
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=120)
        for line in (r.stdout or "").splitlines():
            if line.startswith("{"):
                return json.loads(line)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"torch": None, "hip": None, "cuda_available": False, "device": None}


def openvino_info(python_bin: str | None = None) -> dict:
    py = python_bin or shutil.which("python3")
    code = (
        "import json\n"
        "import openvino as ov\n"
        "c = ov.Core()\n"
        "print(json.dumps({'version': ov.__version__, 'devices': c.available_devices}))\n"
    )
    try:
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=120)
        for line in (r.stdout or "").splitlines():
            if line.startswith("{"):
                return json.loads(line)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"version": None, "devices": []}


def os_release() -> dict:
    d = {}
    p = Path("/etc/os-release")
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v.strip('"')
    return d


def collect_hardware() -> dict:
    free = ""
    try:
        free = Path("/proc/meminfo").read_text()
        memtotal_kb = int(re.search(r"MemTotal:\s+(\d+)", free).group(1))  # type: ignore[union-attr]
    except (OSError, AttributeError, ValueError):
        memtotal_kb = 0
    return {
        "platform_id": platform_id(),
        "cpu": {"model": cpu_model(), "threads": os.cpu_count() or 0},
        "ram_total_mb": memtotal_kb // 1024,
        "gpu": gpu_info(),
        "os": os_release().get("PRETTY_NAME", "unknown"),
        "kernel": platform.release(),
    }


def collect_software(python_bin: str | None = None) -> dict:
    return {
        "python": platform.python_version(),
        "openvino": openvino_info(python_bin),
        "torch_rocm": torch_rocm(python_bin),
        "rocm_dir": str(Path("/opt/rocm")) if Path("/opt/rocm").exists() else None,
    }


def platform_id() -> str:
    """Stable, sanitized platform identifier used as hardware/<platform-id>/."""

    cpu = cpu_model().lower()
    if "ai max" in cpu or "395" in cpu:
        pid = "ryzen-ai-max-395-radeon-8060s"
    else:
        pid = re.sub(r"[^a-z0-9]+", "-", cpu)[:48].strip("-") or "unknown-cpu"
    return pid


def snapshot(out_dir: Path, python_bin: str | None = None) -> dict:
    """Write hardware.json/software.json into an evidence dir and return them."""

    hw = _sanitize(collect_hardware())
    sw = _sanitize(collect_software(python_bin))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hardware.json").write_text(json.dumps(hw, indent=2))
    (out_dir / "software.json").write_text(json.dumps(sw, indent=2))
    return {"hardware": hw, "software": sw}
