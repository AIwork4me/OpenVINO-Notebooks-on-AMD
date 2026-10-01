#!/usr/bin/env python3
"""ROCm twin for notebooks/stable-diffusion-text-to-image (image generation).

Same model as the upstream notebook (stabilityai/stable-diffusion-2-1),
diffusers on PyTorch ROCm, fixed seed. Metrics: load, s/image, peak VRAM.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time
from pathlib import Path

from twin_lib import PeakMemory, emit, setup

MODEL = "stabilityai/stable-diffusion-2-1"
PROMPT = "a photo of an astronaut riding a horse on mars"
STEPS = 20
SEED = 42


def _load_pipeline(evidence: Path):
    """Load SD2.1 from the HF mirror; fall back to the ModelScope mirror when
    the HF mirror rejects this repo (401 for stabilityai/* there). The
    substitution is recorded in the metrics."""

    import torch
    from diffusers import StableDiffusionPipeline

    t0 = time.time()
    source = MODEL
    try:
        pipe = StableDiffusionPipeline.from_pretrained(MODEL, torch_dtype=torch.float16)
    except Exception:  # noqa: BLE001 - any hub failure (401/404 on this mirror) -> ModelScope fallback
        # ModelScope mirror of the same weights (AI-ModelScope/stable-diffusion-2-1)
        local = _Path(__file__).resolve().parent / "weights"  # stable cache across reruns (gitignored)
        from modelscope.hub.snapshot_download import snapshot_download

        # the mirror repo carries every weight format (>30GB); fetch only what
        # the diffusers pipeline needs
        snapshot_download(
            "AI-ModelScope/stable-diffusion-2-1",
            local_dir=str(local),
            allow_patterns=[
                "model_index.json", "*/config.json", "*/preprocessor_config.json",
                "*/special_tokens_map.json", "*/tokenizer_config.json", "*/vocab.json",
                "*/merges.txt", "*/tokenizer.json", "*/scheduler_config.json",
                "*/diffusion_pytorch_model.safetensors", "*/diffusion_pytorch_model.fp16.safetensors",
            ],
        )
        source = "AI-ModelScope/stable-diffusion-2-1 (ModelScope mirror; HF mirror 401 for stabilityai/stable-diffusion-2-1)"
        pipe = StableDiffusionPipeline.from_pretrained(str(local), torch_dtype=torch.float16)
    return pipe.to("cuda:0"), time.time() - t0, source


def main() -> int:
    ap = setup()
    args = ap.parse_args()

    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)

    import torch

    pipe, load_s, source = _load_pipeline(evidence)

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

    h1 = hashlib.sha256((evidence / "out_0.png").read_bytes()).hexdigest()[:16]
    exact = all(
        hashlib.sha256((evidence / f"out_{i}.png").read_bytes()).hexdigest() == h1
        for i in range(3)
    )
    # fp16 GPU kernels are not guaranteed bit-identical across runs; treat
    # max per-pixel deviation within a small tolerance as reproducible
    a0 = _arr(0)
    max_diff = max(int(np.abs(a0 - _arr(i)).max()) for i in (1, 2))
    metrics = {
        "model": MODEL,
        "weights_source": source,
        "precision": "fp16",
        "prompt": PROMPT,
        "seed": SEED,
        "load_s": round(load_s, 2),
        "runs": runs,
        "seconds_per_image": runs[-1]["total_s"],
        "seed_reproducible_exact": exact,
        "seed_reproducible_within_tolerance": max_diff <= 8,
        "max_pixel_diff": max_diff,
        "image_sha256": h1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = len(runs) == 3 and max_diff <= 8 and (evidence / "out_0.png").stat().st_size > 10_000
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
