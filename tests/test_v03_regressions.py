"""v0.3 regression coverage: recovery tooling, ROCm twin metadata, featured
README generation, transport-probe hardening, preseed/skip fixes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# the 12 new v0.3 ROCm twin candidates (reports/v0.3-rocm-candidates.md)
V03_TWIN_IDS = [
    "qwen3-tts", "qwen3-asr", "qwen3-embedding", "qwen3-reranker",
    "paddleocr_vl", "glm-ocr", "deepseek-ocr", "smoldocling",
    "yolov26-object-detection", "minicpm-v-4.6", "florence2", "z-image-turbo",
]

MODEL_FIELDS = {"name", "source", "revision", "license"}


def test_v03_rocm_twins_have_complete_model_metadata() -> None:
    """Every new twin declares model identity (name/source/revision/license)
    in workloads/<id>/workload.yaml — no anonymous model claims."""
    import yaml

    for wid in V03_TWIN_IDS:
        p = REPO / "workloads" / wid / "workload.yaml"
        assert p.exists(), f"{wid}: no workload.yaml"
        cfg = yaml.safe_load(p.read_text()) or {}
        model = cfg.get("model") or {}
        missing = MODEL_FIELDS - {k for k in MODEL_FIELDS if model.get(k)}
        assert not missing, f"{wid}: model metadata missing {missing}"
        assert (cfg.get("gpu") or {}).get("runtime") == "pytorch-rocm", f"{wid}: gpu runtime not declared"
        assert int((cfg.get("gpu") or {}).get("wall_timeout_s", 0)) > 0, f"{wid}: no gpu wall timeout"


def test_v03_rocm_twin_scripts_exist_and_use_twin_lib() -> None:
    """Each new twin ships a run.py that imports the shared twin contract
    (device proof + emit) and declares its model identity in-source."""
    for wid in V03_TWIN_IDS:
        p = REPO / "workloads" / wid / "rocm" / "run.py"
        assert p.exists(), f"{wid}: no rocm/run.py"
        src = p.read_text()
        assert "from twin_lib import" in src, f"{wid}: bypasses twin_lib contract"
        assert "emit(" in src, f"{wid}: no emit() result reporting"
        assert "MODEL" in src, f"{wid}: no MODEL identity constant"


@pytest.mark.parametrize("wid", V03_TWIN_IDS)
def test_v03_twin_ids_map_to_catalog_rows(wid: str) -> None:
    """Candidate ids must be real catalog rows (no phantom twins)."""
    rows = json.loads((REPO / "catalog" / "compatibility.json").read_text())["rows"]
    assert wid in {r["id"] for r in rows}


def test_v03_candidate_set_matches_report() -> None:
    """reports/v0.3-rocm-candidates.md names exactly the 12 implemented twins
    and the exact existing-8 baseline."""
    text = (REPO / "reports" / "v0.3-rocm-candidates.md").read_text()
    for wid in V03_TWIN_IDS:
        assert f"`{wid}`" in text, f"{wid} missing from candidate report"
    for existing in ("qwen3", "deepseek-r1", "hello-detection", "kokoro", "smolvlm2",
                     "stable-diffusion-text-to-image", "stable-diffusion-xl", "whisper-asr-genai"):
        assert existing in text


def test_deepseek_ocr_twin_uses_notebook_default_model() -> None:
    """Gate-4 correction: the twin must run DeepSeek-OCR-2 (the notebook's
    dropdown default), not v1."""
    src = (REPO / "workloads" / "deepseek-ocr" / "rocm" / "run.py").read_text()
    assert 'deepseek-ai/DeepSeek-OCR-2"' in src
    assert '"deepseek-ai/DeepSeek-OCR"' not in src.replace("DeepSeek-OCR-2", "")


def test_florence2_twin_uses_notebook_default_variant() -> None:
    """Gate-4 correction: Florence-2-base-ft is the notebook default."""
    src = (REPO / "workloads" / "florence2" / "rocm" / "run.py").read_text()
    assert "microsoft/Florence-2-base-ft" in src


def test_featured_matrix_generation_writes_only_verified_gpu_rows(tmp_path, monkeypatch) -> None:
    """The generated README featured matrix renders every GPU-verified row
    (never NOT_TESTED) with twin level, between explicit markers."""
    from ov_amd import reporting

    compat = {
        "rows": [
            {"id": "aaa", "upstream_url": "https://x/aaa", "cpu_compatibility_outcome": "VERIFIED",
             "cpu_outcome_reason": "", "gpu_compatibility_outcome": "VERIFIED", "gpu_outcome_reason": "",
             "twin_level": "WORKLOAD_TWIN"},
            {"id": "bbb", "upstream_url": "https://x/bbb", "cpu_compatibility_outcome": "BLOCKED_NETWORK",
             "cpu_outcome_reason": "EXTERNAL_HOST_UNREACHABLE", "gpu_compatibility_outcome": "NOT_TESTED",
             "gpu_outcome_reason": "", "twin_level": "WORKLOAD_TWIN"},
        ]
    }
    readme = tmp_path / "README.md"
    readme.write_text(
        "pre\n<!-- generated:featured begin -->\nold\n<!-- generated:featured end -->\npost\n"
    )
    monkeypatch.setattr(reporting, "README", readme)
    assert reporting.write_featured_matrix(compat) is True
    out = readme.read_text()
    assert "pre" in out and "post" in out
    assert "| [aaa](https://x/aaa)" in out
    assert "bbb" not in out  # NOT_TESTED rows never appear in the featured matrix
    assert "WORKLOAD_TWIN" in out


def test_featured_matrix_requires_markers(tmp_path, monkeypatch) -> None:
    from ov_amd import reporting

    compat = {"rows": []}
    readme = tmp_path / "README.md"
    readme.write_text("no markers here")
    monkeypatch.setattr(reporting, "README", readme)
    assert reporting.write_featured_matrix(compat) is False


def test_demo_close_teardown_is_skipped() -> None:
    """v0.3 C5: demo.close() teardown cells after a skipped UI demo are in the
    documented skip set (core inference must not NameError on `demo`)."""
    import re

    from ov_amd.executor import DEFAULT_SKIP_RES

    joined = "|".join(DEFAULT_SKIP_RES)
    assert re.search(joined, "demo.close()\ntext2image_pipe = None\ngc.collect();", re.M)
    assert re.search(joined, "demo.launch(share=True)")
    # core-inference cells must not be skipped by these patterns
    assert not re.search(joined, "x = model.generate(prompt)", re.M)
    assert not re.search(joined, "result = pipe(prompt=p, num_steps=4).images[0]", re.M)


def test_sibling_package_dir_detector(tmp_path) -> None:
    """v0.3 C6: sibling python-package directories qualify for preseed."""
    from ov_amd.notebook_runner import _is_helper_package_dir

    pkg = tmp_path / "deepsort_utils"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "deep_sort.py").write_text("x = 1\n")
    assert _is_helper_package_dir(pkg) is True

    heavy = tmp_path / "model_weights"
    heavy.mkdir()
    (heavy / "weights.bin").write_bytes(b"\0" * 32)
    assert _is_helper_package_dir(heavy) is False  # non-.py content

    nopy = tmp_path / "assets"
    nopy.mkdir()
    (nopy / "a.json").write_text("{}")
    assert _is_helper_package_dir(nopy) is False  # no .py at all


def test_git_transport_probe_verifies_worktree(monkeypatch) -> None:
    """v0.3 defect fix: a clone that exits 0 but materializes an empty
    worktree (git-wrapper http fallback dying mid-fetch) must select the
    codeload mode, not direct."""
    from ov_amd import environment

    monkeypatch.setattr(environment, "_GIT_TRANSPORT_CACHE", {})
    import subprocess as sp

    def fake_run(cmd, capture_output=True, text=True, timeout=60):
        class R:
            returncode = 0
            stderr = ""
            stdout = ""
        return R()

    monkeypatch.setattr(sp, "run", fake_run)
    # clone "succeeds" but the probe dir stays empty (no files written)
    result = environment.resolve_git_transport()
    assert result["mode"] == "codeload"
    assert "worktree=EMPTY" in result["probe"]


def test_git_transport_probe_direct_when_materialized(monkeypatch) -> None:
    from ov_amd import environment

    monkeypatch.setattr(environment, "_GIT_TRANSPORT_CACHE", {})
    import subprocess as sp

    def fake_run2(cmd, capture_output=True, text=True, timeout=60):
        dest = Path(cmd[-1])
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "README").write_text("ok")
        class R:
            returncode = 0
            stderr = ""
            stdout = ""
        return R()

    monkeypatch.setattr(sp, "run", fake_run2)
    result = environment.resolve_git_transport()
    assert result["mode"] == "direct"


def test_snapshot_raw_asset_preseed_preserves_subdirs(tmp_path, monkeypatch) -> None:
    """v0.3 defect fix: raw.githubusercontent fetches into subdirectories are
    preseeded at the RELATIVE path (model/u2net.py), not only flat."""
    import sys as _s

    _s.path.insert(0, str(REPO))
    from ov_amd import notebook_runner
    from ov_amd.notebook_runner import _preseed_helpers

    root = tmp_path / "upstream"
    nb_dir = root / "notebooks" / "vbr"
    (nb_dir / "model").mkdir(parents=True)
    (nb_dir / "model" / "u2net.py").write_text("# helper\n")
    nb = nb_dir / "vbr.ipynb"
    nb.write_text(
        json.dumps(
            {"cells": [{"cell_type": "code", "source": [
                'if not Path("./model/u2net.py").exists():\n',
                '    download_file(url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/notebooks/vbr/model/u2net.py")\n',
            ]}]}
        )
    )
    monkeypatch.setattr(notebook_runner, "upstream_root", lambda: root)
    cwd = tmp_path / "workdir"
    cwd.mkdir()
    notes = _preseed_helpers(cwd, nb)
    assert (cwd / "model" / "u2net.py").exists(), "subdir asset must be preseeded at its relative path"
    assert any("model/u2net.py" in n for n in notes)


def test_recovery_plan_clusters_are_catalog_bound() -> None:
    """Every cluster member in the v0.3 recovery plan is a real catalog id
    (guards against drift between the plan and the catalog)."""
    rows = json.loads((REPO / "catalog" / "compatibility.json").read_text())["rows"]
    ids = {r["id"] for r in rows}
    text = (REPO / "reports" / "v0.3-recovery-priority.md").read_text()
    import re

    listed = set(re.findall(r"- `([\w.-]+)` —", text))
    assert listed <= ids, f"unknown ids in recovery plan: {listed - ids}"


def test_freshness_monitor_workflow_exists_and_scopes_impact() -> None:
    """§43: scheduled pin-vs-latest check that flags ONLY affected workloads."""
    p = REPO / ".github" / "workflows" / "upstream-freshness-monitor.yml"
    assert p.exists()
    text = p.read_text()
    assert "schedule" in text
    assert "openvinotoolkit/openvino_notebooks" in text
    assert "affected workloads" in text  # incremental scope, not blanket invalidation



def test_raw_asset_preseed_rejects_path_traversal(tmp_path, monkeypatch) -> None:
    """Gate-7 finding: a crafted ../ in a raw.githubusercontent URL path must
    never read outside the snapshot or write outside the kernel cwd."""
    import sys as _s

    _s.path.insert(0, str(REPO))
    from ov_amd import notebook_runner
    from ov_amd.notebook_runner import _preseed_helpers

    root = tmp_path / "upstream"
    nb_dir = root / "notebooks" / "x"
    nb_dir.mkdir(parents=True)
    nb = nb_dir / "x.ipynb"
    nb.write_text(json.dumps({"cells": [{"cell_type": "code", "source": [
        'download_file(url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/../../evil.py")\n',
    ]}]}))
    monkeypatch.setattr(notebook_runner, "upstream_root", lambda: root)
    cwd = tmp_path / "workdir"
    cwd.mkdir()
    _preseed_helpers(cwd, nb)
    assert not (tmp_path / "evil.py").exists(), "traversal escaped the workdir"
    assert not (tmp_path / "upstream" / "evil.py").exists()
