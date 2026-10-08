"""Regression tests for the v0.2.2 current-upstream release closure.

Covers the defect classes fixed in this closure:
  1. Qwen3 wrong-device attribution — a cpu-backend attempt whose device proof
     is PROVEN_GPU must never be counted as an AMD CPU compatibility failure.
  2. gpu-device CPU applicability — GPU-purpose notebooks adjudicate to
     NOT_APPLICABLE on the CPU dimension, never FAILED_COMPATIBILITY.
  3. New upstream notebook discovery — incremental rediscovery preserves
     audited classifications and adds new ids.
  4. Upstream changed notebook — evidence on a different sha than the pin is
     only valid when notebook content is identical (pre-repin evidence rule).
  5. Corrupt download recovery — the pinned snapshot actually contains the
     upstream atomic-download fix this closure relies on.
  6. Coverage count drift — README/coverage numbers derive from the catalog
     dynamically; a pin bump that changes the catalog must change the counts.
  7. Freshness rendering — README renders the committed freshness record
     without network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ov_amd.environment import REPO_ROOT
from ov_amd.outcomes import CompatibilityOutcome, derive_outcome

REPO = REPO_ROOT


# 1. Qwen3 wrong-device attribution -----------------------------------------


def test_gpu_plugin_failure_is_not_cpu_compatibility_failure() -> None:
    """The v0.2.1 defect: clEnqueueMapBuffer CL_INVALID_VALUE (an OpenVINO
    GPU-plugin-on-Radeon failure, device proof PROVEN_GPU) was recorded on the
    cpu backend as FAILED_COMPATIBILITY. The guard must make that impossible."""

    outcome, reason = derive_outcome(
        "FAILED",
        "OPENVINO_ERROR",
        "RuntimeError: [GPU] clEnqueueMapBuffer, error code: -30 CL_INVALID_VALUE",
        device_proof="PROVEN_GPU",
        backend="cpu",
    )
    assert outcome is not CompatibilityOutcome.FAILED_COMPATIBILITY
    assert outcome is CompatibilityOutcome.NOT_TESTED
    assert reason == "DEVICE_ATTRIBUTION_INVALID_GPU_PLUGIN"


def test_cpu_proven_failure_still_is_compatibility_failure() -> None:
    """Guard must not over-fire: a genuine CPU-plugin failure with PROVEN_CPU
    stays a compatibility failure."""

    outcome, reason = derive_outcome(
        "FAILED",
        "OPENVINO_ERROR",
        "Exception from src/plugins/intel_cpu/src/graph.cpp: ReadValue node doesn't have sibling output",
        device_proof="PROVEN_CPU",
        backend="cpu",
    )
    assert outcome is CompatibilityOutcome.FAILED_COMPATIBILITY
    assert reason == "OPENVINO_RUNTIME"


def test_category_mapped_gpu_failure_also_guarded() -> None:
    """Failures reaching FAILED_COMPATIBILITY via category mapping (no
    signature hit) are guarded too."""

    outcome, _ = derive_outcome(
        "FAILED",
        "INFERENCE_ERROR",
        "some unclassified native error",
        device_proof="PROVEN_GPU",
        backend="cpu",
    )
    assert outcome is CompatibilityOutcome.NOT_TESTED


def test_gpu_backend_gpu_proof_is_fine() -> None:
    """On the gpu (ROCm twin) backend, PROVEN_GPU failures are legitimate
    compatibility verdicts — the guard is CPU-attribution specific."""

    outcome, _ = derive_outcome(
        "FAILED",
        "OPENVINO_ERROR",
        "[GPU] clEnqueueMapBuffer CL_INVALID_VALUE",
        device_proof="PROVEN_GPU",
        backend="gpu",
    )
    assert outcome is CompatibilityOutcome.FAILED_COMPATIBILITY


def test_current_dataset_has_no_gpu_proof_cpu_compat_failures() -> None:
    """Dataset-level invariant: no cpu row may carry FAILED_COMPATIBILITY
    together with a GPU device proof (regression tripwire for any future
    adjudication/migration script)."""

    state = json.loads((REPO / "results" / "marathon-state.json").read_text())
    bad = [
        wid
        for wid, rec in state.get("attempts", {}).items()
        if (rec.get("cpu") or {}).get("compatibility_outcome") == "FAILED_COMPATIBILITY"
        and (rec.get("cpu") or {}).get("device_proof") == "PROVEN_GPU"
    ]
    assert not bad, f"GPU-plugin failures recorded as CPU compatibility failures: {bad}"


# 2. gpu-device CPU applicability -------------------------------------------


def test_gpu_device_notebook_is_gpu_purpose_by_construction() -> None:
    """The pinned upstream gpu-device notebook hardcodes device = "GPU" for
    its property walkthrough/compilation cells; its CPU-dimension outcome must
    be NOT_APPLICABLE (adjudicated), and the adjudication must be present in
    the dataset with provenance."""

    nb_path = REPO / ".cache" / "upstream" / "notebooks" / "gpu-device" / "gpu-device.ipynb"
    if not nb_path.exists():
        pytest.skip("pinned upstream snapshot not fetched in this environment")
    nb = json.loads(nb_path.read_text())
    code = "\n".join(
        "".join(c["source"]) for c in nb["cells"] if c.get("cell_type") == "code"
    )
    assert 'device = "GPU"' in code, "upstream changed the hardcoded GPU device — re-adjudicate applicability"
    state = json.loads((REPO / "results" / "marathon-state.json").read_text())
    rec = state["attempts"]["gpu-device"]["cpu"]
    assert rec["compatibility_outcome"] == "NOT_APPLICABLE", (
        f"gpu-device cpu outcome is {rec['compatibility_outcome']}; expected NOT_APPLICABLE adjudication"
    )
    assert any("gpu-purpose" in n or "NOT_APPLICABLE" in n or "applicability" in n for n in rec.get("notes", [])), (
        "gpu-device NOT_APPLICABLE adjudication lacks a provenance note"
    )


# 3. new upstream notebook discovery ----------------------------------------


def test_catalog_contains_new_upstream_notebooks() -> None:
    """After the 329562e -> 5f0b2b5 sync, the two pyannote notebooks must be
    catalogued (and classified — never NOT_CLASSIFIED)."""

    cat = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())
    by_id = {e["id"]: e for e in cat["notebooks"]}
    for wid in ("pyannote-audio", "pyannote-embedding"):
        assert wid in by_id, f"{wid} missing from catalog — discovery did not pick up the upstream addition"
        assert by_id[wid]["twin_level"] != "NOT_CLASSIFIED"
        assert by_id[wid]["category"] == "ASR"


def test_discovery_preserves_audited_classification() -> None:
    """Re-running discovery on a re-pin must not reset audited twin levels
    (the 171 enriched rows survived the 5f0b2b5 rediscovery)."""

    cat = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())
    levels = [e["twin_level"] for e in cat["notebooks"]]
    assert "NOT_CLASSIFIED" not in levels, "rediscovery reset audited twin classifications"


# 4. upstream changed notebook — evidence pin coherence ----------------------


def test_changed_notebook_old_pin_evidence_is_not_current() -> None:
    """For every .ipynb that changed between the old and new pin, the current
    dataset row must point at evidence recorded on the NEW pin (or an explicit
    revalidation marker) — old-pin evidence must not masquerade as current.

    Snapshot-scoped to the LATEST pin sync: v0.2.2 checked the 329562e->5f0b2b5
    delta (llm-chatbot x2, openvino-tokenizers; all revalidated then). v0.3
    moved the pin 5f0b2b5->2b1600d with exactly two changed notebooks
    (kokoro fp16 default, whisper-asr-genai nightly/NPU prep); those two must
    carry new-pin evidence. Notebooks unchanged in a delta legitimately keep
    evidence recorded at the earlier, content-identical pin."""

    changed = {
        "notebooks/kokoro/kokoro.ipynb",
        "notebooks/whisper-asr-genai/whisper-asr-genai.ipynb",
    }
    pin = json.loads((REPO / "upstream" / "openvino-notebooks.json").read_text())["commit"]
    cat = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())
    by_path = {e["upstream_path"]: e["id"] for e in cat["notebooks"]}
    state = json.loads((REPO / "results" / "marathon-state.json").read_text())
    for path in changed:
        wid = by_path.get(path)
        if not wid:
            continue
        rec = state["attempts"].get(wid, {}).get("cpu")
        assert rec, f"{wid}: no current attempt record"
        ev = Path(rec.get("evidence_dir", ""))
        up = ev / "upstream.json" if ev.exists() else None
        if up and up.exists():
            ev_commit = json.loads(up.read_text()).get("commit", "")
            assert ev_commit == pin, (
                f"{wid}: evidence still bound to old pin {ev_commit[:12]} — revalidation missing"
            )


# 5. corrupt download recovery ----------------------------------------------


def test_pinned_snapshot_contains_atomic_download_fix() -> None:
    """The recovery cluster relies on upstream #3667 (atomic .part download,
    enforced content length). Assert the pinned snapshot actually carries it —
    if upstream reverts it, recovery conclusions must be revisited."""

    nu = REPO / ".cache" / "upstream" / "utils" / "notebook_utils.py"
    if not nu.exists():
        pytest.skip("pinned upstream snapshot not fetched in this environment")
    text = nu.read_text()
    assert 'enforce_content_length = True' in text
    assert '".part"' in text  # atomic temp-file suffix in download_file()


def test_recovery_cluster_rows_are_evidence_derived() -> None:
    """The 8-workload corrupted-download cluster is exactly the set of
    MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT rows minus the two with independent
    root causes (bernini: topology mismatch; multimodal-rag: missing IR export).
    Re-derivation must stay stable — new corrupt rows extend the cluster."""

    state = json.loads((REPO / "results" / "marathon-state.json").read_text())
    all_corr = {
        wid
        for wid, rec in state["attempts"].items()
        if "MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT" in ((rec.get("cpu") or {}).get("outcome_reason") or "")
    }
    excluded = {"bernini-r-image-video", "multimodal-rag-llamaindex"}
    assert excluded <= all_corr
    # every remaining corrupt row must have been re-attempted after the
    # re-pin (fresh upstream.json commit) or resolved to a different outcome
    pin = json.loads((REPO / "upstream" / "openvino-notebooks.json").read_text())["commit"]
    for wid in sorted(all_corr - excluded):
        rec = state["attempts"][wid]["cpu"]
        ev = Path(rec.get("evidence_dir", ""))
        up = ev / "upstream.json" if ev.exists() else None
        if (rec.get("outcome_reason") or "") == "MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT":
            assert up and up.exists() and json.loads(up.read_text()).get("commit") == pin, (
                f"{wid}: stale corrupt-artifact record not re-attempted on the new pin"
            )


# 6. coverage count drift ----------------------------------------------------


def test_coverage_counts_match_catalog_size_dynamically() -> None:
    """The compatibility counts must always equal the catalog total (173 after
    the sync — but no literal may be asserted here; drift = generation bug)."""

    cat = yaml.safe_load((REPO / "catalog" / "notebooks.yaml").read_text())
    compat = json.loads((REPO / "catalog" / "compatibility.json").read_text())
    assert compat["counts"]["total"] == len(cat["notebooks"])
    assert compat["counts"]["cpu_attempted"] == len(cat["notebooks"])
    assert compat["counts"]["cpu_attempt_coverage_pct"] == 100.0


# 7. freshness rendering -----------------------------------------------------


def test_freshness_line_renders_committed_record(tmp_path, monkeypatch) -> None:
    import ov_amd.reporting as reporting

    monkeypatch.setattr(reporting, "REPO_ROOT", tmp_path)
    (tmp_path / "reports").mkdir(parents=True)
    (tmp_path / "reports" / "upstream-freshness.json").write_text(
        json.dumps(
            {
                "checked_at": "2026-10-07T15:17:07Z",
                "pinned_commit": "5f0b2b5f63fd84e91f5c4e87f9bf9d13141a1e9b",
                "latest_commit": "5f0b2b5f63fd84e91f5c4e87f9bf9d13141a1e9b",
                "ahead_by": 0,
                "status": "CURRENT",
            }
        )
    )
    line = reporting._freshness_line("5f0b2b5f")
    assert "CURRENT" in line

    (tmp_path / "reports" / "upstream-freshness.json").write_text(
        json.dumps({"checked_at": "2026-10-08T00:00:00Z", "latest_commit": "abc123def456", "ahead_by": 4})
    )
    line = reporting._freshness_line("5f0b2b5f")
    assert "UPSTREAM AHEAD BY 4 COMMITS" in line
    assert "REVALIDATION_REQUIRED" in line


def test_freshness_line_without_record_is_honest(tmp_path, monkeypatch) -> None:
    import ov_amd.reporting as reporting

    monkeypatch.setattr(reporting, "REPO_ROOT", tmp_path)
    line = reporting._freshness_line("5f0b2b5f")
    assert "UNKNOWN" in line


def test_guard_helper_notebook_utils_fetch_transforms_upstream_helpers() -> None:
    """The preseed's sibling-guard transformation pins the exact surgery applied
    to upstream helpers that refetch notebook_utils.py unconditionally."""

    from ov_amd.notebook_runner import _guard_helper_notebook_utils_fetch

    src = (
        "import requests\n\n"
        "r = requests.get(\n"
        '    url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/utils/notebook_utils.py",\n'
        "    timeout=30,\n"
        ")\n"
        'open("notebook_utils.py", "w").write(r.text)\n'
        "from notebook_utils import segmentation_map_to_overlay\n"
    )
    out = _guard_helper_notebook_utils_fetch(src)
    assert out is not None
    assert 'if not Path("notebook_utils.py").exists():' in out
    assert "from pathlib import Path" in out
    # the fetch + write lines are indented under the guard
    assert '    r = requests.get(' in out
    assert '    open("notebook_utils.py", "w").write(r.text)' in out
    # guarded/foreign sources pass through untouched
    assert _guard_helper_notebook_utils_fetch("import requests\nprint('hi')\n") is None
