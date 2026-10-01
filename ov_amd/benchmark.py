"""Benchmark capture helpers.

CPU side: wall-clock metrics come from execution evidence; medians are
computed across the repeatability runs. GPU side: workloads/<id>/rocm
scripts emit metrics.json consumed here. See benchmarks/METHODOLOGY.md.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

from ov_amd.environment import REPO_ROOT


def summarize_runs(durations_s: list[float]) -> dict[str, Any]:
    if not durations_s:
        return {"runs": 0}
    out: dict[str, Any] = {
        "runs": len(durations_s),
        "median_s": round(statistics.median(durations_s), 3),
        "min_s": round(min(durations_s), 3),
        "max_s": round(max(durations_s), 3),
    }
    if len(durations_s) >= 3:
        # simple P95 over a small sample: second-largest value
        s = sorted(durations_s)
        out["p95_s"] = round(s[-2], 3)
    return out


def load_gpu_metrics(workload_id: str) -> dict[str, Any]:
    p = REPO_ROOT / "workloads" / workload_id / "rocm" / "metrics.json"
    if not p.exists():
        # fall back to latest evidence dir metrics
        ev_root = REPO_ROOT / "results" / workload_id
        if ev_root.exists():
            latest = sorted(ev_root.glob("*-gpu"))
            if latest:
                mp = latest[-1] / "metrics.json"
                if mp.exists():
                    return json.loads(mp.read_text())
        return {}
    return json.loads(p.read_text())


def merge_cpu_metrics(workload_id: str, durations: list[float], device: str) -> dict[str, Any]:
    return {
        "backend": "cpu",
        "device": device or "CPU (assumed; see evidence outputs)",
        "wall_clock": summarize_runs(durations),
    }
