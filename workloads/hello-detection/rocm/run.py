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
IMG_URL = "https://storage.openvinotoolkit.org/repositories/openvino_notebooks/data/data/image/coco.jpg"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    evidence = _Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    img = evidence / "coco.jpg"
    fetch(IMG_URL, img)

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
    metrics = {
        "model": MODEL,
        "task": "object detection (WORKLOAD_TWIN of hello-detection)",
        "precision": "fp32 default",
        "load_s": round(load_s, 2),
        "runs": runs,
        "median_latency_s": sorted(r["latency_s"] for r in runs)[2],
        "fps": round(1 / sorted(r["latency_s"] for r in runs)[2], 1),
        "detections": n_boxes,
        "class_ids": classes,
        "conf_range": [round(min(confs), 3), round(max(confs), 3)] if confs else [],
        "device": "gfx1151 via torch.cuda",
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = n_boxes >= 1 and classes and all(0.0 < c <= 1.0 for c in confs)
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
