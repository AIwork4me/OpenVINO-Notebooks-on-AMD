#!/usr/bin/env python3
"""ROCm twin for notebooks/qwen3-reranker (relevance reranking).

Same model as the upstream notebook's default (Qwen/Qwen3-Reranker-0.6B),
transformers AutoModelForCausalLM with the Qwen3Rerarker yes/no logit
contract on PyTorch ROCm. Correctness: finite scores + correct ranking of a
relevant over an irrelevant passage + stability.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "Qwen/Qwen3-Reranker-0.6B"
QUERY = "What is the capital of France?"
DOC_RELEVANT = "The capital of France is Paris."
DOC_IRRELEVANT = "Photosynthesis converts sunlight into chemical energy in plants."


def _format_prompt(query: str, doc: str) -> str:
    return (
        f"<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct"
        f" provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n"
        f"<|im_start|>user\n"
        f"<Instruct>: Given a web search query, retrieve relevant passages that answer the query\n"
        f"<Query>: {query}\n"
        f"<Document>: {doc}<|im_end|>\n"
        f"<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token_yes = torch.tensor([16]).to("cuda:0")  # "yes" token id for Qwen3 tokenizer, verified at runtime
    token_no = torch.tensor([11]).to("cuda:0")

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0").eval()
    load_s = time.time() - t0

    yes_id = tok("yes", add_special_tokens=False)["input_ids"][0]
    no_id = tok("no", add_special_tokens=False)["input_ids"][0]
    token_yes = torch.tensor([yes_id]).to("cuda:0")
    token_no = torch.tensor([no_id]).to("cuda:0")

    def _score(doc: str) -> float:
        ids = tok(_format_prompt(QUERY, doc), return_tensors="pt", truncation=True, max_length=512)
        ids = {k: v.to("cuda:0") for k, v in ids.items()}
        with torch.inference_mode():
            logits = model(**ids).logits[0, -1, :]
        return float(logits[token_yes] - logits[token_no])

    _score(DOC_RELEVANT)  # warmup
    torch.cuda.synchronize()

    runs = []
    scores = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            rel = _score(DOC_RELEVANT)
            irr = _score(DOC_IRRELEVANT)
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 3), "score_relevant": round(rel, 3), "score_irrelevant": round(irr, 3)})
            scores.append((rel, irr))

    finite = all(isinstance(a, float) and a == a and abs(a) != float("inf") for s in scores for a in s)
    ranking_ok = all(rel > irr for rel, irr in scores)
    stable = all(abs(scores[i][0] - scores[0][0]) < 0.05 and abs(scores[i][1] - scores[0][1]) < 0.05 for i in range(1, len(scores)))
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "load_s": round(load_s, 2),
        "runs": runs,
        "yes_token_id": int(yes_id),
        "no_token_id": int(no_id),
        "finite": finite,
        "ranking_correct": ranking_ok,
        "stable": stable,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = finite and ranking_ok and stable
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
