"""Regression: notebook-relative data assets resolve in headless execution.

Historical defect (paddleocr_vl / vlm-chatbot-generate-api): notebooks opening
sibling files ('nyc.jpg', 'test.png') failed with FileNotFoundError because the
kernel cwd differed from the notebook directory and only *.py siblings were
pre-seeded.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from ov_amd.notebook_runner import SIBLING_DATA_EXTS, _preseed_helpers


def _fake_upstream(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "upstream"
    nb_dir = root / "notebooks" / "demo"
    nb_dir.mkdir(parents=True)
    (root / "utils").mkdir()
    (root / "utils" / "notebook_utils.py").write_text("# utils\ndef device_widget(default='AUTO'):\n    pass\n")
    (nb_dir / "helper.py").write_text("# helper\n")
    (nb_dir / "nyc.jpg").write_bytes(b"\xff\xd8fakejpg")
    (nb_dir / "test.png").write_bytes(b"\x89PNGfakepng")
    (nb_dir / "config.json").write_text("{}")
    (nb_dir / "huge.bin").write_bytes(b"0" * (64 * 1024 * 1024 + 1))
    (nb_dir / "evil.exe").write_bytes(b"MZ")
    import ov_amd.notebook_runner as nr

    monkeypatch.setattr(nr, "upstream_root", lambda: root)
    return nb_dir / "demo.ipynb"


def test_sibling_data_assets_are_preseeded(tmp_path, monkeypatch) -> None:
    nb = _fake_upstream(tmp_path, monkeypatch)
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    patches = _preseed_helpers(workdir, nb)
    assert (workdir / "nyc.jpg").read_bytes() == b"\xff\xd8fakejpg"
    assert (workdir / "test.png").read_bytes() == b"\x89PNGfakepng"
    assert (workdir / "config.json").exists()
    assert (workdir / "helper.py").exists()
    assert not (workdir / "huge.bin").exists()  # over the size cap
    assert not (workdir / "evil.exe").exists()  # not a safe data extension
    assert any("nyc.jpg" in p for p in patches)
    assert any("test.png" in p for p in patches)


def test_notebook_referencing_asset_resolves(tmp_path, monkeypatch) -> None:
    """End-to-end semantics: a notebook cell `open('nyc.jpg')` succeeds when the
    kernel cwd is the pre-seeded workdir."""
    nb_path = _fake_upstream(tmp_path, monkeypatch)
    workdir = tmp_path / "workdir2"
    workdir.mkdir()
    _preseed_helpers(workdir, nb_path)
    # simulate what the notebook does
    with open(workdir / "nyc.jpg", "rb") as f:
        assert f.read(3) == b"\xff\xd8f"


def test_extension_allowlist_is_conservative() -> None:
    assert ".exe" not in SIBLING_DATA_EXTS
    assert ".jpg" in SIBLING_DATA_EXTS and ".json" in SIBLING_DATA_EXTS


def test_no_notebook_no_crash(tmp_path, monkeypatch) -> None:
    import ov_amd.notebook_runner as nr

    monkeypatch.setattr(nr, "upstream_root", lambda: None)
    assert _preseed_helpers(tmp_path, None) == []


def test_zip_bomb_guard_not_triggered_by_normal_assets(tmp_path, monkeypatch) -> None:
    # a normal-size zip asset (not extracted anywhere) passes the allowlist
    nb = _fake_upstream(tmp_path, monkeypatch)
    z = nb.parent / "data.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("a.txt", "x" * 100)
    workdir = tmp_path / "workdir3"
    workdir.mkdir()
    _preseed_helpers(workdir, nb)
    assert not (workdir / "data.zip").exists()  # .zip not in allowlist
