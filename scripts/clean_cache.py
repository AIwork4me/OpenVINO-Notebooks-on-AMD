#!/usr/bin/env python3
"""Cache management / disk guard for long campaigns.

Only removes caches that are safe to re-download. Never touches:
the repo, evidence JSON, logs, result summaries.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.environment import REPO_ROOT, disk_free_mb  # noqa: E402

SAFE_CACHE_DIRS = [
    REPO_ROOT / ".cache" / "pip",
    Path.home() / ".cache" / "pip",
    Path.home() / ".cache" / "torch",
    Path.home() / ".cache" / "huggingface" / "transformers",  # converted-model cache, re-downloadable
]


def human(mb: int) -> str:
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb} MB"


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) // (1024 * 1024)


def clean(min_free_mb: int = 0, dry: bool = False) -> int:
    freed = 0
    for d in SAFE_CACHE_DIRS:
        if d.exists():
            sz = dir_size(d)
            print(f"{'would remove' if dry else 'removing'} {d} ({human(sz)})")
            if not dry:
                shutil.rmtree(d, ignore_errors=True)
            freed += sz
    after = disk_free_mb()
    print(f"freed ~{human(freed)}, disk free now {human(after)}")
    if min_free_mb and after < min_free_mb:
        print(f"WARNING: still below requested {human(min_free_mb)} free", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-free-mb", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    return clean(args.min_free_mb, args.dry)


if __name__ == "__main__":
    sys.exit(main())
