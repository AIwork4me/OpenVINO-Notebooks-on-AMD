"""v0.3.1 Phase-3 regressions: benchmark metric semantics and correctness grading.

Covers the mission's scientific-integrity requirements: standard RTF definition
(never mixed with its inverse), accurate GPU-memory labeling (allocated tensors,
not physical VRAM), correctness-strength vocabulary (SMOKE/STRUCTURAL/
TASK_SEMANTIC/GROUND_TRUTH), and ASR CER normalization.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

CORRECTNESS_LEVELS = {"SMOKE", "STRUCTURAL", "TASK_SEMANTIC", "GROUND_TRUTH"}


class TestRTFSemantics:
    def test_standard_rtf_definition_documented(self):
        src = (REPO / "ov_amd" / "twin_lib.py").read_text()
        assert "inference_time / generated_or_input_audio_duration" in src
        assert "inverse RTF" in src

    def test_tts_twin_reports_standard_rtf(self):
        """Regression: kokoro reported audio_s/latency as 'rtf' (inverted)."""
        src = (REPO / "workloads" / "kokoro" / "rocm" / "run.py").read_text()
        assert '"rtf": round(total / dur, 4)' in src, "kokoro rtf must be inference/audio (standard)"
        assert '"realtime_speed_factor": round(dur / total, 2)' in src, "inverse factor must be reported separately"

    def test_asr_twin_reports_standard_rtf(self):
        """Regression: whisper reported duration/latency as 'rtf' (inverted)."""
        src = (REPO / "workloads" / "whisper-asr-genai" / "rocm" / "run.py").read_text()
        assert '"rtf": round(total / duration_s, 4)' in src
        assert '"realtime_speed_factor": round(duration_s / total, 2)' in src

    def test_no_inverted_rtf_left_in_any_twin(self):
        for run in (REPO / "workloads").glob("*/rocm/run.py"):
            src = run.read_text()
            for m in re.finditer(r'"rtf":\s*round\(([^)]+)\)', src):
                expr = m.group(1)
                assert re.search(r"\btotal\b\s*/", expr) or re.search(r"latency", expr), (
                    f"{run}: rtf expression '{expr}' does not look like inference/audio"
                )

    def test_rtf_math(self):
        """RTF definition sanity: 2 s inference for 10 s audio -> RTF 0.2 (<1 real-time)."""
        inference_s, audio_s = 2.0, 10.0
        rtf = inference_s / audio_s
        speed = audio_s / inference_s
        assert rtf == pytest.approx(0.2)
        assert speed == pytest.approx(5.0)
        assert rtf * speed == pytest.approx(1.0)


class TestGPUMemoryLabeling:
    def test_peak_vram_gb_is_documented_as_allocated_memory(self):
        """torch.cuda.max_memory_allocated() is peak ALLOCATED tensor memory,
        not physical VRAM — the label must say so wherever it is described."""
        src = (REPO / "ov_amd" / "twin_lib.py").read_text()
        assert "max_memory_allocated" in src
        assert "NOT total physical VRAM" in src

    def test_emit_stamps_metric_semantics_block(self, tmp_path):
        import sys

        sys.path.insert(0, str(REPO / "ov_amd"))
        from twin_lib import emit

        metrics_file = tmp_path / "metrics.json"
        import types

        # emit() calls gpu_ready() which imports torch; stub it for a no-GPU test
        import twin_lib as TL

        TL.gpu_ready = lambda: {
            "hip": "stub", "cuda_available": True, "device": "stub", "gcn_arch": "gfx-stub",
            "gcn_arch_source": "stub",
        }
        code = emit(True, tmp_path, {"model": "x", "correctness_level": "SMOKE"}, {})
        assert code == 0
        data = json.loads(metrics_file.read_text())
        sem = data["metric_semantics"]
        assert "ALLOCATED GPU tensor memory" in sem["peak_vram_gb"]
        assert "NOT total physical VRAM" in sem["peak_vram_gb"]
        assert "inverse RTF" in sem["realtime_speed_factor"]

    def test_legacy_evidence_carries_no_semantics_block(self):
        """Historical evidence (pre-v0.3.1) must remain readable as-is — the
        extension is additive only. Spot-check one recorded metrics.json."""
        legacy = REPO / "results" / "qwen3" / "20261007T005803Z-gpu" / "metrics.json"
        if not legacy.exists():
            pytest.skip("legacy evidence not present")
        data = json.loads(legacy.read_text())
        assert data["twin_result"]["metrics"]["model"] == "Qwen/Qwen3-0.6B"
        assert "metric_semantics" not in data  # old reader contract: unknown fields absent, not required


class TestCorrectnessGrading:
    VERIFIED = [
        "qwen3", "deepseek-r1", "qwen3-embedding", "qwen3-reranker", "qwen3-asr", "glm-ocr",
        "paddleocr_vl", "smoldocling", "minicpm-v-4.6", "z-image-turbo", "kokoro",
        "whisper-asr-genai", "smolvlm2", "hello-detection", "stable-diffusion-text-to-image",
        "stable-diffusion-xl",
    ]

    def test_levels_use_the_declared_vocabulary(self):
        for wid in self.VERIFIED:
            src = (REPO / "workloads" / wid / "rocm" / "run.py").read_text()
            m = re.search(r'"correctness_level":\s*"([A-Z_]+)"', src)
            assert m, f"{wid}: no correctness_level"
            assert m.group(1) in CORRECTNESS_LEVELS, f"{wid}: unknown level {m.group(1)}"

    def test_every_level_has_a_contract_description(self):
        for wid in self.VERIFIED:
            src = (REPO / "workloads" / wid / "rocm" / "run.py").read_text()
            assert re.search(r'"correctness_contract":\s*"([^"]{20,})"', src), f"{wid}: missing/short contract"

    def test_ground_truth_only_where_fixture_is_fully_known(self):
        """GROUND_TRUTH requires a fully-known input; only the deterministic
        glm-OCR fixture qualifies today."""
        for wid in self.VERIFIED:
            src = (REPO / "workloads" / wid / "rocm" / "run.py").read_text()
            if '"correctness_level": "GROUND_TRUTH"' in src:
                assert wid == "glm-ocr", f"{wid} claims GROUND_TRUTH without a fully-known fixture"

    def test_asr_cer_strips_language_metadata(self):
        """The qwen3-asr CER must strip [lang=…] metadata and disclose that the
        reference is a loose clip script, not word-level ground truth."""
        src = (REPO / "workloads" / "qwen3-asr" / "rocm" / "run.py").read_text()
        assert "\\[lang=" in src or "[lang=" in src
        assert "loose reference transcript" in src


class TestHistoricalEvidenceUntouched:
    def test_no_historical_metrics_were_rewritten(self):
        """Phase 3 corrects code semantics; recorded evidence must keep its
        original bytes (git-clean results/ tree for metrics files)."""
        import subprocess

        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "results"], capture_output=True, text=True, cwd=REPO
        )
        assert not r.stdout.strip(), f"historical evidence modified: {r.stdout}"
