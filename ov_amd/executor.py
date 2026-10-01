"""Attempt lifecycle orchestration: resource guards, retries, remediation, evidence."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ov_amd import hardware
from ov_amd.correctness import evaluate
from ov_amd.environment import REPO_ROOT, disk_free_mb, pip_install, ram_available_mb, upstream_root, venv_python
from ov_amd.notebook_runner import detect_device_used, extract_outputs_text, run_notebook
from ov_amd.scheduler import TIER_TIMEOUTS, checkpoint, resources_ok, save_state
from ov_amd.schemas import FailureCategory, NotebookEntry, Status, transition_ok

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


_GOLDEN_PKGS = ["optimum-intel>=1.23", "transformers>=5.15", "protobuf>=4.25.8", "sentence-transformers"]

_ENV_HEALTH_CODE = (
    "import importlib.metadata as md, subprocess, sys\n"
    "problems = []\n"
    "try:\n"
    "    import transformers\n"
    "    if int(transformers.__version__.split('.')[0]) < 5:\n"
    "        problems.append('transformers-old')\n"
    "except Exception:\n"
    "    problems.append('transformers-missing')\n"
    "cli = sys.argv[1]\n"
    "r = subprocess.run([cli, '--help'], capture_output=True)\n"
    "if r.returncode != 0:\n"
    "    problems.append('optimum-cli-broken')\n"
    "try:\n"
    "    v = md.version('protobuf')\n"
    "    if int(v.split('.')[0]) < 4:\n"
    "        problems.append('protobuf-old')\n"
    "except Exception:\n"
    "    problems.append('protobuf-missing')\n"
    "print(';'.join(problems))\n"
)


def env_health_check(state: dict[str, Any]) -> bool:
    """Detect env drift caused by notebooks running %pip install; repair the
    golden set when broken. Returns True when the env was healthy on entry."""

    import subprocess

    py = str(venv_python("cpu"))
    cli = str(venv_python("cpu").parent / "optimum-cli")
    try:
        r = subprocess.run([py, "-c", _ENV_HEALTH_CODE, cli], capture_output=True, text=True, timeout=120)
        problems = [p for p in (r.stdout or "").strip().split(";") if p]
    except (OSError, subprocess.TimeoutExpired):
        problems = ["healthcheck-failed"]
    if not problems:
        return True
    print(f"[env-repair] drift detected: {problems} -> reinstalling golden set", flush=True)
    state.setdefault("env_repairs", []).append({"problems": problems, "at": _utcnow()})
    ok, _log = pip_install(_GOLDEN_PKGS, "cpu")
    if not ok:  # one bounded retry with a clean index query
        ok, _log = pip_install(["--force-reinstall", "--no-deps", "optimum-intel>=1.23"], "cpu")
    return False


# UI-only tail cells block forever headless; skipping them is the documented
# §22 policy (CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED)
DEFAULT_SKIP_RES = [r"demo\.launch|iface\.launch|app\.launch|\.launch\(\)"]


class AttemptOutcome:
    def __init__(self) -> None:
        self.status = Status.FAILED
        self.failure_category = ""
        self.evidence_dir: Path | None = None
        self.durations: list[float] = []
        self.ok_runs = 0
        self.device_used = ""
        self.notes: list[str] = []


def run_workload_cpu(entry: NotebookEntry, state: dict[str, Any], dry_run: bool = False) -> AttemptOutcome:
    """Full CPU validation attempt for one catalog entry."""

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
    env_health_check(state)
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

    cpu_cfg = cfg.get("cpu", {}) or {}
    patches = cfg.get("patches", {}) or {}
    wall = TIER_TIMEOUTS.get(entry.est_weight, TIER_TIMEOUTS["medium"])
    wall = int(cpu_cfg.get("wall_timeout_s", wall))
    repeats = _repeats_for(entry, cfg)
    # transport mirror rewrite (decision D2): direct huggingface.co URLs inside
    # notebook code stall on this network; the mirror serves identical weights.
    # '||' delimiter — the pattern itself contains ':' (https://)
    subs = list(patches.get("cell_subs", [])) + [r"https://huggingface\.co||https://hf-mirror.com"]
    remediations = 0
    network_retries = 0
    total_failures = 0
    last_info: dict[str, Any] = {}
    stop_reason = ""

    workdir = RESULTS_DIR / entry.id / "workdir-cpu"
    workdir.mkdir(parents=True, exist_ok=True)  # persistent across repeats: model downloads reused
    remediations = 0
    network_retries = 0
    total_failures = 0
    last_info: dict[str, Any] = {}
    stop_reason = ""

    while True:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ev = RESULTS_DIR / entry.id / f"{ts}-cpu"
        info, nbres = run_notebook(
            nb_path,
            ev,
            backend="cpu",
            wall_timeout_s=wall,
            per_cell_timeout_s=min(wall, 900),
            skip_res=list(patches.get("skip_cells_matching") or DEFAULT_SKIP_RES),
            stop_after_re=patches.get("stop_after_cell_matching"),
            subs=subs,
            cwd=workdir,
        )
        info.retry_count = total_failures
        out.evidence_dir = ev
        last_info = {"execution": info.to_dict(), "nbexec": nbres}
        _write_evidence_meta(ev, entry, info, nbres)
        if info.status == "OK":
            out.durations.append(info.duration_s)
            out.ok_runs += 1
            if len(out.durations) >= repeats:
                break
            continue  # repeatability run

        total_failures += 1
        cat = FailureCategory(info.failure_category or FailureCategory.UNKNOWN.value)
        stop_reason = nbres.get("error_head") or ""
        stderr = (ev / "stderr.log").read_text(errors="replace") if (ev / "stderr.log").exists() else ""

        if cat in (FailureCategory.NETWORK, FailureCategory.DOWNLOAD, FailureCategory.MODEL_ACCESS) and network_retries < 2:
            network_retries += 1
            continue
        if cat == FailureCategory.DEPENDENCY and remediations < 2:
            remediations += 1
            pkg = _missing_pkg(stderr)
            if pkg:
                # targeted install of just the missing package: a blanket
                # `-r requirements.txt` could downgrade the baseline openvino
                ok, log = pip_install([pkg], "cpu")
            else:
                req = _requirements_for(nb_path)
                if req is None:
                    break
                ok, log = _pip_file(req, "cpu")
            state.setdefault("installed_extras", []).append(
                {"workload": entry.id, "source": str(pkg or req), "ok": ok, "log_tail": log[-2000:]}
            )
            if not ok:
                break
            continue
        if total_failures >= 3:
            break
        break

    # --- status decision ---
    runs_needed = repeats
    if out.ok_runs >= runs_needed and out.ok_runs >= 1:
        outputs_text = extract_outputs_text(out.evidence_dir / "executed.ipynb") if out.evidence_dir else ""
        expect = cfg.get("validation", {}) or {}
        if not expect:
            expect = {"output_finite_numbers": False}  # default: runner-level checks only
        val = evaluate(expect, outputs_text, last_info.get("nbexec", {}))
        out.device_used = detect_device_used(outputs_text)
        if val["passed"]:
            out.status = Status.VERIFIED
        else:
            out.status = Status.FAILED
            out.failure_category = FailureCategory.CORRECTNESS_ERROR.value
            out.notes.append(json.dumps(val["checks"])[:500])
        _write_json(out.evidence_dir, "validation.json", val) if out.evidence_dir else None
        if out.status == Status.VERIFIED and runs_needed < 3:
            out.status = Status.VERIFIED_WITH_LIMITATIONS
            out.notes.append("repeatability: single successful run (resource-bounded); 3-run policy not met")
        if out.status == Status.VERIFIED and out.device_used not in ("CPU", ""):
            out.status = Status.VERIFIED_WITH_LIMITATIONS
            out.notes.append(
                f"device selection shows '{out.device_used}', not CPU — CORE path verified but device premise limited"
            )
        if out.status == Status.VERIFIED and last_info.get("nbexec", {}).get("n_skipped", 0):
            out.status = Status.VERIFIED_WITH_LIMITATIONS
            out.notes.append("CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (cells skipped via documented patch)")
    else:
        cat = FailureCategory(
            last_info.get("execution", {}).get("failure_category") or FailureCategory.UNKNOWN.value
        )
        out.status = Status.FAILED if cat not in (FailureCategory.DISK_LIMIT, FailureCategory.RAM_LIMIT) else Status.SKIPPED_RESOURCE
        out.failure_category = cat.value
        out.notes.append(f"ok_runs={out.ok_runs}/{runs_needed}: {stop_reason[:300]}")

    _record(state, entry, "cpu", out)
    checkpoint(state)
    return out


def _pip_file(req_path: Path, backend: str) -> tuple[bool, str]:
    import subprocess

    py = str(venv_python(backend))
    try:
        r = subprocess.run(
            [py, "-m", "pip", "install", "--no-input", "-r", str(req_path)],
            capture_output=True, text=True, timeout=3600,
        )
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _write_json(ev: Path | None, name: str, obj: Any) -> None:
    if ev is None:
        return
    ev.mkdir(parents=True, exist_ok=True)
    (ev / name).write_text(json.dumps(obj, indent=2, default=str))


def _write_evidence_meta(ev: Path, entry: NotebookEntry, info, nbres: dict) -> None:
    meta = load_upstream_meta()
    hw = hardware.snapshot(ev)
    _write_json(ev, "upstream.json", {
        "repository": meta.get("repository"),
        "branch": meta.get("branch"),
        "commit": meta.get("commit"),
        "path": entry.upstream_path,
        "url": entry.upstream_url,
        "notebook_sha256": _sha256(upstream_root() / entry.upstream_path),
    })
    _write_json(ev, "execution.json", info.to_dict())
    _write_json(ev, "metrics.json", {
        "wall_clock_s": info.duration_s,
        "cells_executed": nbres.get("n_cells"),
        "cells_skipped": nbres.get("n_skipped"),
        "cells_substituted": nbres.get("n_substituted"),
        "runs_ok": 0,
        "env": {"openvino": (hw["software"].get("openvino") or {}).get("version")},
    })
    (ev / "summary.md").write_text(
        f"# {entry.id} — CPU attempt\n\n"
        f"- status: {info.status}\n- duration: {info.duration_s}s\n"
        f"- failure: {info.failure_category or '-'}\n"
        f"- patches: {json.dumps(nbres.get('patch_notes', []))}\n"
    )


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
    prev = rec.get(backend, {})
    prev_status = Status(prev.get("status", Status.NOT_TESTED.value))
    if prev_status != out.status and not transition_ok(prev_status, out.status):
        # RUNNING -> terminal always allowed; NOT_TESTED -> anything terminal allowed via QUEUED/RUNNING
        pass
    rec[backend] = {
        "status": out.status.value,
        "failure_category": out.failure_category,
        "ok_runs": out.ok_runs,
        "durations_s": out.durations,
        "device_used": out.device_used,
        "evidence_dir": str(out.evidence_dir) if out.evidence_dir else None,
        "notes": out.notes,
        "updated": _utcnow(),
    }
    # mirror status into workloads/<id>/workload.yaml
    try:
        wf = WORKLOADS_DIR / entry.id / "workload.yaml"
        if wf.exists():
            cfg = yaml.safe_load(wf.read_text()) or {}
            cfg.setdefault(backend, {})["status"] = out.status.value
            cfg["last_verified"] = _utcnow() if out.status in (Status.VERIFIED, Status.VERIFIED_WITH_LIMITATIONS) else cfg.get("last_verified", "")
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
