"""Report and compatibility-matrix generation.

Generated artifacts (never hand-maintained):
  catalog/compatibility.json
  catalog/compatibility.md
  reports/marathon-progress.md
  reports/failures.md
  README.md status-summary block (between GENERATED markers)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ov_amd.environment import REPO_ROOT
from ov_amd.scheduler import load_catalog, load_state
from ov_amd.schemas import STATUS_ICONS, NotebookEntry, Status

CATALOG_MD = REPO_ROOT / "catalog" / "compatibility.md"
CATALOG_JSON = REPO_ROOT / "catalog" / "compatibility.json"
PROGRESS_MD = REPO_ROOT / "reports" / "marathon-progress.md"
FAILURES_MD = REPO_ROOT / "reports" / "failures.md"
README = REPO_ROOT / "README.md"

README_BEGIN = "<!-- generated:compatibility begin -->"
README_END = "<!-- generated:compatibility end -->"


def _icon(status: str) -> str:
    return STATUS_ICONS.get(status, "⏳")


def _rel(p: str | None) -> str | None:
    """Repo-relative evidence path for public artifacts (no /home/... leaks).

    Handles both current repo-relative refs and stale absolute refs written by
    runners on other machines (state migration keeps those records historical).
    """

    if not p:
        return None
    # strip any known runner-local repo prefix, then any absolute path that
    # still points inside a checkout of this repository
    for prefix in (f"{REPO_ROOT}/", "/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/"):
        if p.startswith(prefix):
            return p[len(prefix):]
    m = re.search(r"(?:^|/)(results/[\w./-]+)$", p)
    if m:  # absolute evidence path from any checkout of this repo
        return m.group(1)
    return p


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _sanitize_note(text: str) -> str:
    """Public matrices must not leak local filesystem layout: strip ANSI codes
    and reduce absolute repo paths to repo-relative ones (notes embed raw
    stderr excerpts, which contain e.g. .venv-cpu/bin/python command lines)."""

    text = _ANSI_RE.sub("", text)
    return text.replace(f"{REPO_ROOT}/", "").replace(str(REPO_ROOT), ".")


def build_compatibility(
    catalog: list[NotebookEntry] | None = None, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    catalog = catalog if catalog is not None else load_catalog()
    state = state if state is not None else load_state()
    attempts = state.get("attempts", {})
    rows = []
    for e in catalog:
        rec = attempts.get(e.id, {})
        cpu = rec.get("cpu", {})
        gpu = rec.get("gpu", {})
        # the public Evidence link must point at the evidence of the claim it
        # sits next to: GPU evidence when the GPU path is the verified one
        if str(gpu.get("status", "")).startswith("VERIFIED") and gpu.get("evidence_dir"):
            evidence = gpu["evidence_dir"]
        else:
            evidence = cpu.get("evidence_dir") or gpu.get("evidence_dir")
        rows.append(
            {
                "id": e.id,
                "title": e.title,
                "category": e.category,
                "upstream_path": e.upstream_path,
                "upstream_url": e.upstream_url,
                "priority": e.priority,
                "cpu_status": cpu.get("status", Status.NOT_TESTED.value),
                "cpu_failure_category": cpu.get("failure_category", ""),
                "cpu_evidence": _rel(cpu.get("evidence_dir")),
                "cpu_validation_level": cpu.get("validation_level", ""),
                "cpu_device_proof": cpu.get("device_proof", ""),
                "gpu_status": gpu.get("status", Status.NOT_TESTED.value),
                "gpu_failure_category": gpu.get("failure_category", ""),
                "gpu_evidence": _rel(gpu.get("evidence_dir")),
                "gpu_validation_level": gpu.get("validation_level", ""),
                "gpu_device_proof": gpu.get("device_proof", ""),
                "twin_level": e.twin_level,
                "device_used": cpu.get("device_used", ""),
                "last_tested": cpu.get("updated", "") or gpu.get("updated", ""),
                "evidence": _rel(evidence),
                "notes": [_sanitize_note(n) for n in ((cpu.get("notes") or []) + (gpu.get("notes") or []))],
            }
        )
    upstream_public = {k: v for k, v in (state.get("upstream", {}) or {}).items() if k != "local_path"}
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "upstream": upstream_public,
        "counts": _counts(rows),
        "rows": rows,
    }


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    c = {
        "total": len(rows),
        "cpu": Counter(r["cpu_status"] for r in rows),
        "gpu": Counter(r["gpu_status"] for r in rows),
        "twin_levels": Counter(r["twin_level"] for r in rows),
    }
    out = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in c.items()}
    # Defect I closure: "attempted" counts only real attempt records, never the
    # default catalog NOT_TESTED rows.
    for backend in ("cpu", "gpu"):
        statuses = [r[f"{backend}_status"] for r in rows]
        attempted = sum(1 for s in statuses if s != Status.NOT_TESTED.value)
        out[f"{backend}_attempted"] = attempted
        out[f"{backend}_attempt_coverage_pct"] = round(100 * attempted / len(rows), 1) if rows else 0.0
    classified = sum(1 for r in rows if r["twin_level"] != "NOT_CLASSIFIED")
    out["twin_classified"] = classified
    out["twin_classification_coverage_pct"] = round(100 * classified / len(rows), 1) if rows else 0.0
    return out


def write_compatibility() -> dict[str, Any]:
    compat = build_compatibility()
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(json.dumps(compat, indent=2))

    lines = [
        "# Compatibility Matrix (generated)",
        "",
        f"Generated: {compat['generated']} — do not edit by hand; run `python -m ov_amd report`.",
        "",
        f"Total notebooks: **{compat['counts']['total']}**",
        "",
        "| Notebook | Category | Ryzen CPU / OpenVINO | Radeon GPU / ROCm | Twin | Last Tested | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in compat["rows"]:
        # links are relative to catalog/compatibility.md (../results/...) so
        # they resolve in the GitHub web UI, not only from the repo root
        ev_link = f"../{r['evidence']}" if r["evidence"] and not str(r["evidence"]).startswith(("../", "/")) else r["evidence"]
        ev = f"[link]({ev_link})" if r["evidence"] else "-"
        last = (r["last_tested"] or "")[:10]
        lines.append(
            f"| [{r['id']}]({r['upstream_url']}) | {r['category']} "
            f"| {_icon(r['cpu_status'])} {r['cpu_status']} | {_icon(r['gpu_status'])} {r['gpu_status']} "
            f"| {r['twin_level']} | {last} | {ev} |"
        )
    CATALOG_MD.write_text("\n".join(lines) + "\n")

    # README summary block — every number machine-generated (STEP 29: no
    # manual marketing numbers)
    cpu = compat["counts"]["cpu"]
    gpu = compat["counts"]["gpu"]
    meta = json.loads((REPO_ROOT / "upstream" / "openvino-notebooks.json").read_text()) \
        if (REPO_ROOT / "upstream" / "openvino-notebooks.json").exists() else {}

    block = [
        f"**{compat['counts']['total']} notebooks catalogued** · Evidence Schema **v2** · "
        f"upstream `{str(meta.get('commit', ''))[:12]}`",
        "",
        f"CPU (OpenVINO, Ryzen): **{compat['counts']['cpu_attempted']}/{compat['counts']['total']} attempted** "
        f"({compat['counts']['cpu_attempt_coverage_pct']}%) — "
        f"✅ {cpu.get('VERIFIED', 0)} L3 verified · 🟡 {cpu.get('VERIFIED_WITH_LIMITATIONS', 0)} limited · "
        f"🔵 {cpu.get('REVALIDATION_REQUIRED', 0)} revalidation required · "
        f"🔴 {cpu.get('FAILED', 0)} failed · "
        f"⚫ {cpu.get('SKIPPED_RESOURCE', 0) + cpu.get('BLOCKED', 0)} blocked/skipped · "
        f"➖ {cpu.get('NOT_APPLICABLE', 0)} n/a · ⏳ {cpu.get('NOT_TESTED', 0)} not tested",
        "",
        f"GPU (ROCm twins, Radeon): ✅ {gpu.get('VERIFIED', 0)} verified · "
        f"🟡 {gpu.get('VERIFIED_WITH_LIMITATIONS', 0)} limited · "
        f"🔵 {gpu.get('REVALIDATION_REQUIRED', 0)} revalidation required",
        "",
        f"Twin classification: **{compat['counts']['twin_classified']}/{compat['counts']['total']}** "
        f"({compat['counts']['twin_classification_coverage_pct']}%)",
        "",
        "Full matrix: [catalog/compatibility.md](catalog/compatibility.md) · "
        "Methodology: [docs/validation-policy.md](docs/validation-policy.md) · "
        "[benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md)",
    ]
    if README.exists():
        text = README.read_text()
        if README_BEGIN in text and README_END in text:
            pre, _, rest = text.partition(README_BEGIN)
            _, _, post = rest.partition(README_END)
            README.write_text(pre + README_BEGIN + "\n" + "\n".join(block) + "\n" + README_END + post)
    return compat


def write_progress(state: dict[str, Any] | None = None, current: str | None = None) -> None:
    state = state if state is not None else load_state()
    compat = build_compatibility(state=state)
    c = compat["counts"]
    attempts = state.get("attempts", {})
    done = sum(
        1
        for w in attempts.values()
        for b in ("cpu", "gpu")
        if b in w and w[b].get("status") in (s.value for s in Status if s.value not in ("QUEUED", "RUNNING"))
    )
    fail_cats = Counter(
        (w.get("cpu") or {}).get("failure_category")
        for w in attempts.values()
        if (w.get("cpu") or {}).get("failure_category")
    )
    lines = [
        "# Marathon Progress (generated)",
        "",
        f"Updated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        f"- Catalog discovered: {c['total']}",
        f"- CPU attempted: {c['cpu_attempted']} ({c['cpu_attempt_coverage_pct']}% of catalog; attempt records only, NOT_TESTED excluded)",
        f"- CPU verified: {c['cpu'].get('VERIFIED', 0)}",
        f"- CPU verified with limitations: {c['cpu'].get('VERIFIED_WITH_LIMITATIONS', 0)}",
        f"- CPU failed: {c['cpu'].get('FAILED', 0)}",
        f"- CPU blocked/skipped: {c['cpu'].get('BLOCKED', 0) + c['cpu'].get('SKIPPED_RESOURCE', 0)}",
        f"- CPU not tested: {c['cpu'].get('NOT_TESTED', 0)}",
        f"- GPU attempted: {c['gpu_attempted']} ({c['gpu_attempt_coverage_pct']}%)",
        f"- GPU verified: {c['gpu'].get('VERIFIED', 0)} (+{c['gpu'].get('VERIFIED_WITH_LIMITATIONS', 0)} limited)",
        f"- Twin classification: {c['twin_classified']}/{c['total']} ({c['twin_classification_coverage_pct']}%)",
        f"- Terminal attempt records: {done}",
        f"- Current workload: {current or state.get('current_workload', '-')}",
        "",
        "## Top recurring CPU failure categories",
        "",
    ]
    for cat, n in fail_cats.most_common(10):
        lines.append(f"- {cat}: {n}")
    PROGRESS_MD.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_MD.write_text("\n".join(lines) + "\n")


def write_failures(state: dict[str, Any] | None = None) -> None:
    state = state if state is not None else load_state()
    groups: dict[str, list[dict[str, Any]]] = {}
    for wid, rec in state.get("attempts", {}).items():
        for backend in ("cpu", "gpu"):
            r = rec.get(backend)
            if r and r.get("status") == Status.FAILED.value:
                note = (r.get("notes") or [""])[-1]
                key = f"{backend}:{r.get('failure_category', 'UNKNOWN')}"
                groups.setdefault(key, []).append({"id": wid, "note": note[:220], "evidence": r.get("evidence_dir")})
    lines = ["# Failures (generated)", "", f"Total failed attempts: {sum(len(v) for v in groups.values())}", ""]
    for key in sorted(groups, key=lambda k: -len(groups[k])):
        lines.append(f"## {key} — {len(groups[key])} workload(s)")
        lines.append("")
        for it in groups[key][:50]:
            lines.append(f"- **{it['id']}** — {_sanitize_note(it['note'])}")
        lines.append("")
    FAILURES_MD.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_MD.write_text("\n".join(lines) + "\n")
