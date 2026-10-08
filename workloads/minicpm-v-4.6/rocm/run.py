#!/usr/bin/env python3
"""ROCm twin for notebooks/minicpm-v-4.6 (VLM).

Same model as the upstream notebook (openbmb/MiniCPM-V-4.6), official repo
loading contract (AutoModel trust_remote_code — identical to the notebook) on
PyTorch ROCm. Input: the project's pinned snapshot nyc.jpg.
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, setup

MODEL = "openbmb/MiniCPM-V-4.6"
SNAPSHOT_IMG = _Path(__file__).resolve().parents[4] / ".cache" / "upstream" / "notebooks" / "vlm-chatbot" / "nyc.jpg"
PROMPT = "Describe this image in one sentence."


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.jpg"
    shutil.copy2(SNAPSHOT_IMG, img_path)

    import torch
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, device_map="cuda:0", trust_remote_code=True
    ).eval()
    load_s = time.time() - t0

    image = Image.open(img_path).convert("RGB")

    def _gen() -> str:
        msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}]
        answer = model.chat(
            image=image,
            msgs=msgs,
            tokenizer=tok,
            sampling=False,
            max_new_tokens=64,
        )
        return str(answer).strip()

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
    (evidence / "output.txt").write_text(text)
    relevant = any(k in text.lower() for k in ("street", "people", "city", "building", "new york", "manhattan", "traffic", "sign"))
    metrics = {
        "model": MODEL,
        "precision": "bf16",
        "input": "vlm-chatbot/nyc.jpg (pinned upstream snapshot asset)",
        "prompt": PROMPT,
        "load_s": round(load_s, 2),
        "runs": runs,
        "output": text[:300],
        "nonempty_relevant_response": bool(text) and relevant,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_relevant_response"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
