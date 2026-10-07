"""Execution environment handling: venv discovery, env vars, pip installs.

Network resilience: all installs go through bounded retries with backoff.
HF_ENDPOINT defaults to a reachable mirror because huggingface.co is not
reachable from this network (recorded in docs/engineering-decisions.md).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CPU_VENV = REPO_ROOT / ".venv-cpu"
GPU_VENV = REPO_ROOT / ".venv-gpu"

# Deterministic, resumable download env for notebook kernels.
BASE_KERNEL_ENV = {
    "HF_HUB_DOWNLOAD_TIMEOUT": "60",
    "HF_HUB_DISABLE_XET": "1",  # xet CAS endpoint is unreachable on reference network
    "GRADIO_ANALYTICS_ENABLED": "False",
    "DO_NOT_TRACK": "1",
    "NO_COLOR": "1",
    "TERM": "dumb",
    "PYTHONUNBUFFERED": "1",
    "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "32"),
    # OpenVINO CPU behaviour on AMD: make device selection explicit/inspectable.
    "OPENVINO_LOG_LEVEL": "3",
}

_HF_PROBE_FILE = "https://huggingface.co/bert-base-uncased/resolve/main/config.json"
_HF_ENDPOINT_CACHE: dict[str, object] = {}

_GIT_TRANSPORT_CACHE: dict[str, object] = {}


def resolve_git_transport() -> dict[str, object]:
    """Decide whether `git+https://github.com/...` pip installs work directly
    on this runner, or must be rewritten to codeload tarball URLs.

    Some validation runners sit behind egress proxies that block git protocol
    CONNECTs to github.com (or a site git-wrapper forces them through an
    unreachable gh-proxy), while plain HTTPS to codeload.github.com works.
    Rewriting git+https to the codeload tarball of the same repo/ref is a
    pure transport substitution (same content at install time) and is recorded
    in evidence metadata exactly like the HF endpoint choice.

    Priority: OV_AMD_GIT_TRANSPORT=direct|codeload override, else a live
    `git ls-remote` probe against a tiny public repository.
    """

    if _GIT_TRANSPORT_CACHE:
        return dict(_GIT_TRANSPORT_CACHE)  # type: ignore[arg-type]
    import subprocess as _sp

    mode = ""
    source = ""
    probe = ""
    override = os.environ.get("OV_AMD_GIT_TRANSPORT", "")
    if override in ("direct", "codeload"):
        mode = override
        source = "env-override (OV_AMD_GIT_TRANSPORT)"
        probe = "skipped (override)"
    else:
        # probe with what pip actually does: a shallow clone through the
        # runner's git (including any site git-wrapper that forces proxies)
        import tempfile

        try:
            with tempfile.TemporaryDirectory() as td:
                r = _sp.run(
                    ["git", "clone", "--quiet", "--depth", "1",
                     "https://github.com/octocat/Hello-World.git", td + "/probe"],
                    capture_output=True, text=True, timeout=60,
                )
                direct_ok = r.returncode == 0
                probe = f"clone exit {r.returncode}: {(r.stderr or '').strip().splitlines()[-1][:120] if r.stderr else 'ok'}"
        except (OSError, _sp.TimeoutExpired) as e:
            direct_ok = False
            probe = f"clone failed ({type(e).__name__})"
        mode = "direct" if direct_ok else "codeload"
        source = "probe"
    result = {"mode": mode, "source": source, "probe": probe}
    _GIT_TRANSPORT_CACHE.update(result)
    return result


def resolve_hf_endpoint() -> dict[str, object]:
    """Pick the Hugging Face transport endpoint for THIS network and record why.

    History: decision D2 pinned HF_ENDPOINT=https://hf-mirror.com because the
    reference network could not reach huggingface.co at all. Validation runners
    have different egress policies (the secondary runner reaches
    huggingface.co directly while hf-mirror.com rate-limits it with 429), so
    the endpoint is probed per campaign instead of hardcoded.

    Priority:
      1. OV_AMD_HF_ENDPOINT env override (explicit operator choice)
      2. probe huggingface.co then hf-mirror.com with a small real file;
         prefer the first endpoint that answers 200
      3. ambient HF_ENDPOINT, if set, as a last-resort recorded hint

    The ambient HF_ENDPOINT is deliberately NOT authoritative: hosting
    environments pre-set it for their own reasons (on the secondary runner it
    pins a mirror that rate-limits with 429), so trusting it blindly would
    break the campaign. The probe result is cached in-process and recorded in
    evidence metadata (metrics.json env section) — transport choice is part of
    the auditable record, never a silent default.
    """

    if _HF_ENDPOINT_CACHE:
        return dict(_HF_ENDPOINT_CACHE)  # type: ignore[arg-type]
    import urllib.request

    probes: dict[str, str] = {}
    chosen = ""
    source = ""
    override = os.environ.get("OV_AMD_HF_ENDPOINT")
    if override:
        chosen = override.rstrip("/")
        source = "env-override (OV_AMD_HF_ENDPOINT)"
        probes = {"override": chosen}
    else:
        for endpoint in ("https://huggingface.co", "https://hf-mirror.com"):
            try:
                req = urllib.request.Request(_HF_PROBE_FILE.replace("https://huggingface.co", endpoint, 1),
                                             method="GET")
                with urllib.request.urlopen(req, timeout=12) as r:  # noqa: S310 - fixed https URL
                    probes[endpoint] = f"HTTP {r.status}"
                    if r.status == 200 and not chosen:
                        chosen = endpoint
                        source = "probe"
            except OSError as e:
                probes[endpoint] = f"unreachable ({type(e).__name__})"
        ambient = os.environ.get("HF_ENDPOINT", "").rstrip("/")
        if ambient and ambient not in probes:
            probes["ambient HF_ENDPOINT (not followed)"] = ambient
        if not chosen:
            if ambient:
                chosen = ambient
                source = "ambient HF_ENDPOINT fallback (all probes failed)"
            else:
                # nothing reachable and no hint: keep the reference-network
                # default so behaviour matches D2; failures classify as
                # NETWORK honestly
                chosen = "https://hf-mirror.com"
                source = "fallback-all-probes-failed"
    result = {"endpoint": chosen, "source": source, "probes": probes}
    _HF_ENDPOINT_CACHE.update(result)
    return result

# GPU kernels additionally get the ROCm userspace on PATH.
GPU_KERNEL_ENV_EXTRA = {"PYTORCH_TUNABLEOP_ENABLED": "0", "TORCH_BLAS_PREFER_HIPBLASLT": "1"}


def venv_python(backend: str = "cpu") -> Path:
    v = CPU_VENV if backend == "cpu" else GPU_VENV
    return v / "bin" / "python"


def ensure_ipv4_first(backend: str = "cpu", venv: Path | None = None) -> None:
    """Install/refresh the network-safety hook in a venv.

    A plain sitecustomize.py gets shadowed by /usr/lib/python3.12/sitecustomize.py
    (stdlib dir precedes site-packages on sys.path), so the hook is wired via a
    .pth file, which site.py executes unconditionally at startup. The module
    file is refreshed from source on every call so hook updates propagate.
    Pass `venv` to target a per-workload environment; default is the legacy
    shared backend venv.
    """

    v = venv if venv is not None else (CPU_VENV if backend == "cpu" else GPU_VENV)
    if not v.exists():
        return
    src = Path(__file__).resolve().parent / "ipv4_first.py"
    site = next((v / "lib").glob("python*/site-packages"), None)
    if site is None:
        return
    (site / "ov_amd_ipv4_first.py").write_text(src.read_text())
    pth = site / "ov_amd_net_fix.pth"
    if not pth.exists():
        pth.write_text("import ov_amd_ipv4_first\n")


def venv_exists(backend: str = "cpu") -> bool:
    return venv_python(backend).exists()


def kernel_env(backend: str = "cpu", venv_bin: Path | None = None, python_bin: Path | None = None) -> dict[str, str]:
    """Kernel environment for one execution.

    `venv_bin`/`python_bin` point at a per-workload isolated environment
    (ov_amd.env_manager); when omitted, the legacy shared venv for the backend
    is used. OV_AMD_DEVICE_PROBE_FILE is intentionally NOT set here — the
    executor binds it per run to the run's evidence directory.
    """

    env = dict(os.environ)
    env.update(BASE_KERNEL_ENV)
    # Hugging Face transport for this network, probed and recorded per campaign
    # (see resolve_hf_endpoint); HF libraries honour HF_ENDPOINT natively.
    env["HF_ENDPOINT"] = str(resolve_hf_endpoint()["endpoint"])
    # notebooks shell out to console scripts (optimum-cli, ovc, ...); the venv
    # bin dir must be on PATH or those cells fail with FileNotFoundError
    if venv_bin is None:
        venv_bin = (CPU_VENV if backend == "cpu" else GPU_VENV) / "bin"
    if venv_bin.exists():
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env.pop("PYTHONPATH", None)  # never leak the harness python into the workload env
    if backend == "gpu":
        env.update(GPU_KERNEL_ENV_EXTRA)
        rocm_bin = Path("/opt/rocm/bin")
        if rocm_bin.exists():
            env["PATH"] = f"{rocm_bin}:{env['PATH']}"
    _ = python_bin
    return env


def pip_install(packages: list[str], backend: str = "cpu", retries: int = 3) -> tuple[bool, str]:
    """Install packages into the shared venv with bounded retries and backoff."""

    py = venv_python(backend)
    last = ""
    for attempt in range(retries):
        r = subprocess.run(
            [str(py), "-m", "pip", "install", "--no-input", *packages],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        last = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True, last
        time.sleep(10 * (attempt + 1))
    return False, last


def pip_freeze(backend: str = "cpu") -> str:
    try:
        r = subprocess.run(
            [str(venv_python(backend)), "-m", "pip", "freeze"], capture_output=True, text=True, timeout=180
        )
        return r.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def disk_free_mb(path: str = "/") -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize // (1024 * 1024)


def ram_available_mb() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def upstream_root() -> Path | None:
    """Local pinned upstream snapshot dir (see scripts/fetch_upstream.py).

    Accepts absolute or repo-relative local_path so published metadata carries
    no absolute paths.
    """

    meta_path = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text()).get("local_path", "")
    except (OSError, ValueError):
        return None
    root = Path(raw) if raw.startswith("/") else REPO_ROOT / raw
    return root if raw and root.exists() else None
