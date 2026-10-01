"""Priority scheduler and marathon checkpoint state."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ov_amd.environment import REPO_ROOT
from ov_amd.schemas import NotebookEntry, Status

STATE_PATH = REPO_ROOT / "results" / "marathon-state.json"

TIER_TIMEOUTS = {  # seconds, wall clock per attempt
    "small": 10 * 60,
    "medium": 30 * 60,
    "large": 60 * 60,
    "huge": 90 * 60,
}

MIN_DISK_MB = 20_000  # stop scheduling below ~20 GB free
MIN_RAM_MB = 6_000


def load_catalog(path: Path | None = None) -> list[NotebookEntry]:
    import yaml

    p = path or (REPO_ROOT / "catalog" / "notebooks.yaml")
    data = yaml.safe_load(p.read_text()) or {}
    return [NotebookEntry.from_dict(e) for e in data.get("notebooks", [])]


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "upstream": {},
        "attempts": {},  # workload_id -> {"cpu": {...}, "gpu": {...}}
        "installed_extras": [],
        "last_checkpoint": None,
    }


def save_state(state: dict[str, Any]) -> None:
    """Merge-on-write checkpoint.

    The CPU marathon and GPU twin runners are separate processes writing the
    same file; a blind overwrite clobbers concurrent records. Each attempt
    record carries `updated`, so the newest per (workload, backend) wins.
    """

    if STATE_PATH.exists():
        try:
            disk = json.loads(STATE_PATH.read_text())
            disk_att = disk.get("attempts", {})
            mem_att = state.setdefault("attempts", {})
            for wid, recs in disk_att.items():
                for backend, rec in recs.items():
                    mine = mem_att.get(wid, {}).get(backend)
                    if mine is None or str(rec.get("updated", "")) > str(mine.get("updated", "")):
                        mem_att.setdefault(wid, {})[backend] = rec
            extras = state.setdefault("installed_extras", [])
            seen = {json.dumps(e, sort_keys=True) for e in extras}
            for e in disk.get("installed_extras", []):
                k = json.dumps(e, sort_keys=True)
                if k not in seen:
                    extras.append(e)
        except (OSError, json.JSONDecodeError):
            pass
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["last_checkpoint"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_PATH)


def counts(state: dict[str, Any], backend: str = "cpu") -> dict[str, int]:
    c = {s.value: 0 for s in Status}
    for w in state.get("attempts", {}).values():
        st = (w.get(backend) or {}).get("status")
        if st:
            c[st] = c.get(st, 0) + 1
    c["TOTAL"] = len(state.get("attempts", {}))
    return c


def order_workloads(entries: list[NotebookEntry]) -> list[NotebookEntry]:
    weight_rank = {"small": 0, "medium": 1, "large": 2, "huge": 3}
    return sorted(entries, key=lambda e: (e.priority, weight_rank.get(e.est_weight, 2), e.id))


def resources_ok() -> tuple[bool, str]:
    from ov_amd.environment import disk_free_mb, ram_available_mb

    if disk_free_mb() < MIN_DISK_MB:
        return False, f"disk below {MIN_DISK_MB}MB"
    if ram_available_mb() < MIN_RAM_MB:
        return False, f"available RAM below {MIN_RAM_MB}MB"
    return True, ""


def next_runnable(
    entries: list[NotebookEntry],
    state: dict[str, Any],
    backend: str = "cpu",
    retry_failed: bool = False,
) -> list[NotebookEntry]:
    """Entries still needing an attempt on this backend, in schedule order."""

    def needs_attempt(e: NotebookEntry) -> bool:
        rec = state["attempts"].get(e.id, {}).get(backend)
        if rec is None:
            return True
        st = rec.get("status")
        if st in (Status.QUEUED.value, Status.RUNNING.value, Status.REVALIDATION_REQUIRED.value):
            return True  # interrupted mid-run or pending revalidation
        if retry_failed and st == Status.FAILED.value:
            return True
        return False

    runnable = [e for e in order_workloads(entries) if needs_attempt(e)]
    return runnable


def checkpoint(state: dict[str, Any], workload_id: str | None = None) -> None:
    state.setdefault("current_workload", None)
    if workload_id is not None:
        state["current_workload"] = workload_id
    save_state(state)
    time.sleep(0)  # yield; keeps call sites honest about periodic checkpointing
