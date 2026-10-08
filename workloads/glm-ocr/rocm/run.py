#!/usr/bin/env python3
"""ROCm twin for notebooks/glm-ocr (document OCR).

Same model as the upstream notebook (zai-org/GLM-OCR, 0.9B), transformers
GlmOcrForConditionalGeneration on PyTorch ROCm.

Input provenance (recorded substitution): the notebook's sample images are
GitHub user-attachment S3 URLs, which this runner's egress proxy blocks. The
twin renders a deterministic typewritten fixture (PIL, DejaVu Sans) with
known content; the correctness contract checks the model reads the expected
fragment back. Input is recorded in metrics and the PNG is kept in evidence.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "zai-org/GLM-OCR"
REVISION = "2e85a62840"  # validated revision (verified live 2026-10-08)
EXPECTED = "The quick brown fox jumps over the lazy dog"


def _fixture(path: _Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (760, 180), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    d.text((30, 70), EXPECTED, fill="black", font=font)
    img.save(path)


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.png"
    _fixture(img_path)

    import torch
    from PIL import Image
    from transformers import AutoProcessor, GlmOcrForConditionalGeneration

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
    model = GlmOcrForConditionalGeneration.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0"
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        msgs = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": "OCR:"},
        ]}]
        text = processor.apply_chat_template(msgs, add_generation_prompt=True)
        inputs = processor(text=text, images=[image], return_tensors="pt").to("cuda:0", torch.bfloat16)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=128, do_sample=False)
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
            runs.append({"latency_s": round(total, 3)})
            outs.append(out.strip())

    text = outs[0]
    (evidence / "ocr_output.txt").write_text(text)
    low = text.lower()
    fragment_words = [w for w in EXPECTED.lower().split() if w not in ("the", "a")]
    hits = sum(1 for w in fragment_words if w in low)
    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "precision": "bf16",
        "input": "deterministic typewritten PIL fixture (upstream sample images on blocked GitHub-attachment host)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output": text[:300],
        "expected_fragment": EXPECTED,
        "fragment_word_hits": f"{hits}/{len(fragment_words)}",
        "fragment_ok": hits >= len(fragment_words) - 1,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["fragment_ok"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
