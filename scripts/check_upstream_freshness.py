#!/usr/bin/env python3
"""Record upstream freshness (networked; separate from README generation).

Compares the project pin (upstream/openvino-notebooks.json) against the live
`latest` branch head of openvinotoolkit/openvino_notebooks via the GitHub API
and writes reports/upstream-freshness.json. README generation only renders the
committed record (ov_amd.reporting._freshness_line) — it never needs network.

When upstream is ahead, this script also marks catalog entries whose
notebooks/content changed in the delta as REVALIDATION_REQUIRED in
results/marathon-state.json (status transition with provenance note) — it
never rewrites historical evidence or outcomes wholesale.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.environment import REPO_ROOT  # noqa: E402

REPO = "openvinotoolkit/openvino_notebooks"
BRANCH = "latest"
FRESHNESS_PATH = REPO_ROOT / "reports" / "upstream-freshness.json"


def gh_api(path: str) -> dict:
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {path}: {r.stderr[:200]}")
    return json.loads(r.stdout)


def main() -> int:
    meta = json.loads((REPO_ROOT / "upstream" / "openvino-notebooks.json").read_text())
    pinned = meta["commit"]
    head = gh_api(f"repos/{REPO}/commits/{BRANCH}")
    latest = head["sha"]

    if latest == pinned:
        rec = {
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pinned_commit": pinned,
            "latest_commit": latest,
            "ahead_by": 0,
            "status": "CURRENT",
        }
        FRESHNESS_PATH.write_text(json.dumps(rec, indent=2) + "\n")
        print("upstream freshness: CURRENT")
        return 0

    cmp_data = gh_api(f"repos/{REPO}/compare/{pinned}...{latest}")
    ahead = int(cmp_data.get("ahead_by", -1))
    changed = [f["filename"] for f in cmp_data.get("files", [])]

    # notebooks (and shared helpers) whose change marks dependent workloads
    # REVALIDATION_REQUIRED — deterministic, scope-bounded, never silent
    nb_changed = sorted(
        f for f in changed if f.startswith("notebooks/") and f.endswith(".ipynb")
    )
    helpers_changed = sorted(f for f in changed if f.startswith("utils/") and f.endswith(".py"))
    marked = []
    if nb_changed or helpers_changed:
        import yaml

        catalog = yaml.safe_load((REPO_ROOT / "catalog" / "notebooks.yaml").read_text())
        state_path = REPO_ROOT / "results" / "marathon-state.json"
        state = json.loads(state_path.read_text())
        by_path = {e["upstream_path"]: e["id"] for e in catalog.get("notebooks", [])}
        # direct: changed notebooks; shared helpers affect only workloads whose
        # evidence notes already carry a helper-dependent failure signature —
        # conservative default: direct notebooks only (helper impact analysis
        # is a review activity, recorded in the delta report)
        for path in nb_changed:
            wid = by_path.get(path)
            if not wid:
                continue  # notebook not in our catalog (new upstream addition)
            rec = state.get("attempts", {}).get(wid, {}).get("cpu")
            if rec and rec.get("status", "").startswith("VERIFIED"):
                rec["status"] = "REVALIDATION_REQUIRED"
                rec.setdefault("notes", []).append(
                    f"upstream freshness check {time.strftime('%Y-%m-%d')}: notebook changed upstream "
                    f"({path}; latest {latest[:12]}); revalidation required"
                )
                marked.append(wid)
        if marked:
            state_path.write_text(json.dumps(state, indent=2) + "\n")

    rec = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pinned_commit": pinned,
        "latest_commit": latest,
        "ahead_by": ahead,
        "status": "UPSTREAM_AHEAD",
        "changed_files": changed,
        "changed_notebooks": nb_changed,
        "changed_shared_helpers": helpers_changed,
        "marked_revalidation_required": marked,
    }
    FRESHNESS_PATH.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"upstream freshness: UPSTREAM AHEAD BY {ahead} commits; revalidation marked: {marked or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
