#!/usr/bin/env python3
"""ROCm twin for notebooks/deepseek-r1 (LLM reasoning).

Same model family as the upstream notebook (DeepSeek-R1-Distill-Llama-8B),
transformers on PyTorch ROCm, greedy decoding. HF mirror may 401 deepseek-ai
repos; falls back to ModelScope (recorded) with identical weights.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

HF_ID = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
REVISION = "6a6f4aa419"  # HF revision (verified live 2026-10-08)
MS_REVISION = "21e2cfdbe904bf48ae7336612272291c3285d0fc"  # ModelScope mirror commit (2025-02-24, weights-identical mirror of 6a6f4aa419)
MS_ID = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
PROMPT = "What is 17 * 23? Think briefly and answer."
MAX_NEW_TOKENS = 96


def _load():
    import torch

    # ModelScope first: the HF mirror stalls on deepseek-ai repo files
    from modelscope.hub.snapshot_download import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    source = HF_ID
    try:
        from modelscope.hub.api import HubApi  # noqa: F401

        local = _Path(__file__).resolve().parent / "weights"
        snapshot_download(MS_ID, revision=MS_REVISION, local_dir=str(local))
        source = f"{MS_ID} (ModelScope mirror; HF mirror stalls on deepseek-ai files)"
        tok = AutoTokenizer.from_pretrained(str(local))
        model = AutoModelForCausalLM.from_pretrained(str(local), torch_dtype=torch.bfloat16, device_map="cuda:0")
    except Exception:  # noqa: BLE001 - ModelScope miss -> HF mirror
        tok = AutoTokenizer.from_pretrained(HF_ID, revision=REVISION)
        model = AutoModelForCausalLM.from_pretrained(HF_ID, revision=REVISION, torch_dtype=torch.bfloat16, device_map="cuda:0")
    return tok, model.eval(), source


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import torch

    t0 = time.time()
    tok, model, source = _load()
    load_s = time.time() - t0

    messages = [{"role": "user", "content": PROMPT}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt").to("cuda:0")

    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=8, do_sample=False)  # warmup
    torch.cuda.synchronize()

    runs = []
    outs = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
            torch.cuda.synchronize()
            total = time.time() - t1
            gen = out[0][inputs.input_ids.shape[1]:]
            n = int(gen.shape[0])
            runs.append({"total_s": round(total, 3), "new_tokens": n,
                         "tokens_per_s": round(n / total, 2)})
            outs.append(tok.decode(gen, skip_special_tokens=True))

    combined = "\n---\n".join(outs)
    (evidence / "output.txt").write_text(combined)
    metrics = {
        "model": HF_ID,
        "correctness_level": "STRUCTURAL",
        "correctness_contract": "nonempty full-length reasoning output + determinism",
        "model_revision": REVISION,
        "weights_source": source,
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "deterministic": len(set(outs)) == 1,
        "output_preview": outs[0][-220:],
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = bool(outs[0]) and metrics["deterministic"] and all(r["new_tokens"] == MAX_NEW_TOKENS for r in runs)
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
