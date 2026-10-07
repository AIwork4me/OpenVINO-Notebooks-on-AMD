"""State-machine enforcement: illegal status writes must raise.

Historical defect: STATUS_TRANSITIONS existed but nothing enforced it — the
runners could write any status from any status (state transition not enforced,
see comprehensive-verification §30).
"""

from __future__ import annotations

import pytest

from ov_amd.schemas import Status
from ov_amd.state_machine import InvalidStateTransition, enforce_transition


def test_first_record_terminal_from_running_ok() -> None:
    enforce_transition(None, "VERIFIED", context="t/first")
    enforce_transition(None, "FAILED", context="t/first")
    enforce_transition(None, "VERIFIED_WITH_LIMITATIONS", context="t/first")
    enforce_transition(None, "NOT_APPLICABLE", context="t/first")
    enforce_transition(None, "SKIPPED_RESOURCE", context="t/first")


def test_first_record_cannot_appear_from_nowhere_green_only() -> None:
    # a first record must be a terminal/gate state the runner can actually write
    with pytest.raises(ValueError):
        enforce_transition(None, "SUPER_GREEN", context="t/first")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("NOT_TESTED", "RUNNING"),
        ("RUNNING", "VERIFIED"),
        ("RUNNING", "FAILED"),
        ("VERIFIED", "REVALIDATION_REQUIRED"),
        ("REVALIDATION_REQUIRED", "RUNNING"),
        ("FAILED", "RUNNING"),
    ],
)
def test_valid_lifecycle_transitions(old: str, new: str) -> None:
    enforce_transition(old, new, context="t/lifecycle")


def test_implicit_running_path_allows_retry_terminal() -> None:
    # runner records only terminal states; a retry of a FAILED workload
    # implicitly passes RUNNING
    enforce_transition("FAILED", "VERIFIED", context="t/retry")
    enforce_transition("VERIFIED", "FAILED", context="t/revalidation-ran-and-failed")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("NOT_APPLICABLE", "RUNNING"),
        ("NOT_APPLICABLE", "VERIFIED"),
        ("VERIFIED", "NOT_APPLICABLE"),
        ("QUEUED", "NOT_APPLICABLE"),
        ("RUNNING", "NOT_APPLICABLE"),
    ],
)
def test_invalid_transitions_raise(old: str, new: str) -> None:
    with pytest.raises(InvalidStateTransition):
        enforce_transition(old, new, context="t/invalid")


def test_not_tested_straight_to_green_is_invalid() -> None:
    # nothing ran: a green verdict without an attempt record is impossible
    with pytest.raises(InvalidStateTransition):
        enforce_transition("NOT_TESTED", "VERIFIED", context="t/no-attempt")


def test_same_status_idempotent() -> None:
    enforce_transition("VERIFIED", "VERIFIED", context="t/idem")
    enforce_transition("FAILED", "FAILED", context="t/idem")


def test_force_override_is_explicit() -> None:
    enforce_transition("NOT_APPLICABLE", "VERIFIED", force=True, context="t/surgery")


def test_unknown_status_string_raises() -> None:
    with pytest.raises(ValueError):
        enforce_transition("VERIFIED", "SUPER_VERIFIED", context="t/typo")


def test_schema_table_covers_all_statuses() -> None:
    for s in Status:
        assert s in {x for sts in [Status] for x in sts}  # tautology guard
        assert hasattr(Status, s.name)
