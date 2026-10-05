"""Schema and status-machine tests."""

import pytest

from ov_amd.schemas import (
    STATUS_TRANSITIONS,
    AttemptRecord,
    ExecutionInfo,
    FailureCategory,
    NotebookEntry,
    Status,
    TwinLevel,
    transition_ok,
)


def test_statuses_complete():
    assert Status.VERIFIED.value == "VERIFIED"
    assert Status.SKIPPED_RESOURCE.value == "SKIPPED_RESOURCE"


def test_happy_path_transitions():
    assert transition_ok(Status.NOT_TESTED, Status.QUEUED)
    assert transition_ok(Status.QUEUED, Status.RUNNING)
    assert transition_ok(Status.RUNNING, Status.VERIFIED)
    assert transition_ok(Status.RUNNING, Status.FAILED)


def test_illegal_transitions():
    assert not transition_ok(Status.NOT_TESTED, Status.VERIFIED)
    assert not transition_ok(Status.FAILED, Status.VERIFIED)  # failed must be re-run via RUNNING
    assert not transition_ok(Status.NOT_APPLICABLE, Status.RUNNING)


def test_every_status_has_transitions():
    assert set(STATUS_TRANSITIONS) == set(Status)


def test_notebook_entry_roundtrip():
    e = NotebookEntry(id="x", title="X", category="LLM", upstream_path="notebooks/x/x.ipynb", upstream_url="u")
    d = e.to_dict()
    e2 = NotebookEntry.from_dict(d)
    assert e2 == e


def test_execution_info_defaults():
    info = ExecutionInfo()
    assert info.status == Status.NOT_TESTED.value
    assert info.retry_count == 0
    assert info.failure_category == ""


def test_failure_categories_have_values():
    assert FailureCategory.OOM.value == "OOM"
    assert FailureCategory.ROCM_UNAVAILABLE.value == "ROCM_UNAVAILABLE"


def test_twin_levels():
    assert {t.value for t in TwinLevel} == {
        "EXACT_TWIN",
        "WORKLOAD_TWIN",
        "CONCEPT_MAPPING",
        "OPENVINO_SPECIFIC",
        "NOT_CLASSIFIED",
    }


def test_attempt_record_serializable():
    r = AttemptRecord(workload_id="w", backend="cpu", timestamp="t")
    d = r.to_dict()
    assert d["workload_id"] == "w"
    assert "execution" in d


@pytest.mark.parametrize("status", list(Status))
def test_status_icons_available(status):
    from ov_amd.schemas import STATUS_ICONS

    assert status.value in STATUS_ICONS
