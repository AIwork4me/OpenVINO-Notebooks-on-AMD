# OpenVINO Notebooks on AMD

[![CI](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml/badge.svg)](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Validation Schema](https://img.shields.io/badge/evidence_schema-v2-informational)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

> **Validate and run OpenVINO Notebooks on AMD Ryzen CPUs, with matching ROCm-powered references for AMD Radeon GPUs.**

> **One AI workload. Two AMD paths.**

This is **an AMD validation and ROCm companion project for [OpenVINO Notebooks](https://github.com/openvinotoolkit/openvino_notebooks)** — not a fork. Upstream notebooks are executed unmodified (or with documented, minimal patches) at a pinned upstream commit, on real AMD hardware, with machine-generated evidence for every claim.

```text
                 AI Workload
                      |
            +---------+---------+
            |                   |
      AMD Ryzen CPU       AMD Radeon GPU
            |                   |
         OpenVINO             ROCm
            |                   |
      CPU Evidence        GPU Evidence
            |                   |
            +---------+---------+
                      |
             Compatibility Map
```

The two paths validate the same *workload* through different runtimes — they are
independent evidence chains, not identical model implementations.

<!-- generated:compatibility begin -->
**AMD Ryzen CPU / OpenVINO**

### 174 / 174 — 100.0% Catalog Coverage

> **Coverage means every notebook in the pinned snapshot has a recorded AMD CPU validation outcome. It does NOT mean every notebook passed.**

Outcome totals: ✅ 25 Verified · 🟡 63 Verified with limitations · 🚧 83 Blocked (network / model access / dependency / timeout / resource) · 🧩 1 Compatibility failures · ➖ 2 Not applicable

Successful executions: **88/172** of eligible notebooks (51.2%; 2 N/A excluded) — ✅ 25 verified · 🟡 63 with documented limitations.

**AMD Radeon GPU / ROCm · PyTorch**

### 20 verified high-value workload references

A growing, deliberately-curated set — explicitly **not** a catalog-wide sweep (attempted 22/174). The two numbers above have different denominators and different meanings.

Pinned snapshot `3c3899e68b22` · freshness: **CURRENT** (verified 2026-10-08) · Evidence Schema **v2** · twin classification **174/174** (100.0%)

Full matrix: [catalog/compatibility.md](catalog/compatibility.md) · Methodology: [docs/validation-policy.md](docs/validation-policy.md) · [benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md)
<!-- generated:compatibility end -->

### What "100% coverage" means — and what it does not

```text
100% catalog coverage  ≠  100% pass rate
```

### Two AMD paths, two coverage models

| Path | Coverage model |
|---|---|
| **AMD Ryzen CPU (OpenVINO)** | 100% catalog coverage — every pinned notebook has a recorded outcome (verified / limited / blocked / compatibility-failure / N-A) |
| **AMD Radeon GPU (ROCm)** | A growing set of verified high-value workload references — explicitly **not** a 100% sweep |

The CPU and GPU columns never mix: OpenVINO CPU on Ryzen, ROCm/PyTorch on Radeon are distinct execution paths with separate evidence.

### ROCm-Verified Workloads — Independent AMD CPU Results

<!-- generated:featured begin -->
This table intentionally selects workloads **verified on AMD Radeon GPUs using ROCm**. The **Ryzen CPU column reports independent OpenVINO validation results** for the same workload — CPU results may be Verified, Limited, or Blocked. A blocked result is not necessarily an AMD CPU compatibility failure. Each status links to its own evidence.

| Workload | Ryzen CPU · OpenVINO | Radeon GPU · ROCm | Twin type |
|---|---|---|---|
| [deepseek-ocr](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/deepseek-ocr/deepseek-ocr.ipynb) | 🟡 Limited ([evidence](results/deepseek-ocr/20261006T100046Z-cpu)) | ✅ Verified ([evidence](results/deepseek-ocr/20261008T184205Z-gpu)) | WORKLOAD_TWIN |
| [deepseek-r1](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/deepseek-r1/deepseek-r1.ipynb) | 🟡 Limited ([evidence](results/deepseek-r1/20261007T010259Z-cpu)) | ✅ Verified ([evidence](results/deepseek-r1/20261007T010103Z-gpu)) | WORKLOAD_TWIN |
| [florence2](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/florence2/florence2.ipynb) | 🟡 Limited ([evidence](results/florence2/20261007T011006Z-cpu)) | ✅ Verified ([evidence](results/florence2/20261008T184150Z-gpu)) | WORKLOAD_TWIN |
| [glm-ocr](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/glm-ocr/glm-ocr.ipynb) | 🌐 Network blocked ([evidence](results/glm-ocr/20261007231614Z-cpu)) | ✅ Verified ([evidence](results/glm-ocr/20261008T032829Z-gpu)) | WORKLOAD_TWIN |
| [hello-detection](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/hello-detection/hello-detection.ipynb) | ✅ Verified ([evidence](results/hello-detection/20261005T194339Z-cpu)) | ✅ Verified ([evidence](results/hello-detection/20261007T035733Z-gpu)) | WORKLOAD_TWIN |
| [kokoro](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/kokoro/kokoro.ipynb) | 🟡 Limited ([evidence](results/kokoro/20261007225919Z-cpu)) | ✅ Verified ([evidence](results/kokoro/20261007T230834Z-gpu)) | WORKLOAD_TWIN |
| [minicpm-v-4.6](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/minicpm-v-4.6/minicpm-v-4.6.ipynb) | 🟡 Limited ([evidence](results/minicpm-v-4.6/20261006T172150Z-cpu)) | ✅ Verified ([evidence](results/minicpm-v-4.6/20261008T101436Z-gpu)) | WORKLOAD_TWIN |
| [paddleocr_vl](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/paddleocr_vl/paddleocr_vl.ipynb) | 📦 Dependency blocked ([evidence](results/paddleocr_vl/20261006T123520Z-cpu)) | ✅ Verified ([evidence](results/paddleocr_vl/20261008T063244Z-gpu)) | WORKLOAD_TWIN |
| [qwen3](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/supplementary_materials/notebooks/qwen-3/qwen3.ipynb) | 🟡 Limited ([evidence](results/qwen3/20261007172217Z-cpu)) | ✅ Verified ([evidence](results/qwen3/20261007T005803Z-gpu)) | WORKLOAD_TWIN |
| [qwen3-asr](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/qwen3-asr/qwen3-asr.ipynb) | 📦 Dependency blocked ([evidence](results/qwen3-asr/20261006T161620Z-cpu)) | ✅ Verified ([evidence](results/qwen3-asr/20261008T092400Z-gpu)) | WORKLOAD_TWIN |
| [qwen3-embedding](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/qwen3-embedding/qwen3-embedding.ipynb) | 🟡 Limited ([evidence](results/qwen3-embedding/20261006T183935Z-cpu)) | ✅ Verified ([evidence](results/qwen3-embedding/20261008T045854Z-gpu)) | WORKLOAD_TWIN |
| [qwen3-reranker](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/qwen3-embedding/qwen3-reranker.ipynb) | 🟡 Limited ([evidence](results/qwen3-reranker/20261006T184204Z-cpu)) | ✅ Verified ([evidence](results/qwen3-reranker/20261008T032329Z-gpu)) | WORKLOAD_TWIN |
| [qwen3-tts](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/qwen3-tts/qwen3-tts.ipynb) | 🟡 Limited ([evidence](results/qwen3-tts/20261006T161913Z-cpu)) | ✅ Verified ([evidence](results/qwen3-tts/20261008T184029Z-gpu)) | WORKLOAD_TWIN |
| [qwen3-vl-embedding](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/qwen3-vl-embedding/qwen3-vl-embedding.ipynb) | 🟡 Limited ([evidence](results/qwen3-vl-embedding/20261006T184356Z-cpu)) | ✅ Verified ([evidence](results/qwen3-vl-embedding/20261008T182526Z-gpu)) | WORKLOAD_TWIN |
| [smoldocling](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/smoldocling/smoldocling.ipynb) | 🟡 Limited ([evidence](results/smoldocling/20261006T133210Z-cpu)) | ✅ Verified ([evidence](results/smoldocling/20261008T032635Z-gpu)) | WORKLOAD_TWIN |
| [smolvlm2](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/smolvlm2/smolvlm2.ipynb) | 🟡 Limited ([evidence](results/smolvlm2/20261007T013703Z-cpu)) | ✅ Verified ([evidence](results/smolvlm2/20261007T005844Z-gpu)) | WORKLOAD_TWIN |
| [stable-diffusion-text-to-image](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/stable-diffusion-text-to-image/stable-diffusion-text-to-image.ipynb) | ⏱ Timeout ([evidence](results/stable-diffusion-text-to-image/20261006T135916Z-cpu)) | ✅ Verified ([evidence](results/stable-diffusion-text-to-image/20261007T005940Z-gpu)) | WORKLOAD_TWIN |
| [stable-diffusion-xl](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/stable-diffusion-xl/stable-diffusion-xl.ipynb) | 💾 Resource blocked ([evidence](results/stable-diffusion-xl/20261008082930Z-cpu)) | ✅ Verified ([evidence](results/stable-diffusion-xl/20261007T010006Z-gpu)) | WORKLOAD_TWIN |
| [whisper-asr-genai](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/whisper-asr-genai/whisper-asr-genai.ipynb) | 🌐 Network blocked ([evidence](results/whisper-asr-genai/20261007230104Z-cpu)) | ✅ Verified ([evidence](results/whisper-asr-genai/20261007T230927Z-gpu)) | WORKLOAD_TWIN |
| [z-image-turbo](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/z-image-turbo/z-image-turbo.ipynb) | 📦 Dependency blocked ([evidence](results/z-image-turbo/20261006T211426Z-cpu)) | ✅ Verified ([evidence](results/z-image-turbo/20261008T063439Z-gpu)) | WORKLOAD_TWIN |
<!-- generated:featured end -->

#### High-value workload matrix (generated)

The table above lists every Radeon/ROCm-verified twin next to its independent Ryzen/OpenVINO outcome. The full generated matrix lives in [catalog/compatibility.md](catalog/compatibility.md).

### Verified on AMD Ryzen CPUs

<!-- generated:cpu-showcase begin -->
Selected AMD-Ryzen-VERIFIED notebooks (CPU results only — this table is **not** GPU-selected; every row passed its validation contract on OpenVINO/CPU):

| Workload | CPU status | Category | Evidence |
|---|---|---|---|
| [convnext-classification](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/torchvision-zoo-to-openvino/convnext-classification.ipynb) | ✅ Verified | Vision | [evidence](results/convnext-classification/20261006T192158Z-cpu) |
| [handwritten-ocr](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/handwritten-ocr/handwritten-ocr.ipynb) | ✅ Verified | OCR | [evidence](results/handwritten-ocr/20261005T194844Z-cpu) |
| [hello-detection](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/hello-detection/hello-detection.ipynb) | ✅ Verified | Vision | [evidence](results/hello-detection/20261005T194339Z-cpu) |
| [hello-segmentation](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/hello-segmentation/hello-segmentation.ipynb) | ✅ Verified | Vision | [evidence](results/hello-segmentation/20261005T194349Z-cpu) |
| [llm-lora](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/llm-lora/llm-lora.ipynb) | ✅ Verified | LLM | [evidence](results/llm-lora/20261006T152333Z-cpu) |
| [paddle-to-openvino-classification](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/paddle-to-openvino/paddle-to-openvino-classification.ipynb) | ✅ Verified | OCR | [evidence](results/paddle-to-openvino-classification/20261007T011308Z-cpu) |
| [pointpillars](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/3D-point-pillars/pointpillars.ipynb) | ✅ Verified | Vision | [evidence](results/pointpillars/20261007T013946Z-cpu) |
| [speculative-sampling](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/speculative-sampling/speculative-sampling.ipynb) | ✅ Verified | LLM | [evidence](results/speculative-sampling/20261006T134221Z-cpu) |
| [vehicle-detection-and-recognition](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/vehicle-detection-and-recognition/vehicle-detection-and-recognition.ipynb) | ✅ Verified | Vision | [evidence](results/vehicle-detection-and-recognition/20261006T210145Z-cpu) |
| [yolov26-obb](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/yolov26-optimization/yolov26-obb.ipynb) | ✅ Verified | Vision | [evidence](results/yolov26-obb/20261006T211201Z-cpu) |
| [detectron2-to-openvino](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/detectron2-to-openvino/detectron2-to-openvino.ipynb) | ✅ Verified | Conversion | [evidence](results/detectron2-to-openvino/20261006T192516Z-cpu) |
| [hello-world](https://github.com/openvinotoolkit/openvino_notebooks/blob/3c3899e68b2269bb7fbd5755554335f33acabd5e/notebooks/hello-world/hello-world.ipynb) | ✅ Verified | API | [evidence](results/hello-world/20261007T034828Z-cpu) |

…plus 13 more VERIFIED rows in the [full compatibility matrix](catalog/compatibility.md).
<!-- generated:cpu-showcase end -->

## Compatibility matrix

- Full generated matrix (every catalogued row, with outcome + validation level + reason + evidence link): [catalog/compatibility.md](catalog/compatibility.md)
- Live campaign progress: [reports/marathon-progress.md](reports/marathon-progress.md)
- Failure groups by outcome: [reports/failures.md](reports/failures.md)
- Full dataset audit: [reports/full-173-integrity-audit.md](reports/full-173-integrity-audit.md)

## Quick start

Verified from a clean checkout (uv ≥ 0.10):

```bash
git clone https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD.git
cd OpenVINO-Notebooks-on-AMD

uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]"

.venv-cpu/bin/python -m ov_amd doctor          # hardware/software/venv audit
.venv-cpu/bin/python -m ov_amd list            # catalog + statuses + coverage summary
.venv-cpu/bin/python -m ov_amd info hello-world
.venv-cpu/bin/python -m ov_amd run hello-world --device cpu
.venv-cpu/bin/python -m ov_amd compare hello-world
.venv-cpu/bin/python scripts/run_marathon.py   # unattended, resumable campaign
```

Notebook *execution* additionally needs the notebook stack (jupyter, openvino, torch-cpu) — see [docs/getting-started.md](docs/getting-started.md). The commands above verify the harness and catalog immediately.

## Status semantics (short form)

| Status | Meaning |
|---|---|
| **Verified** | The workload passed its declared validation contract |
| **Limited** | The workload ran with a documented limitation |
| **Blocked** | An external or setup condition prevented completion (network / gated model / dependency / timeout / resource) — **not** necessarily an AMD CPU incompatibility |
| **Compatibility failure** | A validated runtime/model incompatibility was reproduced on a valid environment |

Full state machine and evidence contract: [docs/validation-policy.md](docs/validation-policy.md).

## Status model (two dimensions)

The runner records what it observed; developers read what it means.

| Execution status (internal) | Compatibility outcome (developer-facing) | Icon |
|---|---|---|
| VERIFIED | VERIFIED | ✅ |
| VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | 🟡 |
| FAILED ← network/host | BLOCKED_NETWORK | 🌐 |
| FAILED ← gated/restricted model | BLOCKED_MODEL_ACCESS | 🔐 |
| FAILED ← missing package/CLI/drift | BLOCKED_DEPENDENCY | 📦 |
| FAILED ← wall/cell timeout | BLOCKED_TIMEOUT (stage-aware) | ⏱️ |
| FAILED/OOM/disk/artifact | BLOCKED_RESOURCE | 💾 |
| FAILED ← runtime/model execution | FAILED_COMPATIBILITY | 🧩 |
| NOT_TESTED (GPU twins pending) | NOT_TESTED | ⏳ |
| NOT_APPLICABLE | NOT_APPLICABLE | ➖ |

> **"Verified" means the workload was reproduced successfully on the hardware and software configuration documented by this project. It does not imply official hardware support or certification by the OpenVINO project, Intel, AMD, or the original model authors.**

## Methodology & evidence

Every row in the matrix is machine-generated from a resumable campaign checkpoint (`results/marathon-state.json`) — nothing is hand-entered. Each attempt produces an evidence directory (`results/<workload>/<ts>-<backend>/`) with hardware/software snapshots, upstream pin + notebook sha, device-proof probe events, repeatability aggregates, and validation contracts (Evidence Schema v2). Validation levels: L1 EXECUTION_ONLY → L3 WORKLOAD_CORRECTNESS; green requires L3 + positive `PROVEN_CPU`/`PROVEN_GPU` device proof + repeatability. ROCm twins additionally record model identity + revision, input-asset provenance (SHA-256-managed where applicable), correctness grading (SMOKE / STRUCTURAL / TASK_SEMANTIC / GROUND_TRUTH), and benchmark metric semantics (`metric_semantics` block). See [docs/validation-policy.md](docs/validation-policy.md), [docs/reproducibility.md](docs/reproducibility.md) and [benchmarks/METHODOLOGY.md](benchmarks/METHODOLOGY.md) (WORKLOAD_TWIN rows never carry CPU-vs-GPU speedup claims).

Validation runs on real AMD hardware through self-hosted workflows — [amd-cpu-validation](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/amd-cpu-validation.yml) (Ryzen, OpenVINO) and [amd-rocm-validation](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/amd-rocm-validation.yml) (Radeon, ROCm) — serialized on a shared concurrency group; evidence lands back in this repository via the [ingest workflow](https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/workflows/ingest-validation-evidence.yml).

## Repository layout

| Path | Content |
|---|---|
| `catalog/` | generated compatibility matrix (json + md) |
| `upstream/` | pinned upstream commit metadata |
| `assets/` | managed input fixtures (sha256 manifests; redistributable only) |
| `workloads/<id>/` | workload manifests, ROCm twin scripts, validation config |
| `results/<id>/<ts>-<backend>/` | evidence directories (hardware/software/execution/metrics/logs) |
| `results/marathon-state.json` | resumable campaign checkpoint (source of truth) |
| `ov_amd/` | validation harness + CLI (assets, freshness, reporting) |
| `scripts/` | discovery / marathon / cache / revalidation / audit entry points |
| `benchmarks/METHODOLOGY.md` | how numbers are measured |
| `reports/` | preflight, progress, failures, audits, final reports |
| `reports/upstream/` | root-cause analyses for genuine compatibility issues |

## Contributing & more hardware

Contributions welcome: new AMD CPU results (attach Evidence Schema v2 output), new AMD hardware reports, ROCm twins, failure reproductions, and upstream issue candidates. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/reproducibility.md](docs/reproducibility.md) for reproducing and submitting independently verified results. Every claimed result requires its evidence directory — no evidence, no row.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md). OpenVINO Notebooks retains its own copyright and license; model and dataset licenses remain independent and are never overridden by this repository's license.
