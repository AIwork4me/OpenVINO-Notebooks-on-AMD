#!/usr/bin/env python3
"""Generate reports/v0.2-pinned-baseline.md (STEP 20) from marathon state.

Every green row carries a clickable repo-relative evidence link; counts
reconcile with results/marathon-state.json by construction.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ov_amd.scheduler import load_catalog, load_state  # noqa: E402

OUT = REPO / "reports" / "v0.2-pinned-baseline.md"

GREENS = ("VERIFIED", "VERIFIED_WITH_LIMITATIONS")


def main() -> int:
    state = load_state()
    catalog = load_catalog()
    attempts = state.get("attempts", {})
    meta_path = REPO / "upstream" / "openvino-notebooks.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    cpu = Counter()
    gpu = Counter()
    levels = Counter()
    proofs = Counter()
    green_rows: list[str] = []
    fail_cats = Counter()

    for e in catalog:
        rec = attempts.get(e.id, {})
        c = rec.get("cpu") or {}
        g = rec.get("gpu") or {}
        cpu[c.get("status", "NOT_TESTED")] += 1
        gpu[g.get("status", "NOT_TESTED")] += 1
        if c.get("validation_level"):
            levels[c["validation_level"]] += 1
        if c.get("device_proof"):
            proofs[c["device_proof"]] += 1
        if c.get("failure_category"):
            fail_cats[c["failure_category"]] += 1
        for backend, r in (("cpu", c), ("gpu", g)):
            if r.get("status") in GREENS:
                ev = (r.get("evidence_dir") or "").replace(f"{REPO}/", "")
                green_rows.append(
                    f"| {e.id} | {backend.upper()} | {r['status']} | {r.get('device_proof', '')} | "
                    f"{r.get('validation_level', '')} | {r.get('ok_runs', '-')} | "
                    f"[evidence]({ev}/summary.md) |"
                )

    def fmt_row(counter: Counter, statuses: list[str]) -> str:
        return " · ".join(f"{s}: {counter.get(s, 0)}" for s in statuses)

    cpu_statuses = ["VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED", "BLOCKED",
                    "SKIPPED_RESOURCE", "NOT_APPLICABLE", "REVALIDATION_REQUIRED", "NOT_TESTED"]
    attempted = sum(v for k, v in cpu.items() if k != "NOT_TESTED")

    lines = [
        "# v0.2 Pinned Validation Baseline",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')} from `results/marathon-state.json`.",
        "",
        "## Pinned upstream",
        "",
        f"- repository: `{meta.get('repository', '?')}` branch `{meta.get('branch', '?')}`",
        f"- commit: `{meta.get('commit', '?')}` ({meta.get('commit_date', '?')})",
        "- evidence schema: v2 (per-workload isolated environments, positive device proof,",
        "  validation levels, auditable repeatability aggregates)",
        "",
        "## Reference platform",
        "",
        "- CPU: AMD Ryzen AI Max+ PRO 395 (16C/32T) — OpenVINO CPU plugin",
        "- GPU: AMD Radeon 8060S (gfx1151) — PyTorch ROCm twins",
        "- RAM: 94 GiB shared domain; OS Ubuntu 24.04, kernel 6.17",
        "- Python 3.12.3; OpenVINO 2026.4.x; PyTorch 2.14.1+rocm7.14; ROCm 7.2.1",
        "",
        "## Catalog: 171 notebooks",
        "",
        f"- CPU attempted (real attempt records): **{attempted}/171** ({round(100 * attempted / 171, 1)}%)",
        f"- CPU: {fmt_row(cpu, cpu_statuses)}",
        f"- GPU: {fmt_row(gpu, ['VERIFIED', 'VERIFIED_WITH_LIMITATIONS', 'FAILED', 'REVALIDATION_REQUIRED', 'NOT_TESTED'])}",
        "",
        f"- Validation levels seen (CPU): {dict(levels) or '{}'}",
        f"- Device-proof states seen (CPU): {dict(proofs) or '{}'}",
        f"- Top CPU failure categories: {dict(fail_cats.most_common(8))}",
        "",
        "## Green records (all evidence-backed, clickable)",
        "",
        "| Workload | Backend | Status | Device proof | Validation level | Runs ok | Evidence |",
        "|---|---|---|---|---|---|---|",
        *green_rows,
        "",
        "Legacy v0.1 greens are excluded from the counts above until revalidated",
        "(see reports/revalidation-migration.md); their historical evidence is",
        "preserved unmodified.",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({len(green_rows)} green rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
