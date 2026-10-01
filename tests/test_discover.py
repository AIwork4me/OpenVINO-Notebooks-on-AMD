"""Tests for the discovery classification heuristics (pure functions)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from discover_upstream import classify, priority_for, twin_of, weight_for  # noqa: E402

from ov_amd.schemas import TwinLevel  # noqa: E402


def test_classify_llm():
    cat, _ = classify("notebooks/llm-question-answering/llm-chat-agent.ipynb")
    assert cat == "LLM"


def test_classify_asr():
    cat, _ = classify("notebooks/whisper-subtitles-generation/whisper_subtitles_generation.ipynb")
    assert cat == "ASR"


def test_classify_image_gen():
    cat, _ = classify("notebooks/stable-diffusion-text-to-image/stable_diffusion.ipynb")
    assert cat == "Image Generation"


def test_classify_api():
    cat, _ = classify("notebooks/hello-world/hello-world.ipynb")
    assert cat == "API"


def test_classify_other():
    cat, _ = classify("notebooks/mystery/mystery.ipynb")
    assert cat == "Other"


def test_twin_openvino_specific():
    assert twin_of("notebooks/openvino-api-basics/api.ipynb") == TwinLevel.OPENVINO_SPECIFIC.value


def test_twin_workload():
    assert twin_of("notebooks/whisper-subtitles-generation/whisper.ipynb") == TwinLevel.WORKLOAD_TWIN.value


def test_twin_unclassified():
    assert twin_of("notebooks/mystery/mystery.ipynb") == TwinLevel.NOT_CLASSIFIED.value


def test_priority_p0():
    assert priority_for("hello-world", "API", "small", "notebooks/hello-world/hello-world.ipynb") == 0


def test_priority_p1_for_modern():
    assert priority_for("qwen3", "LLM", "medium", "notebooks/llm-chat-agent/qwen3.ipynb") == 1


def test_weight_by_fake_file(tmp_path):
    nb = tmp_path / "small.ipynb"
    nb.write_text("{}")
    assert weight_for(nb, None) == "small"
    req = tmp_path / "requirements.txt"
    req.write_text("torch\n")
    assert weight_for(nb, req) == "large"
