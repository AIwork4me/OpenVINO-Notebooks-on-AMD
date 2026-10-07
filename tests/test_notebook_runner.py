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


def test_git_clone_subprocess_list_form_is_network():
    # ultralytics-style direct clones raise CalledProcessError with the
    # command as a list: "['git', 'clone', URL]" — no space-form match
    stderr = (
        "CalledProcessError: Command '['git', 'clone', "
        "'https://github.com/Rudrabha/Wav2Lip.git']' returned non-zero exit status 128."
    )
    assert classify_failure(stderr, "", False) == FailureCategory.NETWORK


def test_git_clone_outranks_pip_resolver_banner():
    # wav2lip real case: pip's benign resolver banner coexists with the
    # failed clone; NETWORK must win over PACKAGE_CONFLICT
    stderr = (
        "ERROR: pip's dependency resolver does not currently take into account all "
        "the packages that are installed. This behaviour is the source of the "
        "following dependency conflicts.\n"
        "CalledProcessError: Command '['git', 'clone', "
        "'https://github.com/Rudrabha/Wav2Lip.git']' returned non-zero exit status 128."
    )
    assert classify_failure(stderr, "", False) == FailureCategory.NETWORK


def test_resolver_banner_alone_is_not_package_conflict():
    # the banner shows up in most %pip logs; only ResolutionImpossible (or the
    # legacy conflict wording) is evidence of a real dependency conflict
    banner = (
        "ERROR: pip's dependency resolver does not currently take into account all "
        "the packages that are installed. This behaviour is the source of the "
        "following dependency conflicts."
    )
    assert classify_failure(banner, "", False) != FailureCategory.PACKAGE_CONFLICT


def test_banner_plus_remote_disconnect_is_network():
    # llm-rag-llamaindex real case: benign banner + the actual network error
    stderr = (
        "ERROR: pip's dependency resolver does not currently take into account all "
        "the packages that are installed. This behaviour is the source of the "
        "following dependency conflicts.\n"
        "ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end "
        "closed connection without response'))"
    )
    assert classify_failure(stderr, "", False) == FailureCategory.NETWORK


def test_resolution_impossible_still_package_conflict():
    stderr = (
        "ERROR: Cannot install openvino==2025.3.0 and optimum-intel==2.3.0.dev0 "
        "because these package versions have conflicting dependencies.\n"
        "ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/"
    )
    assert classify_failure(stderr, "", False) == FailureCategory.PACKAGE_CONFLICT


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


def test_cell_timeout_outranks_every_grep_rule():
    """A per-cell timeout in the log must classify as TIMEOUT even when pip
    resolver banners / 'timed out' download lines coexist (rule-order defect
    found by the comprehensive audit: wan2.1 classified NETWORK,
    controlnet-stable-diffusion PACKAGE_CONFLICT despite CellTimeoutError)."""
    from ov_amd.notebook_runner import classify_failure

    stderr = (
        "WARNING: pip's dependency resolver does not currently take into account all the packages...\n"
        "huggingface.co connection timed out. Retrying...\n"
        "-------------------\n"
        "nbclient.exceptions.CellTimeoutError: A cell timed out while it was being executed, after 900 seconds.\n"
    )
    assert classify_failure(stderr, "", timeout=False) is FailureCategory.TIMEOUT
