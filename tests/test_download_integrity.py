"""v0.3.1 Gate-8 hardening: behavioral tests for the DOWNLOAD path of hash
verification. Gate-8 review demonstrated that disabling the downloaded-content
hash check (or twin_lib.fetch's sha256 branch) passed the entire suite because
only the explicit/cache/manifest paths were behaviorally guarded. These tests
deliver wrong bytes through a monkeypatched downloader and must see refusal.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ov_amd import assets as A

GOOD = b"the real bytes of the asset"


@pytest.fixture()
def one_asset(tmp_path, monkeypatch):
    """A manifest whose only source is a (mocked) download URL."""
    manifest = tmp_path / "assets.yaml"
    manifest.write_text(
        "assets:\n"
        f"- id: 'f.bin'\n"
        f"  sha256: '{hashlib.sha256(GOOD).hexdigest()}'\n"
        "  source_urls: ['https://mirror.invalid/f.bin']\n"
        "  license: mit\n"
    )
    monkeypatch.setattr(A, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(A, "FILES_DIR", tmp_path / "files")
    monkeypatch.setattr(A, "DEFAULT_CACHE", tmp_path / "cache")
    return manifest


def test_resolve_asset_rejects_wrong_hash_download(one_asset, monkeypatch):
    """A mirror serving different bytes must NEVER be promoted to the cache."""
    delivered = bytearray()

    def evil_curl(url, dest, timeout_s=600):
        dest.write_bytes(b"tampered content")
        delivered.append(1)

    monkeypatch.setattr(A, "_curl_get", evil_curl)
    with pytest.raises(A.AssetResolutionError, match="hash mismatch"):
        A.resolve_asset("f.bin")
    cache = A.DEFAULT_CACHE
    assert not (cache / "f.bin").exists(), "unverified download leaked into the managed cache"


def test_resolve_asset_accepts_hash_verified_download(one_asset, monkeypatch):
    def good_curl(url, dest, timeout_s=600):
        dest.write_bytes(GOOD)

    monkeypatch.setattr(A, "_curl_get", good_curl)
    r = A.resolve_asset("f.bin")
    assert r.source.startswith("url:")
    assert r.sha256_verified and r.path.read_bytes() == GOOD


def test_resolve_asset_recovers_after_a_bad_mirror(one_asset, monkeypatch):
    """First URL serves garbage, second serves the real bytes: the resolver
    must quarantine the bad attempt and succeed via the good source."""
    calls = []

    def flaky_curl(url, dest, timeout_s=600):
        calls.append(url)
        dest.write_bytes(b"evil" if "mirror1" in url else GOOD)

    manifest = one_asset
    text = manifest.read_text().replace(
        "source_urls: ['https://mirror.invalid/f.bin']",
        "source_urls: ['https://mirror1.invalid/f.bin', 'https://mirror2.invalid/f.bin']",
    )
    manifest.write_text(text)

    specs = A.load_manifests(manifest)

    monkeypatch.setattr(A, "_curl_get", flaky_curl)
    r = A.resolve_asset("f.bin", specs=specs)
    assert len(calls) == 2 and r.sha256_verified


def test_twin_fetch_rejects_wrong_hash_download(tmp_path, monkeypatch):
    """twin_lib.fetch's sha256 enforcement, behaviorally: bad bytes -> refuse
    and retry; correct bytes -> promote. Uses a stubbed curl binary."""
    import sys

    repo_root = Path(__file__).resolve().parent.parent / "ov_amd"
    sys.path.insert(0, str(repo_root))
    from twin_lib import fetch

    dest = tmp_path / "w.bin"
    good_hash = hashlib.sha256(GOOD).hexdigest()
    state = {"n": 0}

    def fake_run(cmd, capture_output=True, **kw):
        state["n"] += 1
        # curl invocation shape: [curl, -sSfL, --max-time, N, URL, -o, TMP]
        out_path = Path(cmd[cmd.index("-o") + 1])
        out_path.write_bytes(b"wrong bytes" if state["n"] == 1 else GOOD)
        import subprocess as _sp

        return _sp.CompletedProcess(cmd, 0, b"", b"")

    import shutil as _sh

    monkeypatch.setattr(_sh, "which", lambda name: "/bin/true")
    import subprocess

    monkeypatch.setattr(subprocess, "run", fake_run)
    # first attempt serves wrong bytes, second serves the right ones:
    # fetch must not accept attempt 1
    fetch("https://x/f", dest, sha256=good_hash, tries=2)
    assert dest.read_bytes() == GOOD, "fetch promoted unverified bytes or did not recover"
