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

from twin_lib import PeakMemory, emit, fetch, setup

MODEL = "yolov8n.pt"
# Same input image the upstream notebook analyses (notebooks/hello-detection
# fetches intel_rnb.jpg from user-images.githubusercontent.com). The canonical
# storage.openvinotoolkit.org copy is the fallback, not the primary, because
# that host is blocked on some validation runners.
IMG_URL = "https://user-images.githubusercontent.com/36741649/128489933-bf215a3f-06fa-4918-8833-cb0bf9fb1cc7.jpg"
IMG_FALLBACK = "https://storage.openvinotoolkit.org/repositories/openvino_notebooks/data/data/image/intel_rnb.jpg"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    evidence = _Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    img = evidence / "intel_rnb.jpg"
    fetch(IMG_URL, img, fallbacks=[IMG_FALLBACK])

    import hashlib

    import torch
    from ultralytics import YOLO

    t0 = time.time()
    model = YOLO(MODEL)  # auto-downloads from ultralytics github release (fast CDN)
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
        "task": "object detection (WORKLOAD_TWIN of hello-detection)",
        "precision": "fp32 default",
        "input_image": str(img.name),
        "input_sha256": hashlib.sha256(img.read_bytes()).hexdigest()[:16],
        "load_s": round(load_s, 2),
        "runs": runs,
        "median_latency_s": sorted(r["latency_s"] for r in runs)[len(runs) // 2],
        "detections": n_boxes,
        "class_ids": classes,
        "conf_range": [round(min(confs), 3), round(max(confs), 3)] if confs else [],
        "device": f"{gpu['gcn_arch']} via torch.cuda" if gpu["gcn_arch"] else gpu["device"],
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = n_boxes >= 1 and classes and all(0.0 < c <= 1.0 for c in confs)
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
