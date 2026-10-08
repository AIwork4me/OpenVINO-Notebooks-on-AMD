"""v0.3.1 Phase-8 regression: release/version metadata consistency.

The v0.3.0 release shipped while pyproject still declared 0.2.0 (and the
package __version__ 0.1.0). These tests keep every version surface aligned.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    m = re.search(r'^version = "([^"]+)"', (REPO / "pyproject.toml").read_text(), re.M)
    assert m, "pyproject version missing"
    return m.group(1)


def _lock_version() -> str:
    m = re.search(r'name = "ov-amd"\nversion = "([^"]+)"', (REPO / "uv.lock").read_text())
    assert m, "uv.lock ov-amd entry missing"
    return m.group(1)


def _init_version() -> str:
    m = re.search(r'__version__ = "([^"]+)"', (REPO / "ov_amd" / "__init__.py").read_text())
    assert m, "__version__ missing"
    return m.group(1)


def test_pyproject_lock_and_dunder_agree():
    v = _pyproject_version()
    assert _lock_version() == v, "uv.lock version drifted from pyproject"
    assert _init_version() == v, "__init__.__version__ drifted from pyproject"


def test_installed_package_reports_same_version():
    r = subprocess.run(
        ["python", "-c", "import sys; sys.path.insert(0, '.'); import ov_amd; print(ov_amd.__version__)"],
        capture_output=True, text=True, cwd=REPO, timeout=120,
    )
    if r.returncode != 0:
        import pytest

        pytest.skip(f"ov_amd not importable here: {r.stderr.strip()[:80]}")
    assert r.stdout.strip() == _pyproject_version()


def test_release_tags_never_moved():
    """Annotated release tags are immutable: v0.3.0 must still exist and point
    at a commit reachable from main's history (no rewrites)."""
    r = subprocess.run(["git", "tag", "-l", "v0.3.*"], capture_output=True, text=True, cwd=REPO)
    tags = r.stdout.split()
    assert "v0.3.0" in tags
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "v0.3.0", "HEAD"],
        capture_output=True, cwd=REPO,
    )
    assert r.returncode == 0, "v0.3.0 tag is no longer an ancestor of HEAD — history rewrite?"
