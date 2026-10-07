#!/usr/bin/env python3
"""Re-run selected workloads: --failed, --smoke N, or explicit ids.

Used after shared-framework fixes: rerun failures and a small smoke subset
instead of the whole verified catalog (scientific efficiency).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    from ov_amd.executor import run_workload_cpu
    from ov_amd.scheduler import load_catalog, load_state, save_state

    ap = argparse.ArgumentParser()
    ap.add_argument("--failed", action="store_true", help="rerun all FAILED cpu workloads")
    ap.add_argument("--smoke", type=int, default=0, help="rerun N verified workloads as smoke test")
    ap.add_argument("ids", nargs="*", help="explicit workload ids")
    args = ap.parse_args()

    catalog = {e.id: e for e in load_catalog()}
    state = load_state()
    targets: list[str] = list(args.ids)

    if args.failed:
        for wid, rec in state.get("attempts", {}).items():
            if (rec.get("cpu") or {}).get("status") == "FAILED":
                targets.append(wid)
    if args.smoke:
        verified = [
            wid
            for wid, rec in state.get("attempts", {}).items()
            if (rec.get("cpu") or {}).get("status", "").startswith("VERIFIED")
        ]
        targets.extend(verified[: args.smoke])

    rc = 0
    for wid in dict.fromkeys(targets):  # dedupe, keep order
        entry = catalog.get(wid)
        if entry is None:
            print(f"skip unknown id {wid}", file=sys.stderr)
            continue
        out = run_workload_cpu(entry, state)
        print(f"{wid}: {out.status.value} {out.failure_category} runs={out.ok_runs}")
        if out.status.value.startswith("VERIFIED"):
            rc = 0
    save_state(state)
    return rc


if __name__ == "__main__":
    sys.exit(main())
