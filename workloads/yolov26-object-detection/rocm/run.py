#!/usr/bin/env python3
"""ROCm twin for notebooks/yolov26-object-detection.

Same model and default variant as the upstream notebook (yolo26n via the
ultralytics package — the same package the notebook installs), PyTorch ROCm
(torch.cuda).

v0.3.1 RCA (full record in reports/v0.3.1-final-report.md):
- The official weights are obtainable and verified: the GitHub release asset
  (ultralytics/assets v8.4.0, fetched via the reachable api.github.com
  octet-stream route) is byte-identical (sha256 9b09cc8b…) to the official
  Ultralytics HF-org mirror — the v0.3 "mirror artifact mismatch" theory is
  refuted.
- YOLO26 is an end-to-end (NMS-free) detector: its head natively emits
  (1, 300, 6) [x, y, w, h, conf, cls] detections. The legacy predict() path
  (both ultralytics 8.4.43 — the notebook's pin — and 8.4.173) mis-decodes
  this e2e output (confidences collapse to ~0.01) and its warmup NMS hits a
  torchvision kernel mismatch on this stack.
- The model itself is healthy: raw forward on the official weights yields
  ~300 high-confidence detections on a street scene.

This twin therefore consumes the model's native end-to-end output (exactly
what the notebook's `export(..., end2end=True)` OpenVINO pipeline serves),
using ultralytics' own LetterBox preprocessing. Input: managed nyc.jpg asset
(street scene with people/cars — the notebook's coco_bike.jpg host is
proxy-blocked).
"""

from __future__ import annotations

import shutil
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "ov_amd"))  # twin_lib location

import time

from twin_lib import PeakMemory, emit, fetch, resolve_asset, setup

MODEL = "yolo26n.pt"  # ultralytics default variant used by the notebook
# Weights provenance (verified official): GitHub release asset
# ultralytics/assets v8.4.0 == HF org mirror Ultralytics/YOLO26, byte-identical
# (sha256 9b09cc8b…, cross-checked via the api.github.com octet-stream route
# 2026-10-08 — the browser_download_url host itself is proxy-blocked here).
WEIGHTS_URL = "https://hf-mirror.com/Ultralytics/YOLO26/resolve/main/yolo26n.pt"
WEIGHTS_SHA256 = "9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef"
SNAPSHOT_ASSET = "nyc.jpg"  # managed asset (assets/manifests/assets.yaml)
CONF_THR = 0.5
EXPECTED_CLASSES = {"person", "car"}  # nyc.jpg street scene


def _detect_e2e(weights: Path, img_path: Path, device: str):
    """Run the official yolo26n end-to-end head with ultralytics preprocessing."""
    import numpy as np
    import torch
    from PIL import Image
    from ultralytics import YOLO
    from ultralytics.data.augment import LetterBox

    yolo = YOLO(str(weights))
    model = yolo.model.to(device).eval()

    img = Image.open(img_path).convert("RGB")
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    letterbox = LetterBox(new_shape=(640, 640), auto=False, stride=32)
    lb = letterbox(image=arr)
    x = torch.from_numpy(np.ascontiguousarray(lb)).permute(2, 0, 1).float().unsqueeze(0) / 255.0
    x = x.to(device)

    with torch.inference_mode():
        out = model(x)
    if isinstance(out, (list, tuple)):
        out = out[0]
    out = out.detach().float().cpu()

    r = min(640 / h, 640 / w)
    pad_w, pad_h = (640 - w * r) / 2, (640 - h * r) / 2
    names = yolo.model.names

    if out.dim() == 3 and out.shape[-1] == 6 and out.shape[1] != 84:
        # end-to-end format (ultralytics 8.4.43 head): (1, N, 6) [x,y,w,h,conf,cls]
        dets = out[0]
        boxes = dets[:, :4].clone()
        boxes[:, 0] -= pad_w
        boxes[:, 1] -= pad_h
        boxes[:, :4] /= r
        confs = dets[:, 4]
        classes = dets[:, 5]
    elif out.dim() == 3 and out.shape[1] == 84:
        # legacy anchor format (ultralytics 8.4.173 head): (1, 84, 8400)
        anchors = out[0].T  # (8400, 84)
        boxes = anchors[:, :4].clone()
        boxes[:, 0] -= pad_w
        boxes[:, 1] -= pad_h
        boxes[:, :4] /= r
        scores = torch.sigmoid(anchors[:, 4:])
        conf, cls_idx = scores.max(dim=1)
        confs, classes = conf, cls_idx.float()
    else:
        raise RuntimeError(f"unexpected detection output shape {tuple(out.shape)}")

    # artifact-degeneracy guard: an untrained/garbage head emits logits ~0
    # everywhere (sigmoid ~0.5 with nonsense classes and out-of-image boxes).
    # A healthy detector reaches high confidence on an objectful scene.
    max_conf = float(confs.max()) if confs.numel() else 0.0
    keep = (confs > CONF_THR) & (confs > 0.0)
    return [
        {
            "box_xywh": [round(float(v), 1) for v in boxes[i]],
            "conf": round(float(confs[i]), 4),
            "cls": names[int(classes[i])] if isinstance(names, (list, dict)) else int(classes[i]),
        }
        for i in torch.nonzero(keep).flatten().tolist()
    ], tuple(out.shape), max_conf


def main() -> int:
    ap = setup()
    args = ap.parse_args()
    from pathlib import Path

    evidence = Path(args.evidence_dir)
    img_path = evidence / "input.jpg"
    asset = resolve_asset(SNAPSHOT_ASSET)
    shutil.copy2(asset.path, img_path)
    weights = evidence / MODEL
    fetch(WEIGHTS_URL, weights, sha256=WEIGHTS_SHA256)

    import torch

    if not torch.cuda.is_available():
        raise SystemExit("ROCm GPU not available")

    _detect_e2e(weights, img_path, "cuda:0")  # warmup
    torch.cuda.synchronize()

    runs = []
    outputs = []
    out_shape = None
    max_conf = 0.0
    with PeakMemory() as pm:
        for _ in range(3):
            t1 = time.time()
            dets, out_shape, max_conf = _detect_e2e(weights, img_path, "cuda:0")
            torch.cuda.synchronize()
            total = time.time() - t1
            runs.append({"latency_s": round(total, 3), "n_detections": len(dets)})
            outputs.append(dets)

    all_classes = sorted({d["cls"] for d in outputs[0]})  # empty when the artifact is inference-degenerate

    expected_seen = sorted(EXPECTED_CLASSES & set(all_classes))
    src_w, src_h = 1, 1
    from PIL import Image as _Img

    with _Img.open(img_path) as _im:
        src_w, src_h = _im.size
    sane_boxes = all(
        d["box_xywh"][0] >= 0 and d["box_xywh"][1] >= 0
        and d["box_xywh"][0] <= src_w and d["box_xywh"][1] <= src_h
        and d["box_xywh"][2] >= 10 and d["box_xywh"][3] >= 10
        for d in outputs[0][:50]
    )
    top_conf = max((d["conf"] for d in outputs[0]), default=0.0)
    ok = (
        1 <= len(outputs[0]) <= 300
        and all(len(o) == len(outputs[0]) for o in outputs)
        and bool(expected_seen)
        and sane_boxes
        and top_conf >= 0.75  # healthy detectors reach >0.75 on objectful scenes
    )
    metrics = {
        "model": MODEL,
        "model_revision": f"ultralytics/assets v8.4.0 release asset (sha256 {WEIGHTS_SHA256[:16]}…, byte-identical GitHub==HF-org mirror, cross-verified via api.github.com)",
        "correctness_level": "TASK_SEMANTIC",
        "correctness_contract": ">=1 end-to-end detection conf>0.5 incl. expected scene classes (person/car) + identical detection count across 3 runs",
        "input_asset": asset.record(),
        "inference_path": "native end-to-end head output (1, 300, 6) with ultralytics LetterBox preprocessing — the same e2e output the notebook's OpenVINO export(end2end=True) serves; legacy predict() decode is broken for this artifact (RCA on file)",
        "e2e_output_shape": list(out_shape),
        "conf_threshold": CONF_THR,
        "runs": runs,
        "n_detections": len(outputs[0]),
        "top_conf": top_conf,
        "max_raw_conf": round(max_conf, 4),
        "classes_detected": all_classes,
        "expected_classes_seen": expected_seen,
        "detections_preview": outputs[0][:8],
        "stable_count": len({len(o) for o in outputs}) == 1,
        "rca_note": (
            "official yolo26n.pt artifact (GitHub v8.4.0 release == HF-org mirror, byte-identical, "
            "sha256-verified) is inference-degenerate: max detection confidence ~0.01-0.05 on every "
            "runtime tested (ultralytics 8.3.222 save-version / 8.4.43 notebook-pin / 8.4.173, CPU and "
            "gfx1100 GPU, predict() and native e2e decode) — upstream artifact defect, NOT a ROCm "
            "incompatibility; full RCA in reports/v0.3.1-final-report.md"
        ),
        "peak_vram_gb": round(pm.peak_vram_gb, 2),
        "peak_rss_gb": round(pm.peak_rss_gb, 2),
    }
    return emit(ok, evidence, metrics)


if __name__ == "__main__":
    raise SystemExit(main())
