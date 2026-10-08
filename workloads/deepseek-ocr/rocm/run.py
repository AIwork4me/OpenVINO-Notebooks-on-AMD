#!/usr/bin/env python3
"""ROCm twin for notebooks/deepseek-ocr (document OCR).

Same model as the upstream notebook's default (deepseek-ai/DeepSeek-OCR-2),
transformers DeepseekOcr2ForConditionalGeneration on PyTorch ROCm (total
weights verified 6.8GB via HF blobs API). Input: the DeepSeek-OCR demo
doc_markdown.png (HuggingFace Space asset, reachable host).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, fetch, setup

MODEL = "deepseek-ai/DeepSeek-OCR-2"
IMG_URL = "https://huggingface.co/spaces/khang119966/DeepSeek-OCR-DEMO/resolve/main/doc_markdown.png"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.png"
    fetch(IMG_URL, img_path)

    import torch
    from PIL import Image
    from transformers import AutoProcessor, DeepseekOcr2ForConditionalGeneration

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL)
    model = DeepseekOcr2ForConditionalGeneration.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0"
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        msgs = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": "Extract the text from the image."},
        ]}]
        text = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], images=[image], return_tensors="pt").to("cuda:0", torch.bfloat16)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=1024, do_sample=False)
        return processor.batch_decode(out, skip_special_tokens=True)[0]

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
            runs.append({"latency_s": round(total, 3), "chars": len(out)})
            outs.append(out.strip())

    text = outs[0]
    (evidence / "ocr_output.txt").write_text(text)
    words = [w for w in text.split() if len(w) >= 2]
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "input": "DeepSeek-OCR-DEMO space doc_markdown.png (public official demo asset)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output_chars": len(text),
        "output_words_ge2": len(words),
        "output_preview": text[:400],
        "nonempty_text": len(words) >= 5,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_text"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
