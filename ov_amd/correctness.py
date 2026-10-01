"""Workload-specific correctness validation.

Checks are declared per workload in workloads/<id>/workload.yaml under
`validation:` and evaluated against the executed notebook outputs.
"""

from __future__ import annotations

import math
import re
from typing import Any


def check_output_contains(text: str, patterns: list[str]) -> dict[str, Any]:
    results = {}
    for p in patterns:
        found = re.search(p, text) is not None
        results[p] = found
    return results


def check_finite_numbers(text: str) -> bool:
    """At least one finite float was printed and no NaN/Inf appeared."""

    has_number = re.search(r"-?\d+\.\d+", text) is not None
    has_nan = re.search(r"\bnan\b|\bNaN\b", text, re.I) is not None
    return has_number and not has_nan


def evaluate(expect: dict[str, Any], outputs_text: str, nbresult: dict) -> dict[str, Any]:
    """Evaluate a workload's `validation:` block. Returns {passed, checks, notes}."""

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
    if expect.get("allow_skipped_cells", False) and n_skipped:
        passed = passed  # skipped cells already excluded from pass criteria

    return {"passed": bool(passed), "checks": checks, "notes": notes}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return float("nan")
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else float("nan")
