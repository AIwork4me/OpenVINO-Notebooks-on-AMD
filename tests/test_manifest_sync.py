"""Regression: workload.yaml mirrors must never disagree with marathon-state.

Historical defect (Gate 1 of the comprehensive closure): 9 status rows and 53
twin levels drifted because GPU twins and audit corrections wrote state without
mirroring into the manifests.
"""

from __future__ import annotations

import yaml

from ov_amd.environment import REPO_ROOT
from ov_amd.manifest_sync import mirror_into_manifest, sync_manifests
from ov_amd.scheduler import load_catalog, load_state


def test_mirror_into_manifest_updates_status(tmp_path, monkeypatch) -> None:
    wf = tmp_path / "wl.yaml"
    wf.write_text(yaml.safe_dump({"id": "wl", "cpu": {"status": "FAILED"}, "last_verified": ""}))
    monkeypatch.setattr("ov_amd.manifest_sync.WORKLOADS_DIR", tmp_path.parent)
    (tmp_path.parent / "wl").mkdir(exist_ok=True)
    (tmp_path.parent / "wl" / "workload.yaml").write_text(wf.read_text())
    wf.write_text(yaml.safe_dump({"id": "wl", "cpu": {"status": "FAILED"}}))
    import ov_amd.manifest_sync as ms

    ms.WORKLOADS_DIR = tmp_path.parent
    mirror_into_manifest("wl", "cpu", "VERIFIED", verified_now="2026-10-07T00:00:00+00:00")
    cfg = yaml.safe_load((tmp_path.parent / "wl" / "workload.yaml").read_text())
    assert cfg["cpu"]["status"] == "VERIFIED"
    assert cfg["last_verified"] == "2026-10-07T00:00:00+00:00"


def test_current_dataset_manifests_agree_with_state() -> None:
    catalog = load_catalog()
    state = load_state()
    attempts = state["attempts"]
    mismatches = []
    for e in catalog:
        wf = REPO_ROOT / "workloads" / e.id / "workload.yaml"
        cfg = yaml.safe_load(wf.read_text()) or {}
        for backend in ("cpu", "gpu"):
            want = (attempts.get(e.id, {}).get(backend) or {}).get("status", "NOT_TESTED")
            got = (cfg.get(backend) or {}).get("status")
            if got != want:
                mismatches.append(f"{e.id}.{backend}: manifest={got} state={want}")
        if (cfg.get("twin") or {}).get("level") != e.twin_level:
            mismatches.append(f"{e.id}.twin: manifest={cfg.get('twin')} catalog={e.twin_level}")
    assert not mismatches, f"manifest/state mirror drift: {mismatches[:10]}"


def test_sync_manifests_is_idempotent() -> None:
    changed = sync_manifests(load_catalog(), load_state())
    assert changed == {"status": 0, "twin": 0, "pin": 0, "manifests": 0}, (
        f"sync should be a no-op on a clean dataset: {changed}"
    )


def test_sync_manifests_repin_on_upstream_change(tmp_path, monkeypatch) -> None:
    """Regression (v0.2.2): a pin switch must refresh manifest upstream pins.

    The 171 manifests recorded pin 329562e…; after fetching 5f0b2b5… every
    manifest mirror must carry the new pin (content-verified snapshot), else
    manifests contradict the catalog/state sources of truth.
    """


    import ov_amd.manifest_sync as ms

    ms.WORKLOADS_DIR = tmp_path
    wf = tmp_path / "wl" / "workload.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text(
        yaml.safe_dump(
            {
                "id": "wl",
                "upstream": {
                    "repository": "openvinotoolkit/openvino_notebooks",
                    "commit": "329562e6031d1a989017d08697b0fabe5a989492",
                    "path": "notebooks/old/nb.ipynb",
                    "url": "https://github.com/openvinotoolkit/openvino_notebooks/blob/old/nb.ipynb",
                },
                "cpu": {"status": "NOT_TESTED"},
                "twin": {"level": "WORKLOAD_TWIN"},
            }
        )
    )
    entry = type("E", (), {})()
    entry.id = "wl"
    entry.twin_level = "WORKLOAD_TWIN"
    entry.upstream_path = "notebooks/new/nb.ipynb"
    entry.upstream_url = "https://github.com/openvinotoolkit/openvino_notebooks/blob/5f0b2b5f/notebooks/new/nb.ipynb"
    state = {"attempts": {}, "upstream": {"commit": "5f0b2b5f63fd84e91f5c4e87f9bf9d13141a1e9b"}}
    changed = sync_manifests([entry], state)
    assert changed["pin"] == 1
    cfg = yaml.safe_load(wf.read_text())
    assert cfg["upstream"]["commit"] == "5f0b2b5f63fd84e91f5c4e87f9bf9d13141a1e9b"
    assert cfg["upstream"]["path"] == "notebooks/new/nb.ipynb"
    assert cfg["upstream"]["url"].endswith("notebooks/new/nb.ipynb")
