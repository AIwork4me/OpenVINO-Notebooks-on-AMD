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
    # xet-backed HF files route to cas-server.xethub.hf.co, which 401s on some
    # networks; plain HTTP download via the endpoint works
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    # twins download models too: use the same probed, recorded HF transport
    from ov_amd.environment import resolve_hf_endpoint

    os.environ["HF_ENDPOINT"] = str(resolve_hf_endpoint()["endpoint"])
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
        "gcn_arch_source": None,
    }
    if torch.cuda.is_available():
        info["device"] = torch.cuda.get_device_name(0)
        # Authoritative arch only (Step 10 contract): never construct gfxXXX
        # from CUDA capability numbers — cap (11,0) is gfx1100, not gfx110,
        # and cap (11,5) is gfx1151, not gfx115. If neither the ROCm device
        # property nor rocminfo yields the arch, it stays null (unknown).
        props = torch.cuda.get_device_properties(0)
        arch_name = getattr(props, "gcnArchName", None)
        if arch_name:
            info["gcn_arch"] = str(arch_name)
            info["gcn_arch_source"] = "torch.cuda.get_device_properties().gcnArchName"
        else:
            import re as _re
            import subprocess as _sp

            try:
                out = _sp.run(["rocminfo"], capture_output=True, text=True, timeout=90).stdout or ""
                m = _re.search(r"^\s*Name:\s*(gfx\S+)", out, _re.M)
                if m:
                    info["gcn_arch"] = m.group(1)
                    info["gcn_arch_source"] = "rocminfo"
            except (OSError, _sp.TimeoutExpired):
                pass
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
    # v0.3.1 metric-semantics block (additive, Evidence Schema v2 compatible):
    # names exactly what the numbers measure so no reader over-reads them.
    result["metric_semantics"] = {
        "peak_vram_gb": (
            "torch.cuda.max_memory_allocated() — peak ALLOCATED GPU tensor memory via "
            "PyTorch's caching allocator. NOT total physical VRAM usage (driver/runtime "
            "reservations and other processes are excluded)."
        ),
        "peak_rss_gb": "process resident high-water mark (VmHWM from /proc/self/status)",
        "latency_s": "wall time of one full workload invocation including torch.cuda.synchronize()",
        "load_s": "wall time of model+processor construction (from_pretrained/pipeline load)",
        "rtf": "standard RTF = inference_time / generated_or_input_audio_duration (lower is faster; <1 is real-time capable)",
        "realtime_speed_factor": "inverse RTF = audio_duration / inference_time (higher is faster) — reported separately, never mixed with rtf",
    }
    if "correctness_level" not in metrics:
        result["metric_semantics"]["correctness_level"] = (
            "not recorded for this evidence (add correctness_level to the twin metrics to grade it)"
        )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "metrics.json").write_text(json.dumps(result, indent=2))
    print(TWIN_RESULT_KEY + json.dumps(result))
    return 0 if result["ok"] else 1


def fetch(url: str, dest: Path, tries: int = 3, fallbacks: list[str] | None = None, sha256: str | None = None) -> Path:
    """curl-based fetch (python http stack is IPv6-fragile on some networks).

    v0.3.1 hardening: downloads are written to an atomic temp file and moved into
    place only after the size check AND (when provided) the SHA-256 check pass.
    `fallbacks` are alternative URLs for the same official asset; the URL that
    actually served the file is recorded by the caller in its metrics for input
    provenance. When `sha256` is given, an existing dest that fails verification
    is deleted and re-downloaded (cache-corruption recovery).
    """

    import hashlib
    import shutil as _shutil
    import subprocess

    def _ok(p: Path) -> bool:
        if not p.exists() or p.stat().st_size == 0:
            return False
        if sha256:
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest() == sha256.lower()
        return True

    if dest.exists() and _ok(dest):
        return dest
    if dest.exists():
        dest.unlink()  # corrupt or unverified existing file — recover by re-download
    curl = _shutil.which("curl") or "/usr/bin/curl"
    candidates = [url] + list(fallbacks or [])
    last_err = ""
    for cand in candidates:
        for i in range(tries):
            tmp = dest.with_suffix(dest.suffix + ".part")
            r = subprocess.run([curl, "-sSfL", "--max-time", "300", cand, "-o", str(tmp)], capture_output=True)
            if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0 and _ok(tmp):
                tmp.replace(dest)
                return dest
            if tmp.exists():
                tmp.unlink()
            last_err = f"{cand}: curl {r.returncode}" + ("" if r.returncode != 0 else " (hash mismatch)")
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"download failed (last: {last_err})")


def resolve_asset(asset_id: str, explicit: str | None = None):
    """Managed asset resolution (see ov_amd/assets.py). Re-exported here because
    twin scripts import twin_lib as a top-level module from the ov_amd directory."""
    from ov_amd import assets as _assets

    return _assets.resolve_asset(asset_id, explicit=explicit)


def asset_record(resolved) -> dict:
    from ov_amd import assets as _assets

    return _assets.ResolvedAsset.record(resolved)
