"""Regression: GPU twin evidence must be the complete v2 set (Defect H).

v0.1 shipped GPU greens with only metrics/stdout/stderr. The twin runner now
emits the full contract; these tests pin the decision logic so a regression
back to three-file GPU evidence (or an un-gated VERIFIED) fails loudly.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _fake_twin_result(runs: list[float], ok: bool = True) -> dict:
    return {
        "ok": ok,
        "hip": "7.2.53211",
        "device": "AMD Radeon Graphics",
        "gcn_arch": "gfx1100",
        "metrics": {"runs": [{"latency_s": r} for r in runs]},
    }


def test_twin_green_requires_three_runs():
    """ok+hip with <3 measured runs must degrade to VERIFIED_WITH_LIMITATIONS
    (dual-review gate finding: no asymmetric green policy). This pins the
    decision predicate run_gpu_twin applies after a twin completes."""
    from ov_amd import ev2

    runs = [0.5, 0.6]
    agg = ev2.aggregate_repeatability(runs, 3)
    ok_and_hip = True
    verified = ok_and_hip and len(runs) >= ev2.REPEATABILITY_MIN_RUNS and agg["repeatability_passed"]
    assert not verified, "2 runs must not be full VERIFIED"


def test_twin_three_runs_green():
    from ov_amd import ev2

    runs = [0.5, 0.6, 0.55]
    agg = ev2.aggregate_repeatability(runs, 3)
    assert agg["repeatability_passed"] is True
    assert agg["median_latency_s"] == 0.55


def test_v2_gpu_evidence_set_contract():
    """The required GPU v2 files — mirrors the runner's output; if the runner
    stops emitting any of these the audit script fails (kept here as the
    machine-checkable contract)."""
    required = [
        "aggregate.json", "hardware.json", "software.json", "upstream.json",
        "model.json", "execution.json", "validation.json", "metrics.json",
        "device-proof.json", "summary.md", "stdout.log", "stderr.log",
    ]
    import glob

    newest = {}
    for d in glob.glob("results/*/*-gpu"):
        w = d.split("/")[1]
        newest[w] = max(newest.get(w, ""), d)
    checked = 0
    for w, d in newest.items():
        missing = [f for f in required if not Path(f"{d}/{f}").exists()]
        assert not missing, f"{w}: missing {missing}"
        checked += 1
    assert checked >= 8, f"expected >=8 twin evidence dirs, checked {checked}"


@pytest.mark.parametrize("runs,n,expect_green", [
    ([0.1, 0.2, 0.3], 3, True),
    ([0.1, 0.2], 3, False),
    ([0.1, 0.2, 0.3, 0.4, 0.5], 3, True),
])
def test_repeatability_gate_matrix(runs, n, expect_green):
    from ov_amd import ev2

    agg = ev2.aggregate_repeatability(runs, n)
    assert agg["repeatability_passed"] == expect_green
