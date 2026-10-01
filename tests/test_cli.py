"""CLI smoke tests."""

import yaml


def test_cli_help(capsys):
    from ov_amd.cli import main

    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    for cmd in ("doctor", "list", "info", "run", "compare", "marathon", "report"):
        assert cmd in out


def test_cli_list_with_catalog(tmp_path, monkeypatch, capsys):
    import ov_amd.environment as env
    import ov_amd.scheduler as sch

    monkeypatch.setattr(sch, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(env, "REPO_ROOT", tmp_path)
    catdir = tmp_path / "catalog"
    catdir.mkdir()
    (catdir / "notebooks.yaml").write_text(yaml.safe_dump({
        "notebooks": [{"id": "hello-world", "title": "Hello", "category": "API",
                       "upstream_path": "p", "upstream_url": "u", "priority": 0}]
    }))
    st = tmp_path / "results"
    st.mkdir()
    (st / "marathon-state.json").write_text('{"attempts": {}}')

    from ov_amd.cli import main

    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "hello-world" in out and "NOT_TESTED" in out


def test_cli_info_unknown(tmp_path, monkeypatch, capsys):
    import ov_amd.scheduler as sch

    monkeypatch.setattr(sch, "REPO_ROOT", tmp_path)
    catdir = tmp_path / "catalog"
    catdir.mkdir()
    (catdir / "notebooks.yaml").write_text(yaml.safe_dump({"notebooks": []}))
    from ov_amd.cli import main

    assert main(["info", "nope"]) == 1
