# Validation Policy

## What "VERIFIED" means

A workload is `VERIFIED` on a device path only when **all** of the following
are true, with evidence on disk:

1. environment success (venv, deps, OpenVINO runtime present)
2. model acquisition success (or no model needed)
3. conversion success where relevant
4. load success
5. inference success
6. correctness checks pass (workload-specific, see below)
7. repeatability: ≥3 successful runs for small/medium workloads
   (large/huge workloads: 1 run → `VERIFIED_WITH_LIMITATIONS` by policy D5)
8. benchmark metrics captured
9. evidence directory complete

## Statuses

`NOT_TESTED`, `QUEUED`, `RUNNING`, `VERIFIED`, `VERIFIED_WITH_LIMITATIONS`,
`FAILED`, `BLOCKED`, `SKIPPED_RESOURCE`, `REVALIDATION_REQUIRED`,
`NOT_APPLICABLE` — with a machine-checked transition table
(`ov_amd/schemas.py:STATUS_TRANSITIONS`).

## Failure categories

Every failure carries one of: NETWORK, DOWNLOAD, DEPENDENCY, PYTHON_VERSION,
PACKAGE_CONFLICT, MODEL_ACCESS, LICENSE_RESTRICTION, UPSTREAM_BUG,
OPENVINO_ERROR, CONVERSION_ERROR, INFERENCE_ERROR, CORRECTNESS_ERROR, OOM,
RAM_LIMIT, VRAM_LIMIT, DISK_LIMIT, TIMEOUT, ROCM_UNAVAILABLE, ROCM_UNSUPPORTED,
GPU_ARCH, INTERACTIVE_ONLY, EXTERNAL_SERVICE, UNKNOWN.

## Retries (bounded)

- network/download: up to 3 attempts
- package install: up to 2 remediation attempts
- model conversion / inference: up to 2 remediation attempts
- OOM: 1 reasonable lower-memory retry
- timeout: 1 reduced-workload retry
- unknown: 1 diagnostic retry

After bounded retries: record and move on. Failures are grouped by root cause
after the first sweep and re-run once shared fixes land.

## Correctness by workload type

| Type | Checks |
|---|---|
| Classification | output shape / top prediction / tolerances where useful |
| Detection | valid boxes, classes, confidence sanity |
| Embedding | shape, finite values, cosine similarity between implementations |
| LLM | deterministic settings where possible, finite logits, valid generation |
| VLM | output sanity on a stable prompt |
| OCR | expected extracted text, CER/edit distance where practical |
| ASR | transcription content, WER/CER where practical |
| TTS | waveform finite, expected sample rate, nonzero duration, RTF — no cross-implementation waveform equality |
| Image generation | finite tensor/image, dimensions, stable seed — no universal pixel equality |

Checks are declared in `workloads/<id>/workload.yaml` under `validation:` and
evaluated against executed notebook outputs by `ov_amd.correctness.evaluate`.

## Interactive notebooks

UI-only cells (Gradio/webcam/widgets) are skipped via documented patches and
the result is demoted to `VERIFIED_WITH_LIMITATIONS` with
`CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED`. We never claim UI testing
that did not happen.

## GPU validity

A ROCm twin is only VERIFIED when executed with `torch.version.hip != None`
on a detected AMD GPU; the twin script asserts and reports this itself
(`TWIN_RESULT=… "hip": "x.y"`).

## Honesty rules

- No fabricated numbers, statuses, hardware, or commit IDs — ever.
- Inference is never reported as execution.
- Unexecuted things stay `NOT_TESTED` / `SKIPPED_RESOURCE` / `BLOCKED` /
  `NOT_APPLICABLE` with a recorded reason.
