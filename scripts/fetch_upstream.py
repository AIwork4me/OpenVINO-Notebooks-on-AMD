#!/usr/bin/env python3
"""Fetch the pinned upstream snapshot via the GitHub Git Blobs API.

Transport history on this network (see docs/engineering-decisions.md D11):
- git clone / codeload tarball: throttled to ~47KB/s — unusable
- raw.githubusercontent.com: stalls after an initial burst — unusable in parallel
- api.github.com (authenticated via `gh auth token`): fast and stable

Every file is fetched as a base64 git blob and verified against the tree's
git blob SHA-1 before writing, so transport cannot corrupt or tamper content.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ov_amd.environment import REPO_ROOT  # noqa: E402

REPO = "openvinotoolkit/openvino_notebooks"
BRANCH = "latest"
DEST = REPO_ROOT / ".cache" / "upstream"
META_PATH = REPO_ROOT / "upstream" / "openvino-notebooks.json"

KEEP_EXT = (".ipynb", ".txt", ".py", ".json", ".csv", ".yaml", ".yml", ".xml", ".md", ".png", ".jpg", ".jpeg", ".gif")
SKIP_PREFIX = (".",)

CURL = shutil.which("curl") or "/usr/bin/curl"


def gh_token() -> str:
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=30)
    tok = r.stdout.strip()
    if not tok:
        raise SystemExit("gh auth token unavailable — cannot use Blobs API (rate limits)")
    return tok


TOKEN = os.environ.get("GH_TOKEN") or gh_token()


def api_get(url: str, tries: int = 4, timeout: int = 300) -> bytes:
    for i in range(tries):
        r = subprocess.run(
            [
                CURL,
                "-sSfL",
                "--max-time",
                str(timeout),
                "-H",
                f"Authorization: Bearer {TOKEN}",
                "-H",
                "Accept: application/vnd.github+json",
                url,
            ],
            capture_output=True,
            timeout=timeout + 30,
        )
        if r.returncode == 0:
            return r.stdout
        err = r.stderr.decode(errors="replace")[:200]
        if i == tries - 1:
            raise RuntimeError(f"curl {r.returncode}: {err}")
        time.sleep(5 * (i + 1))  # backoff; also covers transient rate limits
    raise RuntimeError("unreachable")


def api_json(url: str) -> dict:
    return json.loads(api_get(url, timeout=60))


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def fetch_one(path: str, blob_sha: str, size: int) -> tuple[str, str]:
    out = DEST / path
    if out.exists() and out.stat().st_size == size:
        return path, "cached"
    out.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{blob_sha}"
    for i in range(4):
        try:
            d = json.loads(api_get(url, timeout=600))
            data = base64.b64decode(d["content"])
            if git_blob_sha(data) != blob_sha:
                raise RuntimeError("blob sha mismatch")
            out.write_bytes(data)
            return path, "ok"
        except Exception as e:  # noqa: BLE001
            if i == 3:
                return path, f"FAIL: {e}"
            time.sleep(5 * (i + 1))
    return path, "FAIL"


def main() -> int:
    head = api_json(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}")
    commit = head["sha"]
    commit_date = head["commit"]["committer"]["date"]
    commit_subject = head["commit"]["message"].splitlines()[0]
    print(f"pinned {BRANCH} @ {commit[:12]} ({commit_subject[:60]})", flush=True)

    tree = api_json(f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1")
    if tree.get("truncated"):
        print("WARNING: tree truncated by API", file=sys.stderr)
    blobs = [
        t
        for t in tree["tree"]
        if t["type"] == "blob" and t["path"].endswith(KEEP_EXT) and not t["path"].startswith(SKIP_PREFIX)
    ]
    total = sum(t.get("size", 0) for t in blobs)
    print(f"{len(blobs)} files, {total / 1e6:.1f} MB", flush=True)

    ok = fail = cached = 0
    fails: list[str] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_one, t["path"], t["sha"], t.get("size", 0)): t["path"] for t in blobs}
        for i, fut in enumerate(as_completed(futs)):
            path, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "cached":
                cached += 1
            else:
                fail += 1
                fails.append(f"{path} {status}")
            if (i + 1) % 25 == 0:
                mb = sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file()) / 1e6
                print(
                    f"  {i + 1}/{len(blobs)} ok={ok} cached={cached} fail={fail} ({mb:.0f}MB, {time.time() - t0:.0f}s)",
                    flush=True,
                )

    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(
        json.dumps(
            {
                "repository": REPO,
                "branch": BRANCH,
                "commit": commit,
                "commit_date": commit_date,
                "commit_subject": commit_subject,
                "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "local_path": str(DEST),
                "fetch_method": "github git-blobs API (sha1-verified); git protocol throttled ~47KB/s, raw CDN stalls on this network",
                "files_ok": ok,
                "files_cached": cached,
                "files_failed": fail,
            },
            indent=2,
        )
    )

    if fails:
        print("FAILED downloads:", file=sys.stderr)
        for f in fails[:20]:
            print("  " + f, file=sys.stderr)
    print(f"done: ok={ok} cached={cached} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
