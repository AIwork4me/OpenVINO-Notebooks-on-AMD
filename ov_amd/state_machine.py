"""Mechanical enforcement of the validation status state machine.

The transition table lived in ov_amd.schemas.STATUS_TRANSITIONS but nothing
enforced it at the write sites — runners could record any status from any
status. This module raises InvalidStateTransition on illegal writes.

Recording model: runners write only terminal attempt records; an attempt
implicitly passed through QUEUED→RUNNING before its terminal record. Therefore:

- no prior record: any status reachable from RUNNING is valid (plus the
  NOT_TESTED-edge states NOT_APPLICABLE / SKIPPED_RESOURCE / BLOCKED, which
  gate before execution starts);
- same -> same: idempotent re-record (re-run with unchanged verdict) is valid;
- otherwise: valid iff old->new is a direct transition OR
  old->RUNNING->new is a valid two-step path;
- `force=True` is the explicit escape hatch for state surgery (documented
  migrations, audit corrections) and must be passed deliberately.
"""

from __future__ import annotations

from ov_amd.schemas import STATUS_TRANSITIONS, Status


class InvalidStateTransition(ValueError):
    """Raised when a status write violates the state machine."""


def enforce_transition(old: str | None, new: str, *, force: bool = False, context: str = "") -> None:
    if force:
        return
    new_st = Status(new)  # ValueError for unknown status strings is desired
    if old is None:
        from_running = STATUS_TRANSITIONS[Status.RUNNING]
        gate_only = {
            Status.NOT_TESTED,
            Status.NOT_APPLICABLE,
            Status.SKIPPED_RESOURCE,
            Status.BLOCKED,
            Status.QUEUED,
            Status.RUNNING,
        }
        if new_st in from_running or new_st in gate_only:
            return
        raise InvalidStateTransition(
            f"{context}: first record must be reachable from RUNNING or a pre-execution gate, got {new!r}"
        )
    old_st = Status(old)
    if old_st is new_st:
        return
    if new_st in STATUS_TRANSITIONS[old_st]:
        return
    # implicit intermediate phases the runner does not record separately:
    # QUEUED (scheduler picked the workload) and RUNNING (the attempt itself)
    for mid in (Status.RUNNING, Status.QUEUED):
        if mid in STATUS_TRANSITIONS[old_st] and new_st in STATUS_TRANSITIONS[mid]:
            return
    raise InvalidStateTransition(f"{context}: illegal transition {old!r} -> {new!r}")
