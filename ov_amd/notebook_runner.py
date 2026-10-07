"""Wall-clock bounded notebook execution with evidence capture.

The heavy lifting happens in ov_amd/_nbexec.py inside the validation venv.
This module manages process groups (kill on timeout), evidence directories
and the execution record.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ov_amd.environment import ensure_ipv4_first, kernel_env, upstream_root, venv_exists, venv_python
from ov_amd.schemas import ExecutionInfo, FailureCategory
from ov_amd.substitution import Substitution, subs_to_json

NBEXEC = Path(__file__).resolve().parent / "_nbexec.py"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def classify_failure(stderr: str, stdout: str, timeout: bool) -> FailureCategory:
    """Best-effort failure classification from captured logs."""

    text = _ANSI_RE.sub("", f"{stderr}\n{stdout}")
    if timeout:
        return FailureCategory.TIMEOUT
    # a per-cell timeout must outrank every log-grep rule: pip banners,
    # "timed out" download lines and resolver warnings coexist with the real
    # CellTimeoutError at the bottom of the log and steal the classification
    if re.search(r"CellTimeoutError", text):
        return FailureCategory.TIMEOUT
    rules: list[tuple[str, FailureCategory]] = [
        (r"No space left on device", FailureCategory.DISK_LIMIT),
        (r"Cannot allocate memory|out of memory|MemoryError|std::bad_alloc|OOM", FailureCategory.OOM),
        (r"Killed", FailureCategory.RAM_LIMIT),
        # missing data resources surfaced as runtime lookups (NLTK corpora)
        (r"Resource \w+ not found.*NLTK Downloader|LookupError:.*Resource", FailureCategory.DEPENDENCY),
        # library API drift: notebook pins an older/newer lib than its code
        (r"cannot import name 'runtime_version' from 'google.protobuf'", FailureCategory.DEPENDENCY),
        (r"'Column' object has no attribute 'dtype'", FailureCategory.DEPENDENCY),
        # shell form "git clone URL" and subprocess-list form "['git', 'clone', URL]"
        # (real cases: Wav2Lip / sam2 direct clones on the throttled network)
        (
            r"git(?:\s+clone|',\s*'clone)|RPC failed|Operation too slow|Could not resolve host",
            FailureCategory.NETWORK,
        ),
        (r"ModuleNotFoundError|ImportError|No module named", FailureCategory.DEPENDENCY),
        # notebooks that %pip install and import in the same session; a rerun
        # after the install completes succeeds (remediation path handles it)
        (r"may need to restart|restart your (kernel|runtime)", FailureCategory.DEPENDENCY),
        # notebook shells out to a console script (optimum-cli, ovc, ...) that a
        # failed %pip git-install was supposed to provide; %pip failures do not
        # raise in-kernel, so the missing executable surfaces cells later. The
        # child_exception_type context separates subprocess spawns from
        # data-file opens (builtins.open/PIL), which are not dependency issues.
        (
            r"child_exception_type\([^)]*\)\s*\n(?:[^\n]*\n){0,4}?FileNotFoundError: \[Errno 2\] No such file or directory: '",
            FailureCategory.DEPENDENCY,
        ),
        # gated-repo denials must outrank PACKAGE_CONFLICT: pip's benign
        # "dependency resolver" warning banner coexists with the real 401 error
        (r"GatedRepoError|Access to model|gated repo", FailureCategory.MODEL_ACCESS),
        # pip's benign "dependency resolver does not currently take into
        # account" banner appears in most %pip outputs and must never classify
        # a failure by itself (it stole real network errors from four llm-*
        # runs); genuine conflicts always carry ResolutionImpossible
        (r"ResolutionImpossible|conflict with the dependencies", FailureCategory.PACKAGE_CONFLICT),
        (
            r"HfHubHTTPError|ConnectionError|SSLError|URLError|timed out|getaddrinfo failed|RemoteDisconnected",
            FailureCategory.NETWORK,
        ),
        (r"403|401|Access to model|gated repo", FailureCategory.MODEL_ACCESS),
        (r"agpl|license|License", FailureCategory.LICENSE_RESTRICTION),
        (r"ovc|openvino\.tools|Conversion|convert model failed", FailureCategory.CONVERSION_ERROR),
        (r"openvino\.(runtime|genai)|CompiledModel|ov\.Core", FailureCategory.OPENVINO_ERROR),
    ]
    for pat, cat in rules:
        if re.search(pat, text):
            return cat
    return FailureCategory.UNKNOWN


def run_notebook(
    notebook: Path,
    evidence_dir: Path,
    backend: str = "cpu",
    wall_timeout_s: int = 1800,
    per_cell_timeout_s: int = 900,
    skip_res: list[str] | None = None,
    stop_after_re: str | None = None,
    subs: list[Substitution] | None = None,
    cwd: Path | None = None,
    python_bin: Path | None = None,
    venv_bin: Path | None = None,
) -> tuple[ExecutionInfo, dict]:
    """Execute one notebook. Returns (ExecutionInfo, nbexec_result_dict).

    `cwd` is the kernel working directory; pointing it at a per-workload
    persistent dir lets repeats/retries reuse downloaded artifacts.
    `python_bin`/`venv_bin` select an isolated per-workload environment
    (ov_amd.env_manager); when omitted the legacy shared backend venv runs.
    The device probe (OV_AMD_DEVICE_PROBE_FILE) is bound to this run's
    evidence directory.
    """

    if not venv_exists(backend) and python_bin is None:
        info = ExecutionInfo(
            start=_utcnow(),
            end=_utcnow(),
            exit_code=None,
            status="FAILED",
            failure_category=FailureCategory.DEPENDENCY.value,
        )
        info.duration_s = 0.0
        return info, {"ok": False, "error_head": f"validation venv for backend {backend} missing"}
    py = python_bin if python_bin is not None else venv_python(backend)
    if not Path(py).exists():
        info = ExecutionInfo(
            start=_utcnow(),
            end=_utcnow(),
            exit_code=None,
            status="FAILED",
            failure_category=FailureCategory.DEPENDENCY.value,
        )
        info.duration_s = 0.0
        return info, {"ok": False, "error_head": f"workload python missing: {py}"}
    if venv_bin is not None:
        ensure_ipv4_first(backend, venv=venv_bin.parent)
    else:
        ensure_ipv4_first(backend)

    kernel_cwd = cwd if cwd is not None else evidence_dir
    kernel_cwd.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    seed_patches = _preseed_helpers(kernel_cwd, notebook)
    for note in seed_patches:
        print(f"AMD-PATCH: {note}")
    out_nb = evidence_dir / "executed.ipynb"
    stdout_path = evidence_dir / "stdout.log"
    stderr_path = evidence_dir / "stderr.log"

    cmd = [str(py), str(NBEXEC), str(notebook), str(out_nb), str(per_cell_timeout_s)]
    for r_ in skip_res or []:
        cmd += ["--skip-re", r_]
    if stop_after_re:
        cmd += ["--stop-after-re", stop_after_re]
    if subs:
        cmd += ["--subs-json", subs_to_json(subs)]

    start = _utcnow()
    t0 = time.time()
    timed_out = False
    env = kernel_env(backend, venv_bin=venv_bin)
    env["OMP_NUM_THREADS"] = env.get("OMP_NUM_THREADS", "32")
    env["OV_AMD_DEVICE_PROBE_FILE"] = str(evidence_dir / "device-proof.jsonl")

    with open(stdout_path, "w") as so, open(stderr_path, "w") as se:
        proc = subprocess.Popen(cmd, stdout=so, stderr=se, env=env, start_new_session=True, cwd=str(kernel_cwd))
        try:
            ret = proc.wait(timeout=wall_timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(proc.pid)
            try:
                ret = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                ret = -9
        finally:
            so.flush()
            se.flush()

    duration = time.time() - t0
    stdout = stdout_path.read_text(errors="replace")
    stderr = stderr_path.read_text(errors="replace")

    nbresult: dict = {}
    for line in reversed(stdout.splitlines()):
        if line.startswith("NBEXEC_RESULT="):
            try:
                nbresult = json.loads(line[len("NBEXEC_RESULT=") :])
            except json.JSONDecodeError:
                pass
            break
    nbresult.setdefault("patch_notes", []).extend(seed_patches)

    ok = bool(nbresult.get("ok")) and ret == 0 and not timed_out
    category = classify_failure(stderr, stdout, timed_out) if not ok else None
    stage = ""
    if timed_out:
        from ov_amd.outcomes import classify_timeout_stage

        stage = classify_timeout_stage(stdout, stderr)
    info = ExecutionInfo(
        start=start,
        end=_utcnow(),
        duration_s=round(duration, 2),
        exit_code=ret,
        retry_count=0,
        status="OK" if ok else "ERROR",
        failure_category=category.value if category else "",
        stage=stage,
    )
    return info, nbresult


#: sibling data assets notebooks reference relative to their own directory
#: (nyc.jpg, test.png, config.json ...). Size-capped; never copies code or
#: huge binaries — the snapshot filter already kept only small assets.
SIBLING_DATA_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".json", ".csv", ".yaml", ".yml", ".xml", ".txt", ".md",
    ".mp3", ".wav", ".mp4", ".pts", ".bin", ".npy",
}
SIBLING_DATA_MAX_BYTES = 64 * 1024 * 1024  # per file


def _preseed_helpers(cwd: Path, nb_path: Path | None = None) -> list[str]:
    """Copy helper modules and data assets into the execution dir, with
    documented patches.

    1. utils pre-seed: nearly every notebook starts with `if not Path("notebook_utils.py")
       .exists(): requests.get(raw.githubusercontent...)`. raw CDN stalls on this
       network, so the existence check is satisfied from the pinned local
       snapshot — no network, identical file (sha-verified at fetch time).
    2. sibling pre-seed: notebooks importing helper modules or opening data
       files that live next to them upstream (e.g. ov_catvton_helper.py,
       nyc.jpg, test.png) get those copied into cwd, because the kernel runs
       with its own working directory (notebook-relative resource semantics).
    3. device pin: `device_widget(default="AUTO")` resolves to whatever AUTO
       picks (on this machine: an enumerated GPU), which would silently break
       the "validated on AMD Ryzen CPU" premise. The preseeded copy pins the
       *default* to CPU; notebooks passing an explicit device are unaffected.
    Returns the patch notes for the evidence record.
    """

    import shutil

    root = upstream_root()
    if root is None:
        return []
    patches: list[str] = []

    def _copy_patched(src: Path, dst: Path) -> None:
        text = src.read_text()
        if src.name == "notebook_utils.py" and 'def device_widget(default="AUTO"' in text:
            text = text.replace('def device_widget(default="AUTO"', 'def device_widget(default="CPU"')
            patches.append(
                "notebook_utils.device_widget default pinned AUTO->CPU "
                "(CPU validation premise; explicit device args unaffected)"
            )
        dst.write_text(text)

    utils = root / "utils"
    if utils.is_dir():
        for py in utils.glob("*.py"):
            dst = cwd / py.name
            if not dst.exists():
                _copy_patched(py, dst)
        # notebooks in notebooks/<folder>/ reach helpers as ../../utils/<mod>.py
        # (e.g. llm-chatbot's llm_config.py copy-or-update cell). The kernel
        # cwd is the workdir, not the notebook dir, so that relative layout
        # must exist too — otherwise the notebook's "update" branch falls
        # back to raw.githubusercontent.com and dies on egress-restricted
        # runners (v0.2.2 llm-chatbot SSLError). Bounded: only when ../../
        # resolves inside RESULTS_DIR (no writes outside the results tree).
        try:
            shared_utils = (cwd / ".." / ".." / "utils").resolve()
            results_root = (Path(__file__).resolve().parent.parent / "results").resolve()
            if str(shared_utils).startswith(str(results_root) + os.sep):
                shared_utils.mkdir(parents=True, exist_ok=True)
                for py in utils.glob("*.py"):
                    dst = shared_utils / py.name
                    if not dst.exists():
                        _copy_patched(py, dst)
                patches.append(
                    "preseeded ../../utils helper layout (notebooks resolve helpers relative to their folder; kernel cwd is the workdir)"
                )
        except OSError:
            pass

    if nb_path is not None and nb_path.parent != root:
        for sibling in sorted(nb_path.parent.iterdir()):
            dst = cwd / sibling.name
            if dst.exists() or not sibling.is_file() or sibling.is_symlink():
                continue
            if sibling.suffix == ".py":
                shutil.copy2(sibling, dst)
                patches.append(f"preseeded sibling helper module {sibling.name} (kernel cwd differs from notebook dir)")
            elif sibling.suffix.lower() in SIBLING_DATA_EXTS:
                try:
                    if sibling.stat().st_size <= SIBLING_DATA_MAX_BYTES:
                        shutil.copy2(sibling, dst)
                        patches.append(
                            f"preseeded sibling data asset {sibling.name} (notebook-relative resource semantics)"
                        )
                except OSError:
                    pass
    return patches


def _kill_process_group(pid: int) -> None:
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def extract_outputs_text(executed_nb: Path | None) -> str:
    """Concatenate text outputs of an executed notebook (for correctness checks)."""

    if not executed_nb or not executed_nb.exists():
        return ""
    try:
        nb = json.loads(executed_nb.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        for out in cell.get("outputs", []):
            if "text" in out:
                chunks.append("".join(out["text"]) if isinstance(out["text"], list) else str(out["text"]))
            data = out.get("data", {})
            if "text/plain" in data:
                t = data["text/plain"]
                chunks.append("".join(t) if isinstance(t, list) else str(t))
    return "\n".join(chunks)


def detect_device_used(text: str) -> str:
    """Guess which OpenVINO device actually ran from notebook outputs.

    Widget cells render `Dropdown(value='X', ...)` — the selection actually
    used. Prefer the last such explicit value; fall back to a plain word scan.
    AUTO is reported as AUTO (it is NOT proof of CPU execution).
    """

    import re as _re

    values = _re.findall(r"value='(AUTO|CPU|GPU|NPU)'", text)
    if values:
        return values[-1]
    for dev in ("NPU", "GPU", "CPU"):
        if _re.search(rf"\b{dev}\b", text):
            return dev
    return ""
