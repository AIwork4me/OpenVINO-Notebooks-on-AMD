"""workloads/<id>/workload.yaml mirror synchronization.

The marathon-state JSON is the source of truth for per-backend statuses; the
catalog is the source of truth for twin levels. Manifests mirror both for
humans browsing workloads/. Mirrors drift when records are corrected directly
in state (release-audit corrections) or when GPU twins are recorded without
mirroring (the pre-closure `_record_gpu` gap). This module regenerates the
mirrors deterministically from the sources of truth — never the reverse.
"""

from __future__ import annotations

import json
from typing import Any

import yaml

from ov_amd.environment import REPO_ROOT
from ov_amd.scheduler import load_catalog, load_state

WORKLOADS_DIR = REPO_ROOT / "workloads"


def mirror_into_manifest(workload_id: str, backend: str, status: str, verified_now: str | None = None) -> None:
    """Mirror one backend status into workloads/<id>/workload.yaml (safe no-op
    when the manifest or status is unchanged)."""

    wf = WORKLOADS_DIR / workload_id / "workload.yaml"
    if not wf.exists():
        return
    try:
        cfg = yaml.safe_load(wf.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return
    changed = False
    slot = cfg.setdefault(backend, {})
    if slot.get("status") != status:
        slot["status"] = status
        changed = True
    if verified_now and status in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS"):
        if cfg.get("last_verified") != verified_now:
            cfg["last_verified"] = verified_now
            changed = True
    if changed:
        try:
            wf.write_text(yaml.safe_dump(cfg, sort_keys=False))
        except OSError:
            pass


def sync_manifests(catalog: list | None = None, state: dict[str, Any] | None = None) -> dict[str, int]:
    """Regenerate every manifest's cpu/gpu status and twin level mirrors from
    the sources of truth. Returns a change count summary."""

    catalog = catalog if catalog is not None else load_catalog()
    state = state if state is not None else load_state()
    attempts = state.get("attempts", {})
    changed = {"status": 0, "twin": 0, "manifests": 0}
    for entry in catalog:
        wf = WORKLOADS_DIR / entry.id / "workload.yaml"
        if not wf.exists():
            continue
        try:
            cfg = yaml.safe_load(wf.read_text()) or {}
        except (OSError, yaml.YAMLError):
            continue
        before = json.dumps(cfg, sort_keys=True)
        rec = attempts.get(entry.id, {})
        for backend in ("cpu", "gpu"):
            status = (rec.get(backend) or {}).get("status") or "NOT_TESTED"
            cfg.setdefault(backend, {})
            if cfg[backend].get("status") != status:
                cfg[backend]["status"] = status
                changed["status"] += 1
        twin = cfg.setdefault("twin", {})
        if twin.get("level") != entry.twin_level:
            twin["level"] = entry.twin_level
            changed["twin"] += 1
        if json.dumps(cfg, sort_keys=True) != before:
            wf.write_text(yaml.safe_dump(cfg, sort_keys=False))
            changed["manifests"] += 1
    return changed
