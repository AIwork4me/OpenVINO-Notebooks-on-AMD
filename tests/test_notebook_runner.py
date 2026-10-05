"""Failure classification and output-parsing tests."""

from ov_amd.notebook_runner import classify_failure, detect_device_used, extract_outputs_text
from ov_amd.schemas import FailureCategory


def test_dependency():
    assert classify_failure("ModuleNotFoundError: No module named 'gradio'", "", False) == FailureCategory.DEPENDENCY


def test_network():
    assert (
        classify_failure("requests.exceptions.ConnectionError: hf-mirror refused", "", False) == FailureCategory.NETWORK
    )
    assert classify_failure("urllib.error.URLError: timed out", "", False) == FailureCategory.NETWORK


def test_oom_and_disk():
    assert classify_failure("torch.cuda.OutOfMemoryError", "", False) == FailureCategory.OOM
    assert classify_failure("[Errno 28] No space left on device", "", False) == FailureCategory.DISK_LIMIT


def test_timeout():
    assert classify_failure("", "", True) == FailureCategory.TIMEOUT


def test_unknown():
    assert classify_failure("weird failure", "", False) == FailureCategory.UNKNOWN


def test_extract_outputs(tmp_path):
    nb = tmp_path / "x.ipynb"
    nb.write_text(
        '{"cells": [{"outputs": [{"text": ["hello "]}, {"text": "world"}]},'
        ' {"outputs": [{"data": {"text/plain": ["array([1, 2])"]}}]}]}'
    )
    text = extract_outputs_text(nb)
    assert "hello" in text and "array([1, 2])" in text


def test_extract_outputs_missing_file():
    assert extract_outputs_text(None) == ""
    assert extract_outputs_text(__import__("pathlib").Path("/nonexistent.ipynb")) == ""


def test_detect_device():
    assert detect_device_used("Selected device: NPU") == "NPU"
    assert detect_device_used("device = 'CPU'") == "CPU"
    assert detect_device_used("nothing") == ""


def test_detect_device_widget_value_wins():
    assert detect_device_used("Dropdown(value='AUTO', options=['CPU','GPU'])") == "AUTO"
    assert detect_device_used("Dropdown(value='GPU')\nDropdown(value='CPU')") == "CPU"
    # device list alone must not claim GPU as the used device
    assert detect_device_used("available devices: ['CPU', 'GPU']") == "GPU"  # word fallback only when no value=...
