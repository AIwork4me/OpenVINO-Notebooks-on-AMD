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


def test_module_map_entries():
    assert MODULE_TO_PKG["yaml"] == "pyyaml"
