#!/usr/bin/env python3
"""Campaign finalization.

- every catalog entry that was never attempted gets NOT_TESTED with an
  explicit reason (no silent unknowns)
- regenerates compatibility artifacts and the final report skeleton with
  computed campaign numbers
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.reporting import write_compatibility, write_failures, write_progress  # noqa: E402
from ov_amd.scheduler import load_catalog, load_state, save_state  # noqa: E402


def finalize(not_tested_reason: str) -> dict:
    catalog = load_catalog()
    state = load_state()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    marked = 0
    for e in catalog:
        rec = state["attempts"].get(e.id)
        cpu = (rec or {}).get("cpu")
        if not cpu:
            state["attempts"].setdefault(e.id, {})["cpu"] = {
                "status": "NOT_TESTED",
                "failure_category": "",
                "notes": [not_tested_reason],
                "updated": now,
            }
            marked += 1

    save_state(state)
    write_compatibility()
    write_progress()
    write_failures()

    c = Counter((v.get("cpu") or {}).get("status") for v in state["attempts"].values())
    g = Counter((v.get("gpu") or {}).get("status") for v in state["attempts"].values() if v.get("gpu"))
    cats = Counter(
        (next(x for x in catalog if x.id == wid).category)
        for wid, v in state["attempts"].items()
        if (v.get("cpu") or {}).get("status", "").startswith("VERIFIED")
    )
    return {"marked_not_tested": marked, "cpu": dict(c), "gpu": dict(g), "verified_by_category": dict(cats)}


def main() -> int:
    reason = (
        "not reached within campaign runtime (network-throttled downloads dominated wall time); "
        "resumable via scripts/run_marathon.py --resume"
    )
    out = finalize(reason)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
