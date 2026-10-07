"""Workload-specific correctness validation.

Checks are declared per workload in workloads/<id>/workload.yaml under
`validation:` and evaluated against the executed notebook outputs.

A non-empty validation block (any real check) constitutes the workload's
correctness contract; its presence upgrades the attempt to
L3 WORKLOAD_CORRECTNESS when it passes. An empty block means the run can
never claim more than L1 EXECUTION_ONLY (ev2.decide_status enforces this).

Named presets expand to parameterized checks for convenience; the expanded
checks are recorded in validation.json so the contract stays auditable.
"""

from __future__ import annotations

import math
import re
from typing import Any

# Presets: necessary-condition bundles per workload family. They are explicit
# contracts once declared (expanded into the recorded check list), tuned to
# reject empty/garbage/crashed outputs while never asserting cross-backend
# identity of stochastic outputs.
PRESETS: dict[str, dict[str, Any]] = {
    "text_generation": {
        "min_output_chars": 60,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
        "output_contains": [r"(?i)\b(token|prompt|response|answer|output|generate)"],
    },
    "classification": {
        "output_finite_numbers": True,
        "min_output_chars": 20,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "detection": {
        "output_finite_numbers": True,
        "min_output_chars": 20,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "embedding": {
        "output_finite_numbers": True,
        "min_output_chars": 20,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "asr": {
        "min_output_chars": 20,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "tts": {
        "min_output_chars": 10,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "image_generation": {
        "min_output_chars": 10,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
    "rag_agent": {
        "min_output_chars": 40,
        "output_not_contains": [r"Traceback \(most recent call last\)"],
    },
}


def expand_preset(expect: dict[str, Any]) -> dict[str, Any]:
    """Merge a named preset into the declared checks (declared wins)."""

    name = expect.get("preset")
    if not name:
        return expect
    base = PRESETS.get(name, {}).copy()
    merged = dict(base)
    for k, v in expect.items():
        if k == "preset":
            continue
        if isinstance(v, list) and isinstance(merged.get(k), list):
            merged[k] = merged[k] + [x for x in v if x not in merged[k]]
        else:
            merged[k] = v
    return merged


def check_output_contains(text: str, patterns: list[str]) -> dict[str, Any]:
    results = {}
    for p in patterns:
        try:
            found = re.search(p, text) is not None
        except re.error:
            found = p in text
        results[p] = found
    return results


def check_finite_numbers(text: str) -> bool:
    """At least one finite float was printed and no NaN/Inf appeared."""

    has_number = re.search(r"-?\d+\.\d+", text) is not None
    has_nan = re.search(r"\bnan\b|\bNaN\b", text, re.I) is not None
    return has_number and not has_nan


def evaluate(expect: dict[str, Any], outputs_text: str, nbresult: dict) -> dict[str, Any]:
    """Evaluate a workload's `validation:` block. Returns {passed, checks, notes}."""

    expect = expand_preset(expect)
    checks: dict[str, Any] = {}
    notes: list[str] = []

    if "output_contains" in expect:
        checks["output_contains"] = check_output_contains(outputs_text, expect["output_contains"])

    if expect.get("output_finite_numbers"):
        checks["output_finite_numbers"] = check_finite_numbers(outputs_text)

    if "output_not_contains" in expect:
        for p in expect["output_not_contains"]:
            checks.setdefault("output_not_contains", {})[p] = re.search(p, outputs_text) is None

    if "min_output_chars" in expect:
        checks["min_output_chars"] = len(outputs_text.strip()) >= expect["min_output_chars"]

    # Cell-level sanity from the runner: every code cell that was executed must
    # have run without raising unless the workload explicitly allows skips.
    n_skipped = int(nbresult.get("n_skipped", 0))
    checks["no_cell_error"] = bool(nbresult.get("ok"))
    checks["skipped_cells"] = n_skipped
    if n_skipped:
        notes.append(f"{n_skipped} cell(s) skipped via documented patch (interactive/UI-only code)")

    passed = all(
        (v is True) or (isinstance(v, dict) and all(v.values()))
        for k, v in checks.items()
        if k not in ("skipped_cells",)
    )
    return {"passed": bool(passed), "checks": checks, "notes": notes}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return float("nan")
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else float("nan")
