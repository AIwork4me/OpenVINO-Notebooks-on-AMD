#!/usr/bin/env python3
"""Entry point for the unattended marathon campaign (resumable)."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    import json

    from ov_amd.marathon import run_marathon

    ap = argparse.ArgumentParser()
    for opt, dest in (("--resume", "resume"), ("--cpu-only", "cpu_only"), ("--gpu-only", "gpu_only"),
                      ("--retry-failed", "retry_failed")):
        ap.add_argument(opt, dest=dest, action="store_true")
    ap.add_argument("--max-runtime", type=float, default=None, help="seconds")
    ap.add_argument("--priority", type=int, default=None)
    ap.add_argument("--category", default=None)
    args = ap.parse_args()

    summary = run_marathon(
        resume=args.resume,
        cpu_only=args.cpu_only,
        gpu_only=args.gpu_only,
        max_runtime_s=args.max_runtime,
        retry_failed=args.retry_failed,
        category=args.category,
        priority_max=args.priority,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
