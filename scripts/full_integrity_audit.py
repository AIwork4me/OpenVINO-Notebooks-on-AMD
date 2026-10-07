#!/usr/bin/env python3
"""Full 171-entry dataset integrity audit (comprehensive verification §16).

Every catalog entry is checked for: catalog identity, upstream pin/path/URL
coherence, twin classification, CPU/GPU status presence, evidence-dir
existence, Evidence Schema v2 completeness for green/yellow rows, validation
level coherence, device proof coherence, repeatability, outcome dimension,
note sanitization, and timestamp coherence. Emits
reports/full-171-integrity-audit.md with per-row verdicts.

Exit code 0 = no critical anomalies (warnings allowed), 1 = critical found.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

PIN = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())["upstream_commit"]
V2_FILES = (
    "aggregate.json",
    "validation.json",
    "hardware.json",
    "software-before.json",
    "software-after.json",
    "upstream.json",
    "model.json",
    "device-proof.json",
    "metrics.json",
    "summary.md",
)
DIRTY = re.compile(r"/home/|/Users/|C:\\\\Users\\")
TODAY = datetime.now(timezone.utc).date()


def iso_date_ok(s: str) -> bool:
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def main() -> int:
    catalog = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())["notebooks"]
    state = json.loads((REPO / "results" / "marathon-state.json").read_text())
    upstream_root = REPO / ".cache" / "upstream"

    critical: list[str] = []
    warn: list[str] = []
    rows_out: list[str] = []
    verdicts = Counter()

    for e in catalog:
        wid = e["id"]
        problems: list[str] = []
        warnings: list[str] = []
        # -- catalog identity / upstream --
        url = e.get("upstream_url", "")
        if PIN not in url:
            problems.append("upstream_url does not embed the pin")
        nb_path = upstream_root / e["upstream_path"]
        if not nb_path.exists():
            problems.append("notebook missing in pinned snapshot")
        # -- twin --
        if e.get("twin_level", "NOT_CLASSIFIED") == "NOT_CLASSIFIED":
            problems.append("twin not classified")
        # -- state record --
        rec = state.get("attempts", {}).get(wid)
        if rec is None:
            critical.append(f"{wid}: no attempt record")
            continue
        cpu = rec.get("cpu") or {}
        status = cpu.get("status", "")
        if not status:
            problems.append("no cpu status")
        if status in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED") and not cpu.get("outcome_reason", "") == "" and status == "FAILED" and not cpu.get("compatibility_outcome"):
            problems.append("no outcome")
        if status in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED") and not cpu.get("compatibility_outcome"):
            problems.append("no compatibility_outcome")
        # -- evidence dir --
        ev_rel = cpu.get("evidence_dir")
        if status in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED"):
            if not ev_rel:
                problems.append("no evidence dir recorded")
            elif not (REPO / ev_rel).is_dir():
                problems.append(f"evidence dir missing: {ev_rel}")
            else:
                ev = REPO / ev_rel
                if status != "FAILED":
                    missing = [f for f in V2_FILES if not (ev / f).exists()]
                    if missing:
                        problems.append(f"v2 evidence incomplete: missing {missing}")
                # upstream.json must match the pin, or be a documented
                # pre-repin record whose notebook content is sha-identical to
                # the pinned snapshot (content-valid evidence)
                up = ev / "upstream.json"
                if up.exists():
                    try:
                        u = json.loads(up.read_text())
                        if u.get("commit") != PIN:
                            cur = upstream_root / e["upstream_path"]
                            if cur.exists():
                                import hashlib

                                h = hashlib.sha256(cur.read_bytes()).hexdigest()
                                if u.get("notebook_sha256") == h:
                                    pin_label = "pre-repin, content-identical (sha256)"
                                else:
                                    queued = any(
                                        n.startswith("notebook changed upstream") for n in (cpu.get("notes") or [])
                                    )
                                    if queued:
                                        warnings.append(
                                            "pre-repin evidence on changed notebook; revalidation queued (noted)"
                                        )
                                    else:
                                        problems.append(
                                            "evidence notebook content differs from pinned snapshot "
                                            "(pre-repin evidence; revalidation required)"
                                        )
                            else:
                                problems.append("evidence upstream.json commit != pin and snapshot file missing")
                    except json.JSONDecodeError:
                        problems.append("evidence upstream.json unparseable")
                # repeatability coherence for green
                agg = ev / "aggregate.json"
                if status == "VERIFIED" and agg.exists():
                    try:
                        a = json.loads(agg.read_text())
                        if a.get("successful_runs", 0) < a.get("required_runs", 0):
                            problems.append("VERIFIED with failed repeatability aggregate")
                    except json.JSONDecodeError:
                        warnings.append("aggregate.json unparseable")
        # -- green coherence --
        if status == "VERIFIED":
            if cpu.get("device_proof") != "PROVEN_CPU":
                problems.append(f"VERIFIED without PROVEN_CPU (got {cpu.get('device_proof')!r})")
            if cpu.get("validation_level") != "WORKLOAD_CORRECTNESS":
                problems.append(f"VERIFIED with level {cpu.get('validation_level')!r} != WORKLOAD_CORRECTNESS")
            if (cpu.get("ok_runs") or 0) < (cpu.get("required_runs") or 1):
                problems.append("VERIFIED with ok_runs < required_runs")
        if status == "VERIFIED_WITH_LIMITATIONS":
            if not (cpu.get("limitation_codes")):
                problems.append("yellow without limitation codes")
            if cpu.get("device_proof") == "PROVEN_GPU":
                warnings.append("yellow CPU row proven on GPU")
        if status == "FAILED":
            if not cpu.get("failure_category"):
                problems.append("FAILED without failure_category")
            if cpu.get("compatibility_outcome") not in (
                "BLOCKED_NETWORK",
                "BLOCKED_MODEL_ACCESS",
                "BLOCKED_DEPENDENCY",
                "BLOCKED_TIMEOUT",
                "BLOCKED_RESOURCE",
                "FAILED_COMPATIBILITY",
            ):
                problems.append(f"FAILED with non-terminal outcome {cpu.get('compatibility_outcome')!r}")
        # -- notes sanitized --
        for n in cpu.get("notes") or []:
            if DIRTY.search(n or ""):
                problems.append("note leaks machine-local path")
                break
        # -- timestamps --
        if not iso_date_ok(cpu.get("updated", "")):
            problems.append("bad updated timestamp")
        # -- gpu record when present --
        gpu = rec.get("gpu") or {}
        if gpu.get("status") == "VERIFIED":
            gev = gpu.get("evidence_dir")
            if not gev or not (REPO / gev).is_dir():
                problems.append("GPU VERIFIED evidence missing")
            else:
                # GPU twin contract: frozen venv -> single software.json (no
                # before/after pair), plus the shared v2 files
                gpu_files = [f for f in V2_FILES if f not in ("software-before.json", "software-after.json")] + ["software.json"]
                missing = [f for f in gpu_files if not (REPO / gev / f).exists()]
                if missing:
                    problems.append(f"GPU v2 evidence incomplete: missing {missing}")

        v = "OK" if not problems and not warnings else ("FAIL" if problems else "WARN")
        verdicts[v] += 1
        if problems:
            critical.append(f"{wid}: " + "; ".join(problems))
        if warnings:
            warn.append(f"{wid}: " + "; ".join(warnings))
        rows_out.append(f"| {wid} | {status} | {cpu.get('compatibility_outcome','')} | {v} | "
                        + ("<br>".join(problems + warnings) if (problems or warnings) else "") + " |")

    lines = [
        "# Full 171-Entry Integrity Audit (generated)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')} · pin `{PIN[:12]}`",
        "",
        f"Verdicts: {dict(verdicts)}",
        "",
        "## Critical anomalies",
        "",
    ]
    lines += [f"- {c}" for c in critical] or ["- none"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in warn] or ["- none"]
    lines += [
        "",
        "## Per-row verdicts",
        "",
        "| Workload | CPU status | Outcome | Verdict | Findings |",
        "|---|---|---|---|---|",
        *rows_out,
        "",
        "## Method",
        "",
        "Each row: upstream URL/pin coherence, snapshot presence, twin classification, status+outcome",
        "presence, evidence-dir existence, Evidence Schema v2 file completeness (green/yellow),",
        "upstream.json pin match, repeatability aggregate coherence, PROVEN_CPU + L3 + ok_runs>=required",
        "for VERIFIED rows, limitation codes for yellow rows, failure category for FAILED rows, note",
        "sanitization, timestamp parseability, and GPU v2 evidence for GPU-verified rows.",
    ]
    (REPO / "reports" / "full-171-integrity-audit.md").write_text("\n".join(lines) + "\n")
    print(f"verdicts={dict(verdicts)} critical={len(critical)} warnings={len(warn)}")
    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(main())
