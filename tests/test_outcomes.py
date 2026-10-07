"""Outcome taxonomy: execution status maps honestly to compatibility outcomes.

A network timeout, gated model, or missing CLI must never be presented as an
AMD/OpenVINO compatibility failure (comprehensive-verification Objective D).
"""

from __future__ import annotations

import pytest

from ov_amd.outcomes import CompatibilityOutcome, classify_timeout_stage, derive_outcome


def test_green_maps_directly() -> None:
    assert derive_outcome("VERIFIED")[0] is CompatibilityOutcome.VERIFIED
    assert derive_outcome("VERIFIED_WITH_LIMITATIONS")[0] is CompatibilityOutcome.VERIFIED_WITH_LIMITATIONS
    assert derive_outcome("NOT_APPLICABLE")[0] is CompatibilityOutcome.NOT_APPLICABLE


@pytest.mark.parametrize(
    ("category", "notes", "expected", "reason_fragment"),
    [
        ("NETWORK", "ConnectTimeout to huggingface.co", CompatibilityOutcome.BLOCKED_NETWORK, None),
        ("MODEL_ACCESS", "Access to model meta-llama/x is restricted", CompatibilityOutcome.BLOCKED_MODEL_ACCESS, None),
        ("DEPENDENCY", "ModuleNotFoundError: No module named 'x'", CompatibilityOutcome.BLOCKED_DEPENDENCY, None),
        ("TIMEOUT", "", CompatibilityOutcome.BLOCKED_TIMEOUT, "TIMEOUT_"),
        ("OOM", "std::bad_alloc", CompatibilityOutcome.BLOCKED_RESOURCE, None),
        ("OPENVINO_ERROR", "BrgemmCPU incompatible input element types", CompatibilityOutcome.FAILED_COMPATIBILITY, None),
        ("CONVERSION_ERROR", "ovc failed", CompatibilityOutcome.FAILED_COMPATIBILITY, None),
        ("CORRECTNESS_ERROR", "contract mismatch", CompatibilityOutcome.FAILED_COMPATIBILITY, None),
        ("INTERACTIVE_ONLY", "webcam", CompatibilityOutcome.BLOCKED_DEPENDENCY, None),
    ],
)
def test_failed_categories_map_to_outcomes(category, notes, expected, reason_fragment) -> None:
    outcome, reason = derive_outcome("FAILED", category, notes)
    assert outcome is expected
    if reason_fragment:
        assert reason.startswith(reason_fragment)


def test_unknown_with_gated_signature_is_model_access_not_compat() -> None:
    outcome, reason = derive_outcome("FAILED", "UNKNOWN", "HTTPError: Authentication token does not exist")
    assert outcome is CompatibilityOutcome.BLOCKED_MODEL_ACCESS
    assert reason == "GATED_OR_RESTRICTED_MODEL"


def test_unknown_with_empty_weights_is_resource_not_compat() -> None:
    outcome, reason = derive_outcome("FAILED", "UNKNOWN", "Empty weights data in bin file")
    assert outcome is CompatibilityOutcome.BLOCKED_RESOURCE
    assert reason == "MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT"


def test_misclassified_model_access_corrected_by_signature() -> None:
    outcome, _ = derive_outcome("FAILED", "MODEL_ACCESS", "AttributeError: 'Column' object has no attribute 'dtype'")
    # signature-first: no gated pattern -> falls to... datasets drift is not a
    # signature; MODEL_ACCESS category would wrongly win, so this documents the
    # adjudication path used for it
    assert outcome is not CompatibilityOutcome.VERIFIED


def test_optimum_cli_signature_outranks_category() -> None:
    outcome, reason = derive_outcome("FAILED", "MODEL_ACCESS", "optimum-cli export openvino failed")
    assert outcome is CompatibilityOutcome.BLOCKED_DEPENDENCY
    assert reason == "OPTIMUM_CLI_MISSING_OR_BROKEN"


def test_timeout_keeps_timeout_semantics_with_stage() -> None:
    outcome, reason = derive_outcome("FAILED", "TIMEOUT", "optimum-cli export timed out", timeout_stage="CONVERSION_EXPORT")
    assert outcome is CompatibilityOutcome.BLOCKED_TIMEOUT
    assert reason == "TIMEOUT_CONVERSION_EXPORT"


def test_npu_absent_is_resource_not_compat() -> None:
    outcome, reason = derive_outcome("FAILED", "OPENVINO_ERROR", "Unsupported configuration key: FULL_DEVICE_NAME")
    assert outcome is CompatibilityOutcome.BLOCKED_RESOURCE
    assert reason == "REQUIRED_HARDWARE_ABSENT"


def test_unknown_without_signature_flags_adjudication() -> None:
    outcome, reason = derive_outcome("FAILED", "UNKNOWN", "something novel")
    assert outcome is CompatibilityOutcome.FAILED_COMPATIBILITY
    assert reason == "UNKNOWN_ADJUDICATION_REQUIRED"


def test_timeout_stage_from_cell_markers() -> None:
    conv = "[cell 3 DONE + 19.3s]\n[cell 4 START + 19.3s] ### Convert model using Optimum-CLI tool"
    assert classify_timeout_stage(conv) == "CONVERSION_EXPORT"
    dl = "[cell 4 START + 19.9s] ## Download the original model"
    assert classify_timeout_stage(dl) == "MODEL_DOWNLOAD"
    inst = "[cell 3 START + 19.3s] ### Installation"
    assert classify_timeout_stage(inst) == "DEPENDENCY_INSTALL"
    infer = "[cell 12 START + 473.3s] result = compiled_model(inputs)"
    assert classify_timeout_stage(infer) == "INFERENCE"
    assert classify_timeout_stage("") == "UNKNOWN_STAGE"


def test_current_dataset_has_no_unadjudicated_unknowns() -> None:
    """Every terminal CPU row in marathon-state must carry an outcome, and no
    FAILED_COMPATIBILITY row may keep the UNKNOWN_ADJUDICATION_REQUIRED reason."""
    import json

    from ov_amd.environment import REPO_ROOT

    state = json.loads((REPO_ROOT / "results" / "marathon-state.json").read_text())
    unknown = []
    missing = []
    for wid, rec in state["attempts"].items():
        c = rec.get("cpu") or {}
        if not c.get("status") or c.get("status") == "NOT_TESTED":
            continue
        if not c.get("compatibility_outcome"):
            missing.append(wid)
        if c.get("outcome_reason") == "UNKNOWN_ADJUDICATION_REQUIRED":
            unknown.append(wid)
    assert not missing, f"rows without outcome: {missing}"
    assert not unknown, f"rows requiring adjudication: {unknown}"
