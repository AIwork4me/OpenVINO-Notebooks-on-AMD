"""Per-workload isolated validation environments (Evidence Schema v2).

Defect B (v0.1): every notebook shared one mutable `.venv-cpu`; any notebook's
`%pip install` (transformers pins, optimum upgrades, protobuf downgrades)
mutated the environment later notebooks were validated in, making
compatibility results unreliable.

v0.2 model:

    immutable seed metadata  ->  per-workload environment  ->  notebook mutates
    (venv seed spec,             keyed by a deterministic      only its own env
     upstream commit,            fingerprint
     python version)

Environment key inputs (env_key):
  backend, python version, pinned upstream commit, dependency fingerprint.

Dependency fingerprint inputs:
  - every requirements*.txt next to the notebook (sorted, with content)
  - every %pip install / !pip install line extracted from the notebook's code
    cells (normalized: leading magics/flags stripped)
  - explicit per-workload dependency override (workload.yaml env.extra_deps)

Two workloads share an environment only when their fingerprints are identical.
The notebook's own upstream dependency declarations take priority: a notebook
that pins older versions mutates its own venv, never the seed.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ov_amd.environment import REPO_ROOT

VENV_ROOT = REPO_ROOT / ".venvs"

# Minimal execution seed: the notebook runtime (kernelspec, nbclient) plus the
# OpenVINO stack. NOT a "golden package set" forcing latest-everything — it is
# the shared baseline a notebook may override inside its own venv.
SEED_PKGS = [
    "ipykernel",
    "ipywidgets",
    "nbclient",
    "nbformat",
    "jupyter_client",
    "numpy",
    "pillow",
    "requests",
    "openvino",
    "openvino-genai",
    "openvino-tokenizers",
    "optimum-intel",
    "transformers",
    "sentence-transformers",
    "protobuf",
    "huggingface_hub",
]

_PIP_MAGIC_RE = re.compile(r"^%?\s*!?\s*pip[3]?\s+install\s+(.*)$", re.M)
_FLAG_RE = re.compile(r"(^|\s)-{1,2}[\w-]+(\s|$)")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def extract_pip_install_lines(nb_path: Path) -> list[str]:
    """Normalized pip-install specs declared by the notebook itself."""

    try:
        nb = json.loads(nb_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    specs: set[str] = set()
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else cell.get("source", "")
        for m in _PIP_MAGIC_RE.finditer(src or ""):
            line = _FLAG_RE.sub(" ", m.group(1)).strip()
            line = " ".join(sorted(line.split()))
            if line:
                specs.add(line)
    return sorted(specs)


def dependency_fingerprint(
    nb_path: Path,
    extra_deps: list[str] | None = None,
    seed_pkgs: list[str] | None = None,
) -> str:
    reqs: list[str] = []
    for p in sorted(nb_path.parent.glob("requirements*.txt")):
        try:
            reqs.append(f"{p.name}:{p.read_text()}")
        except OSError:
            pass
    payload = json.dumps(
        {
            "requirements": reqs,
            "pip_lines": extract_pip_install_lines(nb_path),
            "extra_deps": sorted(extra_deps or []),
            "seed": sorted(seed_pkgs or SEED_PKGS),
        },
        sort_keys=True,
    )
    return _sha256(payload)


@dataclass
class EnvInfo:
    backend: str
    env_key: str
    python: Path
    bin_dir: Path
    fingerprint: str
    reused: bool
    created: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "env_key": self.env_key,
            "python": str(self.python.relative_to(REPO_ROOT))
            if self.python.is_relative_to(REPO_ROOT)
            else str(self.python),
            "fingerprint": self.fingerprint,
            "reused": self.reused,
            "created": self.created,
        }


def compute_env_key(backend: str, python_version: str, upstream_commit: str, dep_fingerprint: str) -> str:
    payload = json.dumps(
        {"backend": backend, "python": python_version, "upstream": upstream_commit, "deps": dep_fingerprint},
        sort_keys=True,
    )
    return _sha256(payload)[:16]


def env_path(backend: str, env_key: str) -> Path:
    return VENV_ROOT / backend / env_key


def _uv_bin() -> str:
    from shutil import which

    found = which("uv")
    if found:
        return found
    home_uv = Path.home() / ".local" / "bin" / "uv"
    if home_uv.exists():
        return str(home_uv)
    return "uv"


def _write_probe_hooks(env_dir: Path) -> None:
    """Wire the device probe + IPv4-first hook into the workload venv.

    Same mechanism as the v0.1 shared venvs (site-packages .pth), scoped to the
    isolated venv so it cannot affect anything else.
    """

    site = next((env_dir / "lib").glob("python*/site-packages"), None)
    if site is None:
        return
    ov_amd_src = Path(__file__).resolve().parent
    (site / "ov_amd_device_probe.py").write_text((ov_amd_src / "device_probe.py").read_text())
    (site / "ov_amd_device_probe.pth").write_text("import ov_amd_device_probe\n")
    ipv4 = ov_amd_src / "ipv4_first.py"
    if ipv4.exists():
        (site / "ov_amd_ipv4_first.py").write_text(ipv4.read_text())
        (site / "ov_amd_net_fix.pth").write_text("import ov_amd_ipv4_first\n")


def _uv_install(python: Path, packages: list[str], timeout: int = 1800) -> tuple[bool, str]:
    cmd = [_uv_bin(), "pip", "install", "--python", str(python), *packages]
    last = ""
    for attempt in range(3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            last = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                return True, last
        except (OSError, subprocess.TimeoutExpired) as e:
            last = str(e)
        time.sleep(10 * (attempt + 1))
    return False, last[-4000:]



def _missing_seed_pkgs(python: Path, packages: list[str]) -> list[str]:
    """Packages among `packages` (bare names, no version specifiers) that are
    not installed in the target venv. Version specs are stripped: the check is
    presence, not resolution."""
    names = [p.split(">=")[0].split("==")[0].split("<")[0].strip() for p in packages]
    code = (
        "import importlib.metadata as md, json, sys\n"
        "missing = []\n"
        "for name in json.load(sys.stdin):\n"
        "    try:\n"
        "        md.version(name)\n"
        "    except Exception:\n"
        "        missing.append(name)\n"
        "print(json.dumps(missing))\n"
    )
    try:
        r = subprocess.run([str(python), "-c", code], input=json.dumps(names),
                           capture_output=True, text=True, timeout=120)
        return json.loads((r.stdout or "[]").strip() or "[]")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return names  # be conservative: treat as unverifiable -> missing

def _python_version_of(system_python: str) -> str:
    try:
        r = subprocess.run(
            [system_python, "-c", "import platform;print(platform.python_version())"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        v = (r.stdout or "").strip()
        if v:
            return v
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "3.12"


def build_env(
    backend: str,
    dep_fingerprint: str,
    python_version: str | None = None,
    upstream_commit: str = "",
    extra_deps: list[str] | None = None,
    seed_pkgs: list[str] | None = None,
) -> EnvInfo:
    """Create the keyed environment. Caller should first check ensure_env for
    reuse; this function always (re)builds."""

    from ov_amd.environment import CPU_VENV

    py_version = python_version or _python_version_of(str(CPU_VENV / "bin" / "python"))
    key = compute_env_key(backend, py_version, upstream_commit, dep_fingerprint)
    target = env_path(backend, key)
    python = target / "bin" / "python"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    seed = seed_pkgs if seed_pkgs is not None else SEED_PKGS
    r = subprocess.run(
        [_uv_bin(), "venv", "--seed", "--python", py_version, str(target)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if r.returncode != 0 or not python.exists():
        raise RuntimeError(f"uv venv failed for {target}: {r.stderr[-2000:]}")
    wanted = [*seed, *(extra_deps or [])]
    ok, log = _uv_install(python, wanted)
    if not ok:
        # leave the broken env in place for inspection but mark it unusable
        (target / "BUILD-FAILED.txt").write_text(log)
        raise RuntimeError(f"seed install failed for {target}: {log[-2000:]}")
    # verify the seed actually landed: uv has been observed to exit 0 on a
    # warm-cache build with a package missing (partial install), which would
    # silently poison every workload sharing this fingerprint
    missing = _missing_seed_pkgs(python, wanted)
    if missing:
        _uv_install(python, missing)
        missing = _missing_seed_pkgs(python, missing)
        if missing:
            (target / "BUILD-FAILED.txt").write_text(f"still missing after retry: {missing}")
            raise RuntimeError(f"seed install incomplete for {target}: missing {missing}")
    _write_probe_hooks(target)
    (target / "env-meta.json").write_text(
        json.dumps(
            {
                "backend": backend,
                "python_version": py_version,
                "upstream_commit": upstream_commit,
                "dependency_fingerprint": dep_fingerprint,
                "seed_pkgs": seed,
                "extra_deps": extra_deps or [],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            indent=2,
        )
    )
    return EnvInfo(
        backend=backend,
        env_key=key,
        python=python,
        bin_dir=target / "bin",
        fingerprint=dep_fingerprint,
        reused=False,
        created=True,
    )


def ensure_env(
    entry,
    backend: str = "cpu",
    extra_deps: list[str] | None = None,
    nb_path: Path | None = None,
    cfg: dict[str, Any] | None = None,
) -> EnvInfo:
    """Resolve-or-create the workload environment (idempotent, fingerprinted).

    `nb_path` defaults to the pinned upstream snapshot location of the entry.
    """

    from ov_amd.environment import CPU_VENV, upstream_root

    cfg = cfg or {}
    root = upstream_root()
    if nb_path is None:
        if root is None:
            raise RuntimeError("upstream snapshot not available; cannot fingerprint notebook")
        nb_path = root / entry.upstream_path
    meta_commit = ""
    meta_path = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    if meta_path.exists():
        try:
            meta_commit = json.loads(meta_path.read_text()).get("commit", "")
        except (OSError, json.JSONDecodeError):
            meta_commit = ""
    deps = list(extra_deps or [])
    deps += list((cfg.get("env") or {}).get("extra_deps") or [])
    fp = dependency_fingerprint(nb_path, extra_deps=deps)
    py_version = _python_version_of(str(CPU_VENV / "bin" / "python"))
    key = compute_env_key(backend, py_version, meta_commit, fp)
    target = env_path(backend, key)
    python = target / "bin" / "python"
    meta_file = target / "env-meta.json"
    if python.exists() and meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            if meta.get("dependency_fingerprint") == fp:
                return EnvInfo(
                    backend=backend, env_key=key, python=python, bin_dir=target / "bin", fingerprint=fp, reused=True
                )
        except (OSError, json.JSONDecodeError):
            pass
    return build_env(backend, fp, python_version=py_version, upstream_commit=meta_commit, extra_deps=deps)


def inspect_env(entry, backend: str = "cpu") -> dict[str, Any]:
    """CLI: show the resolved environment for a workload without building it."""

    from ov_amd.environment import CPU_VENV, upstream_root

    root = upstream_root()
    nb_path = (root / entry.upstream_path) if root else None
    info: dict[str, Any] = {"workload": entry.id, "backend": backend}
    if nb_path is None or not nb_path.exists():
        info["error"] = "notebook not present in upstream snapshot"
        return info
    fp = dependency_fingerprint(nb_path)
    info["dependency_fingerprint"] = fp
    info["pip_lines"] = extract_pip_install_lines(nb_path)
    reqs = sorted(p.name for p in nb_path.parent.glob("requirements*.txt"))
    info["requirements_files"] = reqs
    key = compute_env_key(backend, _python_version_of(str(CPU_VENV / "bin" / "python")), "", fp)
    target = env_path(backend, key)
    info["env_key"] = key
    info["env_path"] = str(target.relative_to(REPO_ROOT))
    info["built"] = (target / "bin" / "python").exists()
    meta_file = target / "env-meta.json"
    if meta_file.exists():
        info["meta"] = json.loads(meta_file.read_text())
    return info


def gc_envs(backend: str | None = None, dry_run: bool = True) -> list[str]:
    """Remove environments whose dependency fingerprint no workload declares.

    A venv is kept when its recorded dependency_fingerprint equals the current
    fingerprint of any catalog workload's notebook.
    """

    from ov_amd.environment import upstream_root
    from ov_amd.scheduler import load_catalog

    root = upstream_root()
    if root is None:
        return []
    catalog = load_catalog()
    current_fps: set[str] | None = None

    def _current() -> set[str]:
        nonlocal current_fps
        if current_fps is None:
            current_fps = set()
            for entry in catalog:
                nb_path = root / entry.upstream_path
                if nb_path.exists():
                    current_fps.add(dependency_fingerprint(nb_path))
        return current_fps

    removed: list[str] = []
    for bdir in sorted(VENV_ROOT.glob("*/")):
        b = bdir.name
        if backend is not None and b != backend:
            continue
        for env in sorted(bdir.iterdir()):
            meta_file = env / "env-meta.json"
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if meta.get("dependency_fingerprint") not in _current():
                removed.append(str(env))
                if not dry_run:
                    shutil.rmtree(env, ignore_errors=True)
    return removed
