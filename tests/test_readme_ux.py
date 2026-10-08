"""v0.3.1 Phase-6 regressions: README information architecture.

The README must not mislead a reader into thinking "Radeon/ROCm = everything
works" or "Ryzen/OpenVINO = most things fail". These tests lock the corrected
presentation: coverage vs pass-rate distinction, GPU-selected featured matrix
with an UP-FRONT selection note, an independent CPU-VERIFIED showcase, and
per-cell evidence links.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ov_amd.reporting import (
    CPU_SHOWCASE_BEGIN,
    FEATURED_BEGIN,
    README,
    build_compatibility,
)

pytestmark = pytest.mark.skipif(not README.exists(), reason="README not present")


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text()


@pytest.fixture(scope="module")
def compat() -> dict:
    return build_compatibility()


class TestCoveragePresentation:
    def test_coverage_distinction_is_prominent(self, readme_text):
        assert "100% catalog coverage  ≠  100% pass rate" in readme_text
        # the generated block states the distinction immediately under the headline
        block = readme_text.split("<!-- generated:compatibility begin -->")[1].split(
            "<!-- generated:compatibility end -->"
        )[0]
        assert "It does NOT mean every notebook passed" in block

    def test_two_paths_have_separate_presentations(self, readme_text, compat):
        c = compat["counts"]
        assert f"### {c['cpu_attempted']} / {c['total']} — {c['cpu_attempt_coverage_pct']}% Catalog Coverage" in readme_text
        assert f"### {c['gpu_outcomes'].get('VERIFIED', 0)} verified high-value workload references" in readme_text
        assert "explicitly **not** a catalog-wide sweep" in readme_text
        assert "different denominators" in readme_text


class TestFeaturedMatrix:
    def test_selection_note_precedes_the_table(self, readme_text):
        note = readme_text.find("This table intentionally selects workloads **verified on AMD Radeon GPUs using ROCm**")
        table = readme_text.find("| Workload | Ryzen CPU · OpenVINO | Radeon GPU · ROCm | Twin type |")
        assert note != -1 and table != -1 and note < table, (
            "the GPU-selection disclosure must appear BEFORE the featured table"
        )

    def test_section_title_names_the_selection(self, readme_text):
        assert "### ROCm-Verified Workloads — Independent AMD CPU Results" in readme_text

    def test_matrix_rows_are_gpu_verified(self, readme_text, compat):
        block = readme_text.split(FEATURED_BEGIN)[1].split("<!-- generated:featured end -->")[0]
        row_ids = set(re.findall(r"\|\s*\[([a-z0-9_.\-]+)\]\(", block))
        gpu_verified = {
            r["id"] for r in compat["rows"] if r["gpu_compatibility_outcome"] in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS")
        }
        assert row_ids == gpu_verified, "featured rows must be exactly the GPU-verified set"

    def test_concise_statuses_no_raw_reasons(self, readme_text):
        block = readme_text.split(FEATURED_BEGIN)[1].split("<!-- generated:featured end -->")[0]
        assert "EXTERNAL_HOST_UNREACHABLE" not in block
        assert "MISSING_OR_BROKEN_DEPENDENCY" not in block
        assert "TIMEOUT_INFERENCE" not in block

    def test_cpu_and_gpu_cells_link_their_own_evidence(self, readme_text, compat):
        block = readme_text.split(FEATURED_BEGIN)[1].split("<!-- generated:featured end -->")[0]
        by_id = {r["id"]: r for r in compat["rows"]}
        for line in block.splitlines():
            m = re.match(r"\|\s*\[([a-z0-9_.\-]+)\]\(", line)
            if not m:
                continue
            r = by_id[m.group(1)]
            cells = line.split("|")
            cpu_cell, gpu_cell = cells[2], cells[3]
            if r.get("cpu_evidence"):
                assert r["cpu_evidence"] in cpu_cell, f"{r['id']}: CPU cell missing its own evidence link"
            if r.get("gpu_evidence"):
                assert r["gpu_evidence"] in gpu_cell, f"{r['id']}: GPU cell missing its own evidence link"

    def test_evidence_links_resolve(self, readme_text):
        repo = Path(__file__).resolve().parent.parent
        block = readme_text.split(FEATURED_BEGIN)[1].split("<!-- generated:featured end -->")[0]
        links = re.findall(r"\]\((results/[^)]+)\)", block)
        assert links, "featured matrix must carry evidence links"
        for rel in links:
            assert (repo / rel).exists(), f"dangling evidence link: {rel}"


class TestCpuShowcase:
    def test_showcase_exists_and_is_cpu_selected(self, readme_text, compat):
        assert CPU_SHOWCASE_BEGIN in readme_text
        block = readme_text.split(CPU_SHOWCASE_BEGIN)[1].split("<!-- generated:cpu-showcase end -->")[0]
        assert "not** GPU-selected" in block
        row_ids = set(re.findall(r"^\|\s*\[([a-z0-9_.\-]+)\]\(", block, re.M))
        cpu_verified = {r["id"] for r in compat["rows"] if r["cpu_compatibility_outcome"] == "VERIFIED"}
        assert row_ids and row_ids <= cpu_verified, "showcase rows must come from CPU VERIFIED only"
        # high-value categories preferred: at least half the rows from the heavy set
        high_value = {"LLM", "VLM", "Image Generation", "Video", "OCR", "TTS", "ASR", "Vision"}
        cats = {r["id"]: r["category"] for r in compat["rows"]}
        high = sum(1 for i in row_ids if cats.get(i) in high_value)
        assert high >= len(row_ids) // 2, "showcase should prefer high-value workloads"

    def test_showcase_links_the_full_matrix(self, readme_text):
        block = readme_text.split(CPU_SHOWCASE_BEGIN)[1].split("<!-- generated:cpu-showcase end -->")[0]
        assert "full compatibility matrix" in block


class TestQuickStart:
    def test_quick_start_uses_explicit_venv_interpreter(self, readme_text):
        qs = readme_text.split("## Quick start")[1].split("##")[0]
        assert "uv venv .venv-cpu --python 3.12" in qs
        assert ".venv-cpu/bin/python -m ov_amd doctor" in qs
        # the pre-fix pattern (bare python -m ov_amd after installing into a venv) is gone
        assert not re.search(r"(?<!bin/)(?<!- )python -m ov_amd", qs), (
            "Quick Start must always invoke the venv interpreter explicitly"
        )

    def test_status_semantics_section_exists(self, readme_text):
        assert "## Status semantics (short form)" in readme_text
        assert "**Blocked**" in readme_text and "not** necessarily an AMD CPU incompatibility" in readme_text

    def test_architecture_diagram_present(self, readme_text):
        assert "AMD Ryzen CPU" in readme_text and "AMD Radeon GPU" in readme_text
        assert "OpenVINO" in readme_text and "ROCm" in readme_text
        assert "Compatibility Map" in readme_text
