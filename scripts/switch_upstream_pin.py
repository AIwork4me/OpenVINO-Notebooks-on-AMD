#!/usr/bin/env python3
"""Switch the pinned upstream and mark impacted workloads for revalidation.

Steps 21-23 of the v0.2 campaign:
1. verify the new snapshot's notebook set against the catalog
2. compute changed/new/removed notebooks vs the previous pinned snapshot
   (content sha256 of every *.ipynb, requirements*.txt, and sibling *.py)
3. update state records for impacted workloads -> REVALIDATION_REQUIRED with
   explicit reasons, preserving historical status/evidence untouched
4. report the impact table (stdout; committed separately in
   reports/upstream-update-impact.md)

Historical evidence is never rewritten. The previous pin stays recorded in
every existing evidence dir's upstream.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ov_amd.environment import REPO_ROOT  # noqa: E402
from ov_amd.scheduler import load_state, save_state  # noqa: E402

KINDS = ("*.ipynb", "requirements*.txt", "*.py")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_index(root: Path) -> dict[str, str]:
    idx: dict[str, str] = {}
    if not root.is_dir():
        return idx
    for kind in KINDS:
        for p in root.rglob(kind):
            if ".ipynb_checkpoints" in str(p) or "/." in f"/{p.relative_to(root)}":
                continue
            idx[p.relative_to(root).as_posix()] = sha256(p)
    return idx


def main() -> int:
    new_root = REPO_ROOT / ".cache" / "upstream"
    old_root = REPO_ROOT / ".cache" / "upstream-prev"
    meta_path = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    meta = json.loads(meta_path.read_text())
    new_commit = meta.get("commit", "")
    old_commit = ""
    state = load_state()
    old_commit = (state.get("upstream") or {}).get("commit", "")
    if not new_commit:
        print("no pinned commit in upstream meta; aborting", file=sys.stderr)
        return 1
    if old_commit and old_commit == new_commit and "--force" not in sys.argv:
        print(f"state already at {new_commit[:12]}; nothing to do")
        return 0

    new_idx = snapshot_index(new_root)
    old_idx = snapshot_index(old_root) if old_root.is_dir() else {}
    if not old_idx:
        print("WARNING: previous snapshot not found; impact computed as all-changed", file=sys.stderr)

    changed = sorted(k for k in new_idx if k in old_idx and new_idx[k] != old_idx[k])
    added = sorted(k for k in new_idx if k not in old_idx)
    removed = sorted(k for k in old_idx if k not in new_idx)
    notebook_changes = [k for k in changed if k.endswith(".ipynb")]

    import yaml

    catalog_path = REPO_ROOT / "catalog" / "notebooks.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())["notebooks"]
    by_path = {e["upstream_path"]: e["id"] for e in catalog}
    impacted: dict[str, list[str]] = {}
    for path in changed + added:
        nb_dir = "/".join(path.split("/")[:-1])
        for cand in (path, *(f"{nb_dir}/{p}" for p in ())):
            if cand in by_path:
                impacted.setdefault(by_path[cand], []).append(path)
        # requirements/helper changes impact every notebook in that folder
        if not path.endswith(".ipynb"):
            for bp, wid in by_path.items():
                if bp.rsplit("/", 1)[0] == nb_dir:
                    impacted.setdefault(wid, []).append(path)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    flipped = 0
    never_tested: list[str] = []
    for wid in sorted(impacted):
        rec = state["attempts"].get(wid, {})
        if not rec.get("cpu") and not rec.get("gpu"):
            # impacted but never validated under the old pin: there is nothing
            # to RE-validate. Creating a REVALIDATION_REQUIRED record would
            # imply prior validation. They stay record-less (NOT_TESTED) and
            # will simply be first-attempted under the new pin.
            never_tested.append(wid)
            continue
        for backend in ("cpu", "gpu"):
            r = rec.get(backend)
            if not r or r.get("status") in ("NOT_TESTED", "REVALIDATION_REQUIRED", "NOT_APPLICABLE"):
                continue
            r["historical_status"] = r.get("status")
            if r.get("evidence_dir") and not r.get("historical_evidence"):
                r["historical_evidence"] = r["evidence_dir"]
            r["revalidation_reasons"] = sorted(
                set(r.get("revalidation_reasons") or [])
                | {"upstream_notebook_changed", f"pin:{(old_commit or '?')[:12]}->{new_commit[:12]}"}
            )
            r["status"] = "REVALIDATION_REQUIRED"
            r["updated"] = now
            flipped += 1
    state["upstream"] = {k: v for k, v in meta.items() if k != "local_path"}
    save_state(state)

    print(f"pin: {(old_commit or '?')[:12]} -> {new_commit[:12]}")
    print(f"changed files: {len(changed)} (notebooks: {len(notebook_changes)})")
    print(f"added: {len(added)}  removed: {len(removed)}")
    print(f"impacted workloads: {len(impacted)} ({flipped} attempt records flipped)")
    if never_tested:
        print(f"impacted but never validated under the old pin (stay NOT_TESTED, first-attempt under new pin): {', '.join(never_tested)}")
    for wid in sorted(impacted):
        print(f"  - {wid}: {len(impacted[wid])} changed file(s)")
    if added:
        print("added:", *added[:10], sep="\n  ")
    if removed:
        print("removed:", *removed[:10], sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
