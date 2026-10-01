#!/usr/bin/env python3
"""Regenerate compatibility artifacts (json/md + README block + progress)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.reporting import write_compatibility, write_failures, write_progress  # noqa: E402


def main() -> int:
    compat = write_compatibility()
    write_progress()
    write_failures()
    print(
        "compatibility regenerated:",
        f"total={compat['counts']['total']}",
        f"cpu={compat['counts']['cpu']}",
        f"gpu={compat['counts']['gpu']}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
