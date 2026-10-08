#!/usr/bin/env python3
"""ROCm twin for notebooks/hello-detection (object detection, WORKLOAD_TWIN).

The upstream notebook runs a lightweight OpenVINO detection model on CPU;
this twin runs the same task (coco object detection on the same input image)
through ultralytics YOLOv8n on PyTorch ROCm. Model differs -> WORKLOAD_TWIN,
not EXACT_TWIN (recorded in workload.yaml).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, resolve_asset, setup

MODEL = "yolov8n.pt"
# Weight provenance chain: the official ultralytics release CDN first; on
# runners whose egress blocks github release objects, the HF community mirror
# (kadirnar/yolov8n-v8.0) serves the same architecture weights; the probed
# HF mirror endpoint is the last resort on networks where huggingface.co is
# unreachable (the campaign's documented HF transport). The URL that
# actually served the file and its sha256 are recorded in metrics — weights
# provenance is part of the evidence, never silently swapped.
WEIGHT_URLS = [
    "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt",
    "https://huggingface.co/kadirnar/yolov8n-v8.0/resolve/main/yolov8n.pt",
    "https://hf-mirror.com/kadirnar/yolov8n-v8.0/resolve/main/yolov8n.pt",
]
WEIGHT_SHA256 = "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36"


def _fetch_first(urls: list[str], dest: _Path, sha256: str) -> str:
    # v0.3.1: every source is hash-verified before use (no unverified mirror
    # artifacts can enter the evidence chain)
    import subprocess

    last = ""
    for u in urls:
        r = subprocess.run(
            ["curl", "-sSfL", "--max-time", "300", u, "-o", str(dest)], capture_output=True
        )
        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            import hashlib

            h = hashlib.sha256(dest.read_bytes()).hexdigest()
            if h == sha256:
                return u
            last = f"{u}: sha256 {h[:16]}… != {sha256[:16]}…"
            dest.unlink()
            continue
        last = f"{u}: curl {r.returncode}"
    raise RuntimeError(f"all weight sources failed (last: {last})")


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    evidence = _Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    img = evidence / "intel_rnb.jpg"
    asset = resolve_asset("intel-rnb.jpg")
    import shutil

    shutil.copy2(asset.path, img)
    weights = evidence / MODEL
    weight_source = _fetch_first(WEIGHT_URLS, weights, WEIGHT_SHA256)

    import hashlib

    import torch
    from ultralytics import YOLO

    # vendor torchvision on this stack lacks the HIP build of the nms kernel
    # (CPU build only): delegate NMS post-processing to CPU tensors. Model
    # inference stays on the GPU; the post-processing location is recorded in
    # metrics so the benchmark reading is honest.
    import torchvision.ops as _tvo

    _orig_nms = _tvo.nms

    def _nms_via_cpu(boxes, scores, iou_threshold):
        if boxes.is_cuda:
            return _orig_nms(boxes.detach().to("cpu"), scores.detach().to("cpu"), iou_threshold).to(boxes.device)
        return _orig_nms(boxes, scores, iou_threshold)

    _tvo.nms = _nms_via_cpu
    nms_on_cpu = not getattr(torch.cuda.get_device_properties(0), "name", "").startswith("NONE")

    t0 = time.time()
    model = YOLO(str(weights))  # local file: no auto-download path involved
    model.to("cuda:0")
    load_s = time.time() - t0

    _ = model(img, verbose=False)  # warmup
    torch.cuda.synchronize()

    runs = []
    det = None
    with PeakMemory() as pm:
        for _ in range(5):
            t1 = time.time()
            r = model(img, verbose=False)
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 4)})
            det = r[0]

    n_boxes = int(len(det.boxes.cls))
    classes = sorted({int(c) for c in det.boxes.cls})
    confs = [float(c) for c in det.boxes.conf]
    from twin_lib import gpu_ready

    gpu = gpu_ready()
    metrics = {
        "model": MODEL,
        "model_revision": "ultralytics release v8.4.0 asset",
        "input_asset": asset.record(),
        "task": "object detection (WORKLOAD_TWIN of hello-detection)",
        "precision": "fp32 default",
        "weights_source": weight_source,
        "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "input_image": str(img.name),
        "input_sha256": hashlib.sha256(img.read_bytes()).hexdigest()[:16],
        "load_s": round(load_s, 2),
        "runs": runs,
        "median_latency_s": sorted(r["latency_s"] for r in runs)[len(runs) // 2],
        "detections": n_boxes,
        "class_ids": classes,
        "conf_range": [round(min(confs), 3), round(max(confs), 3)] if confs else [],
        "device": f"{gpu['gcn_arch']} via torch.cuda" if gpu["gcn_arch"] else gpu["device"],
        "nms_postprocessing": "cpu (vendor torchvision lacks HIP nms kernel)" if nms_on_cpu else "gpu",
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = n_boxes >= 1 and classes and all(0.0 < c <= 1.0 for c in confs)
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
