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


def test_gated_model_outranks_pip_resolver_banner():
    stderr = (
        "ERROR: pip's dependency resolver does not currently take into account all "
        "the packages that are installed. This behaviour is the source of the "
        "following dependency conflicts.\n"
        "huggingface_hub.utils._errors.GatedRepoError: 401 Client Error. "
        "Access to model openai/stable-diffusion-3 is restricted (Repository access forbidden)."
    )
    assert classify_failure(stderr, "", False) == FailureCategory.MODEL_ACCESS


def test_missing_console_script_is_dependency():
    # subprocess spawn failure for a console script (optimum-cli et al):
    # the notebook's %pip git-install failed silently, the executable never
    # landed in the venv — a dependency failure with a remediation path
    stderr = (
        "-> 1955     raise child_exception_type(errno_num, err_msg, err_filename)\n"
        "   1956 else:\n"
        "   1957     raise child_exception_type(errno_num, err_msg)\n"
        "\n"
        "FileNotFoundError: [Errno 2] No such file or directory: 'optimum-cli'"
    )
    assert classify_failure(stderr, "", False) == FailureCategory.DEPENDENCY


def test_missing_data_file_is_not_dependency():
    # builtins.open/PIL FileNotFoundError (missing image on disk) must not
    # route into the pip-remediation path
    stderr = (
        "   3639     fp = builtins.open(filename, \"rb\")\n"
        "\n"
        "FileNotFoundError: [Errno 2] No such file or directory: 'nyc.jpg'"
    )
    assert classify_failure(stderr, "", False) != FailureCategory.DEPENDENCY


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
