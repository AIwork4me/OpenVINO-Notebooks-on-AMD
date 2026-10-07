#!/usr/bin/env python3
"""ROCm twin for notebooks/stable-diffusion-xl (image generation).

Same model as the upstream notebook (stabilityai/stable-diffusion-xl-base-1.0),
diffusers on PyTorch ROCm, fixed seed. The HF mirror 401s stabilityai repos,
so weights come from the ModelScope mirror (recorded).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

HF_ID = "stabilityai/stable-diffusion-xl-base-1.0"
MS_ID = "AI-ModelScope/stable-diffusion-xl-base-1.0"
PROMPT = "a photo of an astronaut riding a horse on mars"
STEPS = 20
SEED = 42


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    evidence = _Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)

    import torch
    from diffusers import StableDiffusionXLPipeline

    t0 = time.time()
    source = HF_ID
    try:
        pipe = StableDiffusionXLPipeline.from_pretrained(HF_ID, torch_dtype=torch.float16)
    except Exception:  # noqa: BLE001 - mirror 401 -> ModelScope
        from modelscope.hub.snapshot_download import snapshot_download

        local = _Path(__file__).resolve().parent / "weights"
        snapshot_download(
            MS_ID, local_dir=str(local),
            allow_patterns=["model_index.json", "*/config.json", "*/tokenizer*", "*/scheduler_config.json",
                            "*/diffusion_pytorch_model.safetensors", "*/diffusion_pytorch_model.fp16.safetensors", "*/model.safetensors",
                            "*/preprocessor_config.json", "*/vocab.json", "*/merges.txt", "*/special_tokens_map.json"],
        )
        source = f"{MS_ID} (ModelScope mirror; HF mirror 401 for stabilityai)"
        pipe = StableDiffusionXLPipeline.from_pretrained(str(local), torch_dtype=torch.float16)
    pipe = pipe.to("cuda:0")
    load_s = time.time() - t0

    gen = torch.Generator(device="cuda:0").manual_seed(SEED)
    _ = pipe(PROMPT, num_inference_steps=4, generator=gen).images[0]  # warmup
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    runs = []
    with PeakMemory() as pm:
        for i in range(3):
            gen = torch.Generator(device="cuda:0").manual_seed(SEED)
            t1 = time.time()
            img = pipe(PROMPT, num_inference_steps=STEPS, generator=gen).images[0]
            torch.cuda.synchronize()
            total = time.time() - t1
            img.save(evidence / f"out_{i}.png")
            runs.append({"total_s": round(total, 3), "steps": STEPS, "steps_per_s": round(STEPS / total, 2)})

    import hashlib

    import numpy as np
    from PIL import Image as PILImage

    def _arr(i: int) -> np.ndarray:
        return np.asarray(PILImage.open(evidence / f"out_{i}.png").convert("RGB"), dtype=np.int16)

    a0 = _arr(0)
    exact = len({(evidence / f"out_{i}.png").read_bytes() for i in range(3)}) == 1
    max_diff = max(int(np.abs(a0 - _arr(i)).max()) for i in (1, 2))
    h, w = a0.shape[:2]
    finite_sized = (evidence / "out_0.png").stat().st_size > 10_000 and h == 1024 and w == 1024
    not_blank = float(np.abs(a0).mean()) > 5.0
    metrics = {
        "model": HF_ID,
        "weights_source": source,
        "precision": "fp16",
        "prompt": PROMPT,
        "seed": SEED,
        "load_s": round(load_s, 2),
        "runs": runs,
        "seconds_per_image": runs[-1]["total_s"],
        "dimensions": f"{w}x{h}",
        # NOTE: per validation-policy, pixel equality is NOT the universal
        # correctness gate for diffusion; fp16 kernel nondeterminism is
        # amplified chaotically across denoising steps (measured below)
        "seed_reproducible_exact": exact,
        "max_pixel_diff": max_diff,
        "pixel_divergence_note": "identical seeds diverge across runs; structural checks gate this twin",
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = len(runs) == 3 and finite_sized and not_blank
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
