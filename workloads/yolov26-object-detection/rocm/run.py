#!/usr/bin/env python3
"""ROCm twin for notebooks/yolov26-object-detection.

Same model family and default variant as the upstream notebook (yolo26n via
the ultralytics package — the same package the notebook installs), PyTorch
ROCm (torch.cuda). Input: the OpenVINO Notebooks coco_bike.jpg is on a
blocked host; the twin uses the project's own nyc.jpg snapshot asset (street
scene with multiple people). Correctness: valid boxes/classes/confidences.
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, fetch, setup

MODEL = "yolo26n.pt"  # ultralytics default variant used by the notebook
# Weights provenance (transport substitution, recorded): ultralytics' primary
# release host is github.com/.../releases/download (blocked on this runner).
# The official Ultralytics HF org mirrors the same release artifacts:
# https://huggingface.co/Ultralytics/YOLO26 — identical official asset.
WEIGHTS_URL = "https://huggingface.co/Ultralytics/YOLO26/resolve/main/yolo26n.pt"
SNAPSHOT_IMG = _Path(__file__).resolve().parents[3] / ".cache" / "upstream" / "notebooks" / "vlm-chatbot" / "nyc.jpg"


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.jpg"
    shutil.copy2(SNAPSHOT_IMG, img_path)
    weights = evidence / "yolo26n.pt"
    fetch(WEIGHTS_URL, weights)

    from ultralytics import YOLO

    # The system torchvision (bridged into this venv) lacks the CUDA/ROCm
    # build of torchvision::nms; run NMS on CPU tensors (recorded limitation —
    # backbone inference is GPU; only the box-suppression op moves to CPU).
    import torchvision.ops as _tops

    _nms_cpu = _tops.nms

    def _nms_maybe_cpu(boxes, scores, iou_threshold):
        if boxes.is_cuda:
            return _nms_cpu(boxes.cpu(), scores.cpu(), iou_threshold).to(boxes.device)
        return _nms_cpu(boxes, scores, iou_threshold)

    _tops.nms = _nms_maybe_cpu
    import sys as _sys_m

    if "torchvision" not in _sys_m.modules:
        import torchvision  # noqa: F401 - ultralytics only uses it if already imported
    _tops.nms = _nms_maybe_cpu  # rebind after the guaranteed import

    t0 = time.time()
    model = YOLO(str(weights))  # official ultralytics release weights (HF org mirror)
    model.to("cuda:0")
    load_s = time.time() - t0

    def _run():
        res = model.predict(source=str(img_path), device=0, verbose=False, conf=0.25)
        return res[0]

    _run()  # warmup
    import torch

    torch.cuda.synchronize()

    runs = []
    results = []
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            res = _run()
            torch.cuda.synchronize()
            total = time.time() - t1
            n = int(res.boxes.conf.shape[0]) if res.boxes is not None else 0
            runs.append({"latency_s": round(total, 3), "n_detections": n})
            results.append(res)

    res = results[0]
    boxes = res.boxes
    conf = boxes.conf.detach().cpu() if boxes is not None else None
    cls = boxes.cls.detach().cpu() if boxes is not None else None
    xyxy = boxes.xyxy.detach().cpu() if boxes is not None else None
    import torch as _t

    valid_boxes = bool(
        conf is not None
        and conf.numel() > 0
        and bool(_t.isfinite(conf).all())
        and bool((conf >= 0).all() and (conf <= 1).all())
        and bool((xyxy[:, 2] > xyxy[:, 0]).all() and (xyxy[:, 3] > xyxy[:, 1]).all())
    )
    names = res.names
    detected = sorted({names.get(int(c), str(int(c))) for c in cls.tolist()}) if cls is not None else []
    stable = len({r["n_detections"] for r in runs}) == 1
    metrics = {
        "model": MODEL,
        "precision": "fp32 (ultralytics default)",
        "input": "vlm-chatbot/nyc.jpg (pinned upstream snapshot asset; notebook's coco_bike.jpg host is proxy-blocked)",
        "load_s": round(load_s, 2),
        "runs": runs,
        "n_detections": runs[0]["n_detections"],
        "classes_detected": detected[:10],
        "valid_boxes_classes_confidences": valid_boxes,
        "stable_count": stable,
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    ok = valid_boxes and runs[0]["n_detections"] >= 1 and stable
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
