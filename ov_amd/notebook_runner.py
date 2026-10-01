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

from ov_amd.environment import kernel_env, venv_exists, venv_python
from ov_amd.schemas import ExecutionInfo, FailureCategory

NBEXEC = Path(__file__).resolve().parent / "_nbexec.py"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def classify_failure(stderr: str, stdout: str, timeout: bool) -> FailureCategory:
    """Best-effort failure classification from captured logs."""

    text = f"{stderr}\n{stdout}"
    if timeout:
        return FailureCategory.TIMEOUT
    rules: list[tuple[str, FailureCategory]] = [
        (r"No space left on device", FailureCategory.DISK_LIMIT),
        (r"Cannot allocate memory|out of memory|MemoryError|std::bad_alloc|OOM", FailureCategory.OOM),
        (r"Killed", FailureCategory.RAM_LIMIT),
        (r"ModuleNotFoundError|ImportError|No module named", FailureCategory.DEPENDENCY),
        (r"ResolutionImpossible|conflict with the dependencies|dependency resolver", FailureCategory.PACKAGE_CONFLICT),
        (r"HfHubHTTPError|ConnectionError|SSLError|URLError|timed out|getaddrinfo failed|RemoteDisconnected",
         FailureCategory.NETWORK),
        (r"403|401|Access to model|gated repo", FailureCategory.MODEL_ACCESS),
        (r"agpl|license|License", FailureCategory.LICENSE_RESTRICTION),
        (r"CellTimeoutError", FailureCategory.TIMEOUT),
        (r"ovc|openvino\.tools|Conversion|convert model failed", FailureCategory.CONVERSION_ERROR),
        (r"openvino|CompiledModel|Core\(\)", FailureCategory.OPENVINO_ERROR),
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
    subs: list[str] | None = None,
) -> tuple[ExecutionInfo, dict]:
    """Execute one notebook. Returns (ExecutionInfo, nbexec_result_dict)."""

    if not venv_exists(backend):
        info = ExecutionInfo(
            start=_utcnow(), end=_utcnow(), exit_code=None, status="FAILED",
            failure_category=FailureCategory.DEPENDENCY.value,
        )
        info.duration_s = 0.0
        return info, {"ok": False, "error_head": f"validation venv for backend {backend} missing"}

    evidence_dir.mkdir(parents=True, exist_ok=True)
    out_nb = evidence_dir / "executed.ipynb"
    stdout_path = evidence_dir / "stdout.log"
    stderr_path = evidence_dir / "stderr.log"

    cmd = [str(venv_python(backend)), str(NBEXEC), str(notebook), str(out_nb), str(per_cell_timeout_s)]
    for r_ in skip_res or []:
        cmd += ["--skip-re", r_]
    if stop_after_re:
        cmd += ["--stop-after-re", stop_after_re]
    for s in subs or []:
        cmd += ["--sub", s]

    start = _utcnow()
    t0 = time.time()
    timed_out = False
    env = kernel_env(backend)
    env["OMP_NUM_THREADS"] = env.get("OMP_NUM_THREADS", "32")

    with open(stdout_path, "w") as so, open(stderr_path, "w") as se:
        proc = subprocess.Popen(cmd, stdout=so, stderr=se, env=env, start_new_session=True, cwd=str(evidence_dir))
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
                nbresult = json.loads(line[len("NBEXEC_RESULT="):])
            except json.JSONDecodeError:
                pass
            break

    ok = bool(nbresult.get("ok")) and ret == 0 and not timed_out
    category = classify_failure(stderr, stdout, timed_out) if not ok else None
    info = ExecutionInfo(
        start=start,
        end=_utcnow(),
        duration_s=round(duration, 2),
        exit_code=ret,
        retry_count=0,
        status="OK" if ok else "ERROR",
        failure_category=category.value if category else "",
    )
    return info, nbresult


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
    """Guess which OpenVINO device actually ran from notebook outputs."""

    for dev in ("NPU", "GPU", "CPU", "AUTO"):
        if re.search(rf"\b{dev}\b", text):
            return dev
    return ""
