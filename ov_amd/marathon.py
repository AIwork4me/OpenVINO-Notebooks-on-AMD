"""Unattended marathon driver: CPU sweep first, ROCm twins second, checkpointed."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import Any

from ov_amd.environment import REPO_ROOT, kernel_env, venv_exists, venv_python
from ov_amd.executor import load_upstream_meta, prune_cache_if_needed, run_workload_cpu
from ov_amd.notebook_runner import classify_failure
from ov_amd.reporting import write_compatibility, write_failures, write_progress
from ov_amd.scheduler import (
    STATE_PATH,
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


def _record_gpu(
    state: dict[str, Any],
    entry,
    status: Status,
    category: str = "",
    notes: list[str] | None = None,
    evidence: str | None = None,
    proof: str = "",
    level: str = "",
) -> None:
    from ov_amd import hardware as _hw
    from ov_amd.environment import REPO_ROOT as _ROOT

    rec = state.setdefault("attempts", {}).setdefault(entry.id, {})
    evidence_ref = None
    if evidence:
        # repo-relative public reference (Defect C) — never machine-local paths
        try:
            evidence_ref = str(_Path(evidence).relative_to(_ROOT))
        except ValueError:
            evidence_ref = evidence
    rec["gpu"] = {
        "status": status.value,
        "failure_category": category,
        "notes": notes or [],
        "evidence_dir": evidence_ref,
        "device_proof": proof,
        "validation_level": level,
        "platform_id": _hw.platform_id(),
        "updated": _utcnow(),
    }
    save_state(state)


def run_gpu_twin(entry, state: dict[str, Any]) -> None:
    """Run workloads/<id>/rocm/run.py with the ROCm venv; Evidence Schema v2."""

    script = REPO_ROOT / "workloads" / entry.id / "rocm" / "run.py"
    if not script.exists():
        _record_gpu(state, entry, Status.NOT_TESTED, notes=["no ROCm twin implementation yet"])
        return
    if not venv_exists("gpu"):
        _record_gpu(
            state,
            entry,
            Status.BLOCKED,
            FailureCategory.ROCM_UNAVAILABLE.value,
            notes=["ROCm torch venv not provisioned"],
        )
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = REPO_ROOT / "results" / entry.id / f"{ts}-gpu"
    ev.mkdir(parents=True, exist_ok=True)
    wall = GPU_WALL_TIMEOUT.get(entry.est_weight, 1800)
    import yaml

    wf = REPO_ROOT / "workloads" / entry.id / "workload.yaml"
    if wf.exists():
        try:
            cfg = yaml.safe_load(wf.read_text()) or {}
            wall = int((cfg.get("gpu") or {}).get("wall_timeout_s", wall))
        except (OSError, yaml.YAMLError, ValueError):
            pass
    cmd = [str(venv_python("gpu")), str(script), "--evidence-dir", str(ev)]
    t0 = time.time()
    start_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    timed_out = False
    with open(ev / "stdout.log", "w") as so, open(ev / "stderr.log", "w") as se:
        proc = subprocess.Popen(cmd, stdout=so, stderr=se, env=kernel_env("gpu"), start_new_session=True, cwd=str(ev))
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
                twin_result = json.loads(line[len("TWIN_RESULT=") :])
            except json.JSONDecodeError:
                pass
            break

    # structured v2 GPU evidence: hardware/software snapshots from the actual
    # ROCm python, upstream/model records, execution + device proof
    from ov_amd import ev2 as _ev2
    from ov_amd import hardware as _hw
    from ov_amd.executor import load_upstream_meta as _meta

    meta = _meta()
    _hw.snapshot(ev, str(venv_python("gpu")))
    _ev2.write_json(
        ev / "upstream.json",
        {
            "repository": meta.get("repository"),
            "branch": meta.get("branch"),
            "commit": meta.get("commit"),
            "path": entry.upstream_path,
            # url binds to the pin actually in force, not the catalog-time one
            "url": f"https://github.com/{meta.get('repository')}/blob/{meta.get('commit')}/{entry.upstream_path}",
        },
    )
    _ev2.write_json(
        ev / "model.json", {"declared": (yaml.safe_load(wf.read_text()) or {}).get("model", {}) if wf.exists() else {}}
    )
    _ev2.write_json(
        ev / "execution.json",
        {
            "start": start_ts,
            "end": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duration_s": round(duration, 2),
            "exit_code": ret,
            "retry_count": 0,
            "status": "OK" if (twin_result.get("ok") and twin_result.get("hip")) else "ERROR",
            "failure_category": "" if twin_result.get("ok") else "CORRECTNESS_ERROR",
        },
    )
    # twin runs carry latency_s (vision) or total_s (generation) — normalize
    run_latencies = [
        float(r[k])
        for r in (twin_result.get("metrics", {}).get("runs") or [])
        if isinstance(r, dict)
        for k in ("latency_s", "total_s")
        if isinstance(r.get(k), (int, float))
    ]
    _ev2.write_json(
        ev / "device-proof.json",
        {
            "state": "PROVEN_GPU" if (twin_result.get("ok") and twin_result.get("hip")) else "UNKNOWN",
            "requested_backend": "gpu",
            "hip": twin_result.get("hip"),
            "device": twin_result.get("device"),
            "gcn_arch": twin_result.get("gcn_arch"),
        },
    )
    _ev2.write_json(
        ev / "aggregate.json",
        _ev2.aggregate_repeatability(run_latencies, 3),
    )
    # validation.json: the twin's ok flag embodies its workload-correctness
    # checks (>=1 detection / deterministic generation / finite audio ...);
    # record them explicitly for the v2 contract
    twin_ok = bool(twin_result.get("ok") and twin_result.get("hip"))
    _ev2.write_json(
        ev / "validation.json",
        {
            "passed": twin_ok,
            "level": _ev2.ValidationLevel.WORKLOAD_CORRECTNESS.value if twin_ok else _ev2.ValidationLevel.EXECUTION_ONLY.value,
            "contract_present": True,
            "contract": "twin self-check (workload-specific checks in workloads/"
            f"{entry.id}/rocm/run.py; ok flag is their conjunction)",
            "checks": [
                {"name": "twin_self_check", "passed": bool(twin_result.get("ok"))},
                {"name": "hip_available", "passed": bool(twin_result.get("hip"))},
                {"name": "amd_device_visible", "passed": bool(twin_result.get("device"))},
            ],
            "runs_ok": len(run_latencies),
            "aggregate_ref": "aggregate.json",
        },
    )
    _ev2.write_json(
        ev / "metrics.json",
        {
            "twin_result": twin_result,
            "duration_s": round(duration, 2),
            "exit_code": ret,
        },
    )
    (ev / "summary.md").write_text(
        f"# {entry.id} — ROCm twin (evidence schema v2)\n\n"
        f"- hip: {twin_result.get('hip')}\n- device: {twin_result.get('device')}\n"
        f"- gcn_arch: {twin_result.get('gcn_arch')}\n- duration: {round(duration, 2)}s\n"
    )
    runs_ok = len(run_latencies)
    if twin_result.get("ok") and twin_result.get("hip"):
        # the twin's own ok embodies its workload correctness checks (e.g.
        # >=1 detection with valid bounded confidences), so a green twin is
        # L3 WORKLOAD_CORRECTNESS with PROVEN_GPU device proof. The same
        # repeatability gate as the CPU path applies (gate finding, dual
        # review): ok+hip with fewer than 3 measured runs degrades honestly
        # instead of rendering full green.
        if runs_ok >= _ev2.REPEATABILITY_MIN_RUNS and _ev2.aggregate_repeatability(run_latencies, 3)[
            "repeatability_passed"
        ]:
            _record_gpu(
                state,
                entry,
                Status.VERIFIED,
                evidence=str(ev),
                proof="PROVEN_GPU",
                level="WORKLOAD_CORRECTNESS",
            )
        else:
            _record_gpu(
                state,
                entry,
                Status.VERIFIED_WITH_LIMITATIONS,
                notes=[f"repeatability_not_established: {runs_ok} measured run(s) < 3"],
                evidence=str(ev),
                proof="PROVEN_GPU",
                level="WORKLOAD_CORRECTNESS",
            )
    elif twin_result:
        # script ran to completion and self-reported failure of its own checks;
        # log-grep classification would misread earlier fallback logs (e.g. a
        # recovered hub 401) as the failure cause
        _record_gpu(
            state,
            entry,
            Status.FAILED,
            FailureCategory.CORRECTNESS_ERROR.value,
            notes=[f"twin self-check failed; metrics={json.dumps(twin_result.get('metrics', {}))[:400]}"],
            evidence=str(ev),
        )
    else:
        cat = classify_failure(stderr, stdout, timed_out)
        notes = [
            f"exit={ret} duration={duration:.0f}s",
            stderr.strip().splitlines()[-1][:300] if stderr.strip() else "",
        ]
        _record_gpu(state, entry, Status.FAILED, cat.value, notes=notes, evidence=str(ev))


def run_marathon(
    resume: bool = True,
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
    if not resume:
        # explicit fresh start: archive the old checkpoint, begin from zero
        archive = STATE_PATH.with_name(f"marathon-state-{int(time.time())}.json.bak")
        if STATE_PATH.exists():
            archive.write_text(STATE_PATH.read_text())
        state = {"started": _utcnow(), "upstream": load_upstream_meta() or {}, "attempts": {}, "installed_extras": []}
        save_state(state)
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
            print(
                f"[marathon/cpu {i + 1}/{len(runnable)}] {entry.id} (p{entry.priority}/{entry.est_weight})"
                + (f" [cache pruned: {freed}]" if freed else ""),
                flush=True,
            )
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
