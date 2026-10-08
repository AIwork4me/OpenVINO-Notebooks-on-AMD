#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-vl-embedding (vision-language embedding).

Same model as the upstream notebook's default (Qwen/Qwen3-VL-Embedding-2B)
via the model repo's official embedding code (scripts/qwen3_vl_embedding.py,
Qwen3VLEmbedder) on PyTorch ROCm. The transformers range the notebook pins
(>=4.57,<=5.0) provides the built-in qwen3_vl backbone; this twin runs in the
bridged .venv-gpu-tf457 environment.

Input provenance: managed coco.jpg fixture (Apache-2.0 upstream data asset).
Correctness: TASK_SEMANTIC — image-text retrieval sanity: the embedding of
coco.jpg must rank a matching caption above a mismatching one.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import sys
import time

from twin_lib import PeakMemory, emit, fetch, resolve_asset, setup

MODEL = "Qwen/Qwen3-VL-Embedding-2B"
REVISION = "9f2f7e710d"  # validated revision (verified live 2026-10-08)
SCRIPT_URL = f"https://hf-mirror.com/{MODEL}/resolve/{REVISION}/scripts/qwen3_vl_embedding.py"
SCRIPT_SHA256 = "8ffa74a1a6bb759610c57865ea416fd4daf9936cb787520e1112a3e1d547f36a"  # verified 2026-10-08
MATCH_TEXT = "a photo of a city street with people"
MISMATCH_TEXT = "a plate of spaghetti and meatballs"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)

    # official embedding implementation, pinned by content hash
    script = evidence / "qwen3_vl_embedding.py"
    fetch(SCRIPT_URL, script, sha256=SCRIPT_SHA256)
    sys.path.insert(0, str(evidence))

    asset = resolve_asset("coco.jpg")

    import torch

    from qwen3_vl_embedding import Qwen3VLEmbedder  # official repo code

    t0 = time.time()
    embedder = Qwen3VLEmbedder(
        MODEL,
        revision=REVISION,
        torch_dtype=torch.bfloat16,
        device_map="cuda:0",
    )
    load_s = time.time() - t0

    def _emb():
        outs = embedder.process(
            [
                {"image": str(asset.path), "instruction": "Represent the image."},
                {"text": MATCH_TEXT, "instruction": "Represent the text."},
                {"text": MISMATCH_TEXT, "instruction": "Represent the text."},
            ],
            normalize=True,
        )
        img, match, mismatch = outs[0], outs[1], outs[2]
        sim_match = float(torch.nn.functional.cosine_similarity(img, match, dim=-1))
        sim_mismatch = float(torch.nn.functional.cosine_similarity(img, mismatch, dim=-1))
        return sim_match, sim_mismatch

    _emb()  # warmup
    torch.cuda.synchronize()

    runs = []
    results = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            sim_match, sim_mismatch = _emb()
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 3)})
            results.append((round(sim_match, 4), round(sim_mismatch, 4)))

    ranking_ok = all(m > x for m, x in results)
    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "correctness_level": "TASK_SEMANTIC",
        "correctness_contract": "image-text retrieval sanity: cos(img, matching caption) > cos(img, mismatching caption) in all 3 runs",
        "input_asset": asset.record(),
        "implementation": "official Qwen3VLEmbedder (repo scripts/qwen3_vl_embedding.py, hash-pinned)",
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "cosine_match": [r[0] for r in results],
        "cosine_mismatch": [r[1] for r in results],
        "ranking_ok": ranking_ok,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = ranking_ok and all(0.0 < r[0] <= 1.0 for r in results)
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
