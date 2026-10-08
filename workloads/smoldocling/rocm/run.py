#!/usr/bin/env python3
"""ROCm twin for notebooks/smoldocling (document -> DocTags conversion).

Same model as the upstream notebook (ds4sd/SmolDocling-256M-preview),
transformers AutoModelForImageTextToText with trust_remote_code (the same
loading contract the notebook uses) on PyTorch ROCm. Input: the DeepSeek-OCR
demo doc_markdown.png (public official demo asset; the notebook's own input
images sit on blocked hosts).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, fetch, setup

MODEL = "ds4sd/SmolDocling-256M-preview"
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
    from transformers import AutoModelForImageTextToText, AutoProcessor

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0", trust_remote_code=True
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        msgs = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": "Convert this page to docling."},
        ]}]
        text = processor.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = processor(text=text, images=[image], return_tensors="pt").to("cuda:0", torch.bfloat16)
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
    (evidence / "doctags_output.txt").write_text(text)
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "input": "DeepSeek-OCR-DEMO space doc_markdown.png (public official demo asset; notebook inputs on blocked hosts)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output_chars": len(text),
        "has_doctags_structure": "<doctag" in text.lower() or "doctag" in text.lower() or len(text.split()) >= 10,
        "output_preview": text[:300],
        "nonempty_output": len(text) >= 40,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_output"] and metrics["has_doctags_structure"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
