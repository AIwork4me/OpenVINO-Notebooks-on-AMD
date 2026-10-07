"""Device-probe installation guards (the probe must actually be consulted).

Regression history: _GenaiWatchFinder was appended to sys.meta_path AFTER the
default PathFinder. Meta-path finders answer in order and the first spec wins,
so the finder was never consulted for openvino_genai — every genai-pipeline
workload recorded DEVICE_PROOF_NOT_OBSERVED across an entire marathon pass.
"""

import sys

from ov_amd.device_probe import _GenaiWatchFinder, _OpenvinoWatchFinder, install


def _pathfinder_index() -> int:
    for i, f in enumerate(sys.meta_path):
        # stdlib registers the PathFinder CLASS object in sys.meta_path, so
        # match its __name__ (type(f).__name__ would be plain "type")
        if getattr(f, "__name__", type(f).__name__) == "PathFinder":
            return i
    return len(sys.meta_path)


def test_genai_finder_sits_before_pathfinder():
    install()
    genai = [i for i, f in enumerate(sys.meta_path) if isinstance(f, _GenaiWatchFinder)]
    assert genai, "genai finder not installed"
    assert genai[0] < _pathfinder_index(), (
        "genai finder must precede PathFinder or it is never consulted"
    )


def test_openvino_finder_sits_before_pathfinder():
    install()
    ov = [i for i, f in enumerate(sys.meta_path) if isinstance(f, _OpenvinoWatchFinder)]
    assert ov, "openvino finder not installed"
    assert ov[0] < _pathfinder_index()


def test_install_is_idempotent():
    install()
    install()
    assert sum(isinstance(f, _GenaiWatchFinder) for f in sys.meta_path) == 1
    assert sum(isinstance(f, _OpenvinoWatchFinder) for f in sys.meta_path) == 1
