"""Regression tests: generated public artifacts never leak machine-local paths.

Historical defect: notes embedding raw stderr excerpts carried
`/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venvs/...` into
catalog/compatibility.json and reports/failures.md when reports were
regenerated on a machine whose checkout root differed from the recorder's.
"""

from __future__ import annotations

from ov_amd.public_paths import sanitize_public_path, sanitize_public_text
from ov_amd.reporting import _rel, _sanitize_note, build_compatibility

DIRTY_NOTE = (
    "ImportError: cannot import name 'resolve_revision' from 'huggingface_hub' "
    "(/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venvs/cpu/2c24bba1/bin/../lib/python3.12/site-packages/"
    "huggingface_hub/__init__.py)"
)

WIN_DIRTY_NOTE = (
    r"FileNotFoundError: C:\Users\val\Desktop\OpenVINO-Notebooks-on-AMD\results\x\workdir-cpu\nyc.jpg missing"
)

WORKSPACE_NOTE = "FileNotFoundError: /workspace/OpenVINO-Notebooks-on-AMD/results/foo/workdir-cpu/data.bin"


def test_sanitize_note_strips_unix_runner_prefix() -> None:
    out = _sanitize_note(DIRTY_NOTE)
    assert "/home/amd/" not in out
    assert "/home/" not in out
    assert out.startswith("ImportError: cannot import name 'resolve_revision'")
    assert ".venvs/cpu/2c24bba1/bin/" in out  # repo-relative remainder preserved


def test_sanitize_note_strips_windows_prefix() -> None:
    out = _sanitize_note(WIN_DIRTY_NOTE)
    assert "C:\\Users\\" not in out
    assert "results\\x\\workdir-cpu\\nyc.jpg" in out


def test_sanitize_note_strips_workspace_prefix() -> None:
    out = _sanitize_note(WORKSPACE_NOTE)
    assert "/workspace/" not in out
    assert "results/foo/workdir-cpu/data.bin" in out


def test_sanitize_note_preserves_urls() -> None:
    url = "https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml"
    assert _sanitize_note(url) == url
    model_url = "https://huggingface.co/openvinotoolkit/gpt-2/resolve/main/config.json"
    assert _sanitize_note(model_url) == model_url


def test_sanitize_note_preserves_model_urls_with_home_like_substrings() -> None:
    # huggingface.co URLs can legitimately contain user-like path segments
    text = "downloaded https://huggingface.co/someuser/home-model/resolve/main/pytorch_model.bin ok"
    assert sanitize_public_text(text) == text


def test_sanitize_public_path_variants() -> None:
    assert sanitize_public_path("/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/results/a/1-cpu") == "results/a/1-cpu"
    assert sanitize_public_path("/workspace/OpenVINO-Notebooks-on-AMD/results/a/1-cpu") == "results/a/1-cpu"
    assert sanitize_public_path("results/a/1-cpu") == "results/a/1-cpu"
    assert sanitize_public_path(None) is None
    assert sanitize_public_path("https://github.com/x/OpenVINO-Notebooks-on-AMD/blob/main/README.md").startswith(
        "https://"
    )


def test_rel_handles_legacy_absolute_refs() -> None:
    assert _rel("/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/results/hello-world/20261007T034828Z-cpu") == (
        "results/hello-world/20261007T034828Z-cpu"
    )
    assert _rel("/somewhere/else/results/x/1-cpu") == "results/x/1-cpu"


def test_build_compatibility_notes_are_sanitized() -> None:
    from ov_amd.schemas import NotebookEntry

    catalog = [
        NotebookEntry(
            id="dirty-row",
            title="Dirty Row",
            category="Test",
            upstream_path="notebooks/x/x.ipynb",
            upstream_url="https://github.com/openvinotoolkit/openvino_notebooks/blob/commit/notebooks/x/x.ipynb",
        )
    ]
    state = {
        "upstream": {},
        "attempts": {
            "dirty-row": {
                "cpu": {
                    "status": "FAILED",
                    "failure_category": "DEPENDENCY",
                    "notes": [DIRTY_NOTE, WIN_DIRTY_NOTE, WORKSPACE_NOTE],
                    "evidence_dir": "/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/results/dirty-row/1-cpu",
                }
            }
        },
    }
    compat = build_compatibility(catalog=catalog, state=state)
    row = next(r for r in compat["rows"] if r["id"] == "dirty-row")
    joined = "\n".join(row["notes"])
    assert "/home/" not in joined
    assert "C:\\Users\\" not in joined
    assert "/workspace/" not in joined
    assert row["cpu_evidence"] == "results/dirty-row/1-cpu"
