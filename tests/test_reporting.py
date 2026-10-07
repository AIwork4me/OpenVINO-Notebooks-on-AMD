"""Compatibility artifact generation tests (no writes to real repo paths)."""

from ov_amd.reporting import build_compatibility
from ov_amd.schemas import NotebookEntry, Status


def make(id_: str, cat="LLM", twin="WORKLOAD_TWIN") -> NotebookEntry:
    return NotebookEntry(
        id=id_,
        title=id_,
        category=cat,
        upstream_path=f"n/{id_}.ipynb",
        upstream_url=f"https://x/{id_}",
        twin_level=twin,
    )


def test_build_compatibility_counts():
    catalog = [make("a"), make("b"), make("c", cat="API", twin="OPENVINO_SPECIFIC")]
    state = {
        "attempts": {
            "a": {
                "cpu": {"status": Status.VERIFIED.value, "evidence_dir": "/e/a", "updated": "2026-10-01T00:00:00+00:00"}
            },
            "b": {"cpu": {"status": Status.FAILED.value, "failure_category": "DEPENDENCY"}},
        }
    }
    compat = build_compatibility(catalog, state)
    assert compat["counts"]["total"] == 3
    assert compat["counts"]["cpu"]["VERIFIED"] == 1
    assert compat["counts"]["cpu"]["FAILED"] == 1
    assert compat["counts"]["cpu"][Status.NOT_TESTED.value] == 1
    row_a = next(r for r in compat["rows"] if r["id"] == "a")
    assert row_a["cpu_status"] == "VERIFIED"
    assert row_a["evidence"] == "/e/a"


def test_build_compatibility_empty():
    compat = build_compatibility([], {"attempts": {}})
    assert compat["counts"]["total"] == 0
    assert compat["rows"] == []


def test_readme_block_insertion(tmp_path, monkeypatch):
    import ov_amd.reporting as rep

    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\nintro\n\n<!-- generated:compatibility begin -->\nold\n<!-- generated:compatibility end -->\n\ntail\n"
    )
    monkeypatch.setattr(rep, "README", readme)
    monkeypatch.setattr(rep, "CATALOG_MD", tmp_path / "compat.md")
    monkeypatch.setattr(rep, "CATALOG_JSON", tmp_path / "compat.json")
    monkeypatch.setattr(
        rep,
        "build_compatibility",
        lambda: {
            "generated": "now",
            "upstream": {},
            "counts": {
                "total": 2,
                "cpu": {"VERIFIED": 1, "FAILED": 1, "VERIFIED_WITH_LIMITATIONS": 0},
                "gpu": {"VERIFIED": 0, "VERIFIED_WITH_LIMITATIONS": 0},
                "cpu_attempted": 2,
                "cpu_attempt_coverage_pct": 100.0,
                "gpu_attempted": 0,
                "gpu_attempt_coverage_pct": 0.0,
                "twin_classified": 2,
                "twin_classification_coverage_pct": 100.0,
                "twin_levels": {},
            },
            "rows": [],
        },
    )
    rep.write_compatibility()
    text = readme.read_text()
    assert "old" not in text
    assert "notebooks catalogued" in text
    assert "intro" in text and "tail" in text
    assert (tmp_path / "compat.md").exists()
