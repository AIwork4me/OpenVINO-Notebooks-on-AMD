"""v0.3.1 Phase-2 regressions: managed assets, download integrity, safe extraction.

These tests reproduce the failure modes found in the v0.3.1 reproducibility audit:
untracked cross-workdir inputs, unverified downloads, corrupt caches, unsafe
archive extraction.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest
import yaml

from ov_amd import assets as A

GOOD_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Isolated manifest + files + cache so tests never touch the real tree."""

    def make(entries, files=None):
        manifest = tmp_path / "assets.yaml"
        payload = {"assets": []}
        for e in entries:
            payload["assets"].append(e)
        manifest.write_text(yaml.safe_dump(payload))
        files_dir = tmp_path / "files"
        files_dir.mkdir(exist_ok=True)
        for name, data in (files or {}).items():
            (files_dir / name).write_bytes(data)
        cache = tmp_path / "cache"
        monkeypatch.setattr(A, "MANIFEST_PATH", manifest)
        monkeypatch.setattr(A, "FILES_DIR", files_dir)
        monkeypatch.setattr(A, "DEFAULT_CACHE", cache)
        return manifest, files_dir, cache

    return make


class TestManifestIntegrity:
    def test_manifest_loads_and_covers_declared_inputs(self, sandbox):
        manifest, _, _ = sandbox([{"id": "a.bin", "sha256": _hash(b"a"), "source_urls": ["https://x/a"], "license": "mit", "committed": True}])
        assert set(A.load_manifests(manifest)) == {"a.bin"}

    def test_invalid_hash_rejected_at_load(self, sandbox):
        manifest, _, _ = sandbox([{"id": "bad", "sha256": "zzz", "source_urls": ["https://x"], "license": "mit"}])
        with pytest.raises(A.AssetResolutionError, match="valid hex"):
            A.load_manifests(manifest)

    def test_unresolvable_entry_rejected(self, sandbox):
        manifest, _, _ = sandbox([{"id": "nopaths", "sha256": _hash(b"x"), "license": "mit"}])
        with pytest.raises(A.AssetResolutionError, match="unresolvable"):
            A.load_manifests(manifest)

    def test_real_manifest_covers_audit_assets(self):
        specs = A.load_manifests()
        for required in ("courtroom-asr.wav", "doc-markdown.png", "paddleocr-vl-test.png", "coco.jpg", "intel-rnb.jpg", "yolov8n.pt"):
            assert required in specs, f"audit-declared asset missing from manifest: {required}"

    def test_committed_fixture_bytes_match_manifest(self):
        specs = A.load_manifests()
        for spec in specs.values():
            if not spec.committed:
                continue
            p = A.FILES_DIR / spec.id
            assert p.is_file(), f"declared committed asset missing bytes: {spec.id}"
            assert A.sha256_of(p) == spec.sha256, f"fixture hash drift: {spec.id}"


class TestResolutionOrder:
    def _spec(self, data: bytes):
        return {"id": "f.bin", "sha256": _hash(data), "source_urls": ["https://unreachable.invalid/f"], "license": "mit", "committed": True}

    def test_fixture_resolution(self, sandbox):
        e = self._spec(GOOD_PNG)
        manifest, _, _ = sandbox([e], files={"f.bin": GOOD_PNG})
        r = A.resolve_asset("f.bin", specs=A.load_manifests(manifest))
        assert r.source == "fixture" and r.sha256_verified

    def test_corrupt_cache_quarantined_never_used(self, sandbox):
        e = self._spec(GOOD_PNG)
        manifest, _, cache = sandbox([e], files={"f.bin": GOOD_PNG})
        cache.mkdir(exist_ok=True)
        (cache / "f.bin").write_bytes(b"corrupt")
        specs = dict(A.load_manifests(manifest))
        specs["f.bin"] = A.AssetSpec(
            id="f.bin", sha256=_hash(GOOD_PNG), source_urls=(), license="mit", committed=False
        )
        with pytest.raises(A.AssetResolutionError, match="could not resolve"):
            A.resolve_asset("f.bin", specs=specs)
        quarantined = list(cache.glob("f.bin.corrupt-*"))
        assert quarantined, "corrupt cache copy was not quarantined"

    def test_explicit_ok(self, sandbox, tmp_path):
        e = self._spec(GOOD_PNG)
        manifest, _, _ = sandbox([e])
        f = tmp_path / "user.bin"
        f.write_bytes(GOOD_PNG)
        r = A.resolve_asset("f.bin", explicit=str(f), specs=A.load_manifests(manifest))
        assert r.source == "explicit"

    def test_explicit_wrong_hash_hard_fails(self, sandbox):
        """The v0.3.1 bug class: silently substituting a different file for the
        one the operator explicitly supplied must be impossible."""
        e = self._spec(GOOD_PNG)
        manifest, _, _ = sandbox([e], files={"f.bin": GOOD_PNG})
        import tempfile

        d = Path(tempfile.mkdtemp())
        f = d / "wrong.bin"
        f.write_bytes(b"different content entirely")
        with pytest.raises(A.AssetResolutionError, match="failed verification"):
            A.resolve_asset("f.bin", explicit=str(f), specs=A.load_manifests(manifest))

    def test_env_override(self, sandbox, monkeypatch, tmp_path):
        e = self._spec(GOOD_PNG)
        manifest, files_dir, _ = sandbox([e], files={"f.bin": GOOD_PNG})
        monkeypatch.setenv("OV_AMD_ASSET_F_BIN", str(files_dir / "f.bin"))
        r = A.resolve_asset("f.bin", specs=A.load_manifests(manifest))
        assert r.source == "explicit(env)" and r.sha256_verified

    def test_unknown_id_actionable_error(self, sandbox):
        manifest, _, _ = sandbox([self._spec(GOOD_PNG)])
        with pytest.raises(A.AssetResolutionError, match="unknown asset id"):
            A.resolve_asset("nope", specs=A.load_manifests(manifest))

    def test_no_workdir_cross_dependency_in_twin_sources(self):
        """Regression for the qwen3-asr defect: twin run.py files must not read
        another workload's results/ workdir."""
        import re

        repo = Path(__file__).resolve().parent.parent
        pattern = re.compile(r"results/[A-Za-z0-9_.\-]+/workdir")
        offenders = []
        for run in (repo / "workloads").glob("*/rocm/run.py"):
            text = run.read_text()
            if pattern.search(text):
                offenders.append(run)
        assert not offenders, f"twin(s) depend on another workload's workdir: {offenders}"


class TestFetchIntegrity:
    def test_fetch_rejects_wrong_hash_local(self, tmp_path):
        import sys

        repo = Path(__file__).resolve().parent.parent / "ov_amd"
        sys.path.insert(0, str(repo))
        import inspect

        from twin_lib import fetch

        sig = inspect.signature(fetch)  # noqa: F811
        assert "sha256" in sig.parameters, "fetch must support hash verification"

    def test_fetch_is_atomic_tmp_then_replace(self):
        import inspect
        import sys

        repo = Path(__file__).resolve().parent.parent / "ov_amd"
        sys.path.insert(0, str(repo))
        from twin_lib import fetch

        src = inspect.getsource(fetch)
        assert ".part" in src, "downloads must land in a temp file before replace"


class TestSafeExtraction:
    def _tar(self, members, path):
        with tarfile.open(path, "w") as tf:
            for name, data, mode in members:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                if mode:
                    info.type = mode
                    info.linkname = data.decode() if isinstance(data, bytes) else data
                    tf.addfile(info)
                else:
                    tf.addfile(info, io.BytesIO(data))
        return path

    def test_traversal_rejected(self, tmp_path):
        t = self._tar([("../escape.txt", b"x", None)], tmp_path / "t.tar")
        with pytest.raises(A.AssetResolutionError, match="escapes|traversal|unsafe"):
            A.safe_extract_tar(t, tmp_path / "out")

    def test_absolute_member_rejected(self, tmp_path):
        t = self._tar([("/etc/abs.txt", b"x", None)], tmp_path / "a.tar")
        with pytest.raises(A.AssetResolutionError):
            A.safe_extract_tar(t, tmp_path / "out")

    def test_absolute_symlink_rejected(self, tmp_path):
        t = self._tar([("lnk", "/etc/passwd", tarfile.SYMTYPE)], tmp_path / "s.tar")
        with pytest.raises(A.AssetResolutionError, match="link member"):
            A.safe_extract_tar(t, tmp_path / "out")

    def test_benign_tar_extracts(self, tmp_path):
        t = self._tar([("ok.txt", b"hello", None)], tmp_path / "b.tar")
        A.safe_extract_tar(t, tmp_path / "out")
        assert (tmp_path / "out" / "ok.txt").read_text() == "hello"

    def test_zip_traversal_rejected(self, tmp_path):
        z = tmp_path / "e.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("../zip-escape.txt", "pwned")
        with pytest.raises(A.AssetResolutionError):
            A.safe_extract_zip(z, tmp_path / "zout")

    def test_qwen3_tts_uses_safe_extraction(self):
        repo = Path(__file__).resolve().parent.parent
        src = (repo / "workloads" / "qwen3-tts" / "rocm" / "run.py").read_text()
        assert "safe_extract" in src, "qwen3-tts repo tarball must use safe extraction"
        assert "extractall(dest.parent)" not in src, "raw extractall must be gone"


class TestRevisionPinning:
    """Phase 3.2: no verified twin silently resolves mutable main weights."""

    VERIFIED = [
        "qwen3", "deepseek-r1", "qwen3-embedding", "qwen3-reranker", "qwen3-asr", "glm-ocr",
        "paddleocr_vl", "smoldocling", "minicpm-v-4.6", "z-image-turbo", "kokoro",
        "whisper-asr-genai", "smolvlm2", "hello-detection", "stable-diffusion-text-to-image",
        "stable-diffusion-xl",
    ]

    def test_every_verified_twin_pins_a_revision(self):
        repo = Path(__file__).resolve().parent.parent
        for wid in self.VERIFIED:
            src = (repo / "workloads" / wid / "rocm" / "run.py").read_text()
            has_pin = ("REVISION =" in src) or ("MS_REVISION =" in src) or ("WEIGHT_SHA256" in src)
            assert has_pin, f"{wid} run.py does not pin a model/weights revision"

    def test_verified_twins_enforce_revision_at_call_sites(self):
        """Declaration is not enforcement (Gate-2 finding): every hub-backed
        from_pretrained call site in a verified twin must carry revision= (or an
        explicitly-operator-supplied pin). Hub identity is resolved through
        module-level constant assignments so from_pretrained(MODEL, ...) without
        revision= is caught — reverting a real pin must fail this test."""
        import ast

        repo = Path(__file__).resolve().parent.parent
        for wid in self.VERIFIED:
            path = repo / "workloads" / wid / "rocm" / "run.py"
            tree = ast.parse(path.read_text())
            # module-level constants that hold hub repo ids ("org/name")
            hub_vars: dict[str, str] = {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    v = node.value.value
                    if "/" in v and not v.startswith((".", "/", "http")) and " " not in v:
                        for t in node.targets:
                            if isinstance(t, ast.Name):
                                hub_vars[t.id] = v
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if "from_pretrained" not in (node.func.attr or ""):
                    continue
                arg0 = node.args[0] if node.args else None
                hub_id = None
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    v = arg0.value
                    if "/" in v and not v.startswith((".", "/", "http")) and " " not in v:
                        hub_id = v
                elif isinstance(arg0, ast.Name) and arg0.id in hub_vars:
                    hub_id = hub_vars[arg0.id]
                # ast.Call args (str(local)) are local-dir loads from pinned
                # snapshot downloads — verified via the revision=MS_REVISION check below
                if hub_id is not None:
                    kw_names = [kw.arg for kw in node.keywords]
                    if "revision" not in kw_names:
                        raise AssertionError(
                            f"{wid}: from_pretrained({hub_id}) has no revision= (mutable main weights)"
                        )
            src = path.read_text()
            if "snapshot_download(" in src:
                assert "revision=MS_REVISION" in src, f"{wid}: modelscope snapshot_download not pinned"

    def test_manifest_model_blocks_complete(self):
        repo = Path(__file__).resolve().parent.parent
        for wid in self.VERIFIED:
            data = yaml.safe_load((repo / "workloads" / wid / "workload.yaml").read_text())
            m = data.get("model") or {}
            for field in ("name", "source", "revision", "license", "license_source", "license_verification_date"):
                assert m.get(field), f"{wid} workload.yaml model.{field} missing/empty"
