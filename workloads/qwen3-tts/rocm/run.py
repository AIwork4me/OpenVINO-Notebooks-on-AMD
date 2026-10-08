#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-tts (TTS).

Same model as the upstream notebook's default (Qwen/Qwen3-TTS-12Hz-0.6B-
CustomVoice) via the official QwenLM/Qwen3-TTS repository at the notebook's
pinned revision (1ab0dd75353392f28a0d05d9ca960c9954b13c83), PyTorch on ROCm.
Transport note: the repo is fetched from codeload.github.com (tarball of the
same pinned revision) because git clone transport is unreliable on this
network — pure transport substitution, identical content.
"""

from __future__ import annotations

import shutil
import subprocess
import sys as _sys
import tempfile
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
MODEL_REVISION = "85e237c12c"  # declared model revision (workload.yaml)
REPO = "https://codeload.github.com/QwenLM/Qwen3-TTS/tar.gz/1ab0dd75353392f28a0d05d9ca960c9954b13c83"
REPO_REV = "1ab0dd75353392f28a0d05d9ca960c9954b13c83"
TEXT = "The quick brown fox jumps over the lazy dog."
SPEAKER = "Cherry"  # predefined CustomVoice speaker used by the notebook


def _ensure_repo(dest: _Path) -> None:
    marker = dest / ".repo-rev"
    if marker.exists() and marker.read_text().strip() == REPO_REV:
        return
    r = subprocess.run(
        ["curl", "-sSfL", "--max-time", "600", REPO],
        capture_output=True,
        timeout=660,
    )
    if r.returncode != 0:
        raise RuntimeError(f"codeload fetch failed: {r.returncode}")
    # v0.3.1: safe extraction — member names validated (no absolute paths,
    # no parent traversal, no symlink members), size/member caps enforced
    from ov_amd.assets import safe_extract_tar

    with tempfile.TemporaryDirectory() as td:
        tar_path = _Path(td) / "repo.tar.gz"
        tar_path.write_bytes(r.stdout)
        safe_extract_tar(tar_path, _Path(td) / "x")
        extracted = [p for p in (_Path(td) / "x").iterdir() if p.is_dir()]
        if not extracted:
            raise RuntimeError("tarball contained no top-level directory")
        src = extracted[0]
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(src), str(dest))
    marker.write_text(REPO_REV + "\n")


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    repo_dir = evidence / "Qwen3-TTS-repo"
    _ensure_repo(repo_dir)
    _sys.path.insert(0, str(repo_dir))

    import numpy as np
    import torch

    from qwen_tts import Qwen3TTSModel  # official repo modeling code (package: qwen_tts)

    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(MODEL, revision=MODEL_REVISION, torch_dtype=torch.bfloat16, device_map="cuda:0")
    load_s = time.time() - t0

    def _gen() -> tuple:
        wavs, sr = model.generate_custom_voice(
            text=[TEXT], speaker=[SPEAKER], non_streaming_mode=True, do_sample=False
        )
        wav = np.asarray(wavs[0]).reshape(-1)
        return wav, int(sr)

    with torch.inference_mode():
        _gen()  # warmup
    torch.cuda.synchronize()

    runs = []
    wavs = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            with torch.inference_mode():
                wav, sr = _gen()
            torch.cuda.synchronize()
            total = time.time() - t1
            dur = len(wav) / sr
            runs.append({"latency_s": round(total, 3), "audio_s": round(dur, 2), "rtf": round(dur / total, 2)})
            wavs.append(wav)

    import soundfile as sf

    sf.write(evidence / "out.wav", wavs[0], sr)

    finite = bool(np.isfinite(wavs[0]).all()) and len(wavs[0]) > sr  # >1s
    exact = len({w.tobytes() for w in wavs}) == 1
    max_diff = max(int(np.abs(wavs[0].astype(np.int32) - w.astype(np.int32)).max()) for w in wavs[1:])
    stable = exact or max_diff <= 300
    metrics = {
        "model": MODEL,
        "repo": f"QwenLM/Qwen3-TTS@{REPO_REV}",
        "precision": "bf16",
        "speaker": SPEAKER,
        "text": TEXT,
        "load_s": round(load_s, 2),
        "runs": runs,
        "sample_rate": sr,
        "seconds_generated": round(len(wavs[0]) / sr, 2),
        "finite_waveform": finite,
        "deterministic_exact": exact,
        "max_sample_diff": max_diff,
        "deterministic": stable,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = finite and stable and len(wavs[0]) / sr > 1.0
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
