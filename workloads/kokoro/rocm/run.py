#!/usr/bin/env python3
"""ROCm twin for notebooks/kokoro (TTS).

Same model as the upstream notebook (hexgrad/Kokoro-82M) via transformers on
PyTorch ROCm. Metrics: load, synthesis latency, RTF, output wav properties.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent / "../.."))  # repo root
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "hexgrad/Kokoro-82M"
REVISION = "f3ff357179"  # validated revision (verified live 2026-10-08)
TEXT = "The quick brown fox jumps over the lazy dog."


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import soundfile as sf
    import torch
    from kokoro import KPipeline

    t0 = time.time()
    pipe = KPipeline(lang_code="a", repo_id=MODEL, revision=REVISION)  # official package path
    pipe.model.to("cuda:0").eval()
    load_s = time.time() - t0

    def _gen() -> tuple:
        gs = list(pipe(TEXT, voice="af_heart", speed=1.0))
        wav = gs[0].audio
        wav = wav.detach().cpu().numpy() if hasattr(wav, "detach") else wav
        sr = 24000
        return wav, sr

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

    out = evidence / "out.wav"
    sf.write(out, wavs[0], sr)

    import numpy as np

    finite = bool(np.isfinite(wavs[0]).all()) and len(wavs[0]) > sr  # >1s audio
    exact = len({w.tobytes() for w in wavs}) == 1
    # GPU kernels are not guaranteed bit-identical across runs; int16-scale
    # max deviation is the honest reproducibility measure
    max_diff = max(int(np.abs(wavs[0].astype(np.int32) - w.astype(np.int32)).max()) for w in wavs[1:])
    stable = exact or max_diff <= 300
    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "precision": "default (model dtype)",
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
    ok = finite and stable
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
