#!/usr/bin/env python3
"""Fetch the pinned upstream snapshot.

Transport history (see docs/engineering-decisions.md D11):
- reference network: git clone / codeload throttled to ~47KB/s; the GitHub
  git-blobs API (authenticated via `gh auth token`) was the only stable route
- secondary runners: codeload tarball is fast and stable, api.github.com also
  works; the mirror/firewall situation differs per runner

Strategy: tarball-first (single HTTPS object for the whole pinned commit),
falling back to the sha1-verified git-blobs API. Both transports serve the
exact pinned commit content; the method actually used is recorded in
upstream/openvino-notebooks.json.

--if-missing: succeed without refetching when a complete snapshot already
exists (used by CI provisioning).
--commit <sha>: fetch THAT exact commit instead of the branch HEAD. Pin
switching must never chase a moving `latest` (the upstream branch advanced
twice during one v0.2 sync attempt); evidence binds to a fixed commit.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ov_amd.environment import REPO_ROOT  # noqa: E402

REPO = "openvinotoolkit/openvino_notebooks"
BRANCH = "latest"
DEST = REPO_ROOT / ".cache" / "upstream"
META_PATH = REPO_ROOT / "upstream" / "openvino-notebooks.json"


def _pinned_commit_arg() -> str | None:
    if "--commit" in sys.argv:
        i = sys.argv.index("--commit")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        raise SystemExit("--commit requires a sha")
    return os.environ.get("OV_AMD_UPSTREAM_COMMIT") or None

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


def snapshot_complete() -> bool:
    """A snapshot counts as complete when its meta records zero failed files
    and the directory still exists (resume support for the blobs route)."""

    if not DEST.is_dir() or not META_PATH.exists():
        return False
    try:
        meta = json.loads(META_PATH.read_text())
    except (OSError, ValueError):
        return False
    pinned = _pinned_commit_arg()
    if pinned and meta.get("commit") != pinned:
        return False  # different target: never treat as satisfiable
    return bool(meta.get("commit")) and meta.get("files_failed", 1) == 0 and any(DEST.iterdir())


def _gh_api_json(url: str) -> dict:
    """Fallback blob fetch through the gh CLI client (different HTTP stack:
    survives proxies that cancel curl's HTTP/2 streams on large bodies)."""

    r = subprocess.run(["gh", "api", url], capture_output=True, text=True, timeout=620)
    if r.returncode == 0:
        return json.loads(r.stdout)
    raise RuntimeError(f"gh api {url}: {r.returncode} {r.stderr[:160]}")


def api_get(url: str, tries: int = 4, timeout: int = 300) -> bytes:
    for i in range(tries):
        r = subprocess.run(
            [
                CURL,
                "-sSfL",
                "--http1.1",  # flaky proxies cancel big HTTP/2 blob streams (curl 92)
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


def fetch_tarball(commit: str, meta: dict) -> bool:
    """Single-object codeload tarball of the pinned commit; keep only notebook
    workflow files (same filter as the blobs route)."""

    url = f"https://codeload.github.com/{REPO}/tar.gz/{commit}"
    for attempt in range(2):
        try:
            r = subprocess.run(
                [CURL, "-sSfL", "--max-time", "900", url, "-o", "/tmp/ov_upstream.tar.gz"],
                capture_output=True,
                timeout=930,
            )
            if r.returncode != 0:
                raise RuntimeError(f"curl {r.returncode}")
            data = Path("/tmp/ov_upstream.tar.gz").read_bytes()
            kept = 0
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                for member in tf.getmembers():
                    name = member.name.split("/", 1)[-1]
                    if not name or member.isdir():
                        continue
                    if not name.endswith(KEEP_EXT):
                        continue
                    top = name.split("/", 1)[0]
                    if top in SKIP_PREFIX or name.startswith(SKIP_PREFIX):
                        continue
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    out = DEST / name
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(f.read())
                    kept += 1
            meta.update(
                {
                    "fetch_method": f"codeload tarball ({kept} files kept, filter {KEEP_EXT}); blobs API fallback available",
                    "files_ok": kept,
                    "files_cached": 0,
                    "files_failed": 0,
                }
            )
            return True
        except (OSError, tarfile.TarError, RuntimeError) as e:
            print(f"tarball attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    return False


def fetch_one(path: str, blob_sha: str, size: int) -> tuple[str, str]:
    out = DEST / path
    # resume check is content-verified, not just existence+size: a file left
    # over from a different pinned commit must never pass as cached
    if out.exists() and out.stat().st_size == size:

        try:
            if git_blob_sha(out.read_bytes()) == blob_sha:
                return path, "cached"
        except OSError:
            pass
    out.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{blob_sha}"
    for i in range(4):
        try:
            try:
                d = json.loads(api_get(url, timeout=600))
            except Exception:  # noqa: BLE001 - curl route failed; try gh client
                d = _gh_api_json(url)
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
    if "--if-missing" in sys.argv and snapshot_complete():
        print("upstream snapshot already complete; skipping fetch")
        return 0

    pinned = _pinned_commit_arg()
    if pinned:
        head = api_json(f"https://api.github.com/repos/{REPO}/commits/{pinned}")
    else:
        head = api_json(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}")
    commit = head["sha"]
    commit_date = head["commit"]["committer"]["date"]
    commit_subject = head["commit"]["message"].splitlines()[0]
    print(f"pinned {BRANCH} @ {commit[:12]} ({commit_subject[:60]})", flush=True)

    meta: dict = {}
    force_blobs = "--blobs" in sys.argv or os.environ.get("OV_AMD_FETCH") == "blobs"
    if not force_blobs and fetch_tarball(commit, meta):
        ok = meta["files_ok"]
        cached = fail = 0
        fails: list[str] = []
    else:
        print("tarball transport unavailable; falling back to git-blobs API", file=sys.stderr)
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
        fails = []
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
        meta.update(
            {
                "fetch_method": "github git-blobs API (sha1-verified); tarball transport failed on this network",
                "files_ok": ok,
                "files_cached": cached,
                "files_failed": fail,
            }
        )

    meta.update(
        {
            "repository": REPO,
            "branch": BRANCH,
            "commit": commit,
            "commit_date": commit_date,
            "commit_subject": commit_subject,
            "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            # repo-relative on purpose: the manifest is published and shared
            # across validation machines, and upstream_root() resolves relative
            # paths against the repo root — an absolute path works only on the
            # machine that ran the fetch (the reference machine's all-23-BLOCKED
            # pass-3 launch was exactly this)
            "local_path": str(DEST.relative_to(REPO_ROOT)),
        }
    )
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2))

    if fails:
        print("FAILED downloads:", file=sys.stderr)
        for f in fails[:20]:
            print("  " + f, file=sys.stderr)
    print(f"done: ok={ok} cached={cached} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
