"""Evidence Schema v2 — validation levels, device proof, repeatability.

Every v2 evidence JSON file carries "schema_version": 2. v0.1 evidence is
never rewritten into v2; it stays historical and is marked stale for current
compatibility purposes (see reports/revalidation-migration.md).

Validation levels (status is separate from validation_level):

- L1 EXECUTION_ONLY: notebook completed without unhandled error. Never a
  green VERIFIED on its own.
- L2 DEVICE_VERIFIED: inference positively proven on the requested device.
- L3 WORKLOAD_CORRECTNESS: device verified + workload-specific output
  correctness.

Device proof states (positive proof required for CPU VERIFIED):

- PROVEN_CPU / PROVEN_GPU / PROVEN_NPU: runtime evidence of execution on that
  device (EXECUTION_DEVICES property, or the explicit compile_model device
  argument when the property is unavailable).
- NOT_INFERENCE: the probe captured no OpenVINO compile_model call — either the notebook truly does not run inference (conversion/API-only), or it compiles internally via openvino_genai pipelines which bypass the Python Core API.
- AUTO_UNRESOLVED: compile happened, device argument AUTO and the runtime
  property was not queryable.
- UNKNOWN: no usable device evidence.

Status policy (decide_status): VERIFIED requires L3 + PROVEN_CPU + the
repeatability policy met. Anything green-but-lesser degrades honestly to
VERIFIED_WITH_LIMITATIONS with explicit machine-readable limitation notes.
"""

from __future__ import annotations

import json
import statistics
from enum import Enum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

REPEATABILITY_MIN_RUNS = 3  # VERIFIED policy for small/medium workloads


class ValidationLevel(str, Enum):
    EXECUTION_ONLY = "EXECUTION_ONLY"
    DEVICE_VERIFIED = "DEVICE_VERIFIED"
    WORKLOAD_CORRECTNESS = "WORKLOAD_CORRECTNESS"


class DeviceProof(str, Enum):
    PROVEN_CPU = "PROVEN_CPU"
    PROVEN_GPU = "PROVEN_GPU"
    PROVEN_NPU = "PROVEN_NPU"
    NOT_INFERENCE = "NOT_INFERENCE"
    AUTO_UNRESOLVED = "AUTO_UNRESOLVED"
    UNKNOWN = "UNKNOWN"


PROVEN_STATES = {DeviceProof.PROVEN_CPU, DeviceProof.PROVEN_GPU, DeviceProof.PROVEN_NPU}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    """Write one v2 evidence file with the schema version stamped in."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, **obj}
    path.write_text(json.dumps(payload, indent=2, default=str))


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def evidence_schema_version(path: Path) -> int | None:
    d = read_json(path)
    if d is None:
        return None
    v = d.get("schema_version")
    return int(v) if isinstance(v, int) else None


# ---------------------------------------------------------------------------
# repeatability aggregate
# ---------------------------------------------------------------------------


def p95_nearest_rank(sorted_values: list[float]) -> float:
    """Nearest-rank P95 (documented, stable for small samples)."""

    import math

    if not sorted_values:
        return 0.0
    rank = max(1, math.ceil(0.95 * len(sorted_values)))
    return sorted_values[rank - 1]


def aggregate_repeatability(durations_s: list[float], required_runs: int) -> dict[str, Any]:
    ok = sorted(durations_s)
    return {
        "successful_runs": len(ok),
        "required_runs": required_runs,
        "latencies_s": [round(v, 3) for v in durations_s],
        "median_latency_s": round(statistics.median(ok), 3) if ok else None,
        "p95_latency_s": round(p95_nearest_rank(ok), 3) if ok else None,
        "repeatability_passed": bool(ok) and len(ok) >= required_runs and required_runs > 0,
    }


# ---------------------------------------------------------------------------
# device proof
# ---------------------------------------------------------------------------


def summarize_device_proof(
    probe_jsonl: Path | None,
    requested_backend: str = "cpu",
    supporting_device_used: str = "",
) -> dict[str, Any]:
    """Summarize raw probe events into a device-proof verdict.

    Positive proof comes from probe events: the runtime's EXECUTION_DEVICES
    property (authoritative), else the explicit device argument. Text/ widget
    scans are supporting evidence only and can never create positive proof.
    """

    events: list[dict[str, Any]] = []
    probe_present = probe_jsonl is not None and probe_jsonl.exists() and probe_jsonl.stat().st_size > 0
    if probe_jsonl is not None and probe_jsonl.exists():
        for line in probe_jsonl.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    probe_installed = any(e.get("kind") == "probe_installed" for e in events)

    compiles = [e for e in events if e.get("kind") == "compile_model"]
    genai_events = [e for e in events if e.get("kind") == "genai_pipeline"]
    exec_devices: list[list[str]] = []
    device_args: list[str | None] = []
    genai_args: list[str | None] = []
    for e in compiles:
        ed = e.get("execution_devices")
        if isinstance(ed, list) and ed:
            exec_devices.append([str(d) for d in ed])
        if e.get("device_arg") is not None:
            device_args.append(str(e["device_arg"]))
    for e in genai_events:
        # openvino_genai pipelines compile internally (C++ Core); the explicit
        # device argument the notebook passes is Method B evidence
        if e.get("device_arg") is not None:
            genai_args.append(str(e["device_arg"]))

    all_args = device_args + genai_args

    state = DeviceProof.UNKNOWN
    if not probe_present:
        # no probe output at all: instrumentation did not run, so "no compile
        # events" cannot be distinguished from "no evidence collected"
        state = DeviceProof.UNKNOWN
    else:
        seen_upper = {d.upper() for devs in exec_devices for d in devs}
        if exec_devices:
            # every resolved compile must agree; mixed evidence degrades honestly
            if seen_upper <= {"CPU"}:
                state = DeviceProof.PROVEN_CPU
            elif "GPU" in seen_upper:
                state = DeviceProof.PROVEN_GPU
            elif "NPU" in seen_upper:
                state = DeviceProof.PROVEN_NPU
            else:
                state = DeviceProof.AUTO_UNRESOLVED
        elif all_args:
            # property unavailable; explicit non-AUTO device argument is Method B
            if all(a.upper() == "CPU" for a in all_args):
                state = DeviceProof.PROVEN_CPU
            elif any(a.upper() == "GPU" for a in all_args):
                state = DeviceProof.PROVEN_GPU
            elif any(a.upper() == "NPU" for a in all_args):
                state = DeviceProof.PROVEN_NPU
            else:
                state = DeviceProof.AUTO_UNRESOLVED
        elif not compiles and not genai_events:
            state = DeviceProof.NOT_INFERENCE
        else:
            state = DeviceProof.AUTO_UNRESOLVED

    return {
        "state": state.value,
        "requested_backend": requested_backend,
        "compile_events": len(compiles),
        "genai_pipeline_events": len(genai_events),
        "execution_devices": exec_devices,
        "device_args": device_args,
        "genai_device_args": genai_args,
        "supporting_device_used": supporting_device_used,
        "probe_events": len(events),
        "probe_present": probe_present,
        "probe_installed": probe_installed,
    }


def proof_state(v: dict[str, Any] | str) -> DeviceProof:
    if isinstance(v, dict):
        v = v.get("state", DeviceProof.UNKNOWN.value)
    try:
        return DeviceProof(str(v))
    except ValueError:
        return DeviceProof.UNKNOWN


# ---------------------------------------------------------------------------
# validation level + status policy
# ---------------------------------------------------------------------------

CONTRACT_KEYS = ("output_contains", "output_not_contains", "min_output_chars", "output_finite_numbers")


def has_contract(validation_cfg: dict[str, Any] | None) -> bool:
    """A real workload-specific correctness contract exists (Defect F)."""

    if not validation_cfg:
        return False
    return any(k in validation_cfg for k in CONTRACT_KEYS)


def decide_status(
    *,
    runs_ok: int,
    required_runs: int,
    contract_present: bool,
    proof: DeviceProof,
    n_cells: int,
    n_skipped: int,
) -> tuple[str, list[str], ValidationLevel]:
    """v2 status decision for one backend attempt.

    Returns (status_value, limitation_notes, validation_level).
    FAILED handling (runs_ok == 0, contract failure) is the caller's job.
    """

    from ov_amd.schemas import Status

    notes: list[str] = []
    if n_cells == 0:
        return Status.NOT_APPLICABLE.value, ["notebook has no executable code cells"], ValidationLevel.EXECUTION_ONLY

    level = ValidationLevel.WORKLOAD_CORRECTNESS if contract_present else ValidationLevel.EXECUTION_ONLY

    green = runs_ok >= 1
    full_green = (
        green
        and contract_present
        and proof == DeviceProof.PROVEN_CPU
        and runs_ok >= required_runs >= REPEATABILITY_MIN_RUNS
    )

    if full_green:
        if n_skipped:
            notes.append("CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (documented skip policy)")
            return Status.VERIFIED_WITH_LIMITATIONS.value, notes, level
        return Status.VERIFIED.value, notes, level

    if not green:
        return Status.FAILED.value, notes, level

    # executed successfully but at least one v2 requirement is missing
    if level is ValidationLevel.EXECUTION_ONLY:
        notes.append("EXECUTION_ONLY: no workload correctness contract (validation: {})")
    if proof is DeviceProof.NOT_INFERENCE:
        notes.append(
            "DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the "
            "probe (notebooks driving openvino_genai pipelines or conversion-only code "
            "bypass the Python Core API; positive device execution therefore unproven)"
        )
    elif proof not in PROVEN_STATES:
        notes.append(f"DEVICE_PROOF_INCOMPLETE: device proof state {proof.value}")
    if proof is DeviceProof.PROVEN_GPU:
        notes.append("execution proven on GPU, not the requested CPU path")
    if runs_ok < REPEATABILITY_MIN_RUNS:
        notes.append("repeatability_not_established: fewer than 3 successful runs (resource-bounded policy)")
    if n_skipped:
        notes.append("CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (documented skip policy)")
    return Status.VERIFIED_WITH_LIMITATIONS.value, notes, level
