#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-asr (ASR).

Same model as the upstream notebook's default (Qwen/Qwen3-ASR-0.6B-hf),
transformers Qwen3ASRForConditionalGeneration on PyTorch ROCm.

Input provenance (recorded substitution): the notebook's sample audio is
hosted on qianwen-res.oss-cn-beijing.aliyuncs.com, which this runner's egress
proxy blocks (403). The twin uses the OpenVINO Notebooks project's own
courtroom.wav sample (storage.openvinotoolkit.org origin) from the already-
validated local copy — an official upstream asset, identical role.
Expected content ("A Few Good Men" clip): "you can't handle the truth".
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Qwen/Qwen3-ASR-0.6B-hf"
COURTROOM = _Path(__file__).resolve().parents[3] / "results" / "whisper-asr-genai" / "workdir-cpu" / "data" / "courtroom.wav"
EXPECTED_FRAGMENT = "truth"  # "You can't handle the truth!" — verified transcript of the clip


def _cer(ref: str, hyp: str) -> float:
    ref_c, hyp_c = list(ref), list(hyp)
    dp = list(range(len(hyp_c) + 1))
    for i, rc in enumerate(ref_c, 1):
        prev, dp[0] = dp[0], i
        for j, hc in enumerate(hyp_c, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (rc != hc))
            prev = cur
    return dp[-1] / max(1, len(ref_c))


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    audio = evidence / "input.wav"
    shutil.copy2(COURTROOM, audio)

    import librosa
    import torch
    from transformers import Qwen3ASRForConditionalGeneration, AutoProcessor

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL)
    model = Qwen3ASRForConditionalGeneration.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0"
    ).eval()
    load_s = time.time() - t0

    speech, sr = librosa.load(str(audio), sr=16000, mono=True)

    def _gen() -> str:
        # official processor API used by the upstream notebook
        inputs = processor.apply_transcription_request(audio=speech, sampling_rate=sr)
        inputs = inputs.to("cuda:0", torch.bfloat16)
        with torch.inference_mode():
            ids = model.generate(**inputs, max_new_tokens=256)
        ids = ids[:, inputs["input_ids"].shape[1] :]
        parsed = processor.decode(ids, return_format="parsed")[0]
        return f"{parsed.get('transcription','')} [lang={parsed.get('language','?')}]"

    _gen()  # warmup
    torch.cuda.synchronize()

    runs = []
    outs = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            out = _gen()
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 3)})
            outs.append(out.strip())

    transcript = outs[0]
    (evidence / "transcript.txt").write_text(transcript)
    # reference: the known script of the clip (A Few Good Men courtroom scene
    # — the sample's ground-truth dialogue); CER measures ASR recognition error
    ref = (
        "Colonel Jessep, did you order the Code Red? You don't have to answer that question. "
        "I'll answer the question. You want answers? I think I'm entitled. You want answers? "
        "I want the truth. You can't handle the truth."
    )
    cer = _cer(ref.lower(), transcript.lower())
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "input": "courtroom.wav (upstream OpenVINO Notebooks sample; official asset copy — notebook's qianwen-res.oss host is proxy-blocked)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "transcript": transcript[:300],
        "expected_fragment": EXPECTED_FRAGMENT,
        "fragment_found": EXPECTED_FRAGMENT.lower() in transcript.lower(),
        "cer_vs_reference_transcript": round(cer, 3),
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = bool(transcript) and metrics["fragment_found"] and metrics["output_stable"] and cer < 0.35
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
