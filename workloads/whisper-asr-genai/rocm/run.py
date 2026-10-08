#!/usr/bin/env python3
"""ROCm twin for notebooks/whisper-asr-genai (ASR).

Same model as the upstream notebook (openai/whisper-base), same input audio
(courtroom.wav from the dataset the notebook uses), PyTorch ROCm path.
Metrics: load, transcription latency, RTF, output text.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "openai/whisper-base"
REVISION = "e37978b90c"  # validated revision (evidence 20261007T230927Z-gpu)


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    wav = evidence / "courtroom.wav"
    asset = resolve_asset("courtroom-asr.wav")
    import shutil

    shutil.copy2(asset.path, wav)

    import torch
    from transformers import AutoProcessor, WhisperForConditionalGeneration

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL, revision=REVISION, torch_dtype=torch.float32).to("cuda:0")
    model.eval()
    load_s = time.time() - t0

    import librosa  # noqa: F401 - ensure present

    audio, sr = librosa.load(str(wav), sr=16000)
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt").to("cuda:0")
    duration_s = len(audio) / 16000

    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=8)  # warmup
    torch.cuda.synchronize()

    runs = []
    texts = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            with torch.inference_mode():
                ids = model.generate(**inputs, language="en")
            torch.cuda.synchronize()
            total = time.time() - t1
            text = processor.batch_decode(ids, skip_special_tokens=True)[0]
            runs.append({"latency_s": round(total, 3), "rtf": round(duration_s / total, 2)})
            texts.append(text.strip())

    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "input": "courtroom.wav (managed asset courtroom-asr.wav; notebook's own sample)",
        "input_asset": asset.record(),
        "precision": "fp32",
        "audio_seconds": round(duration_s, 2),
        "load_s": round(load_s, 2),
        "runs": runs,
        "transcription": texts[0][:300],
        "transcription_stable": len(set(texts)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = bool(texts[0]) and metrics["transcription_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
