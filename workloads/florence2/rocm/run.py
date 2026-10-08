#!/usr/bin/env python3
"""ROCm twin for notebooks/florence2 (vision foundation tasks).

Same model as the upstream notebook's default (microsoft/Florence-2-base-ft,
0.23B), transformers Florence2ForConditionalGeneration with trust_remote_code
(the notebook's loading contract) on PyTorch ROCm. Task: dense caption on the
pinned snapshot nyc.jpg (the notebook's own demo images sit on blocked hosts).
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "microsoft/Florence-2-base-ft"
SNAPSHOT_ASSET = "nyc.jpg"  # managed asset (assets/manifests/assets.yaml)
TASK = "<MORE_DETAILED_CAPTION>"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.jpg"
    asset = resolve_asset(SNAPSHOT_ASSET)
    shutil.copy2(asset.path, img_path)

    import torch
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor

    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0", trust_remote_code=True
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        inputs = processor(text=TASK, images=image, return_tensors="pt").to("cuda:0", torch.bfloat16)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=128, do_sample=False, num_beams=3)
        return processor.batch_decode(out, skip_special_tokens=True)[0].strip()

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
            outs.append(out)

    text = outs[0]
    (evidence / "caption.txt").write_text(text)
    relevant = any(k in text.lower() for k in ("street", "people", "city", "building", "new york", "traffic", "sign", "sidewalk"))
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "task": TASK,
        "input_asset": asset.record(),
        "load_s": round(load_s, 2),
        "runs": runs,
        "output": text[:400],
        "nonempty_relevant_response": bool(text) and relevant,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_relevant_response"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
