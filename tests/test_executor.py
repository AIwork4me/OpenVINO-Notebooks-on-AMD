"""Executor unit tests (pure parts)."""

from ov_amd.executor import MODULE_TO_PKG, _missing_pkg


def test_missing_pkg_gradio():
    assert _missing_pkg("ModuleNotFoundError: No module named 'gradio'") == "gradio"


def test_missing_pkg_ansi_codes():
    ansi = "\x1b[31mModuleNotFoundError\x1b[39m: No module named 'kagglehub'"
    assert _missing_pkg(ansi) == "kagglehub"


def test_missing_pkg_mapped():
    assert _missing_pkg("ModuleNotFoundError: No module named 'cv2'") == "opencv-python"
    assert _missing_pkg("ModuleNotFoundError: No module named 'PIL'") == "pillow"
    assert _missing_pkg("ModuleNotFoundError: No module named 'sklearn'") == "scikit-learn"


def test_missing_pkg_special_namespaces():
    assert _missing_pkg("ModuleNotFoundError: No module named 'optimum.intel'") == "optimum-intel"
    assert _missing_pkg("ModuleNotFoundError: No module named 'openvino.genai'") == "openvino-genai"
    assert _missing_pkg("ModuleNotFoundError: No module named 'openvino.tokenizers'") == "openvino-tokenizers"


def test_missing_pkg_dotted():
    assert _missing_pkg("ModuleNotFoundError: No module named 'transformers.models'") == "transformers"


def test_missing_pkg_none():
    assert _missing_pkg("SomeOtherError") is None


SUBPROCESS_TRACEBACK = (
    "-> 1955     raise child_exception_type(errno_num, err_msg, err_filename)\n"
    "   1956 else:\n"
    "   1957     raise child_exception_type(errno_num, err_msg)\n"
    "\n"
    "FileNotFoundError: [Errno 2] No such file or directory: 'optimum-cli'"
)

PIL_OPEN_TRACEBACK = (
    "   3639     fp = builtins.open(filename, \"rb\")\n"
    "\n"
    "FileNotFoundError: [Errno 2] No such file or directory: 'nyc.jpg'"
)


def test_missing_pkg_console_script():
    # optimum-cli comes from optimum-intel (verified: PyPI release installs
    # the entry point plus optimum.intel.openvino.OVModelForVisualCausalLM)
    assert _missing_pkg(SUBPROCESS_TRACEBACK) == "optimum-intel"


def test_missing_pkg_console_script_unknown_script_unmapped():
    stderr = SUBPROCESS_TRACEBACK.replace("'optimum-cli'", "'some-unknown-tool'")
    assert _missing_pkg(stderr) is None


def test_missing_pkg_data_file_open_is_not_a_package():
    # builtins.open/PIL shape must not be mistaken for a console script
    assert _missing_pkg(PIL_OPEN_TRACEBACK) is None


def test_module_map_entries():
    assert MODULE_TO_PKG["yaml"] == "pyyaml"
