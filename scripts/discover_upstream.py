#!/usr/bin/env python3
"""Discover the upstream openvino_notebooks catalog.

Scans the pinned clone, classifies every discoverable notebook, and writes
catalog/notebooks.yaml + upstream/openvino-notebooks.json.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from ov_amd.environment import REPO_ROOT  # noqa: E402
from ov_amd.schemas import NotebookEntry, PriorityTier, TwinLevel  # noqa: E402

UPSTREAM_DIR = REPO_ROOT / ".cache" / "upstream"
UPSTREAM_META = REPO_ROOT / "upstream" / "openvino-notebooks.json"
CATALOG = REPO_ROOT / "catalog" / "notebooks.yaml"

# category detection rules, evaluated in order on the upstream-relative path
CATEGORY_RULES: list[tuple[str, str]] = [
    (r"hello-world|hellogenerateimage", "API"),
    (r"openvino-api|openvino-2024|pot-quantization|model-server|model_api|async-api|auto-device|gpu-device|hello-npu|hugging-face-hub|openvino-tokenizers|optimize-preprocessing", "API"),
    (r"tensorflow|onnx|pytorch|detectron2|modelscope|tflite|convert|export|migration", "Conversion"),
    (r"neural-compression|quantization|weight-compression|compression|language-quantize", "Optimization"),
    (r"whisper|asr|speech-recognition|wav2vec|speech-to-text|mms-massively|omnivoice", "ASR"),
    (r"tts|text-to-speech|speech-synthesis|sunset|kokoro|fish-speech|bark-text-to-audio|openvoice|freevc|voice-conversion|music-generation|ace-step", "TTS"),
    (r"wav2lip|animate-anyone|catvton|instant-id|ernie-image|muse-glimmer|image-to-image-genai|text-to-image-genai|rmbg|background-removal|darkir|photo-restoration|inpainting|image-editing", "Image Generation"),
    (r"stable-diffusion|latent-consistency|flux|animatediff|kandinsky|image-generation|unet|style", "Image Generation"),
    (r"florence2|glm4|glm4\.1|minicpm|internvl|vlm|visual-language|llava|git-base|grounding-dino|grounded-segment|molmo|smolvlm|video-llm|multimodal|visual-chat|omnimodal", "VLM"),
    (r"ocr|paddle|docling|mineru|smoldocling|omniparser|meter-reader", "OCR"),
    (r"llm|qwen|llama|chatbot|question-answering|rag|agent|phi-|gemma|mistral|ministral|deepseek|opt-|gpt2|text-generation|instruction|translation|nuextract|speculative|simplifying|hunyuan|physical-ai|aloha", "LLM"),
    (r"yolo|detection|object-detection|ssd|retinaface|owl-vit|dino|rtdetr|pointpillars|person-counting", "Vision"),
    (r"pose-estimation|segmentation|maskrcnn|monodepth|depth|segformer|segment-anything|sam2|sam3", "Vision"),
    (r"classification|mobilenet|resnet|vit|clip|image-classification|similarity", "Vision"),
    (r"video|action-recognition|tracking", "Video"),
    (r"anomaly|industrial|anomalib", "Industrial"),
]

HEAVY_DEPS = {
    "torch": "large",
    "tensorflow": "large",
    "paddlepaddle": "huge",
    "paddleocr": "large",
    "monai": "large",
    "librosa": "medium",
    "nncf": "small",
}

WEIGHT_BY_SOURCE = [(400_000, "huge"), (100_000, "large"), (30_000, "medium"), (0, "small")]

TWIN_RULES: list[tuple[str, str]] = [
    (r"openvino-api|pot-quantization|model-server|async-api|neural-compression|weight-compression|nncf|optimization|convert|export|migration|tensorflow-to-openvino|pytorch-to-openvino|onnx", TwinLevel.OPENVINO_SPECIFIC.value),
    (r"whisper|asr|speech", TwinLevel.WORKLOAD_TWIN.value),
    (r"stable-diffusion|image-generation|animatediff|inpainting", TwinLevel.WORKLOAD_TWIN.value),
    (r"llm|qwen|llama|chatbot|rag|agent|question-answering|text-generation", TwinLevel.WORKLOAD_TWIN.value),
    (r"yolo|detection|classification|segmentation|clip", TwinLevel.WORKLOAD_TWIN.value),
    (r"ocr|paddle", TwinLevel.WORKLOAD_TWIN.value),
    (r"tts", TwinLevel.WORKLOAD_TWIN.value),
    (r"vlm|visual-language|internvl", TwinLevel.WORKLOAD_TWIN.value),
]

P0_IDS = {"hello-world", "hello-world-cell", "openvino-api", "openvino-2024", "classification"}


def git_info(repo: Path) -> dict:
    """Prefer existing fetch metadata (scripts/fetch_upstream.py); fall back to git."""

    meta_path = REPO_ROOT / "upstream" / "openvino-notebooks.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("commit"):
            return meta
    if not (repo / ".git").exists():
        raise SystemExit("no upstream metadata and no git clone — run scripts/fetch_upstream.py first")

    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True).stdout.strip()

    branch = run("rev-parse", "--abbrev-ref", "HEAD")
    return {
        "repository": "openvinotoolkit/openvino_notebooks",
        "branch": branch,
        "commit": run("rev-parse", "HEAD"),
        "commit_date": run("log", "-1", "--format=%ci"),
        "commit_subject": run("log", "-1", "--format=%s"),
        "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "local_path": str(repo),
    }


def nb_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def title_of(path: Path) -> str:
    name = path.stem
    return name.replace("-", " ").replace("_", " ").strip().title()


def source_bytes(nb: Path) -> int:
    """Code volume only (embedded output images excluded)."""

    try:
        import json

        data = json.loads(nb.read_text(errors="ignore"))
        total = 0
        for cell in data.get("cells", []):
            if cell.get("cell_type") == "code":
                src = cell.get("source", "")
                total += len("".join(src) if isinstance(src, list) else src)
        return total
    except (OSError, ValueError):
        return nb_size(nb)


def source_text(nb: Path) -> str:
    """All cell source text (code only)."""

    try:
        import json

        data = json.loads(nb.read_text(errors="ignore"))
        chunks = []
        for cell in data.get("cells", []):
            if cell.get("cell_type") == "code":
                src = cell.get("source", "")
                chunks.append("".join(src) if isinstance(src, list) else src)
        return "\n".join(chunks)
    except (OSError, ValueError):
        return ""


def model_weight_bump(nb: Path) -> str | None:
    """Weight implied by referenced model scale (params/diffusion keywords).

    Code size says nothing about the model a notebook downloads; a 20KB
    notebook can pull a 30GB checkpoint. Rough but far better than nothing.
    """

    text = source_text(nb)
    if not text:
        return None
    big = re.findall(r"(\d+(?:\.\d+)?)\s*[Bb]\b", text)
    if big:
        params = [float(x) for x in big]
        m = max(params)
        if m >= 13:
            return "huge"
        if m >= 2:
            return "large"
        if m >= 0.5:
            return "medium"
    for kw in ("flux", "sd3", "stable-diffusion-3", "video", "hunyuan", "wan2", "animatediff", "sdxl"):
        if kw in text.lower():
            return "large"
    return None


def weight_for(nb: Path, req: Path | None) -> str:
    w = next((label for bound, label in WEIGHT_BY_SOURCE if source_bytes(nb) >= bound), "small")
    bump = model_weight_bump(nb)
    if bump:
        rank = {"small": 0, "medium": 1, "large": 2, "huge": 3}
        if rank[bump] > rank[w]:
            w = bump
    if req and req.exists():
        text = req.read_text(errors="ignore").lower()
        for dep, heavy in HEAVY_DEPS.items():
            if re.search(rf"^{dep}\b", text, re.M) or dep in text:
                rank = {"small": 0, "medium": 1, "large": 2, "huge": 3}
                if rank[heavy] > rank[w]:
                    w = heavy
    return w


def classify(path_rel: str) -> tuple[str, str]:
    p = path_rel.lower()
    for pat, cat in CATEGORY_RULES:
        if re.search(pat, p):
            return cat, pat
    return "Other", ""


def twin_of(path_rel: str) -> str:
    p = path_rel.lower()
    for pat, lvl in TWIN_RULES:
        if re.search(pat, p):
            return lvl
    return TwinLevel.NOT_CLASSIFIED.value


def priority_for(entry_id: str, category: str, weight: str, path_rel: str) -> int:
    if entry_id in P0_IDS or re.search(r"hello|api-basic", path_rel.lower()):
        return PriorityTier.P0_FOUNDATIONAL.value
    if category in ("LLM", "VLM", "ASR", "TTS", "OCR", "Image Generation") and weight in ("small", "medium", "large"):
        return PriorityTier.P1_HIGH_VALUE.value
    if weight in ("small", "medium"):
        return PriorityTier.P2_MEDIUM.value
    if weight == "large":
        return PriorityTier.P3_HEAVY.value
    return PriorityTier.P4_EXTREME.value


def main() -> int:
    if not UPSTREAM_DIR.exists():
        print("upstream clone missing — run: git clone --depth 1 "
              "https://github.com/openvinotoolkit/openvino_notebooks.git .cache/upstream", file=sys.stderr)
        return 1
    meta = git_info(UPSTREAM_DIR)
    UPSTREAM_META.parent.mkdir(parents=True, exist_ok=True)
    UPSTREAM_META.write_text(json.dumps(meta, indent=2))

    base = f"https://github.com/openvinotoolkit/openvino_notebooks/blob/{meta['commit']}"
    entries: list[NotebookEntry] = []
    for nb in sorted(UPSTREAM_DIR.rglob("*.ipynb")):
        rel = nb.relative_to(UPSTREAM_DIR).as_posix()
        if rel.startswith((".git/",)) or ".ipynb_checkpoints" in rel or "/." in f"/{rel}":
            continue
        req = None
        for cand in nb.parent.glob("requirements*.txt"):
            req = cand
            break
        category, _pat = classify(rel)
        weight = weight_for(nb, req)
        entry_id = nb.stem.lower()
        entries.append(
            NotebookEntry(
                id=entry_id,
                title=title_of(nb),
                category=category,
                upstream_path=rel,
                upstream_url=f"{base}/{rel}",
                requirements_path=(nb.parent / req.name).relative_to(UPSTREAM_DIR).as_posix() if req else None,
                priority=priority_for(entry_id, category, weight, rel),
                workload_type=category.lower().replace(" ", "-"),
                est_weight=weight,
                cpu_meaningful=True,
                gpu_meaningful=twin_of(rel) in ("EXACT_TWIN", "WORKLOAD_TWIN"),
                twin_level=twin_of(rel),
            )
        )

    # de-duplicate ids (same stem in different dirs) by suffixing parent dir
    seen: dict[str, int] = {}
    for e in entries:
        seen[e.id] = seen.get(e.id, 0) + 1
    counts = {}
    for e in entries:
        if seen[e.id] > 1:
            counts[e.id] = counts.get(e.id, 0) + 1
            e.id = f"{e.id}~{counts[e.id]}"

    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(
        yaml.safe_dump(
            {
                "generated": meta["discovered_at"],
                "upstream_commit": meta["commit"],
                "notebooks": [e.to_dict() for e in entries],
            },
            sort_keys=False,
        )
    )
    print(f"catalog: {len(entries)} notebooks -> {CATALOG}")
    from collections import Counter

    print("categories:", dict(Counter(e.category for e in entries)))
    print("priorities:", dict(sorted(Counter(e.priority for e in entries).items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
