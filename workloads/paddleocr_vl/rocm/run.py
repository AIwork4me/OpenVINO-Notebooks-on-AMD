#!/usr/bin/env python3
"""ROCm twin for notebooks/paddleocr_vl (document OCR).

Same model as the upstream notebook (PaddlePaddle/PaddleOCR-VL), transformers
PaddleOCRVLForConditionalGeneration on PyTorch ROCm. Input: the notebook's own
bundled test.png from the pinned snapshot (sha-verified upstream asset).
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "PaddlePaddle/PaddleOCR-VL"
REVISION = "7fa00a8c55"  # validated revision (evidence 20261008T063244Z-gpu)


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.png"
    asset = resolve_asset("paddleocr-vl-test.png")
    shutil.copy2(asset.path, img_path)

    import torch
    from PIL import Image
    from transformers import AutoProcessor, PaddleOCRVLForConditionalGeneration

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
    model = PaddleOCRVLForConditionalGeneration.from_pretrained(
        MODEL, revision=REVISION, torch_dtype=torch.bfloat16, device_map="cuda:0"
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        msgs = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": "OCR:"},
        ]}]
        text = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = processor(images=[image], text=[text], return_tensors="pt").to("cuda:0", torch.bfloat16)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=512, do_sample=False)
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
        "model_revision": REVISION,
        "input_asset": asset.record(),
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output_chars": len(text),
        "output_words_ge2": len(words),
        "output_preview": text[:300],
        "nonempty_text": len(words) >= 5,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_text"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
