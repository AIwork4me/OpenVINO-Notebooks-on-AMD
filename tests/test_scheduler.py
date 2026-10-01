"""Scheduler: ordering, resumability, next_runnable."""


import yaml

from ov_amd.scheduler import counts, load_catalog, next_runnable, order_workloads, resources_ok, save_state
from ov_amd.schemas import NotebookEntry, Status


def make(id_: str, prio=2, weight="medium") -> NotebookEntry:
    return NotebookEntry(id=id_, title=id_, category="LLM", upstream_path=f"n/{id_}.ipynb",
                         upstream_url="u", priority=prio, est_weight=weight)


def test_order_by_priority_then_weight():
    entries = [make("c", prio=1, weight="large"), make("a", prio=0), make("b", prio=1, weight="small")]
    assert [e.id for e in order_workloads(entries)] == ["a", "b", "c"]


def test_next_runnable_skips_terminal(tmp_path, monkeypatch):
    import ov_amd.scheduler as sch

    monkeypatch.setattr(sch, "REPO_ROOT", tmp_path)
    entries = [make("done"), make("todo"), make("failed")]
    state = {
        "attempts": {
            "done": {"cpu": {"status": Status.VERIFIED.value}},
            "failed": {"cpu": {"status": Status.FAILED.value}},
        }
    }
    ids = [e.id for e in next_runnable(entries, state, "cpu")]
    assert ids == ["todo"]
    ids = [e.id for e in next_runnable(entries, state, "cpu", retry_failed=True)]
    assert sorted(ids) == ["failed", "todo"]


def test_interrupted_running_counts_as_runnable():
    entries = [make("mid")]
    state = {"attempts": {"mid": {"cpu": {"status": Status.RUNNING.value}}}}
    assert [e.id for e in next_runnable(entries, state, "cpu")] == ["mid"]


def test_state_roundtrip(tmp_path, monkeypatch):
    import ov_amd.scheduler as sch

    monkeypatch.setattr(sch, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sch, "STATE_PATH", tmp_path / "results" / "marathon-state.json")
    state = {"attempts": {"w": {"cpu": {"status": "VERIFIED"}}}}
    save_state(state)
    loaded = sch.load_state()
    assert loaded["attempts"]["w"]["cpu"]["status"] == "VERIFIED"
    assert loaded["last_checkpoint"]


def test_counts():
    state = {"attempts": {"a": {"cpu": {"status": "VERIFIED"}}, "b": {"cpu": {"status": "FAILED"}}}}
    c = counts(state, "cpu")
    assert c["VERIFIED"] == 1 and c["FAILED"] == 1 and c["TOTAL"] == 2


def test_load_catalog_yaml(tmp_path, monkeypatch):
    import ov_amd.scheduler as sch

    catdir = tmp_path / "catalog"
    catdir.mkdir()
    (catdir / "notebooks.yaml").write_text(yaml.safe_dump({
        "notebooks": [{"id": "x", "title": "X", "category": "API", "upstream_path": "p", "upstream_url": "u"}]
    }))
    monkeypatch.setattr(sch, "REPO_ROOT", tmp_path)
    entries = load_catalog()
    assert len(entries) == 1 and entries[0].id == "x"


def test_resources_ok_shape():
    ok, why = resources_ok()
    assert isinstance(ok, bool)
    assert ok or why  # if not ok there must be a reason
