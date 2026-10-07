"""Kernel-death / OOM discrimination diagnostics (v0.2.2).

DeadKernelError outcomes were previously classified KERNEL_DEATH_UNDIAGNOSED:
"kernel died" is not a verdict. This module captures the host-level evidence
needed to distinguish:

  OOM / resource exhaustion   -> BLOCKED_RESOURCE (provable)
  OpenVINO native crash       -> FAILED_COMPATIBILITY (reproducible segfault
                                 without resource exhaustion)
  Python kernel crash         -> case-by-case from the stderr signature

Sources (container-safe; dmesg is read-restricted on validation runners):
  - /sys/fs/cgroup/memory.events        -> oom / oom_kill counters
  - /sys/fs/cgroup/memory.peak          -> peak memory high-water mark (cgroup v2)
  - /sys/fs/cgroup/memory.current,.max  -> usage vs limit at capture time
  - /proc/pressure/memory               -> PSI (some/full stalls, %)
  - /proc/vmstat oom_kill counter       -> node-level kills
  - kernel stderr tail                  -> DeadKernel/abort signature

All captured post-mortem into the run's evidence directory; nothing here
changes outcomes by itself — the classifier/adjudication reads the record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CG = Path("/sys/fs/cgroup")


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def capture_kernel_death_diagnosis(run_dir: Path, stderr_tail: str = "") -> dict[str, Any]:
    """Write kernel-death-diagnosis.json into the evidence run dir."""

    events: dict[str, int] = {}
    for line in _read_text(_CG / "memory.events").splitlines():
        if " " in line:
            k, v = line.split(None, 1)
            try:
                events[k] = int(v)
            except ValueError:
                pass
    psi = {}
    for line in _read_text(Path("/proc/pressure/memory")).splitlines():
        m = re.match(r"(some|full) avg10=(\S+) avg60=(\S+) avg300=(\S+) total=(\S+)", line)
        if m:
            psi[m.group(1)] = {
                "avg10": m.group(2),
                "avg60": m.group(3),
                "avg300": m.group(4),
                "total_us": m.group(5),
            }
    vmstat_oom = None
    vmstat = _read_text(Path("/proc/vmstat"))
    m = re.search(r"^oom_kill (\d+)$", vmstat, re.M)
    if m:
        vmstat_oom = int(m.group(1))

    record = {
        "schema_version": 1,
        "captured": "post-mortem (after kernel exit)",
        "cgroup_memory_events": events,
        "cgroup_memory_peak_bytes": _read_int(_CG / "memory.peak"),
        "cgroup_memory_current_bytes": _read_int(_CG / "memory.current"),
        "cgroup_memory_max_bytes": _read_int(_CG / "memory.max"),
        "memory_psi": psi,
        "proc_vmstat_oom_kill": vmstat_oom,
        "dmesg": "not permitted in validation container (kernel buffer read restricted)",
        "stderr_signature": (stderr_tail or "")[-800:],
        "indicators": {
            "oom_kill_events": events.get("oom_kill", 0),
            "oom_events": events.get("oom", 0),
            "psi_full_avg10_pct": float(psi.get("full", {}).get("avg10", 0) or 0),
        },
        "verdict_hint": "",
    }
    kills = events.get("oom_kill", 0)
    oom_events = events.get("oom", 0)
    if kills > 0:
        record["verdict_hint"] = (
            f"OOM_PROVEN: cgroup oom_kill={kills} — kernel death is resource "
            "exhaustion in this container (BLOCKED_RESOURCE)"
        )
    elif oom_events > 0:
        record["verdict_hint"] = (
            "OOM_PRESSURE_PROVEN: cgroup oom events without kill in this container — "
            "allocation stalls preceded the death (BLOCKED_RESOURCE unless a native "
            "crash signature contradicts)"
        )
    else:
        # /proc/vmstat oom_kill is NODE-WIDE (all containers/tenants) and cannot
        # attribute a death to this workload; only the scoped cgroup counters can
        record["verdict_hint"] = (
            "NO_CONTAINER_OOM_EVIDENCE: cgroup counters show no OOM activity in this "
            "container (node-wide vmstat oom_kill is unscoped and not attributive); "
            "treat as runtime crash — FAILED_COMPATIBILITY if a native crash signature "
            "is present (e.g. GPU-plugin inline-asm), else adjudicate from stderr"
        )
    try:
        (run_dir / "kernel-death-diagnosis.json").write_text(json.dumps(record, indent=2) + "\n")
    except OSError:
        pass
    return record
