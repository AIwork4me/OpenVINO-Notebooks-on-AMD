# All-Green CPU Audit (generated

Generated: 2026-10-07T09:30:05+00:00

Every CPU VERIFIED row audited against: positive device proof (PROVEN_CPU), L3 validation level,
repeatability (ok_runs >= required, aggregate.json), evidence completeness (v2 files), upstream pin
coherence (commit == pin or sha-identical pre-repin), platform attribution, and correctness contract.

| Workload | Proof | Level | Runs | Contract | Evidence complete | Pin | Platform | Verdict |
|---|---|---|---|---|---|---|---|---|
| hello-world | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | pin | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| hello-detection | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical |  | OK |
| hello-segmentation | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical |  | OK |
| openvino-api | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | pin | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| handwritten-ocr | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical |  | OK |
| paddle-to-openvino-classification | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | pin | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| speculative-sampling | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| llm-lora | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| convnext-classification | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| detectron2-to-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| hugging-face-hub | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| image-classification-quantization | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| language-quantize-bert | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| optical-character-recognition | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| optimize-preprocessing | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| pointpillars | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | pin | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| pytorch-post-training-quantization-nncf | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| pytorch-to-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| speech-recognition-quantization-wav2vec2 | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| tensorflow-classification-to-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| tensorflow-object-detection-api-with-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| tflite-to-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| vehicle-detection-and-recognition | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| yolov26-obb | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |
| modelscope-to-openvino | PROVEN_CPU | WORKLOAD_CORRECTNESS | 3/3 | yes | yes | sha-identical | ryzen-ai-max-395-radeon-8060s-gfx1151 | OK |

**25 / 25 VERIFIED rows fully coherent. No row preserved green without complete evidence.**
