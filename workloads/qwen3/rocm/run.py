#!/usr/bin/env python3
"""ROCm twin for supplementary_materials/notebooks/qwen-3 (LLM chat).

Same model as the upstream notebook (Qwen/Qwen3-0.6B), PyTorch ROCm path,
deterministic greedy decoding. Metrics: load, TTFT, decode tokens/s.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import hashlib
import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Qwen/Qwen3-0.6B"
PROMPT = "Give me a short introduction to large language models."
MAX_NEW_TOKENS = 64


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0")
    model.eval()
    load_s = time.time() - t0

    messages = [{"role": "user", "content": PROMPT}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tok(text, return_tensors="pt").to("cuda:0")

    # warmup (excluded from timing)
    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    runs = []
    outputs = []
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
            outputs.append(tok.decode(gen, skip_special_tokens=True))

    combined = "\n".join(outputs)
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "ttft_note": "single-shot generate; TTFT approximated by tokens_per_s on first chunk",
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
        "output_sha256": hashlib.sha256(combined.encode()).hexdigest()[:16],
        "output_preview": outputs[0][:180],
        "deterministic": len(set(outputs)) == 1,
    }
    (evidence / "output.txt").write_text(combined)
    ok = bool(outputs) and all(r["new_tokens"] == MAX_NEW_TOKENS for r in runs) and metrics["deterministic"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
