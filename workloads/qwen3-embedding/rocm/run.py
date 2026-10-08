#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-embedding (text embedding).

Same model as the upstream notebook's default (Qwen/Qwen3-Embedding-0.6B),
transformers AutoModel with last-token pooling on PyTorch ROCm. Correctness:
shape, finiteness, and cosine-ranking sanity (query closer to the relevant
document than to an irrelevant one).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Qwen/Qwen3-Embedding-0.6B"
REVISION = "97b0c614be"  # validated revision (verified live 2026-10-08)
QUERY = "What is the capital of France?"
DOC_RELEVANT = "The capital of France is Paris."
DOC_IRRELEVANT = "Photosynthesis converts sunlight into chemical energy in plants."


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import torch
    from transformers import AutoModel, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModel.from_pretrained(MODEL, revision=REVISION, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    load_s = time.time() - t0

    def _embed(texts: list[str]):
        # Qwen3-Embedding: last-token pooling (model-card contract), L2 norm.
        # One text at a time — no padding ambiguity about which token is last.
        vecs = []
        with torch.inference_mode():
            for t in texts:
                batch = tok(t, truncation=True, max_length=128, return_tensors="pt")
                batch = {k: v.to("cuda:0") for k, v in batch.items()}
                out = model(**batch).last_hidden_state
                vecs.append(out[0, -1, :])
        return torch.nn.functional.normalize(torch.stack(vecs), p=2, dim=-1).float().cpu()

    _embed([QUERY])  # warmup
    torch.cuda.synchronize()

    runs = []
    sims = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            q = _embed([QUERY])[0]
            d = _embed([DOC_RELEVANT, DOC_IRRELEVANT])
            torch.cuda.synchronize()
            total = time.time() - t1
            cos = (q @ d.T).tolist()
            runs.append({"latency_s": round(total, 4), "cos_relevant": round(cos[0], 4), "cos_irrelevant": round(cos[1], 4)})
            sims.append(cos)

    shape_ok = tuple(q.shape) == (int(q.numel()),) and q.numel() > 0
    finite = bool(torch.isfinite(torch.tensor(sims)).all())
    ranking_ok = all(s[0] > s[1] for s in sims)
    stable = all(abs(sims[i][0] - sims[0][0]) < 1e-3 and abs(sims[i][1] - sims[0][1]) < 1e-3 for i in range(1, len(sims)))
    metrics = {
        "model": MODEL,
        "model_revision": REVISION,
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "embedding_dim": int(q.numel()),
        "finite": finite,
        "ranking_sanity": ranking_ok,
        "stable": stable,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = shape_ok and finite and ranking_ok and stable
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
