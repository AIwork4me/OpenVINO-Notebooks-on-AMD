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


def _is_helper_package_dir(p: Path) -> bool:
    """True for small pure-code sibling directories (helper packages like
    deepsort_utils/): only .py/.json/.yaml/.txt files, total <= 4 MB, at
    least one .py. Never copies model/asset directories."""

    try:
        entries = list(p.rglob("*"))
    except OSError:
        return False
    total = 0
    has_py = False
    for e in entries:
        if e.is_dir():
            if e.name == "__pycache__":
                continue
            continue
        if not e.is_file() or e.is_symlink():
            return False
        if e.suffix not in (".py", ".json", ".yaml", ".yml", ".txt"):
            return False
        if e.suffix == ".py":
            has_py = True
        total += e.stat().st_size
        if total > 4 * 1024 * 1024:
            return False
    return has_py


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
            if sibling.is_dir() and not sibling.is_symlink():
                # sibling PYTHON PACKAGE directories (e.g. person-tracking's
                # deepsort_utils/): notebooks import them from their own
                # folder; the file-only preseed below missed them entirely
                # (v0.3 Defect C6 — ModuleNotFoundError: deepsort_utils)
                if (
                    sibling.name not in ("__pycache__", "_cache")
                    and not dst.exists()
                    and _is_helper_package_dir(sibling)
                ):
                    shutil.copytree(sibling, dst, dirs_exist_ok=True)
                    patches.append(
                        f"preseeded sibling helper package directory {sibling.name} (kernel cwd differs from notebook dir)"
                    )
                continue
            if not sibling.is_file() or sibling.is_symlink():
                continue
            if sibling.suffix == ".py":
                text = sibling.read_text()
                patched = _guard_helper_notebook_utils_fetch(text)
                if patched is not None:
                    # refresh an unpatched copy we seeded earlier (preseed
                    # normally skips existing files; a guard-fix landed after
                    # the first seeding must still reach the workdir)
                    if not dst.exists() or (dst.read_text() == text):
                        dst.write_text(patched)
                    text = patched
                    patches.append(
                        f"guarded unconditional notebook_utils.py fetch in sibling helper {sibling.name} "
                        "(upstream helper refetches from raw.githubusercontent.com at import time; "
                        "preseeded copy satisfies it offline)"
                    )
                if not dst.exists():
                    dst.write_text(text)
                    patches.append(f"preseeded sibling helper module {sibling.name} (kernel cwd differs from notebook dir)")
            elif sibling.suffix.lower() in SIBLING_DATA_EXTS and not dst.exists():
                try:
                    if sibling.stat().st_size <= SIBLING_DATA_MAX_BYTES:
                        shutil.copy2(sibling, dst)
                        patches.append(
                            f"preseeded sibling data asset {sibling.name} (notebook-relative resource semantics)"
                        )
                except OSError:
                    pass
        # cross-notebook assets fetched from OUR OWN pinned repo via
        # raw.githubusercontent.com (e.g. vlm-chatbot/nyc.jpg referenced by
        # muse-glimmer): satisfy them from the sha-verified snapshot — pure
        # transport substitution, identical content, recorded per file
        patches.extend(_preseed_snapshot_raw_assets(cwd, nb_path, root))
    return patches


def _preseed_snapshot_raw_assets(cwd: Path, nb_path: Path, root: Path) -> list[str]:
    """Preseed files the notebook downloads from
    raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/<ref>/<path>
    when <path> exists in the pinned snapshot (the raw CDN is unreachable on
    egress-restricted runners). Foreign-repo URLs are left alone — those are
    honest network blocks, not transport substitutions."""

    import re as _re
    import shutil

    raw_re = _re.compile(
        r"raw\.githubusercontent\.com/openvinotoolkit/openvino_notebooks/[^\s\"'/]+/([^\s\"')]+)"
    )
    try:
        nb_text = nb_path.read_text(errors="ignore")
    except OSError:
        return []
    notes: list[str] = []
    seen: set[str] = set()
    for match in raw_re.finditer(nb_text):
        rel = match.group(1).split("\\")[0]
        if not rel or rel in seen:
            continue
        seen.add(rel)
        # security guard (Gate-7 finding): the captured URL path must stay a
        # real child of the snapshot root and of the notebook-adjacent tree —
        # a crafted `../` in a raw URL must never read outside the snapshot
        # or write outside the kernel cwd
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            continue
        src = root / rel
        if not src.is_file():
            continue
        # destination candidates, in preference order:
        # 1. notebook-folder-relative (the fetch destination when the URL
        #    points inside the notebook's own folder, e.g. model/u2net.py)
        # 2. repo-relative mirror of the URL path
        # 3. flat file name (legacy behavior)
        # v0.3 defect fix: the flat-only copy left subdir fetches attempting
        # the unreachable raw CDN (vision-background-removal model/u2net.py)
        try:
            nb_rel = nb_path.parent.relative_to(root)
        except ValueError:
            nb_rel = None
        cands: list[Path] = []
        if nb_rel and rel.startswith(nb_rel.as_posix() + "/"):
            cands.append(cwd / Path(rel).relative_to(nb_rel))
        cands += [cwd / Path(rel), cwd / Path(rel).name]
        for dst in cands:
            if dst.exists():
                continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                notes.append(
                    f"preseeded snapshot asset {rel} -> {dst.relative_to(cwd)} (notebook fetches it from "
                    "raw.githubusercontent.com; identical sha-verified snapshot content, transport substitution)"
                )
            except OSError:
                continue
    return notes


def _guard_helper_notebook_utils_fetch(text: str) -> str | None:
    """Wrap a sibling helper's unconditional notebook_utils.py refetch in an
    exists() guard (documented minimal patch, recorded in evidence).

    Upstream helpers (ct-segmentation-quantize's custom_segmentation.py,
    async_pipeline.py) fetch notebook_utils.py from raw.githubusercontent.com
    at import time with no existence check. The preseed already provides the
    pinned, sha-verified notebook_utils.py in the kernel cwd; on
    egress-restricted runners the unconditional fetch kills the import. The
    guard keeps upstream behavior when the file is genuinely absent.
    """

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    changed = False
    start_mark = "r = requests.get("
    end_mark = 'open("notebook_utils.py", "w").write(r.text)'
    while i < len(lines):
        if lines[i].strip() == start_mark:
            # confirm this fetch targets notebook_utils.py within the block
            j = i + 1
            block_end = None
            targets_utils = False
            while j < len(lines) and j <= i + 12:
                if "notebook_utils.py" in lines[j] and "raw.githubusercontent" not in lines[j]:
                    targets_utils = True
                if lines[j].rstrip("\n").rstrip() == ")":
                    block_end = j
                    if targets_utils:
                        break
                j += 1
            if block_end is not None and targets_utils:
                k = block_end + 1
                while k < len(lines) and not lines[k].startswith(end_mark):
                    k += 1
                if k < len(lines):
                    indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
                    out.append(f'{indent}if not Path("notebook_utils.py").exists():\n')
                    for m in range(i, k + 1):
                        out.append("    " + lines[m])
                    i = k + 1
                    changed = True
                    continue
        out.append(lines[i])
        i += 1
    if not changed:
        return None
    new_text = "".join(out)
    if "from pathlib import Path" not in new_text and "import pathlib" not in new_text:
        new_text = new_text.replace("import requests\n", "import requests\nfrom pathlib import Path\n", 1)
    return new_text


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
