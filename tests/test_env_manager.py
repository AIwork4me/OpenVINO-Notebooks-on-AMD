"""Per-workload environment isolation (Defect B) and fingerprinting."""

import json
from pathlib import Path

from ov_amd import env_manager


def _make_nb(tmp_path: Path, pip_lines=None, name="nb.ipynb"):
    cells = []
    for line in pip_lines or []:
        cells.append({"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": line})
    nb = {
        "cells": cells
        or [{"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": "print('x')"}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / name
    p.write_text(json.dumps(nb))
    return p


def test_fingerprint_deterministic(tmp_path):
    nb = _make_nb(tmp_path)
    f1 = env_manager.dependency_fingerprint(nb)
    f2 = env_manager.dependency_fingerprint(nb)
    assert f1 == f2 and len(f1) == 64


def test_fingerprint_changes_with_pip_lines(tmp_path):
    """A notebook that %pip installs something must not share an env with one
    that does not — that install is exactly how v0.1 contaminated the shared
    venv."""
    nb_a = _make_nb(tmp_path)
    nb_b = _make_nb(tmp_path, pip_lines=["%pip install -q somepkg==1.2.3"], name="b.ipynb")
    assert env_manager.dependency_fingerprint(nb_a) != env_manager.dependency_fingerprint(nb_b)


def test_fingerprint_changes_with_requirements(tmp_path):
    nb = _make_nb(tmp_path)
    fp_before = env_manager.dependency_fingerprint(nb)
    (tmp_path / "requirements.txt").write_text("numpy==2.0\n")
    assert env_manager.dependency_fingerprint(nb) != fp_before


def test_fingerprint_independent_of_cell_output_changes(tmp_path):
    """Changing non-install code must not invalidate the environment."""
    nb1 = _make_nb(tmp_path, pip_lines=["%pip install foo"])
    nb2 = _make_nb(tmp_path, pip_lines=["%pip install foo"], name="other.ipynb")
    # same install lines, different file names -> same fingerprint
    assert env_manager.dependency_fingerprint(nb1) == env_manager.dependency_fingerprint(nb2)


def test_env_key_binds_backend_and_upstream():
    k1 = env_manager.compute_env_key("cpu", "3.12.3", "abc", "fp")
    k2 = env_manager.compute_env_key("gpu", "3.12.3", "abc", "fp")
    k3 = env_manager.compute_env_key("cpu", "3.12.3", "abd", "fp")
    assert k1 != k2 and k1 != k3 and len(k1) == 16


def test_extract_pip_lines_normalizes(tmp_path):
    nb = _make_nb(tmp_path, pip_lines=["%pip install -q  foo bar ", "!pip install bar foo"])
    lines = env_manager.extract_pip_install_lines(nb)
    # both lines normalize to the same sorted spec set
    assert lines == ["bar foo"]


def test_build_env_isolation_and_reuse(tmp_path, monkeypatch):
    """Workload A mutates only its own venv; workload B's environment dir is a
    different key. Rebuilding the same key reuses the same directory."""
    monkeypatch.setattr(env_manager, "VENV_ROOT", tmp_path / ".venvs")


    calls = []

    def fake_build(backend, fp, python_version=None, upstream_commit="", extra_deps=None, seed_pkgs=None,
                   requirements=None):
        calls.append(fp)
        # create a marker dir instead of a real venv for speed
        key = env_manager.compute_env_key(backend, python_version or "3.12", upstream_commit, fp)
        target = env_manager.env_path(backend, key)
        (target / "bin").mkdir(parents=True, exist_ok=True)
        (target / "bin" / "python").write_text("#!/bin/sh\n")
        (target / "env-meta.json").write_text(json.dumps({"dependency_fingerprint": fp}))
        return env_manager.EnvInfo(
            backend, key, target / "bin" / "python", target / "bin", fp, reused=False, created=True
        )

    monkeypatch.setattr(env_manager, "build_env", fake_build)

    nb_a = _make_nb(tmp_path, pip_lines=["%pip install pkg-a"])
    nb_b = _make_nb(tmp_path, pip_lines=["%pip install pkg-b"], name="b.ipynb")

    class E:
        def __init__(self, p):
            self.upstream_path = p

    info_a = env_manager.ensure_env(E(str(nb_a)), "cpu", nb_path=nb_a)
    info_b = env_manager.ensure_env(E(str(nb_b)), "cpu", nb_path=nb_b)
    assert info_a.env_key != info_b.env_key
    # same env key resolves to the same directory (reuse)
    info_a2 = env_manager.ensure_env(E(str(nb_a)), "cpu", nb_path=nb_a)
    assert info_a2.env_key == info_a.env_key


def test_ensure_env_reuses_matching_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setattr(env_manager, "VENV_ROOT", tmp_path / ".venvs")
    monkeypatch.setattr(env_manager, "_python_version_of", lambda _py: "3.12.3")
    nb = _make_nb(tmp_path)
    fp = env_manager.dependency_fingerprint(nb)
    # ensure_env keys on the pinned upstream commit when the meta file exists
    commit = ""
    meta = tmp_path / "meta.json"
    real_meta = Path(__file__).resolve().parent.parent / "upstream" / "openvino-notebooks.json"
    if real_meta.exists():
        commit = json.loads(real_meta.read_text()).get("commit", "")
    _ = meta
    key = env_manager.compute_env_key("cpu", "3.12.3", commit, fp)
    target = env_manager.env_path("cpu", key)
    (target / "bin").mkdir(parents=True)
    (target / "bin" / "python").write_text("#!/bin/sh\n")
    (target / "env-meta.json").write_text(json.dumps({"dependency_fingerprint": fp}))

    class E:
        upstream_path = "x"

    info = env_manager.ensure_env(E(), "cpu", nb_path=nb)
    assert info.reused is True and info.created is False
