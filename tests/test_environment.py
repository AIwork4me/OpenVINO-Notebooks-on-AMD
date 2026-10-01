"""Environment helper tests."""

import socket


def test_ipv4_first_reorders():
    import importlib.util
    from pathlib import Path

    fake = [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:50c0::154", 443, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("185.199.110.133", 443)),
    ]
    orig = socket.getaddrinfo
    try:
        socket.getaddrinfo = lambda *a, **k: list(fake)  # module wraps this at load time
        spec = importlib.util.spec_from_file_location(
            "ipv4_first", Path(__file__).resolve().parent.parent / "ov_amd" / "ipv4_first.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = socket.getaddrinfo("x", 443)
        assert out[0][0] == socket.AF_INET
        assert out[1][0] == socket.AF_INET6
    finally:
        socket.getaddrinfo = orig


def test_upstream_root_from_meta(tmp_path, monkeypatch):
    import ov_amd.environment as env

    (tmp_path / "upstream").mkdir()
    import json as _json

    (tmp_path / "upstream" / "openvino-notebooks.json").write_text(
        _json.dumps({"local_path": str(tmp_path / "snap")})
    )
    monkeypatch.setattr(env, "REPO_ROOT", tmp_path)
    (tmp_path / "snap").mkdir()
    assert env.upstream_root() == tmp_path / "snap"


def test_upstream_root_missing(tmp_path, monkeypatch):
    import ov_amd.environment as env

    monkeypatch.setattr(env, "REPO_ROOT", tmp_path)
    assert env.upstream_root() is None
