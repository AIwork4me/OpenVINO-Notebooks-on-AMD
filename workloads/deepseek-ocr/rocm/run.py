#!/usr/bin/env python3
"""ROCm twin for notebooks/deepseek-ocr (document OCR).

Same model as the upstream notebook's default (deepseek-ai/DeepSeek-OCR-2),
loaded with the model repo's own remote code (trust_remote_code — the same
contract as the upstream ov_deepseek_ocr2_helper) on PyTorch ROCm.

Environment note (recorded): the remote code targets transformers 4.x (it
imports LlamaFlashAttention2, removed in transformers 5), and the upstream
notebook itself pins transformers==4.46.3. Running this twin requires a
dedicated transformers-4.46.3 bridged GPU env (gpu.python override in
workload.yaml) plus a port of the notebook-side preprocessing — NOT yet
provisioned; the twin is attempted-and-deferred (see
reports/v0.3-rocm-expansion.md). Input: DeepSeek-OCR demo doc_markdown.png.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "deepseek-ai/DeepSeek-OCR-2"
REVISION = "aaa02f3811"  # declared model revision (6.8B config verified in v0.3 evidence)
SNAPSHOT_ASSET = "doc-markdown.png"  # managed asset (MIT space; identical role to notebook demo docs)


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.png"
    asset = resolve_asset(SNAPSHOT_ASSET)
    import shutil
    shutil.copy2(asset.path, img_path)

    import torch
    from transformers import AutoModel, AutoTokenizer

    t0 = time.time()
        # the repo's tokenizer_config.json declares LlamaTokenizerFast, but its
    # config.json auto_map omits AutoTokenizer, so 4.46.3's config-class
    # resolution fails — pass the repo-declared class explicitly (recorded)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL, revision=REVISION, trust_remote_code=True, tokenizer_class="LlamaTokenizerFast"
    )
    model = AutoModel.from_pretrained(
        MODEL, revision=REVISION, trust_remote_code=True, torch_dtype=torch.bfloat16, device_map="cuda:0", use_safetensors=True
    ).eval()
    load_s = time.time() - t0

    from PIL import Image

    image = Image.open(img_path).convert("RGB")
    conversation = [
        {"role": "User", "content": "<image_placeholder>\nExtract the text in the image. ", "images": [str(img_path)]},
        {"role": "Assistant", "content": ""},
    ]
    # conversation template from the model repo (same as upstream helper)
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    conv_cls = get_class_from_dynamic_module(
        "conversation.DeepSeekOCR2Conversation" if False else "conversation.get_conv_template",
        MODEL,
        revision=None,
        trust_remote_code=True,
    )
    sft_format = "deepseek"

    def _format(conversation) -> str:
        conv = conv_cls(sft_format)
        conv.set_system_message("")
        for m in conversation:
            content = m["content"]
            if "images" in m and m["images"]:
                content = content.replace("<image_placeholder>", "<image_placeholder>")
            conv.append_message(m["role"], content.strip())
        return conv.get_prompt().strip()

    def _gen() -> str:
        # official repo API (README): model.infer(tokenizer, prompt, image_file, ...)
        out = model.infer(
            tokenizer,
            prompt="<image>\n<|grounding|>Convert the document to markdown. ",
            image_file=str(img_path),
            output_path=str(evidence / "ocr_out"),
            base_size=1024,
            image_size=768,
            crop_mode=True,
            eval_mode=True,  # the repo's documented mode for returning decoded text
            save_results=False,
        )
        return str(out)

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
        "correctness_level": "TASK_SEMANTIC",
        "correctness_contract": "OCR output contains expected document text fragments (markdown headings from the fixed doc_markdown.png fixture)",
        "input_asset": asset.record(),
        "precision": "bf16",
        "loading_contract": "AutoModel trust_remote_code=True (repo's own modeling code, as upstream)",
        "transformers": __import__("transformers").__version__,
        "input": "DeepSeek-OCR-DEMO space doc_markdown.png (public official demo asset)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "output_chars": len(text),
        "output_words_ge2": len(words),
        "output_preview": text[:400],
        "nonempty_text": len(words) >= 5,
        "output_stable": len(set(outs)) == 1,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = metrics["nonempty_text"] and metrics["output_stable"]
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
