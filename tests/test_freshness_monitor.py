"""v0.3.1 Phase-4 regressions: structured upstream-freshness detection.

The old monitor extracted changed notebook-dir names with a regex and mapped
them against the catalog — it could not see ADDED notebooks (they are not in
the catalog yet), REMOVED or RENAMED ones, or shared-helper impact. These
tests drive ov_amd.freshness.analyze with synthetic compare fixtures,
including the real vjepa-2.1 add that motivated the redesign.
"""

from __future__ import annotations

from pathlib import Path

from ov_amd.freshness import DeltaReport, analyze, helper_importing_dirs, notebook_dirs_from_path

CATALOG = {
    "notebooks": [
        {"id": "hello-world", "upstream_path": "notebooks/hello-world/hello-world.ipynb"},
        {"id": "qwen3", "upstream_path": "supplementary_materials/notebooks/qwen-3/qwen3.ipynb"},
        {"id": "stable-diffusion-xl", "upstream_path": "notebooks/stable-diffusion-xl/stable-diffusion-xl.ipynb"},
    ]
}


def _cmp(files, commits=1):
    return {"total_commits": commits, "files": files}


class TestDirMapping:
    def test_notebook_dir(self):
        assert notebook_dirs_from_path("notebooks/hello-world/hello-world.ipynb") == "hello-world"

    def test_supplementary(self):
        assert notebook_dirs_from_path("supplementary_materials/notebooks/qwen-3/qwen3.ipynb") == "qwen-3"

    def test_non_notebook_ignored(self):
        assert notebook_dirs_from_path("notebooks/README.md") is None
        assert notebook_dirs_from_path(".github/workflows/x.yml") is None


class TestAddedDetection:
    def test_added_notebook_not_in_catalog_is_flagged(self):
        """THE motivating case: vjepa-2.1 was added upstream and the old
        regex+catalog monitor missed it entirely."""
        rep = analyze("p" * 12, "h" * 12, _cmp([
            {"filename": "notebooks/vjepa-2.1/vjepa2-video-embeddings.ipynb", "status": "added"},
            {"filename": "notebooks/vjepa-2.1/README.md", "status": "added"},
        ]), CATALOG)
        assert any("vjepa-2.1" in a for a in rep.added_missing), rep.sections()
        assert rep.is_current is False

    def test_modified_catalogued_notebook_lands_in_modified(self):
        rep = analyze("p", "h", _cmp([
            {"filename": "notebooks/hello-world/hello-world.ipynb", "status": "modified"},
        ]), CATALOG)
        assert rep.modified == ["hello-world"]
        assert rep.added_missing == []

    def test_real_v031_delta_shape(self):
        """Replay the actual 2b1600d..3c3899e file list (abridged to the
        notebook-relevant entries)."""
        rep = analyze("2b1600de9620", "3c3899e68b22", _cmp([
            {"filename": ".ci/ignore_treon_docker.txt", "status": "modified"},
            {"filename": ".docker/Pipfile", "status": "modified"},
            {"filename": ".docker/Pipfile.lock", "status": "modified"},
            {"filename": ".github/workflows/job_unix.yml", "status": "modified"},
            {"filename": "notebooks/README.md", "status": "modified"},
            {"filename": "notebooks/vjepa-2.1/README.md", "status": "added"},
            {"filename": "notebooks/vjepa-2.1/vjepa2-video-embeddings.ipynb", "status": "added"},
            {"filename": "notebooks/vjepa-2.1/vjepa_helper.py", "status": "added"},
            {"filename": "requirements.txt", "status": "modified"},
            {"filename": "selector/package-lock.json", "status": "modified"},
        ], commits=8), CATALOG)
        assert [a for a in rep.added_missing if "vjepa-2.1" in a]
        assert rep.modified == []
        assert rep.dependency_policy_files == [".docker/Pipfile", ".docker/Pipfile.lock", "requirements.txt"]
        assert rep.affected_by_shared_helper == []


class TestRemovedRenamed:
    def test_removed(self):
        rep = analyze("p", "h", _cmp([
            {"filename": "notebooks/stable-diffusion-xl/stable-diffusion-xl.ipynb", "status": "removed"},
        ]), CATALOG)
        assert rep.removed == ["stable-diffusion-xl"]

    def test_renamed(self):
        rep = analyze("p", "h", _cmp([
            {"filename": "notebooks/new-name/nb.ipynb", "status": "renamed",
             "previous_filename": "notebooks/old-name/nb.ipynb"},
        ]), CATALOG)
        assert rep.renamed == []
        # old dir not in catalog -> it shows up as added-missing for the new dir
        assert any("new-name" in a for a in rep.added_missing)

    def test_renamed_catalogued(self):
        cat = {"notebooks": [{"id": "old-name", "upstream_path": "notebooks/old-name/nb.ipynb"}]}
        rep = analyze("p", "h", _cmp([
            {"filename": "notebooks/new-name/nb.ipynb", "status": "renamed",
             "previous_filename": "notebooks/old-name/nb.ipynb"},
        ]), cat)
        assert rep.renamed and "old-name" in rep.renamed[0]


class TestSharedHelperImpact:
    def test_helper_change_flags_importing_notebooks(self, tmp_path):
        root = tmp_path / "snapshot"
        (root / "notebooks" / "hello-world").mkdir(parents=True)
        (root / "notebooks" / "hello-world" / "hello-world.ipynb").write_text(
            '{"cells": [{"source": ["from notebook_utils import download_file"]}], "metadata": {}, "nbformat": 4}'
        )
        (root / "notebooks" / "stable-diffusion-xl").mkdir(parents=True)
        (root / "notebooks" / "stable-diffusion-xl" / "stable-diffusion-xl.ipynb").write_text("{}")
        rep = analyze("p", "h", _cmp([
            {"filename": "utils/notebook_utils.py", "status": "modified"},
        ]), CATALOG, snapshot_root=root)
        assert rep.affected_by_shared_helper == ["hello-world"]
        assert rep.unchanged == ["qwen3", "stable-diffusion-xl"]

    def test_helper_import_scanner(self, tmp_path):
        root = tmp_path / "s"
        (root / "notebooks" / "a").mkdir(parents=True)
        (root / "notebooks" / "a" / "a.ipynb").write_text('x = "from utils.pip_helper import install"')
        (root / "notebooks" / "b").mkdir(parents=True)
        (root / "notebooks" / "b" / "b.ipynb").write_text("no imports here")
        dirs = helper_importing_dirs(root)
        assert dirs == {"a"}


class TestNoChange:
    def test_current_pin(self):
        rep = analyze("x", "x", _cmp([], commits=0), CATALOG)
        assert rep.is_current
        assert rep.markdown().startswith("### Upstream freshness: `CURRENT`")
        assert len(rep.unchanged) == 3

    def test_ci_only_change_is_not_a_workload_impact(self):
        rep = analyze("p", "h", _cmp([
            {"filename": ".github/workflows/job_unix.yml", "status": "modified"},
            {"filename": "selector/package-lock.json", "status": "modified"},
        ]), CATALOG)
        assert rep.sections()["MODIFIED"] == []
        assert len(rep.unchanged) == 3


class TestWorkflowContract:
    def test_workflow_uses_structured_analyzer(self):
        repo = Path(__file__).resolve().parent.parent
        wf = (repo / ".github" / "workflows" / "upstream-freshness-monitor.yml").read_text()
        assert "ov_amd.freshness" in wf, "workflow must use the structured analyzer, not regex extraction"
        assert "issues: write" in wf, "issue alerts require explicit issues:write permission"
        assert "re.findall" not in wf  # old regex extraction gone

    def test_workflow_dedups_issues(self):
        repo = Path(__file__).resolve().parent.parent
        wf = (repo / ".github" / "workflows" / "upstream-freshness-monitor.yml").read_text()
        assert "gh issue list" in wf and "gh issue create" in wf
        assert "already tracks head" in wf or "commenting instead of duplicating" in wf


def test_deltareport_sections_keys():
    rep = DeltaReport(pin="p", head="h")
    assert set(rep.sections()) == {
        "ADDED", "MODIFIED", "REMOVED", "RENAMED", "AFFECTED_BY_SHARED_HELPER", "UNAFFECTED"
    }
