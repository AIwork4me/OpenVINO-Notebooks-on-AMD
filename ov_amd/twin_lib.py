"""Shared helpers for ROCm twin scripts (workloads/<id>/rocm/run.py).

Contract for every twin:
  - assert torch.version.hip is not None and an AMD GPU is visible (no fake GPU validation)
  - deterministic settings where possible
  - print TWIN_RESULT={"ok": true, "hip": "<ver>", "device": "...", "metrics": {...}}
  - write metrics.json + artifacts into --evidence-dir
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

TWIN_RESULT_KEY = "TWIN_RESULT="


def setup() -> argparse.ArgumentParser:
    import os
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ov_amd.environment import ensure_ipv4_first

    ensure_ipv4_first("gpu")
    # xet-backed HF files route to cas-server.xethub.hf.co, which 401s on this
    # network; plain HTTP download via the mirror works
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", default=".")
    return ap


def gpu_ready() -> dict:
    import torch

    info = {
        "hip": torch.version.hip,
        "cuda_available": torch.cuda.is_available(),
        "device": None,
        "gcn_arch": None,
    }
    if torch.cuda.is_available():
        info["device"] = torch.cuda.get_device_name(0)
        cap = torch.cuda.get_device_capability(0)
        info["gcn_arch"] = f"gfx{cap[0]}{cap[1]}"
    return info


class PeakMemory:
    """Samples torch GPU allocated + RSS while the twin runs."""

    def __init__(self) -> None:
        import torch

        self.torch = torch
        self.stop = threading.Event()
        self.peak_vram_gb = 0.0
        self.peak_rss_gb = 0.0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.is_set():
            try:
                v = self.torch.cuda.max_memory_allocated() / (1024**3) if self.torch.cuda.is_available() else 0
                self.peak_vram_gb = max(self.peak_vram_gb, v)
                rss = 0.0
                for line in Path("/proc/self/status").read_text().splitlines():
                    if line.startswith("VmHWM:"):
                        rss = int(line.split()[1]) / (1024**2)
                self.peak_rss_gb = max(self.peak_rss_gb, rss)
            except Exception:  # noqa: BLE001 - sampler must never kill the twin
                pass
            time.sleep(0.2)

    def __enter__(self) -> PeakMemory:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop.set()
        self._thread.join(timeout=2)


def emit(ok: bool, evidence_dir: Path, metrics: dict, extra: dict | None = None) -> int:

    info = gpu_ready()
    result = {
        "ok": bool(ok),
        "hip": info["hip"],
        "device": info["device"],
        "gcn_arch": info["gcn_arch"],
        "metrics": metrics,
    }
    if extra:
        result.update(extra)
    if not ok or not info["hip"] or not info["cuda_available"]:
        result["ok"] = False
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "metrics.json").write_text(json.dumps(result, indent=2))
    print(TWIN_RESULT_KEY + json.dumps(result))
    return 0 if result["ok"] else 1


def fetch(url: str, dest: Path, tries: int = 3) -> Path:
    """curl-based fetch (python http stack is IPv6-fragile on this network)."""

    import shutil
    import subprocess

    if dest.exists() and dest.stat().st_size > 0:
        return dest
    curl = shutil.which("curl") or "/usr/bin/curl"
    for i in range(tries):
        r = subprocess.run([curl, "-sSfL", "--max-time", "300", url, "-o", str(dest)], capture_output=True)
        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return dest
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"download failed: {url}")
