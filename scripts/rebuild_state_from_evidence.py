#!/usr/bin/env python3
"""Rebuild marathon-state attempt records from their evidence directories.

The state JSON is a resumable checkpoint INDEX of the evidence tree. When the
index is lost or reverted while the evidence directories survive, each record
can be reconstructed losslessly from the Evidence Schema v2 files the runner
already wrote per attempt (execution.json, device-proof.json, validation.json,
aggregate.json, environment.lock.json, upstream.json). Reconstruction only
accepts evidence bound to the CURRENT pin and always records its provenance.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.outcomes import derive_outcome  # noqa: E402
from ov_amd.scheduler import load_state, save_state  # noqa: E402
from ov_amd.state_machine import enforce_transition  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
PIN = json.loads((REPO / "upstream" / "openvino-notebooks.json").read_text())["commit"]

_STATUS_BY_EXEC = {"OK": "VERIFIED", "ERROR": "FAILED", "TIMEOUT": "FAILED"}


def _latest_pin_evidence(wid: str, backend: str) -> Path | None:
    root = RESULTS / wid
    if not root.is_dir():
        return None
    best: Path | None = None
    for ev in root.glob(f"*-{backend}"):
        up = ev / "upstream.json"
        if not up.exists():
            continue
        try:
            if json.loads(up.read_text()).get("commit") != PIN:
                continue
        except (OSError, ValueError):
            continue
        if best is None or ev.name > best.name:
            best = ev
    return best


def _rebuild(wid: str, backend: str, ev: Path) -> dict | None:
    runs = sorted(ev.glob("run-*"))
    if not runs:
        return None
    last = runs[-1]
    try:
        execj = json.loads((last / "execution.json").read_text())
        proof = json.loads((ev / "device-proof.json").read_text())
    except (OSError, ValueError):
        return None
    ok_runs = 0
    durations = []
    for r in runs:
        try:
            e = json.loads((r / "execution.json").read_text())
            if e.get("status") == "OK":
                ok_runs += 1
                durations.append(float(e.get("duration_s", 0)))
        except (OSError, ValueError):
            continue
    status = _STATUS_BY_EXEC.get(execj.get("status", "ERROR"), "FAILED")
    if status == "VERIFIED" and ok_runs < 3:
        status = "VERIFIED_WITH_LIMITATIONS"
    notes = [f"ok_runs={ok_runs}: reconstructed from evidence by v0.2.2 index rebuild"]
    if status == "VERIFIED_WITH_LIMITATIONS" and ok_runs < 3:
        notes.append("repeatability_not_established: fewer than 3 successful runs")
    outcome, reason = derive_outcome(
        status,
        execj.get("failure_category", ""),
        "\n".join(notes),
        device_proof=proof.get("state", ""),
        backend=backend,
    )
    val_level = ""
    try:
        v = json.loads((ev / "validation.json").read_text())
        val_level = v.get("level", "")
    except (OSError, ValueError):
        pass
    env = {}
    try:
        env = json.loads((ev / "environment.lock.json").read_text()).get("env", env)
    except (OSError, ValueError):
        pass
    updated = execj.get("end") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "status": status,
        "failure_category": execj.get("failure_category", ""),
        "compatibility_outcome": outcome.value,
        "outcome_reason": reason,
        "ok_runs": ok_runs,
        "required_runs": 3 if status.startswith("VERIFIED") and ok_runs >= 3 else max(ok_runs, 1),
        "durations_s": durations,
        "device_used": proof.get("supporting_device_used", ""),
        "device_proof": proof.get("state", ""),
        "validation_level": val_level,
        "platform_id": json.loads((ev / "hardware.json").read_text()).get("platform_id", "")
        if (ev / "hardware.json").exists()
        else "",
        "evidence_dir": str(ev.relative_to(REPO)),
        "env": env,
        "notes": notes,
        "updated": updated,
    }


def main() -> int:
    only = set(sys.argv[1:])
    state = load_state()
    rebuilt = []
    for wid in sorted(p.name for p in RESULTS.iterdir() if p.is_dir()):
        if only and wid not in only:
            continue
        for backend in ("cpu", "gpu"):
            ev = _latest_pin_evidence(wid, backend)
            if ev is None:
                continue
            rec = _rebuild(wid, backend, ev)
            if rec is None:
                continue
            cur = state.get("attempts", {}).get(wid, {}).get(backend, {})
            if str(cur.get("evidence_dir", "")) == rec["evidence_dir"]:
                continue  # index already points at this evidence
            enforce_transition(
                cur.get("status"), rec["status"], force=True, context=f"rebuild:{wid}/{backend}"
            )
            rec["notes"] = (cur.get("notes") or [])[-4:] + rec["notes"]
            state.setdefault("attempts", {}).setdefault(wid, {})[backend] = rec
            rebuilt.append(f"{wid}/{backend}: {cur.get('status')} -> {rec['status']} ({rec['evidence_dir']})")
    if rebuilt:
        save_state(state)
    for line in rebuilt:
        print(line)
    print(f"rebuilt {len(rebuilt)} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
