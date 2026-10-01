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


def build_compatibility(catalog: list[NotebookEntry] | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = catalog if catalog is not None else load_catalog()
    state = state if state is not None else load_state()
    attempts = state.get("attempts", {})
    rows = []
    for e in catalog:
        rec = attempts.get(e.id, {})
        cpu = rec.get("cpu", {})
        gpu = rec.get("gpu", {})
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
                "gpu_status": gpu.get("status", Status.NOT_TESTED.value),
                "gpu_failure_category": gpu.get("failure_category", ""),
                "twin_level": e.twin_level,
                "device_used": cpu.get("device_used", ""),
                "last_tested": cpu.get("updated", "") or gpu.get("updated", ""),
                "evidence": cpu.get("evidence_dir") or gpu.get("evidence_dir"),
                "notes": (cpu.get("notes") or []) + (gpu.get("notes") or []),
            }
        )
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "upstream": state.get("upstream", {}),
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
    return {k: (dict(v) if isinstance(v, Counter) else v) for k, v in c.items()}


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
        ev = f"[link]({r['evidence']})" if r["evidence"] else "-"
        last = (r["last_tested"] or "")[:10]
        lines.append(
            f"| [{r['id']}]({r['upstream_url']}) | {r['category']} "
            f"| {_icon(r['cpu_status'])} {r['cpu_status']} | {_icon(r['gpu_status'])} {r['gpu_status']} "
            f"| {r['twin_level']} | {last} | {ev} |"
        )
    CATALOG_MD.write_text("\n".join(lines) + "\n")

    # README summary block
    cpu = compat["counts"]["cpu"]
    gpu = compat["counts"]["gpu"]
    block = [
        f"**{compat['counts']['total']} notebooks catalogued** — "
        f"CPU: ✅ {cpu.get('VERIFIED', 0)} verified, 🟡 {cpu.get('VERIFIED_WITH_LIMITATIONS', 0)} limited, "
        f"🔴 {cpu.get('FAILED', 0)} failed, ⚫ {cpu.get('SKIPPED_RESOURCE', 0) + cpu.get('BLOCKED', 0)} blocked/skipped "
        f"| GPU: ✅ {gpu.get('VERIFIED', 0)}, 🟡 {gpu.get('VERIFIED_WITH_LIMITATIONS', 0)}",
        "",
        "Full matrix: [catalog/compatibility.md](catalog/compatibility.md)",
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
    done = sum(1 for w in attempts.values() for b in ("cpu", "gpu") if b in w and w[b].get("status")
               in (s.value for s in Status if s.value not in ("QUEUED", "RUNNING")))
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
        f"- CPU attempted: {sum(c['cpu'].values())}",
        f"- CPU verified: {c['cpu'].get('VERIFIED', 0)}",
        f"- CPU verified with limitations: {c['cpu'].get('VERIFIED_WITH_LIMITATIONS', 0)}",
        f"- CPU failed: {c['cpu'].get('FAILED', 0)}",
        f"- CPU blocked/skipped: {c['cpu'].get('BLOCKED', 0) + c['cpu'].get('SKIPPED_RESOURCE', 0)}",
        f"- GPU verified: {c['gpu'].get('VERIFIED', 0)} (+{c['gpu'].get('VERIFIED_WITH_LIMITATIONS', 0)} limited)",
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
            lines.append(f"- **{it['id']}** — {it['note']}")
        lines.append("")
    FAILURES_MD.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_MD.write_text("\n".join(lines) + "\n")
