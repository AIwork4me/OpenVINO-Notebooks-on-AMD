#!/usr/bin/env python3
"""v0.3 Phase B: cluster CPU-blocked rows by shared root cause and rank
recovery opportunities.

priority = developer_value x workloads_unlocked / expected_engineering_cost

Clusters are derived from the LATEST evidence signatures (see
reports/v0.3-recovery-priority.md for the per-row evidence trail). The point
is shared-root-cause ordering, not a vanity score: a one-line transport fix
that unlocks six notebooks outranks three hours on one obscure workload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.environment import REPO_ROOT  # noqa: E402

COMPAT = REPO_ROOT / "catalog" / "compatibility.json"

# signature -> (cluster, cost_h, remedy) ; cost = expected engineering hours
CLUSTERS: list[tuple[str, str, float, str, list[str]]] = [
    (
        "C1-optimum-export-git-transport",
        "optimum-cli export subprocess dies building git+https dependencies "
        "(nested optimum-onnx@<branch> in the optimum-intel fork's setup.py; GnuTLS "
        "TLS death on this network's github clone path)",
        2.0,
        "codeload tarball install of the nested dependency + --no-deps fork install "
        "(documented cell substitution; identical package content)",
        ["glm-ocr", "ernie-image", "qwen-image", "hunyuan-ocr"],
    ),
    (
        "C2-optimum-intel-import-chain",
        "optimum-intel / optimum-cli unusable in the workload env (missing console "
        "script, ImportError, or setup.py guard tripping on the git-source install)",
        2.5,
        "satisfy optimum-intel from PyPI release first, keep the fork only where the "
        "notebook genuinely needs it; per-workload env extra_deps",
        [
            "llm-rag-langchain",
            "llm-rag-langchain-eval",
            "llm-rag-langchain-genai",
            "ltx-video",
            "phi3_chatbot_demo",
            "qwen3-asr",
            "olmocr-pdf-vlm",
            "openvoice2-and-melotts",
            "convert-to-openvino",
        ],
    ),
    (
        "C3-hf-github-flap-rerun",
        "transient HF/github egress flaps during the v0.2.2 campaign window "
        "(ConnectTimeout / EOFError mid-download / avatar CDN); hosts are reachable "
        "again on current passes",
        0.5,
        "plain rerun (bounded, 2 attempts); no notebook changes",
        [
            "qwen3_agent",
            "llm-agent-mcp",
            "vision-background-removal",
            "qwen3.8-mtp",
            "gemma4",
            "instant-id",
            "llm-code-assistant",
            "wav2lip",
        ],
    ),
    (
        "C4-transformers5-contract",
        "notebook-pinned transformers 5.x breaks optimum-intel/peft import chain "
        "(HybridCache removal) during export",
        3.0,
        "per-workload compatible peft/transformers contract via documented cell "
        "substitution; only where the notebook's own pins conflict",
        ["z-image-turbo", "flux.2-klein", "funasr-nano", "text-to-speech-genai", "glm4.1-v-thinking"],
    ),
    (
        "C5-ui-teardown-scoping",
        "NameError after UI-skip (demo/var undefined) or notebook-scoped rerun "
        "variables (point_data, vocab_file_path) — headless teardown gaps, not "
        "model failures",
        1.5,
        "extend documented skip patterns to teardown cells / predefine widget-derived "
        "variables; core inference already ran",
        ["stable-diffusion-xl", "3d-segmentation-point-clouds", "action-recognition-webcam"],
    ),
    (
        "C6-sibling-asset-preseed",
        "notebook-relative sibling assets not present in kernel cwd (test.png, "
        "nyc.jpg, deepsort_utils)",
        1.0,
        "harness preseed extension for the specific missing siblings (sha-verified "
        "snapshot copies)",
        ["paddleocr_vl", "vlm-chatbot-generate-api", "person-tracking"],
    ),
    (
        "C7-torch-absent",
        "transformers Auto* import fails: torch absent from the workload env",
        1.0,
        "env extra_deps torch cpu wheel",
        ["clip-zero-shot-classification", "001-whisper-evaluation"],
    ),
    (
        "C8-download-timeout",
        "TIMEOUT_MODEL_DOWNLOAD on throttled egress",
        2.0,
        "resume-aware rerun (HF cache warm), raised per-cell download bound where "
        "progress is measurable",
        ["aloha-act", "qwen-image-2.1", "unlimited-ocr", "voxcpm2-tts"],
    ),
    (
        "C9-conversion-timeout",
        "TIMEOUT_CONVERSION_EXPORT — measurable-progress exports killed by the wall",
        2.5,
        "longer conversion bound with progress evidence; only where export "
        "progressed",
        [
            "blip-visual-language-processing",
            "deepseek-vl2",
            "fireredtts2",
            "jina-clip",
            "omnivoice",
            "siglip-zero-shot-image-classification",
            "wan2.1-text-to-video",
            "yolov11-quantization-with-accuracy-control",
        ],
    ),
    (
        "C10-inference-timeout",
        "TIMEOUT_INFERENCE — first-token/diffusion latency on CPU",
        3.5,
        "smallest upstream-supported variant where the notebook itself offers one "
        "(recorded); otherwise honest re-block",
        [
            "bark-text-to-audio",
            "controlnet-stable-diffusion",
            "grounded-segment-anything",
            "inpainting-genai",
            "minicpm-v-multimodal-chatbot",
            "music-generation",
            "phi-3-vision",
            "phi-4-multimodal",
            "stable-diffusion-text-to-image",
            "text-to-image-genai",
        ],
    ),
]

NOT_RECOVERABLE = {
    # storage.openvinotoolkit.org is proxy-blocked (403) on this runner and is
    # the sole asset host for these notebooks — honest external blocks
    "ct-segmentation-quantize-nncf": "external host 403 (storage.openvinotoolkit.org)",
    "freevc-voice-conversion": "external host 403 (storage.openvinotoolkit.org)",
    "muse-glimmer": "external host 403 (storage.openvinotoolkit.org)",
    "yoloe-26-open-vocabulary": "external host 403 (storage.openvinotoolkit.org)",
    "whisper-asr-genai": "external host 403 (storage.openvinotoolkit.org; core ASR verified)",
    "omniparser": "download host timeout (proxy) during model fetch",
}

DEV_VALUE = {0: 5.0, 1: 3.0, 2: 2.0, 3: 1.2, 4: 0.8}


def main() -> int:
    rows = json.loads(COMPAT.read_text())["rows"]
    by_id = {r["id"]: r for r in rows}
    out_lines: list[str] = []
    ranked: list[tuple[float, dict]] = []
    for cid, desc, cost, remedy, members in CLUSTERS:
        present = [m for m in members if by_id.get(m, {}).get("cpu_compatibility_outcome", "").startswith("BLOCKED")]
        value = sum(DEV_VALUE.get(by_id[m].get("priority", 4), 0.8) for m in present)
        score = round(value * max(len(present), 1) / cost, 2)
        ranked.append((score, {"id": cid, "desc": desc, "cost": cost, "remedy": remedy, "members": members, "present": present}))
    ranked.sort(key=lambda t: -t[0])

    out_lines += [
        "# v0.3 CPU Failure-Recovery Priority",
        "",
        "Derived from latest-attempt evidence signatures per blocked row",
        "(see `catalog/compatibility.json` + each row's `cpu_evidence`).",
        "",
        "```text",
        "priority = developer_value x workloads_unlocked / expected_engineering_cost",
        "```",
        "",
        "| Rank | Cluster | Score | Rows | Est. cost | Remedy |",
        "|---|---|---|---|---|---|",
    ]
    for i, (score, c) in enumerate(ranked, 1):
        out_lines.append(
            f"| {i} | {c['id']} | {score} | {len(c['present'])} | {c['cost']}h | {c['remedy']} |"
        )
    out_lines += ["", "## Cluster membership (evidence-linked)", ""]
    for _, c in ranked:
        out_lines += [f"### {c['id']} — {c['desc']}", ""]
        for m in c["members"]:
            r = by_id.get(m)
            if not r:
                out_lines.append(f"- `{m}` (not in catalog)")
                continue
            oc = r.get("cpu_compatibility_outcome", "")
            out_lines.append(
                f"- `{m}` — {oc} ({r.get('cpu_outcome_reason', '')}) · evidence `{r.get('cpu_evidence', '')}`"
            )
        out_lines.append("")
    nr = [(k, v) for k, v in NOT_RECOVERABLE.items() if by_id.get(k, {}).get("cpu_compatibility_outcome", "").startswith("BLOCKED")]
    out_lines += ["## Explicitly not pursued this pass (honest external blocks)", ""]
    out_lines += [f"- `{k}` — {v}" for k, v in nr]
    out_lines += [
        "",
        "## Blocked MODEL_ACCESS (out of scope by policy)",
        "",
        "*No credential bypass is attempted; retained honestly unless upstream switches to an open artifact.*",
    ]
    out_lines += [
        f"- `{r['id']}` — {r.get('cpu_outcome_reason', '')}"
        for r in rows
        if r.get("cpu_compatibility_outcome") == "BLOCKED_MODEL_ACCESS"
    ]
    out_lines += [
        "",
        "## Blocked RESOURCE (case-by-case)",
        "",
    ]
    out_lines += [
        f"- `{r['id']}` — {r.get('cpu_outcome_reason', '')}"
        for r in rows
        if r.get("cpu_compatibility_outcome") == "BLOCKED_RESOURCE"
    ]
    out_lines += [""]
    (REPO_ROOT / "reports" / "v0.3-recovery-priority.md").write_text("\n".join(out_lines))
    print(f"wrote reports/v0.3-recovery-priority.md; {sum(len(c['present']) for _, c in ranked)} blocked rows clustered")
    for score, c in ranked:
        print(f"  {score:6.2f} {c['id']} ({len(c['present'])} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
