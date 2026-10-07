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
    # multi-GPU servers enumerate slowly; 90s avoids a false "no GPU" record
    out = _run(["rocminfo"], timeout=90)
    g = re.findall(r"^\s*Name:\s*(gfx\S+?)\s*$", out, re.M)
    # Marketing Name must belong to the GPU agent. In rocminfo the GPU agent
    # block reads: Name: gfxXXXX followed by its own Marketing Name line —
    # take the first Marketing Name AFTER the gfx Name line, bounded by the
    # next Agent header.
    gpu_name = "AMD Radeon Graphics"
    if g:
        idx = out.find(g[0])
        tail = out[idx if idx != -1 else 0 :]
        nxt = tail.find("Agent ")
        section = tail[: nxt if nxt != -1 else len(tail)]
        m2 = re.search(r"^\s*Marketing Name:\s*(.+?)\s*$", section, re.M)
        if m2:
            gpu_name = m2.group(1).strip()
    if g:
        info["available"] = True
        archs = sorted(set(g))
        info["arch"] = archs[0] if len(archs) == 1 else archs
        info["marketing_name"] = gpu_name
        info["gpu_count"] = len(g)
    smi = _run(["rocm-smi", "--showmeminfo", "vram", "--csv"], timeout=60)
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


def python_version(python_bin: str | None = None) -> str:
    """Exact interpreter version of the python that will execute the workload
    (Defect D: platform.python_version() reports the *caller*, not the target
    venv, when evidence is collected from a different process)."""

    py = python_bin or shutil.which("python3")
    try:
        r = subprocess.run(
            [py, "-c", "import platform;print(platform.python_version())"], capture_output=True, text=True, timeout=30
        )
        v = (r.stdout or "").strip()
        if v:
            return v
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def collect_software(python_bin: str | None = None) -> dict:
    return {
        "python": python_version(python_bin),
        "python_bin": _sanitize_path(python_bin) if python_bin else None,
        "openvino": openvino_info(python_bin),
        "torch_rocm": torch_rocm(python_bin),
        "rocm_dir": str(Path("/opt/rocm")) if Path("/opt/rocm").exists() else None,
    }


def _sanitize_path(p: str) -> str:
    """Repo-absolute interpreter paths stay useful locally but must not leak
    the local layout into published evidence."""

    from ov_amd.environment import REPO_ROOT

    return p.replace(f"{REPO_ROOT}/", "")


def platform_id() -> str:
    """Stable, sanitized platform identifier used as hardware/<platform-id>/."""

    cpu = cpu_model().lower()
    gpu = gpu_info()
    if "ai max" in cpu or "395" in cpu:
        pid = "ryzen-ai-max-395-radeon-8060s"
    else:
        pid = re.sub(r"[^a-z0-9]+", "-", cpu)[:48].strip("-") or "unknown-cpu"
    # a machine with a discrete AMD GPU gets it in the identity so evidence
    # from iGPU and dGPU runners can never be conflated
    arch = gpu.get("arch") if gpu.get("available") else None
    if arch and isinstance(arch, str) and arch not in pid:
        pid = f"{pid}-{arch}"
    return pid


def snapshot(
    out_dir: Path, python_bin: str | None = None, names: tuple[str, str] = ("hardware.json", "software.json")
) -> dict:
    """Write hardware/software evidence into an evidence dir and return them.

    `names` selects the software filename so v2 evidence can record
    software-before.json / software-after.json from the same collector.
    """

    hw = _sanitize(collect_hardware())
    sw = _sanitize(collect_software(python_bin))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / names[0]).write_text(json.dumps(hw, indent=2))
    (out_dir / names[1]).write_text(json.dumps(sw, indent=2))
    return {"hardware": hw, "software": sw}
