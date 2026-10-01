"""Executor unit tests (pure parts)."""

from ov_amd.executor import MODULE_TO_PKG, _missing_pkg


def test_missing_pkg_gradio():
    assert _missing_pkg("ModuleNotFoundError: No module named 'gradio'") == "gradio"


def test_missing_pkg_mapped():
    assert _missing_pkg("ModuleNotFoundError: No module named 'cv2'") == "opencv-python"
    assert _missing_pkg("ModuleNotFoundError: No module named 'PIL'") == "pillow"
    assert _missing_pkg("ModuleNotFoundError: No module named 'sklearn'") == "scikit-learn"


def test_missing_pkg_dotted():
    assert _missing_pkg("ModuleNotFoundError: No module named 'transformers.models'") == "transformers"


def test_missing_pkg_none():
    assert _missing_pkg("SomeOtherError") is None


def test_module_map_entries():
    assert MODULE_TO_PKG["yaml"] == "pyyaml"
