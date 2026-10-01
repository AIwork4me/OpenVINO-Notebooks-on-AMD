"""Unattended marathon driver: CPU sweep first, ROCm twins second, checkpointed."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from ov_amd.environment import REPO_ROOT, kernel_env, venv_exists, venv_python
from ov_amd.executor import load_upstream_meta, prune_cache_if_needed, run_workload_cpu
from ov_amd.notebook_runner import classify_failure
from ov_amd.reporting import write_compatibility, write_failures, write_progress
from ov_amd.scheduler import (
    checkpoint,
    load_catalog,
    load_state,
    next_runnable,
    resources_ok,
    save_state,
)
from ov_amd.schemas import FailureCategory, Status

GPU_WALL_TIMEOUT = {"small": 900, "medium": 1800, "large": 2700, "huge": 3600}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record_gpu(state: dict[str, Any], entry, status: Status, category: str = "", notes: list[str] | None = None,
                evidence: str | None = None) -> None:
    rec = state.setdefault("attempts", {}).setdefault(entry.id, {})
    rec["gpu"] = {
        "status": status.value,
        "failure_category": category,
        "notes": notes or [],
        "evidence_dir": evidence,
        "updated": _utcnow(),
    }
    save_state(state)


def run_gpu_twin(entry, state: dict[str, Any]) -> None:
    """Run workloads/<id>/rocm/run.py with the ROCm venv if it exists."""

    script = REPO_ROOT / "workloads" / entry.id / "rocm" / "run.py"
    if not script.exists():
        _record_gpu(state, entry, Status.NOT_TESTED, notes=["no ROCm twin implementation yet"])
        return
    if not venv_exists("gpu"):
        _record_gpu(state, entry, Status.BLOCKED, FailureCategory.ROCM_UNAVAILABLE.value,
                    notes=["ROCm torch venv not provisioned"])
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = REPO_ROOT / "results" / entry.id / f"{ts}-gpu"
    ev.mkdir(parents=True, exist_ok=True)
    wall = GPU_WALL_TIMEOUT.get(entry.est_weight, 1800)
    cmd = [str(venv_python("gpu")), str(script), "--evidence-dir", str(ev)]
    t0 = time.time()
    timed_out = False
    with open(ev / "stdout.log", "w") as so, open(ev / "stderr.log", "w") as se:
        proc = subprocess.Popen(cmd, stdout=so, stderr=se, env=kernel_env("gpu"), start_new_session=True,
                                cwd=str(ev))
        try:
            ret = proc.wait(timeout=wall)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                import os
                import signal
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                proc.kill()
            ret = -9
    duration = time.time() - t0
    stdout = (ev / "stdout.log").read_text(errors="replace")
    stderr = (ev / "stderr.log").read_text(errors="replace")

    # ROCm twin scripts print TWIN_RESULT={json} on success
    twin_result: dict[str, Any] = {}
    for line in reversed(stdout.splitlines()):
        if line.startswith("TWIN_RESULT="):
            try:
                twin_result = json.loads(line[len("TWIN_RESULT="):])
            except json.JSONDecodeError:
                pass
            break

    hip_ok = "hip" in stderr.lower() or twin_result.get("hip") or "torch.version.hip" in stdout
    if ret == 0 and twin_result.get("ok") and twin_result.get("hip"):
        _record_gpu(state, entry, Status.VERIFIED, evidence=str(ev))
        (ev / "metrics.json").write_text(json.dumps(twin_result.get("metrics", {}), indent=2))
    elif ret == 0:
        _record_gpu(state, entry, Status.FAILED, FailureCategory.CORRECTNESS_ERROR.value,
                    notes=["twin script exited 0 but did not emit a valid TWIN_RESULT with hip=true"],
                    evidence=str(ev))
    else:
        cat = classify_failure(stderr, stdout, timed_out)
        notes = [f"exit={ret} duration={duration:.0f}s", stderr.strip().splitlines()[-1][:300] if stderr.strip() else ""]
        _record_gpu(state, entry, Status.FAILED, cat.value, notes=notes, evidence=str(ev))
    _ = hip_ok


def run_marathon(
    cpu_only: bool = False,
    gpu_only: bool = False,
    max_runtime_s: float | None = None,
    retry_failed: bool = False,
    category: str | None = None,
    priority_max: int | None = None,
    report_every: int = 5,
) -> dict[str, Any]:
    """The autonomous campaign loop. Resumable via results/marathon-state.json."""

    state = load_state()
    meta = load_upstream_meta()
    if meta and not state.get("upstream"):
        state["upstream"] = meta
    catalog = load_catalog()
    if category:
        catalog = [e for e in catalog if e.category == category]
    if priority_max is not None:
        catalog = [e for e in catalog if e.priority <= priority_max]

    t0 = time.time()
    n_done = 0
    summary = {"cpu_attempted": 0, "verified": 0, "failed": 0, "blocked": 0, "skipped": 0}

    # ---- CPU sweep (primary) ----
    if not gpu_only:
        runnable = next_runnable(catalog, state, "cpu", retry_failed)
        for i, entry in enumerate(runnable):
            if max_runtime_s and (time.time() - t0) > max_runtime_s:
                summary["stopped"] = "max runtime reached"
                break
            ok, why = resources_ok()
            if not ok:
                summary["stopped"] = f"resources: {why}"
                break
            freed = prune_cache_if_needed()
            checkpoint(state, entry.id)
            write_progress(state, entry.id)
            print(f"[marathon/cpu {i + 1}/{len(runnable)}] {entry.id} (p{entry.priority}/{entry.est_weight})"
                  + (f" [cache pruned: {freed}]" if freed else ""), flush=True)
            out = run_workload_cpu(entry, state)
            summary["cpu_attempted"] += 1
            if out.status == Status.VERIFIED:
                summary["verified"] += 1
            elif out.status == Status.FAILED:
                summary["failed"] += 1
            elif out.status in (Status.BLOCKED, Status.SKIPPED_RESOURCE):
                summary["blocked"] += 1
            n_done += 1
            if n_done % report_every == 0:
                write_compatibility()
                write_progress(state)

    # ---- GPU twin sweep (secondary) ----
    if not cpu_only:
        for entry in catalog:
            if max_runtime_s and (time.time() - t0) > max_runtime_s:
                break
            rec = state["attempts"].get(entry.id, {})
            if rec.get("gpu", {}).get("status") in (Status.VERIFIED.value, Status.FAILED.value) and not retry_failed:
                continue
            if entry.twin_level == "OPENVINO_SPECIFIC":
                _record_gpu(state, entry, Status.NOT_APPLICABLE, notes=["OpenVINO-specific, no useful ROCm twin"])
                continue
            script = REPO_ROOT / "workloads" / entry.id / "rocm" / "run.py"
            if not script.exists():
                _record_gpu(state, entry, Status.NOT_TESTED, notes=["twin not implemented"])
                continue
            print(f"[marathon/gpu] {entry.id}", flush=True)
            checkpoint(state, entry.id)
            run_gpu_twin(entry, state)

    write_compatibility()
    write_progress(state)
    write_failures(state)
    save_state(state)
    return summary
