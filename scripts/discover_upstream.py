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
    (r"openvino-api|openvino-2024|pot-quantization|model-server|model_api|async-api", "API"),
    (r"segformer|segment-anything|segmentation|maskrcnn|monodepth|depth", "Vision"),
    (r"yolo|detection|object-detection|ssd|retinaface|owl-vit|dino|rtdetr", "Vision"),
    (r"classification|mobilenet|resnet|vit|clip|image-classification|similarity", "Vision"),
    (r"whisper|asr|speech-recognition|wav2vec|speech-to-text|mms-speech", "ASR"),
    (r"tts|text-to-speech|speech-synthesis|sunset|kokoro|fish-speech", "TTS"),
    (r"stable-diffusion|latent-consistency|flux|animatediff|kandinsky|image-generation|inpainting|image-editing|photos|stable-diffusion-xl|turbo|unet|photo-restoration|style", "Image Generation"),
    (r"llm|qwen|llama|chatbot|question-answering|rag|agent|phi-|gemma|mistral|deepseek|opt-|gpt2|text-generation|instruction|reinforcement-learning-rl|simplifying", "LLM"),
    (r"internvl|internvl3|internvl2_5|internvl2|vlm|visual-language|llava|git-base| Florence|-- VL|grounding-dino|grounded-segment|molmo|smolvlm|video-llm|multimodal|visual-chat", "VLM"),
    (r"ocr|paddle|paddleocr", "OCR"),
    (r"video|action-recognition|tracking", "Video"),
    (r"anomaly|industrial|anomalib", "Industrial"),
    (r"neural-compression|quantization|weight-compression|compression", "Optimization"),
    (r"tensorflow|onnx|pytorch|convert|export|migration", "Conversion"),
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

WEIGHT_BY_SIZE = [(25_000, "huge"), (10_000, "large"), (3_000, "medium"), (0, "small")]

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


def weight_for(nb: Path, req: Path | None) -> str:
    size = nb_size(nb)
    w = next((label for bound, label in WEIGHT_BY_SIZE if size >= bound), "small")
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
