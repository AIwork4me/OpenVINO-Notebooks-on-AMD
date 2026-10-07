"""Twin comparison safety (Defect: WORKLOAD_TWIN speedup claims) and
reporting attempt counts (Defect I)."""

from ov_amd.benchmark import comparison_policy
from ov_amd.reporting import _counts

# ---------------------------------------------------------------------------
# twin comparison guard
# ---------------------------------------------------------------------------


def test_exact_twin_allows_speedup():
    p = comparison_policy("EXACT_TWIN")
    assert p["speedup_allowed"] is True


def test_workload_twin_forbids_speedup():
    p = comparison_policy("WORKLOAD_TWIN")
    assert p["speedup_allowed"] is False
    assert "no direct speedup" in p["requirement"]


def test_concept_mapping_and_unclassified_have_no_comparison():
    assert comparison_policy("CONCEPT_MAPPING")["speedup_allowed"] is False
    assert comparison_policy("NOT_CLASSIFIED")["speedup_allowed"] is False


def test_openvino_specific_has_no_gpu_path():
    p = comparison_policy("OPENVINO_SPECIFIC")
    assert p["speedup_allowed"] is False and p["mode"] == "NO_GPU_PATH"


# ---------------------------------------------------------------------------
# reporting counts: attempted != catalog size (Defect I)
# ---------------------------------------------------------------------------


def test_counts_attempt_excludes_default_not_tested():
    rows = [
        {"cpu_status": "VERIFIED", "gpu_status": "NOT_TESTED", "twin_level": "WORKLOAD_TWIN"},
        {"cpu_status": "FAILED", "gpu_status": "NOT_TESTED", "twin_level": "NOT_CLASSIFIED"},
        {"cpu_status": "NOT_TESTED", "gpu_status": "NOT_TESTED", "twin_level": "NOT_CLASSIFIED"},
    ]
    c = _counts(rows)
    assert c["total"] == 3
    assert c["cpu_attempted"] == 2  # NOT_TESTED default row excluded
    assert c["gpu_attempted"] == 0
    assert c["cpu_attempt_coverage_pct"] == 66.7
    assert c["twin_classified"] == 1
    assert c["twin_classification_coverage_pct"] == 33.3


def test_counts_full_catalog_never_counts_as_attempted():
    rows = [
        {"cpu_status": "NOT_TESTED", "gpu_status": "NOT_TESTED", "twin_level": "NOT_CLASSIFIED"} for _ in range(171)
    ]
    c = _counts(rows)
    assert c["cpu_attempted"] == 0
    assert c["cpu_attempt_coverage_pct"] == 0.0
