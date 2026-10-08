"""Managed input-asset resolution for ROCm twins and the validation harness.

Every runtime input that is not generated deterministically by a workload script
must be declared in ``assets/manifests/assets.yaml`` with a verified SHA-256.
Resolution order (mission v0.3.1 Phase 2):

1. an explicitly supplied path (CLI arg or ``OV_AMD_ASSET_<ID>`` env var)
2. a repository-committed fixture (``assets/files/<id>``) — only for assets whose
   license permits redistribution
3. the managed cache (``.cache/assets/<id>``)
4. a download from the declared source URLs (atomic temp file, hash-verified
   before it is promoted into the cache)

Every step verifies the SHA-256; mismatches are quarantined, never reused.
A twin input must never depend on another workload's results/ workdir.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "assets" / "manifests" / "assets.yaml"
FILES_DIR = Path(__file__).resolve().parent.parent / "assets" / "files"
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / ".cache" / "assets"


class AssetResolutionError(RuntimeError):
    """Raised when an asset cannot be resolved with verifiable integrity."""


@dataclass(frozen=True)
class AssetSpec:
    id: str
    sha256: str
    source_urls: tuple[str, ...]
    license: str
    license_source: str = ""
    committed: bool = False
    description: str = ""
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedAsset:
    spec: AssetSpec
    path: Path
    source: str  # "explicit" | "fixture" | "cache" | "url:<...>"
    sha256_verified: bool

    def record(self) -> dict:
        """Machine-readable provenance block for metrics/evidence."""
        return {
            "asset_id": self.spec.id,
            "sha256": self.spec.sha256,
            "resolved_from": self.source,
            "license": self.spec.license,
            "license_source": self.spec.license_source,
            "description": self.spec.description,
        }


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def load_manifests(path: Path | None = None) -> dict[str, AssetSpec]:
    import yaml

    manifest_file = path or MANIFEST_PATH
    data = yaml.safe_load(manifest_file.read_text()) or {}
    specs: dict[str, AssetSpec] = {}
    for entry in data.get("assets", []):
        spec = AssetSpec(
            id=str(entry["id"]),
            sha256=str(entry["sha256"]).lower(),
            source_urls=tuple(entry.get("source_urls", [])),
            license=str(entry.get("license", "unspecified")),
            license_source=str(entry.get("license_source", "")),
            committed=bool(entry.get("committed", False)),
            description=str(entry.get("description", "")),
            extra={k: v for k, v in entry.items() if k not in {"id", "sha256", "source_urls", "license", "license_source", "committed", "description"}},
        )
        if not _valid_hash(spec.sha256):
            raise AssetResolutionError(f"asset {spec.id}: manifest sha256 is not a valid hex digest")
        if not spec.source_urls and not spec.committed:
            raise AssetResolutionError(f"asset {spec.id}: no source_urls and not committed — unresolvable")
        specs[spec.id] = spec
    return specs


def _curl_get(url: str, dest: Path, timeout_s: int = 600) -> None:
    curl = shutil.which("curl") or "/usr/bin/curl"
    r = subprocess.run([curl, "-sSfL", "--max-time", str(timeout_s), url, "-o", str(dest)], capture_output=True)
    if r.returncode != 0:
        raise AssetResolutionError(f"download failed ({url}): curl exit {r.returncode}")


def resolve_asset(
    asset_id: str,
    explicit: str | Path | None = None,
    cache_dir: Path | None = None,
    specs: dict[str, AssetSpec] | None = None,
) -> ResolvedAsset:
    """Resolve a declared asset with SHA-256 enforcement at every step."""
    specs = specs if specs is not None else load_manifests()
    if asset_id not in specs:
        raise AssetResolutionError(
            f"unknown asset id '{asset_id}'. Declared assets: {sorted(specs)}; "
            f"add an entry to {MANIFEST_PATH} — undeclared inputs are not permitted."
        )
    spec = specs[asset_id]
    cache = cache_dir or DEFAULT_CACHE
    tried: list[str] = []
    env_value = os.environ.get("OV_AMD_ASSET_" + "".join(c if c.isalnum() else "_" for c in asset_id.upper()))

    # An explicitly supplied path is authoritative: if it fails verification the
    # resolution FAILS (never silently substitute a different file for one the
    # operator explicitly chose).
    for label, value in (("explicit", explicit), ("explicit(env)", env_value)):
        if not value:
            continue
        path = Path(value)
        if not path.exists() or not path.is_file():
            raise AssetResolutionError(
                f"explicit asset path for '{asset_id}' does not exist: {path} "
                f"(expected sha256 {spec.sha256})"
            )
        actual = sha256_of(path)
        if actual != spec.sha256:
            raise AssetResolutionError(
                f"explicit asset path for '{asset_id}' failed verification: {path} "
                f"has sha256 {actual}, manifest declares {spec.sha256}. Refusing to "
                f"substitute a different file for an explicitly supplied one."
            )
        return ResolvedAsset(spec, path, label, True)

    candidates: list[tuple[str, Path]] = []
    if spec.committed:
        candidates.append(("fixture", FILES_DIR / asset_id))
    candidates.append(("cache", cache / asset_id))

    for source, path in candidates:
        if not path.exists() or not path.is_file():
            tried.append(f"{source}: {path} (missing)")
            continue
        actual = sha256_of(path)
        if actual == spec.sha256:
            return ResolvedAsset(spec, path, source, True)
        tried.append(f"{source}: {path} (sha256 {actual[:16]}… != manifest {spec.sha256[:16]}…)")
        if source == "cache":
            # corrupted cache: quarantine and fall through to download
            quarantine = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
            shutil.move(str(path), str(quarantine))
            tried.append(f"cache: quarantined corrupt copy -> {quarantine.name}")

    # download path
    cache.mkdir(parents=True, exist_ok=True)
    tmp = cache / f".{asset_id}.incomplete"
    for url in spec.source_urls:
        try:
            _curl_get(url, tmp)
            if not tmp.exists() or tmp.stat().st_size == 0:
                raise AssetResolutionError(f"empty download from {url}")
            actual = sha256_of(tmp)
            if actual != spec.sha256:
                raise AssetResolutionError(
                    f"downloaded content hash mismatch for {asset_id} from {url}: "
                    f"got {actual[:16]}… expected {spec.sha256[:16]}…"
                )
            final = cache / asset_id
            os.replace(tmp, final)
            return ResolvedAsset(spec, final, f"url:{url}", True)
        except AssetResolutionError as exc:
            tried.append(f"url:{url} ({exc})")
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            continue
    raise AssetResolutionError(
        f"could not resolve asset '{asset_id}' ({spec.description}). Attempted:\n  "
        + "\n  ".join(tried)
        + "\nSupply the file explicitly via --input / OV_AMD_ASSET_"
        + "".join(c if c.isalnum() else "_" for c in asset_id.upper())
        + " (sha256 " + spec.sha256 + ")."
    )


# ---------------------------------------------------------------------------
# Safe archive extraction (path-traversal / symlink / bomb hardening)
# ---------------------------------------------------------------------------

_MAX_ARCHIVE_MEMBERS = 20000
_MAX_ARCHIVE_BYTES = 20 * 1024**3  # 20 GiB decompressed cap


def _check_member(name: str, dest: Path, seen: set[str]) -> None:
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise AssetResolutionError(f"unsafe archive member (absolute path): {name!r}")
    target = (dest / name).resolve()
    dest_resolved = dest.resolve()
    if not str(target).startswith(str(dest_resolved) + os.sep) and target != dest_resolved:
        raise AssetResolutionError(f"unsafe archive member (escapes destination): {name!r}")
    if name.endswith(("/", os.sep)) is False and ("/../" in name or name.startswith("../")):
        raise AssetResolutionError(f"unsafe archive member (parent traversal): {name!r}")
    if name in seen:
        raise AssetResolutionError(f"duplicate archive member: {name!r}")


def safe_extract_tar(archive: Path | tempfile.SpooledTemporaryFile, dest: Path) -> None:
    """tarfile extraction with member validation, symlink refusal, size caps."""
    dest.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    total = 0
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        if len(members) > _MAX_ARCHIVE_MEMBERS:
            raise AssetResolutionError(f"archive has too many members: {len(members)}")
        for m in members:
            _check_member(m.name, dest, seen)
            seen.add(m.name)
            if m.issym() or m.islnk():
                link = m.linkname or ""
                if link.startswith("/") or ".." in Path(link).parts:
                    raise AssetResolutionError(f"unsafe archive link member: {m.name!r} -> {link!r}")
                continue  # links are skipped during extraction below
            total += m.size
            if total > _MAX_ARCHIVE_BYTES:
                raise AssetResolutionError("archive exceeds decompression size cap")
        extractable = [m for m in members if not (m.issym() or m.islnk())]
        if hasattr(tarfile, "data_filter"):
            tf.extractall(dest, members=extractable, filter="data")
        else:  # Python < 3.12 fallback — members were validated above
            tf.extractall(dest, members=extractable)


def safe_extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        if len(infos) > _MAX_ARCHIVE_MEMBERS:
            raise AssetResolutionError(f"archive has too many members: {len(infos)}")
        total = 0
        for info in infos:
            _check_member(info.filename, dest, seen)
            seen.add(info.filename)
            total += info.file_size
            if total > _MAX_ARCHIVE_BYTES:
                raise AssetResolutionError("archive exceeds decompression size cap")
        zf.extractall(dest)
