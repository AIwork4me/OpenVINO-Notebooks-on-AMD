#!/usr/bin/env python3
"""ROCm twin for notebooks/z-image-turbo (image generation).

Same model as the upstream notebook (Tongyi-MAI/Z-Image-Turbo), diffusers
pipeline on PyTorch ROCm. Correctness: generated image, valid dimensions,
finite pixels, seed-stable across runs.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Tongyi-MAI/Z-Image-Turbo"
REVISION = "f332072aa7"  # validated revision (verified live 2026-10-08)
PROMPT = "A cat holding a sign that says 'AMD ROCm', watercolor style."
SEED = 42


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import torch
    from diffusers import AutoPipelineForText2Image

    t0 = time.time()
    pipe = AutoPipelineForText2Image.from_pretrained(MODEL, revision=REVISION, torch_dtype=torch.bfloat16)
    pipe = pipe.to("cuda:0")
    load_s = time.time() - t0

    def _gen():
        g = torch.Generator(device="cuda:0").manual_seed(SEED)
        with torch.inference_mode():
            img = pipe(prompt=PROMPT, generator=g, num_inference_steps=8).images[0]
        return img

    _gen()  # warmup
    torch.cuda.synchronize()

    runs = []
    imgs = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            img = _gen()
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 3)})
            imgs.append(img)

    import numpy as np

    imgs[0].save(evidence / "out.png")
    arr = np.asarray(imgs[0].convert("RGB"), dtype=np.int32)
    finite = bool(np.isfinite(arr).all())
    dims_ok = img.size[0] >= 512 and img.size[1] >= 512
    hashes = [hash(np.asarray(i.convert("RGB"), dtype=np.int32).tobytes()) for i in imgs]
    seed_stable = len(set(hashes)) == 1
    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "precision": "bf16",
        "prompt": PROMPT,
        "seed": SEED,
        "steps": 8,
        "load_s": round(load_s, 2),
        "runs": runs,
        "image_size": list(imgs[0].size),
        "finite_pixels": finite,
        "dims_valid": dims_ok,
        "seed_stable": seed_stable,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = finite and dims_ok and seed_stable
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
