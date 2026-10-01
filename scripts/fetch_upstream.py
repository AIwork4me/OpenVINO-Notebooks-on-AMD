#!/usr/bin/env python3
"""Fetch the pinned upstream snapshot via GitHub API + raw CDN.

Why not `git clone`: bulk git/https transfer to github.com is throttled to
~47KB/s on this network, while api.github.com and raw.githubusercontent.com
run at full speed. We fetch the exact same blobs (verified by path+size from
the tree API) and pin the branch head commit SHA from the API.

Files: every .ipynb/.txt/.py/.json/.csv/.yaml/.yml/.xml/.md/.png/.jpg/.gif
blob under the tree (assets notebooks need at runtime), into .cache/upstream/.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ov_amd.environment import REPO_ROOT  # noqa: E402

REPO = "openvinotoolkit/openvino_notebooks"
BRANCH = "latest"
DEST = REPO_ROOT / ".cache" / "upstream"
META_PATH = REPO_ROOT / "upstream" / "openvino-notebooks.json"

KEEP_EXT = (".ipynb", ".txt", ".py", ".json", ".csv", ".yaml", ".yml", ".xml", ".md", ".png", ".jpg", ".jpeg", ".gif")
SKIP_PREFIX = (".")


def get_json(url: str, tries: int = 3) -> dict:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise RuntimeError("unreachable")


def fetch_one(commit: str, path: str, size: int, tries: int = 4) -> tuple[str, str]:
    out = DEST / path
    if out.exists() and out.stat().st_size == size:
        return path, "cached"
    out.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                data = r.read()
            if len(data) != size:
                raise RuntimeError(f"size mismatch {len(data)} != {size}")
            out.write_bytes(data)
            return path, "ok"
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                return path, f"FAIL: {e}"
            time.sleep(3 * (i + 1))
    return path, "FAIL"


def main() -> int:
    head = get_json(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}")
    commit = head["sha"]
    commit_date = head["commit"]["committer"]["date"]
    commit_subject = head["commit"]["message"].splitlines()[0]
    print(f"pinned {BRANCH} @ {commit[:12]} ({commit_subject[:60]})")

    tree = get_json(f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1")
    if tree.get("truncated"):
        print("WARNING: tree truncated by API", file=sys.stderr)
    blobs = [t for t in tree["tree"]
             if t["type"] == "blob" and t["path"].endswith(KEEP_EXT)
             and not t["path"].startswith(SKIP_PREFIX)]
    total = sum(t.get("size", 0) for t in blobs)
    print(f"{len(blobs)} files, {total / 1e6:.1f} MB")

    ok = fail = cached = 0
    fails: list[str] = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch_one, commit, t["path"], t.get("size", 0)): t["path"] for t in blobs}
        for i, fut in enumerate(as_completed(futs)):
            path, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "cached":
                cached += 1
            else:
                fail += 1
                fails.append(f"{path} {status}")
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(blobs)} ok={ok} cached={cached} fail={fail}", flush=True)

    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps({
        "repository": REPO,
        "branch": BRANCH,
        "commit": commit,
        "commit_date": commit_date,
        "commit_subject": commit_subject,
        "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "local_path": str(DEST),
        "fetch_method": "github-api-tree + raw.githubusercontent (git protocol throttled ~47KB/s on this network)",
        "files_ok": ok, "files_cached": cached, "files_failed": fail,
    }, indent=2))

    if fails:
        print("FAILED downloads:", file=sys.stderr)
        for f in fails[:20]:
            print("  " + f, file=sys.stderr)
    print(f"done: ok={ok} cached={cached} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
