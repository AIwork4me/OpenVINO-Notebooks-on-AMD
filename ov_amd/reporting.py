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
    """Repo-relative evidence path for public artifacts (no machine-local path
    leaks). Central implementation: ov_amd.public_paths."""

    from ov_amd.public_paths import sanitize_public_path

    if not p:
        return None
    out = sanitize_public_path(p)
    if out != p:
        return out
    m = re.search(r"(?:^|/)(results/[\w./-]+)$", p)
    if m:  # absolute evidence path from any checkout of this repo
        return m.group(1)
    return p


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _sanitize_note(text: str) -> str:
    """Public matrices must not leak local filesystem layout: strip ANSI codes
    and reduce machine-local repo paths to repo-relative ones (notes embed raw
    stderr excerpts, which contain e.g. venv/bin/python command lines)."""

    from ov_amd.public_paths import sanitize_public_text

    return sanitize_public_text(text)


def build_compatibility(
    catalog: list[NotebookEntry] | None = None, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    from ov_amd.outcomes import derive_outcome

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

        def _backend_fields(b: dict[str, Any], backend: str = "cpu") -> dict[str, Any]:
            outcome = b.get("compatibility_outcome") or ""
            reason = b.get("outcome_reason") or ""
            if not outcome:
                outcome_o, reason = derive_outcome(
                    b.get("status", Status.NOT_TESTED.value),
                    b.get("failure_category", ""),
                    "\n".join(b.get("notes") or []),
                    device_proof=b.get("device_proof", ""),
                    backend=backend,
                )
                outcome = outcome_o.value
            return {"compatibility_outcome": outcome, "outcome_reason": reason}

        cpu_fields = _backend_fields(cpu, "cpu")
        gpu_fields = _backend_fields(gpu, "gpu")
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
                "cpu_compatibility_outcome": cpu_fields["compatibility_outcome"],
                "cpu_outcome_reason": cpu_fields["outcome_reason"],
                "cpu_limitation_codes": cpu.get("limitation_codes", []),
                "cpu_evidence": _rel(cpu.get("evidence_dir")),
                "cpu_validation_level": cpu.get("validation_level", ""),
                "cpu_device_proof": cpu.get("device_proof", ""),
                "gpu_status": gpu.get("status", Status.NOT_TESTED.value),
                "gpu_failure_category": gpu.get("failure_category", ""),
                "gpu_compatibility_outcome": gpu_fields["compatibility_outcome"],
                "gpu_outcome_reason": gpu_fields["outcome_reason"],
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


def _freshness_line(pinned_commit: str) -> str:
    """Render the upstream-freshness signal from the last recorded check.

    The freshness check itself (scripts/check_upstream_freshness.py) is a
    separate networked workflow — README generation never requires network.
    It records `latest_commit` + `ahead_by` into reports/upstream-freshness.json;
    this renderer only formats the committed record. When upstream moved, the
    relevant scope is marked REVALIDATION_REQUIRED by the checker — historical
    result statuses are never silently rewritten."""

    fp = REPO_ROOT / "reports" / "upstream-freshness.json"
    try:
        rec = json.loads(fp.read_text())
    except (OSError, ValueError):
        return "UNKNOWN (no freshness check recorded yet)"
    ahead = int(rec.get("ahead_by", -1))
    latest = str(rec.get("latest_commit", ""))[:12]
    checked = str(rec.get("checked_at", ""))[:10]
    if ahead == 0:
        return f"**CURRENT** (verified {checked})"
    if ahead > 0:
        return f"**UPSTREAM AHEAD BY {ahead} COMMITS** (`{latest}`; checked {checked}; affected scope flagged REVALIDATION_REQUIRED)"
    return "UNKNOWN (freshness record unreadable)"


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # tolerate minimal synthetic rows (tests): derive outcome fields on demand
    for r in rows:
        r.setdefault("cpu_compatibility_outcome", r["cpu_status"])
        r.setdefault("gpu_compatibility_outcome", r["gpu_status"])
    c = {
        "total": len(rows),
        "cpu": Counter(r["cpu_status"] for r in rows),
        "gpu": Counter(r["gpu_status"] for r in rows),
        "twin_levels": Counter(r["twin_level"] for r in rows),
        "cpu_outcomes": Counter(r["cpu_compatibility_outcome"] for r in rows),
        "gpu_outcomes": Counter(r["gpu_compatibility_outcome"] for r in rows),
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
    # Successful-execution coverage: green+yellow over everything that could
    # have run (catalog minus NOT_APPLICABLE). Distinct from catalog coverage.
    na = sum(1 for r in rows if r["cpu_compatibility_outcome"] == "NOT_APPLICABLE")
    green = sum(1 for r in rows if r["cpu_compatibility_outcome"] in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS"))
    eligible = len(rows) - na
    out["cpu_successful_execution_coverage"] = {
        "verified": sum(1 for r in rows if r["cpu_compatibility_outcome"] == "VERIFIED"),
        "verified_with_limitations": sum(
            1 for r in rows if r["cpu_compatibility_outcome"] == "VERIFIED_WITH_LIMITATIONS"
        ),
        "eligible_total": eligible,
        "pct": round(100 * green / eligible, 1) if eligible else 0.0,
    }
    return out


def _rca_index() -> dict[str, str]:
    """workload id -> reports/upstream/ RCA file that documents it."""

    root = REPO_ROOT / "reports" / "upstream"
    if not root.is_dir():
        return {}
    import re as _re

    idx: dict[str, str] = {}
    for p in sorted(root.glob("rca-*.md")):
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        # RCA files document workloads on "**Workload(s)**/Workload:" lines as `id`
        m = _re.search(r"\*\*Workload\(?s?\)?\*\*:[^\n]*", text)
        span = m.group(0) if m else text[:400]
        for wid in _re.findall(r"`([\w.-]+)`", span):
            idx.setdefault(wid, f"reports/upstream/{p.name}")
        # cluster files list member workloads anywhere with backticks
        if "cluster" in p.name or "undiagnosed" in p.name:
            for wid in _re.findall(r"`([\w.-]+)`", text[:2000]):
                idx.setdefault(wid, f"reports/upstream/{p.name}")
    return idx


def write_compatibility() -> dict[str, Any]:
    from ov_amd.outcomes import OUTCOME_ICONS

    compat = build_compatibility()
    rca = _rca_index()
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(json.dumps(compat, indent=2))

    def _outcome_cell(outcome: str, reason: str) -> str:
        icon = OUTCOME_ICONS.get(outcome, "⏳")
        return f"{icon} {outcome}" + (f" ({reason})" if reason else "")

    lines = [
        "# Compatibility Matrix (generated)",
        "",
        f"Generated: {compat['generated']} — do not edit by hand; run `python -m ov_amd report`.",
        "",
        f"Total notebooks: **{compat['counts']['total']}** — "
        f"AMD CPU catalog coverage **{compat['counts']['cpu_attempted']}/{compat['counts']['total']}** "
        f"({compat['counts']['cpu_attempt_coverage_pct']}%). Coverage means every notebook has an AMD CPU "
        "validation outcome; it does not mean every notebook passed.",
        "",
        "Legend: ✅ VERIFIED · 🟡 VERIFIED_WITH_LIMITATIONS · 🌐 BLOCKED_NETWORK · 🔐 BLOCKED_MODEL_ACCESS · "
        "📦 BLOCKED_DEPENDENCY · ⏱️ BLOCKED_TIMEOUT · 💾 BLOCKED_RESOURCE · 🧩 FAILED_COMPATIBILITY · ➖ NOT_APPLICABLE",
        "",
        "## Outcome summary",
        "",
    ]
    oc = compat["counts"]["cpu_outcomes"]
    for outcome in (
        "VERIFIED",
        "VERIFIED_WITH_LIMITATIONS",
        "BLOCKED_NETWORK",
        "BLOCKED_MODEL_ACCESS",
        "BLOCKED_DEPENDENCY",
        "BLOCKED_TIMEOUT",
        "BLOCKED_RESOURCE",
        "FAILED_COMPATIBILITY",
        "NOT_APPLICABLE",
    ):
        if oc.get(outcome):
            lines.append(f"- {OUTCOME_ICONS[outcome]} {outcome}: {oc[outcome]}")
    sec = compat["counts"]["cpu_successful_execution_coverage"]
    lines += [
        "",
        "Successful-execution coverage (VERIFIED + VERIFIED_WITH_LIMITATIONS over eligible catalog): "
        f"**{sec['verified'] + sec['verified_with_limitations']}/{sec['eligible_total']} ({sec['pct']}%)** "
        f"— ✅ {sec['verified']} verified · 🟡 {sec['verified_with_limitations']} with limitations",
        "",
        "## Category summary",
        "",
        "| Category | Total | ✅ | 🟡 | Blocked | 🧩 | ➖ |",
        "|---|---|---|---|---|---|---|",
    ]
    blocked_set = {"BLOCKED_NETWORK", "BLOCKED_MODEL_ACCESS", "BLOCKED_DEPENDENCY", "BLOCKED_TIMEOUT", "BLOCKED_RESOURCE"}
    cats: dict[str, list[int]] = {}
    for r in compat["rows"]:
        c = cats.setdefault(r["category"], [0, 0, 0, 0, 0, 0])
        c[0] += 1
        o = r["cpu_compatibility_outcome"]
        if o == "VERIFIED":
            c[1] += 1
        elif o == "VERIFIED_WITH_LIMITATIONS":
            c[2] += 1
        elif o in blocked_set:
            c[3] += 1
        elif o == "FAILED_COMPATIBILITY":
            c[4] += 1
        elif o == "NOT_APPLICABLE":
            c[5] += 1
    for cat in sorted(cats, key=lambda k: -cats[k][0]):
        c = cats[cat]
        lines.append(f"| {cat} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} |")
    lines += [
        "",
        "## Full matrix",
        "",
        "| Notebook | Category | AMD Ryzen CPU | Validation Level | Outcome Reason | Radeon ROCm | Twin Level | Last Tested | Evidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in compat["rows"]:
        # links are relative to catalog/compatibility.md (../results/...) so
        # they resolve in the GitHub web UI, not only from the repo root
        ev_link = f"../{r['evidence']}" if r["evidence"] and not str(r["evidence"]).startswith(("../", "/")) else r["evidence"]
        ev = f"[link]({ev_link})" if r["evidence"] else "-"
        rca_link = rca.get(r["id"])
        if r["cpu_compatibility_outcome"] == "FAILED_COMPATIBILITY" and rca_link:
            ev += f" · [rca](../{rca_link})"
        last = (r["last_tested"] or "")[:10]
        lines.append(
            f"| [{r['id']}]({r['upstream_url']}) | {r['category']} "
            f"| {_outcome_cell(r['cpu_compatibility_outcome'], '')} "
            f"| {r['cpu_validation_level'] or '-'} "
            f"| {r['cpu_outcome_reason'] or '-'} "
            f"| {_outcome_cell(r['gpu_compatibility_outcome'], '')} "
            f"| {r['twin_level']} | {last} | {ev} |"
        )
    CATALOG_MD.write_text("\n".join(lines) + "\n")

    # README summary block — every number machine-generated (STEP 29: no
    # manual marketing numbers)
    gpu = compat["counts"]["gpu"]
    oc = compat["counts"]["cpu_outcomes"]
    sec = compat["counts"]["cpu_successful_execution_coverage"]
    na = oc.get("NOT_APPLICABLE", 0)
    meta = json.loads((REPO_ROOT / "upstream" / "openvino-notebooks.json").read_text()) \
        if (REPO_ROOT / "upstream" / "openvino-notebooks.json").exists() else {}
    blocked_total = sum(oc.get(k, 0) for k in (
        "BLOCKED_NETWORK", "BLOCKED_MODEL_ACCESS", "BLOCKED_DEPENDENCY", "BLOCKED_TIMEOUT", "BLOCKED_RESOURCE"))
    freshness = _freshness_line(meta.get("commit", ""))

    block = [
        "**AMD Ryzen CPU / OpenVINO**",
        "",
        f"### {compat['counts']['cpu_attempted']} / {compat['counts']['total']} — "
        f"{compat['counts']['cpu_attempt_coverage_pct']}% Catalog Coverage",
        "",
        "> **Coverage means every notebook in the pinned snapshot has a recorded AMD CPU "
        "validation outcome. It does NOT mean every notebook passed.**",
        "",
        f"Outcome totals: ✅ {oc.get('VERIFIED', 0)} Verified · "
        f"🟡 {oc.get('VERIFIED_WITH_LIMITATIONS', 0)} Verified with limitations · "
        f"🚧 {blocked_total} Blocked (network / model access / dependency / timeout / resource) · "
        f"🧩 {oc.get('FAILED_COMPATIBILITY', 0)} Compatibility failures · "
        f"➖ {oc.get('NOT_APPLICABLE', 0)} Not applicable",
        "",
        f"Successful executions: **{sec['verified'] + sec['verified_with_limitations']}/{sec['eligible_total']}** "
        f"of eligible notebooks ({sec['pct']}%; {na} N/A excluded) — ✅ {sec['verified']} verified · "
        f"🟡 {sec['verified_with_limitations']} with documented limitations.",
        "",
        "**AMD Radeon GPU / ROCm · PyTorch**",
        "",
        f"### {gpu.get('VERIFIED', 0)} verified high-value workload references",
        "",
        f"A growing, deliberately-curated set — explicitly **not** a catalog-wide sweep "
        f"(attempted {compat['counts']['gpu_attempted']}/{compat['counts']['total']}). "
        "The two numbers above have different denominators and different meanings.",
        "",
        f"Pinned snapshot `{str(meta.get('commit', ''))[:12]}` · freshness: {freshness} · "
        f"Evidence Schema **v2** · twin classification "
        f"**{compat['counts']['twin_classified']}/{compat['counts']['total']}** "
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


FEATURED_BEGIN = "<!-- generated:featured begin -->"
FEATURED_END = "<!-- generated:featured end -->"


CONCISE = {
    "VERIFIED": "✅ Verified",
    "VERIFIED_WITH_LIMITATIONS": "🟡 Limited",
    "BLOCKED_NETWORK": "🌐 Network blocked",
    "BLOCKED_MODEL_ACCESS": "🔐 Model access",
    "BLOCKED_DEPENDENCY": "📦 Dependency blocked",
    "BLOCKED_TIMEOUT": "⏱ Timeout",
    "BLOCKED_RESOURCE": "💾 Resource blocked",
    "FAILED_COMPATIBILITY": "🧩 Compat failure",
    "NOT_APPLICABLE": "➖ N/A",
    "NOT_TESTED": "⏳ Not tested",
}


def _evidence_link(ev: str | None, label: str = "evidence") -> str:
    if not ev:
        return "—"
    rel = ev if str(ev).startswith(("../", "/")) else f"../{ev}"
    # README-relative: results/... lives at repo root, so from README drop the ../
    if rel.startswith("../"):
        rel = rel[3:]
    return f"[{label}]({rel})"


def write_featured_matrix(compat: dict[str, Any] | None = None) -> bool:
    """Render the ROCm-verified workload matrix (README).

    Selection criterion (stated ABOVE the table): rows are the workloads
    VERIFIED on AMD Radeon GPUs via ROCm; the AMD Ryzen CPU column reports
    INDEPENDENT OpenVINO validation results for the same workload. The CPU
    outcome may be Verified, Limited, or Blocked — a Blocked result is not
    necessarily an AMD CPU compatibility failure."""

    compat = compat if compat is not None else build_compatibility()
    rows = [r for r in compat["rows"] if r["gpu_compatibility_outcome"] in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS")]
    if not rows:
        return False
    lines = [
        "This table intentionally selects workloads **verified on AMD Radeon GPUs using ROCm**. "
        "The **Ryzen CPU column reports independent OpenVINO validation results** for the same workload — "
        "CPU results may be Verified, Limited, or Blocked. A blocked result is not necessarily an AMD CPU "
        "compatibility failure. Each status links to its own evidence.",
        "",
        "| Workload | Ryzen CPU · OpenVINO | Radeon GPU · ROCm | Twin type |",
        "|---|---|---|---|",
    ]
    order = {"VERIFIED": 0, "VERIFIED_WITH_LIMITATIONS": 1}
    for r in sorted(rows, key=lambda r: (order.get(r["gpu_compatibility_outcome"], 9), r["id"])):
        cpu = CONCISE.get(r["cpu_compatibility_outcome"], r["cpu_compatibility_outcome"])
        gpu = CONCISE.get(r["gpu_compatibility_outcome"], r["gpu_compatibility_outcome"])
        cpu_cell = f"{cpu}" + (f" ([evidence]({r['cpu_evidence']}))" if r.get("cpu_evidence") else "")
        gpu_cell = f"{gpu}" + (f" ([evidence]({r['gpu_evidence']}))" if r.get("gpu_evidence") else "")
        lines.append(
            f"| [{r['id']}]({r['upstream_url']}) | {cpu_cell} | {gpu_cell} | {r['twin_level']} |"
        )
    if README.exists():
        text = README.read_text()
        block = "\n".join(lines)
        if FEATURED_BEGIN in text and FEATURED_END in text:
            pre, _, rest = text.partition(FEATURED_BEGIN)
            _, _, post = rest.partition(FEATURED_END)
            README.write_text(pre + FEATURED_BEGIN + "\n" + block + "\n" + FEATURED_END + post)
            return True
    return False


CPU_SHOWCASE_BEGIN = "<!-- generated:cpu-showcase begin -->"
CPU_SHOWCASE_END = "<!-- generated:cpu-showcase end -->"


def write_cpu_showcase(compat: dict[str, Any] | None = None, limit: int = 12) -> bool:
    """Independent AMD-CPU success showcase (mission Step 6.5).

    Selected from cpu_compatibility_outcome == VERIFIED (never GPU-selected),
    preferring high-value non-trivial categories. Full list: the compatibility
    matrix's VERIFIED filter."""

    compat = compat if compat is not None else build_compatibility()
    verified = [r for r in compat["rows"] if r["cpu_compatibility_outcome"] == "VERIFIED"]
    if not verified:
        return False
    high_value = ("LLM", "VLM", "Image Generation", "Video", "OCR", "TTS", "ASR", "Vision", "Detection")
    ranked = sorted(
        verified,
        key=lambda r: (0 if r["category"] in high_value else 1, r["id"]),
    )
    lines = [
        "Selected AMD-Ryzen-VERIFIED notebooks (CPU results only — this table is **not** "
        "GPU-selected; every row passed its validation contract on OpenVINO/CPU):",
        "",
        "| Workload | CPU status | Category | Evidence |",
        "|---|---|---|---|",
    ]
    for r in ranked[:limit]:
        ev = f"[evidence]({r['cpu_evidence']})" if r.get("cpu_evidence") else "—"
        lines.append(
            f"| [{r['id']}]({r['upstream_url']}) | ✅ Verified | {r['category']} | {ev} |"
        )
    lines += [
        "",
        f"…plus {len(verified) - min(limit, len(verified))} more VERIFIED rows in the "
        "[full compatibility matrix](catalog/compatibility.md).",
    ]
    if README.exists():
        text = README.read_text()
        if CPU_SHOWCASE_BEGIN in text and CPU_SHOWCASE_END in text:
            pre, _, rest = text.partition(CPU_SHOWCASE_BEGIN)
            _, _, post = rest.partition(CPU_SHOWCASE_END)
            README.write_text(
                pre + CPU_SHOWCASE_BEGIN + "\n" + "\n".join(lines) + "\n" + CPU_SHOWCASE_END + post
            )
            return True
    return False


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
    outcomes = Counter(
        (w.get("cpu") or {}).get("compatibility_outcome")
        for w in attempts.values()
        if (w.get("cpu") or {}).get("compatibility_outcome")
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
        f"- CPU failed (execution): {c['cpu'].get('FAILED', 0)}",
        f"- CPU blocked/skipped: {c['cpu'].get('BLOCKED', 0) + c['cpu'].get('SKIPPED_RESOURCE', 0)}",
        f"- CPU not tested: {c['cpu'].get('NOT_TESTED', 0)}",
        f"- GPU attempted: {c['gpu_attempted']} ({c['gpu_attempt_coverage_pct']}%)",
        f"- GPU verified: {c['gpu'].get('VERIFIED', 0)} (+{c['gpu'].get('VERIFIED_WITH_LIMITATIONS', 0)} limited)",
        f"- Twin classification: {c['twin_classified']}/{c['total']} ({c['twin_classification_coverage_pct']}%)",
        f"- Terminal attempt records: {done}",
        f"- Current workload: {current or state.get('current_workload', '-')}",
        "",
        "## CPU compatibility outcomes (developer-facing)",
        "",
    ]
    for outcome, n in outcomes.most_common():
        lines.append(f"- {outcome}: {n}")
    lines += ["", "## Top recurring CPU failure categories (execution taxonomy)", ""]
    for cat, n in fail_cats.most_common(10):
        lines.append(f"- {cat}: {n}")
    PROGRESS_MD.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_MD.write_text("\n".join(lines) + "\n")


def write_failures(state: dict[str, Any] | None = None) -> None:
    from ov_amd.outcomes import OUTCOME_ICONS, derive_outcome

    state = state if state is not None else load_state()
    groups: dict[str, list[dict[str, Any]]] = {}
    for wid, rec in state.get("attempts", {}).items():
        for backend in ("cpu", "gpu"):
            r = rec.get(backend)
            if r and r.get("status") in (Status.FAILED.value, Status.BLOCKED.value, Status.SKIPPED_RESOURCE.value):
                note = (r.get("notes") or [""])[-1]
                outcome = r.get("compatibility_outcome") or ""
                reason = r.get("outcome_reason") or ""
                if not outcome:
                    outcome_o, reason = derive_outcome(
                        r.get("status", ""),
                        r.get("failure_category", ""),
                        note,
                        device_proof=r.get("device_proof", ""),
                        backend=backend,
                    )
                    outcome = outcome_o.value
                key = f"{backend}:{outcome}" + (f":{reason}" if reason else "")
                groups.setdefault(key, []).append(
                    {"id": wid, "note": note[:220], "evidence": r.get("evidence_dir"), "reason": reason}
                )
    lines = [
        "# Failures (generated)",
        "",
        "Grouped by developer-facing compatibility outcome. BLOCKED_* outcomes are environment/"
        "network/model-access blockers — not AMD/OpenVINO compatibility failures. FAILED_COMPATIBILITY "
        "rows carry a reason identifying the failing layer.",
        "",
        f"Total non-green attempts: {sum(len(v) for v in groups.values())}",
        "",
    ]
    order = {
        "BLOCKED_NETWORK": 0,
        "BLOCKED_MODEL_ACCESS": 1,
        "BLOCKED_DEPENDENCY": 2,
        "BLOCKED_TIMEOUT": 3,
        "BLOCKED_RESOURCE": 4,
        "FAILED_COMPATIBILITY": 5,
    }
    for key in sorted(groups, key=lambda k: (order.get(k.split(":")[1], 9), -len(groups[k]))):
        parts = key.split(":")
        outcome = parts[1]
        icon = OUTCOME_ICONS.get(outcome, "⚫")
        reason = f" — {parts[2].replace('_', ' ').lower()}" if len(parts) > 2 else ""
        lines.append(f"## {icon} {key.replace(':', ' · ')}{reason} — {len(groups[key])} workload(s)")
        lines.append("")
        for it in groups[key][:60]:
            ev = f" (evidence: {it['evidence']})" if it.get("evidence") else ""
            note = _sanitize_note(it["note"]).strip()
            if not note or set(note) <= set("-;*=# "):
                note = it.get("reason") or "(no excerpt recorded — see evidence)"
            lines.append(f"- **{it['id']}** — {note}{ev}")
        lines.append("")
    FAILURES_MD.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_MD.write_text("\n".join(lines) + "\n")
