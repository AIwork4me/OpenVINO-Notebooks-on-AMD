"""Attempt lifecycle orchestration: env resolution, retries, remediation, Evidence Schema v2.

v0.2 evidence layout (per attempt):

    results/<workload>/<ts>-<backend>/
    ├── aggregate.json          repeatability (successful/required, median, p95)
    ├── hardware.json
    ├── software-before.json    snapshot of the actual workload python, pre-run
    ├── software-after.json     post-run (notebooks may %pip install)
    ├── upstream.json
    ├── model.json
    ├── validation.json         contract evaluation + validation_level
    ├── metrics.json
    ├── device-proof.json       positive device-execution proof (or its absence)
    ├── summary.md
    └── run-01/
        ├── execution.json
        ├── device-proof.jsonl  raw probe events (kernel-side)
        ├── stdout.log
        ├── stderr.log
        └── executed.ipynb
    └── run-02/ ... run-03/

v0.1 evidence is historical and is never rewritten into this layout.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ov_amd import ev2, hardware
from ov_amd.correctness import evaluate
from ov_amd.env_manager import ensure_env
from ov_amd.environment import REPO_ROOT, disk_free_mb, ram_available_mb, upstream_root
from ov_amd.notebook_runner import detect_device_used, extract_outputs_text, run_notebook
from ov_amd.scheduler import TIER_TIMEOUTS, checkpoint, resources_ok, save_state
from ov_amd.schemas import FailureCategory, NotebookEntry, Status
from ov_amd.substitution import Substitution

RESULTS_DIR = REPO_ROOT / "results"
WORKLOADS_DIR = REPO_ROOT / "workloads"

# top-level module name -> pip package name
MODULE_TO_PKG = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "yaml": "pyyaml",
    "bbox": "bbox-utility",
    "matplotlib_inline": "matplotlib",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_upstream_meta() -> dict[str, Any]:
    p = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    return json.loads(p.read_text()) if p.exists() else {}


def workload_config(entry: NotebookEntry) -> dict[str, Any]:
    """workloads/<id>/workload.yaml if present (patches, validation, overrides)."""

    p = WORKLOADS_DIR / entry.id / "workload.yaml"
    if p.exists():
        try:
            return yaml.safe_load(p.read_text()) or {}
        except yaml.YAMLError:
            return {}
    return {}


def ensure_workload_dir(entry: NotebookEntry) -> Path:
    d = WORKLOADS_DIR / entry.id
    d.mkdir(parents=True, exist_ok=True)
    meta = load_upstream_meta()
    manifest = d / "workload.yaml"
    if not manifest.exists():
        manifest.write_text(
            yaml.safe_dump(
                {
                    "id": entry.id,
                    "title": entry.title,
                    "category": entry.category,
                    "upstream": {
                        "repository": "openvinotoolkit/openvino_notebooks",
                        "branch": meta.get("branch", ""),
                        "commit": meta.get("commit", ""),
                        "path": entry.upstream_path,
                        "url": entry.upstream_url,
                    },
                    "model": {"name": "", "source": "", "revision": "", "license": ""},
                    "cpu": {"runtime": "openvino", "status": Status.NOT_TESTED.value},
                    "gpu": {"runtime": "", "status": Status.NOT_TESTED.value},
                    "twin": {"level": entry.twin_level},
                    "validation": {},
                    "patches": {},
                    "last_verified": "",
                },
                sort_keys=False,
            )
        )
    (d / "rocm").mkdir(exist_ok=True)
    (d / "validation").mkdir(exist_ok=True)
    return d


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _missing_pkg(stderr: str) -> str | None:
    clean = _strip_ansi(stderr)
    m = re.search(r"ModuleNotFoundError: No module named '([\w\.]+)'", clean)
    if not m:
        m = re.search(r"ImportError: cannot import name .+ from '([\w\.]+)'", clean)
    if not m:
        return None
    module = m.group(1)
    # namespace packages whose pip name differs from the import path
    special = {
        "optimum.intel": "optimum-intel",
        "optimum.exporters": "optimum",
        "openvino.genai": "openvino-genai",
        "openvino.tokenizers": "openvino-tokenizers",
    }
    if module in special:
        return special[module]
    top = module.split(".")[0]
    return MODULE_TO_PKG.get(top, top)


def _requirements_for(nb_path: Path) -> Path | None:
    for cand in nb_path.parent.glob("requirements*.txt"):
        return cand
    return None


def _repeats_for(entry: NotebookEntry, cfg: dict[str, Any]) -> int:
    """VERIFIED requires repeatability >= 3 successful runs; expensive workloads
    get 1 run and an explicit limitation note instead."""

    override = cfg.get("repeats")
    if override:
        return int(override)
    return 3 if entry.est_weight in ("small", "medium") else 1


# UI-only tail cells block forever headless; skipping them is the documented
# §22 policy (CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED)
DEFAULT_SKIP_RES = [r"demo\.launch|iface\.launch|app\.launch|\.launch\(\)"]


def _hf_mirror_subs() -> list[Substitution]:
    """Transport rewrite (decision D2), applied ONLY when the mirror is the
    chosen transport for this network (see environment.resolve_hf_endpoint).

    When huggingface.co itself is reachable — as on the secondary validation
    runner — no source rewriting happens at all: HF_ENDPOINT handles transport
    for the HF libraries and literal URLs already resolve. Rewriting only the
    Hugging Face host (never github.com / storage.openvinotoolkit.org / other
    hosts) remains the documented fallback for the reference network."""

    from ov_amd.environment import resolve_hf_endpoint

    if str(resolve_hf_endpoint()["endpoint"]) != "https://hf-mirror.com":
        return []
    return [
        Substitution(
            pattern=r"https://huggingface\.co",
            replacement="https://hf-mirror.com",
        )
    ]


def _cell_subs(patches: dict[str, Any]) -> list[Substitution]:
    """workload.yaml patches.cell_subs entries in structured form:
    either {pattern, replacement} maps or [pattern, replacement] pairs.
    Delimiter-encoded strings are rejected (Defect A)."""

    subs: list[Substitution] = []
    for p in patches.get("cell_subs") or []:
        if isinstance(p, dict):
            subs.append(Substitution.from_dict(p))
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            subs.append(Substitution(pattern=str(p[0]), replacement=str(p[1])))
        else:
            raise ValueError(
                f"patches.cell_subs entries must be structured {{pattern, replacement}} or "
                f"[pattern, replacement]; got {p!r} — delimiter-encoded strings are not accepted"
            )
    return subs


def _pip_install_into(env_python: Path, packages: list[str], retries: int = 3) -> tuple[bool, str]:
    """Install into the workload's own isolated environment (never shared)."""

    import subprocess
    import time

    last = ""
    for attempt in range(retries):
        try:
            r = subprocess.run(
                [str(env_python), "-m", "pip", "install", "--no-input", *packages],
                capture_output=True,
                text=True,
                timeout=1800,
            )
            last = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                return True, last
        except (OSError, subprocess.TimeoutExpired) as e:
            last = str(e)
        time.sleep(10 * (attempt + 1))
    return False, last


class AttemptOutcome:
    def __init__(self) -> None:
        self.status = Status.FAILED
        self.failure_category = ""
        self.evidence_dir: Path | None = None
        self.durations: list[float] = []
        self.ok_runs = 0
        self.required_runs = 0
        self.device_used = ""
        self.notes: list[str] = []
        self.validation_level = ""
        self.device_proof = ""
        self.env_info: dict[str, Any] = {}


def _write_json(ev: Path | None, name: str, obj: dict[str, Any]) -> None:
    if ev is None:
        return
    ev2.write_json(ev / name, obj)


def run_workload_cpu(entry: NotebookEntry, state: dict[str, Any], dry_run: bool = False) -> AttemptOutcome:
    """Full CPU validation attempt for one catalog entry (Evidence Schema v2)."""

    out = AttemptOutcome()
    ok_res, why = resources_ok()
    if not ok_res:
        out.status = Status.SKIPPED_RESOURCE
        out.failure_category = (
            FailureCategory.DISK_LIMIT.value if why.startswith("disk") else FailureCategory.RAM_LIMIT.value
        )
        out.notes.append(why)
        _record(state, entry, "cpu", out)
        return out

    cfg = workload_config(entry)
    ensure_workload_dir(entry)
    root = upstream_root()
    if root is None:
        out.status = Status.BLOCKED
        out.failure_category = FailureCategory.DEPENDENCY.value
        out.notes.append("upstream clone not present")
        _record(state, entry, "cpu", out)
        return out
    nb_path = root / entry.upstream_path
    if not nb_path.exists():
        out.status = Status.BLOCKED
        out.failure_category = FailureCategory.UPSTREAM_BUG.value
        out.notes.append(f"notebook path missing in clone: {entry.upstream_path}")
        _record(state, entry, "cpu", out)
        return out

    if dry_run:
        out.status = Status.QUEUED
        return out

    # --- per-workload isolated environment (Defect B closure) ---
    try:
        env = ensure_env(entry, "cpu", cfg=cfg, nb_path=nb_path)
    except RuntimeError as e:
        out.status = Status.FAILED
        out.failure_category = FailureCategory.DEPENDENCY.value
        out.notes.append(f"env build failed: {e}"[:500])
        _record(state, entry, "cpu", out)
        checkpoint(state)
        return out
    out.env_info = env.to_dict()

    cpu_cfg = cfg.get("cpu", {}) or {}
    patches = cfg.get("patches", {}) or {}
    wall = TIER_TIMEOUTS.get(entry.est_weight, TIER_TIMEOUTS["medium"])
    wall = int(cpu_cfg.get("wall_timeout_s", wall))
    # per-runner cap (OV_AMD_WALL_CAP, seconds): throttled-network runners use
    # it to bound wall time for large/huge tiers whose model downloads cannot
    # complete; recorded transparently because evidence notes the timeout hit
    try:
        cap = int(os.environ.get("OV_AMD_WALL_CAP", "0"))
    except ValueError:
        cap = 0
    if cap > 0:
        wall = min(wall, cap)
    repeats = _repeats_for(entry, cfg)
    out.required_runs = repeats
    from ov_amd.environment import resolve_hf_endpoint

    hf_transport = resolve_hf_endpoint()
    subs = _hf_mirror_subs() + _cell_subs(patches)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = RESULTS_DIR / entry.id / f"{ts}-cpu"
    ev.mkdir(parents=True, exist_ok=True)
    out.evidence_dir = ev
    workdir = RESULTS_DIR / entry.id / "workdir-cpu"
    workdir.mkdir(parents=True, exist_ok=True)  # persistent across repeats: model downloads reused

    # --- evidence bound to the actual workload python (Defect D closure) ---
    hardware.snapshot(ev, str(env.python), names=("hardware.json", "software-before.json"))

    _upstream_meta = load_upstream_meta()
    _write_json(
        ev,
        "upstream.json",
        {
            "repository": _upstream_meta.get("repository"),
            "branch": _upstream_meta.get("branch"),
            "commit": _upstream_meta.get("commit"),
            "path": entry.upstream_path,
            "url": entry.upstream_url,
            "notebook_sha256": _sha256(nb_path),
        },
    )
    _write_json(ev, "model.json", _model_record(cfg, ev, nb_path))

    remediations = 0
    network_retries = 0
    total_failures = 0
    last_info: dict[str, Any] = {}
    stop_reason = ""
    run_idx = 0

    while True:
        run_idx += 1
        run_dir = ev / f"run-{run_idx:02d}"
        info, nbres = run_notebook(
            nb_path,
            run_dir,
            backend="cpu",
            wall_timeout_s=wall,
            per_cell_timeout_s=min(wall, 900),
            skip_res=list(patches.get("skip_cells_matching") or DEFAULT_SKIP_RES),
            stop_after_re=patches.get("stop_after_cell_matching"),
            subs=subs,
            cwd=workdir,
            python_bin=env.python,
            venv_bin=env.bin_dir,
        )
        info.retry_count = total_failures
        last_info = {"execution": info.to_dict(), "nbexec": nbres, "run_dir": str(run_dir)}
        _write_json(run_dir, "execution.json", info.to_dict())
        if info.status == "OK":
            out.durations.append(info.duration_s)
            out.ok_runs += 1
            if len(out.durations) >= repeats:
                break
            continue  # repeatability run

        total_failures += 1
        cat = FailureCategory(info.failure_category or FailureCategory.UNKNOWN.value)
        stop_reason = nbres.get("error_head") or ""
        stderr = (run_dir / "stderr.log").read_text(errors="replace") if (run_dir / "stderr.log").exists() else ""

        if (
            cat in (FailureCategory.NETWORK, FailureCategory.DOWNLOAD, FailureCategory.MODEL_ACCESS)
            and network_retries < 2
        ):
            network_retries += 1
            continue
        if cat == FailureCategory.DEPENDENCY and remediations < 2:
            remediations += 1
            pkg = _missing_pkg(stderr)
            if pkg:
                # targeted install into THIS workload's venv only
                ok, log = _pip_install_into(env.python, [pkg])
            else:
                req = _requirements_for(nb_path)
                if req is None:
                    break
                ok, log = _pip_install_into(env.python, ["-r", str(req)])
            state.setdefault("installed_extras", []).append(
                {"workload": entry.id, "source": str(pkg or req), "ok": ok, "log_tail": log[-2000:]}
            )
            if not ok:
                break
            continue
        if total_failures >= 3:
            break
        break

    # --- post-run evidence ---
    hardware.snapshot(ev, str(env.python), names=("hardware.json", "software-after.json"))

    runs_needed = repeats
    final_run = Path(last_info.get("run_dir", "")) if last_info else None
    outputs_text = extract_outputs_text(final_run / "executed.ipynb") if final_run else ""
    expect = cfg.get("validation", {}) or {}
    contract = ev2.has_contract(expect)
    if not contract:
        expect = {}
    val = evaluate(expect, outputs_text, last_info.get("nbexec", {}))
    val["level"] = (
        ev2.ValidationLevel.WORKLOAD_CORRECTNESS.value if contract else ev2.ValidationLevel.EXECUTION_ONLY.value
    )
    val["contract_present"] = contract
    out.device_used = detect_device_used(outputs_text)
    proof = ev2.summarize_device_proof(
        final_run / "device-proof.jsonl" if final_run else None,
        requested_backend="cpu",
        supporting_device_used=out.device_used,
    )
    out.device_proof = proof["state"]
    _write_json(final_run, "validation.json", val) if final_run else None
    _write_json(ev, "validation.json", {**val, "aggregate_ref": "aggregate.json"})
    _write_json(ev, "device-proof.json", proof)
    _write_json(ev, "aggregate.json", ev2.aggregate_repeatability(out.durations, runs_needed))

    # --- status decision (validation levels + positive device proof) ---
    if out.ok_runs >= 1:
        status_value, notes, _level = ev2.decide_status(
            runs_ok=out.ok_runs,
            required_runs=runs_needed,
            contract_present=contract,
            proof=ev2.proof_state(proof),
            n_cells=int(last_info.get("nbexec", {}).get("n_cells", 1) or 0),
            n_skipped=int(last_info.get("nbexec", {}).get("n_skipped", 0) or 0),
        )
        if contract and not val["passed"]:
            status_value = Status.FAILED.value
            out.failure_category = FailureCategory.CORRECTNESS_ERROR.value
            out.notes.append(json.dumps(val["checks"])[:500])
        if status_value in (Status.VERIFIED.value, Status.VERIFIED_WITH_LIMITATIONS.value):
            out.notes.extend(notes)
        out.status = Status(status_value)
        out.validation_level = val["level"]
    else:
        cat = FailureCategory(last_info.get("execution", {}).get("failure_category") or FailureCategory.UNKNOWN.value)
        out.status = (
            Status.FAILED
            if cat not in (FailureCategory.DISK_LIMIT, FailureCategory.RAM_LIMIT)
            else Status.SKIPPED_RESOURCE
        )
        out.failure_category = cat.value
        out.notes.append(f"ok_runs={out.ok_runs}/{runs_needed}: {stop_reason[:300]}")

    _write_json(
        ev,
        "metrics.json",
        {
            "runs_ok": out.ok_runs,
            "runs_required": runs_needed,
            "wall_clock_s": out.durations,
            "cells_executed": last_info.get("nbexec", {}).get("n_cells"),
            "cells_skipped": last_info.get("nbexec", {}).get("n_skipped"),
            "cells_substituted": last_info.get("nbexec", {}).get("n_substituted"),
            "aggregate": "aggregate.json",
            "env": out.env_info,
            "hf_transport": hf_transport,
        },
    )
    (ev / "summary.md").write_text(_summary_md(entry, out, last_info))

    _record(state, entry, "cpu", out)
    checkpoint(state)
    return out


def _model_record(cfg: dict[str, Any], ev: Path, nb_path: Path) -> dict[str, Any]:
    """Declared model metadata + refs detected in notebook sources (honest,
    best-effort; nothing inferred beyond a source scan)."""

    declared = cfg.get("model", {}) or {}
    detected: list[str] = []
    try:
        src = nb_path.read_text(errors="replace")
        detected = sorted(
            set(re.findall(r"(?:huggingface\.co|hf-mirror\.com|modelscope\.cn)/models?/([\w.-]+/[\w.-]+)", src))
        )[:8]
    except OSError:
        pass
    return {
        "declared": declared,
        "detected_hf_refs": detected,
        "notebook": nb_path.name,
    }


def _summary_md(entry: NotebookEntry, out: AttemptOutcome, last_info: dict[str, Any]) -> str:
    exec_info = last_info.get("execution", {})
    lines = [
        f"# {entry.id} — CPU attempt (evidence schema v2)",
        "",
        f"- status: **{out.status.value}**",
        f"- validation level: {out.validation_level or '-'}",
        f"- device proof: {out.device_proof or '-'} (supporting widget scan: '{out.device_used or '-'}')",
        f"- successful runs: {out.ok_runs}/{out.required_runs} (see aggregate.json)",
        f"- last duration: {exec_info.get('duration_s', '-')}s",
        f"- failure: {out.failure_category or '-'}",
        f"- environment: `.venvs/cpu/{out.env_info.get('env_key', '-')}` (reused={out.env_info.get('reused')})",
    ]
    for n in out.notes:
        lines.append(f"- note: {n}")
    return "\n".join(lines) + "\n"


def _sha256(p: Path | None) -> str | None:
    import hashlib

    if p is None or not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(state: dict[str, Any], entry: NotebookEntry, backend: str, out: AttemptOutcome) -> None:
    rec = state.setdefault("attempts", {}).setdefault(entry.id, {})
    # Evidence references are stored repo-relative (Defect C): state files must
    # never carry machine-local absolute paths.
    evidence_ref = None
    if out.evidence_dir is not None:
        try:
            evidence_ref = str(out.evidence_dir.relative_to(REPO_ROOT))
        except ValueError:
            evidence_ref = str(out.evidence_dir)
    rec[backend] = {
        "status": out.status.value,
        "failure_category": out.failure_category,
        "ok_runs": out.ok_runs,
        "required_runs": out.required_runs,
        "durations_s": out.durations,
        "device_used": out.device_used,
        "device_proof": out.device_proof,
        "validation_level": out.validation_level,
        "platform_id": hardware.platform_id(),
        "evidence_dir": evidence_ref,
        "env": out.env_info,
        "notes": out.notes,
        "updated": _utcnow(),
    }
    # mirror status into workloads/<id>/workload.yaml
    try:
        wf = WORKLOADS_DIR / entry.id / "workload.yaml"
        if wf.exists():
            cfg = yaml.safe_load(wf.read_text()) or {}
            cfg.setdefault(backend, {})["status"] = out.status.value
            cfg["last_verified"] = (
                _utcnow()
                if out.status in (Status.VERIFIED, Status.VERIFIED_WITH_LIMITATIONS)
                else cfg.get("last_verified", "")
            )
            wf.write_text(yaml.safe_dump(cfg, sort_keys=False))
    except (OSError, yaml.YAMLError):
        pass
    save_state(state)


def prune_cache_if_needed() -> str:
    """Resource guard: drop pip/hf caches when disk gets tight. Never touches evidence."""

    if disk_free_mb() > 40_000:
        return ""
    freed = []
    for path in (REPO_ROOT / ".cache" / "pip", Path.home() / ".cache" / "pip", Path.home() / ".cache" / "torch"):
        if path.exists():
            sz = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            shutil.rmtree(path, ignore_errors=True)
            freed.append(f"{path} ({sz // (1 << 20)}MB)")
    return "; ".join(freed)


def ram_ok() -> bool:
    return ram_available_mb() > 4000
