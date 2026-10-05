"""Benchmark capture helpers.

CPU side: wall-clock metrics come from execution evidence; medians are
computed across the repeatability runs. GPU side: workloads/<id>/rocm
scripts emit metrics.json consumed here. See benchmarks/METHODOLOGY.md.

Twin comparison safety (v0.2): direct speedup claims are only allowed for
EXACT_TWIN (same model, same revision, same input, comparable precision
explicitly disclosed). WORKLOAD_TWIN gets side-by-side numbers only;
CONCEPT_MAPPING gets no comparison; OPENVINO_SPECIFIC has no GPU path.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

from ov_amd.environment import REPO_ROOT

# twin level -> what may be published
COMPARISON_POLICY: dict[str, dict[str, Any]] = {
    "EXACT_TWIN": {
        "mode": "DEPLOYMENT_OR_CONTROLLED",
        "speedup_allowed": True,
        "requirement": "same model + revision + input; precision/config disclosed",
    },
    "WORKLOAD_TWIN": {
        "mode": "SIDE_BY_SIDE_ONLY",
        "speedup_allowed": False,
        "requirement": "same task, possibly different models — no direct speedup claim",
    },
    "CONCEPT_MAPPING": {
        "mode": "NO_COMPARISON",
        "speedup_allowed": False,
        "requirement": "concept-level mapping only, no benchmark comparison",
    },
    "OPENVINO_SPECIFIC": {
        "mode": "NO_GPU_PATH",
        "speedup_allowed": False,
        "requirement": "GPU NOT_APPLICABLE for OpenVINO-specific APIs",
    },
    "NOT_CLASSIFIED": {
        "mode": "NO_COMPARISON",
        "speedup_allowed": False,
        "requirement": "twin must be classified before any comparison",
    },
}


def comparison_policy(twin_level: str) -> dict[str, Any]:
    return COMPARISON_POLICY.get(
        twin_level,
        {"mode": "NO_COMPARISON", "speedup_allowed": False, "requirement": "unknown twin level"},
    )


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
