#!/usr/bin/env python3
"""ROCm twin for notebooks/smolvlm2 (VLM).

Same model as the upstream notebook's large option
(HuggingFaceTB/SmolVLM2-2.2B-Instruct), transformers on PyTorch ROCm,
stable prompt + image. Metrics: load, total generation time, tokens/s.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, fetch, setup

MODEL = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
# input substitution (recorded): the notebook's default image lives on a CDN
# blocked from this network; coco.jpg is the standard catalog input class
IMG_URL = "https://storage.openvinotoolkit.org/repositories/openvino_notebooks/data/data/image/coco.jpg"
PROMPT = "Describe this image in one sentence."


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.png"
    fetch(IMG_URL, img_path)

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL)
    model = AutoModelForImageTextToText.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    load_s = time.time() - t0

    from PIL import Image

    image = Image.open(img_path).convert("RGB")
    messages = [{"role": "user", "content": [
        {"type": "image"}, {"type": "text", "text": PROMPT},
    ]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=text, images=[image], return_tensors="pt").to("cuda:0", torch.bfloat16)

    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=8, do_sample=False)  # warmup
    torch.cuda.synchronize()

    runs = []
    outputs = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=48, do_sample=False)
            torch.cuda.synchronize()
            total = time.time() - t1
            gen_len = int(out[0].shape[0] - inputs.input_ids.shape[1])
            runs.append({"total_s": round(total, 3), "new_tokens": gen_len,
                         "tokens_per_s": round(gen_len / total, 2)})
            outputs.append(processor.batch_decode(out, skip_special_tokens=True)[0].split("Assistant:")[-1].strip())

    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output": outputs[0][:300],
        "output_stable": len(set(outputs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = bool(outputs[0]) and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
