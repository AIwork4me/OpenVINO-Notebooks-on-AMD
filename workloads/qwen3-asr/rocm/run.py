#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-asr (ASR).

Same model as the upstream notebook's default (Qwen/Qwen3-ASR-0.6B-hf),
transformers Qwen3ASRForConditionalGeneration on PyTorch ROCm.

Input provenance (recorded substitution, v0.3.1 hardened): the notebook's sample
audio is hosted on qianwen-res.oss-cn-beijing.aliyuncs.com, which this runner's
egress proxy blocks (403). The twin uses the OpenVINO Notebooks project's own
courtroom.wav sample (the whisper-asr-genai notebook's input, sourced from the
Xenova/transformers.js-docs dataset) — resolved through the managed asset
manifest (assets/manifests/assets.yaml, SHA-256 enforced; explicit user-supplied
path via --input or OV_AMD_ASSET_COURTROOM_ASR_WAV overrides).
Expected content ("A Few Good Men" clip): "you can't handle the truth".
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import argparse
import time
from pathlib import Path

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "Qwen/Qwen3-ASR-0.6B-hf"
REVISION = "7f1569a48a"  # validated revision (evidence 20261008T092400Z-gpu)
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
    ap.add_argument("--input", default=None, help="explicit courtroom.wav path (hash-verified against the manifest)")
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    audio = evidence / "input.wav"

    asset = resolve_asset("courtroom-asr.wav", explicit=args.input)
    import shutil

    shutil.copy2(asset.path, audio)

    import librosa
    import torch
    from transformers import Qwen3ASRForConditionalGeneration, AutoProcessor

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
    model = Qwen3ASRForConditionalGeneration.from_pretrained(
        MODEL, revision=REVISION, torch_dtype=torch.bfloat16, device_map="cuda:0"
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
    # — the sample's ground-truth dialogue); CER measures ASR recognition error.
    # Language metadata ([lang=…]) is stripped before normalization — it is not
    # part of the spoken content.
    import re as _re

    hyp_clean = _re.sub(r"\[lang=[^\]]*\]", "", transcript).strip()
    ref = (
        "Colonel Jessep, did you order the Code Red? You don't have to answer that question. "
        "I'll answer the question. You want answers? I think I'm entitled. You want answers? "
        "I want the truth. You can't handle the truth."
    )
    cer = _cer(ref.lower(), hyp_clean.lower())
    metrics = {
        "model": MODEL,
        "correctness_level": "TASK_SEMANTIC",
        "correctness_contract": "expected transcript fragment + CER vs loose clip-script reference (not word-level ground truth)",
        "model_revision": REVISION,
        "precision": "bf16",
        "input": "courtroom.wav (managed asset courtroom-asr.wav; notebook's qianwen-res.oss host is proxy-blocked)",
        "input_asset": asset.record(),
        "load_s": round(load_s, 2),
        "runs": runs,
        "transcript": transcript[:300],
        "expected_fragment": EXPECTED_FRAGMENT,
        "fragment_found": EXPECTED_FRAGMENT.lower() in transcript.lower(),
        "cer_vs_reference_transcript": round(cer, 3),
        "cer_normalization": "reference/hypothesis lowercased; [lang=…] metadata stripped before CER; loose reference transcript (clip script), not word-level ground truth",
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = bool(transcript) and metrics["fragment_found"] and metrics["output_stable"] and cer < 0.35
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
