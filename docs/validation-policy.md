# Validation Policy

## Evidence Schema v2 (v0.2)

Every v0.2 evidence file carries `schema_version: 2`. An attempt directory
contains `hardware.json`, `software-before.json` / `software-after.json`
(collected from the actual workload python, before/after in-notebook
`%pip install`), `upstream.json`, `model.json`, `validation.json`,
`metrics.json`, `aggregate.json`, `device-proof.json`, `summary.md`, and
`run-NN/` subdirectories with `execution.json`, `device-proof.jsonl`,
`stdout.log`, `stderr.log`, `executed.ipynb`.

Environments are isolated per workload (`.venvs/<backend>/<env-key>/`, keyed
by backend + python + pinned upstream commit + dependency fingerprint), so one
notebook's `%pip install` can never contaminate another's validation.

## Validation levels (separate from status)

- **L1 `EXECUTION_ONLY`** — notebook completed without unhandled error. Never
  sufficient for `VERIFIED`.
- **L2 `DEVICE_VERIFIED`** — inference positively proven on the requested
  device (runtime `EXECUTION_DEVICES` property, else the explicit
  `compile_model` device argument; captured by a transparent kernel-side
  probe into `device-proof.jsonl`).
- **L3 `WORKLOAD_CORRECTNESS`** — device verified **and** the workload's
  declared correctness contract passed.

Device-proof states: `PROVEN_CPU` / `PROVEN_GPU` / `PROVEN_NPU`,
`NOT_INFERENCE` (no compile in the notebook), `AUTO_UNRESOLVED`, `UNKNOWN`.
Widget text scans are supporting evidence only — never positive proof.

## What "VERIFIED" means

A workload is `VERIFIED` on a device path only when **all** of the following
are true, with v2 evidence on disk:

1. workload environment built/resolved by fingerprint (isolated per workload)
2. model acquisition success (or no model needed)
3. conversion success where relevant; load success; inference success
4. **positive device proof: `PROVEN_CPU` for the CPU path**
   (`PROVEN_GPU` + HIP proof for the GPU path)
5. **validation level L3**: a declared correctness contract exists and passed
   — `validation: {}` stays `EXECUTION_ONLY` and can never render green
6. repeatability: ≥3 successful runs for small/medium workloads
   (large/huge: 1 run → `VERIFIED_WITH_LIMITATIONS`,
   `repeatability_not_established`, by policy D5)
7. benchmark metrics captured; aggregate.json reconciles with run-NN dirs
8. evidence directory complete under schema v2

Anything green-but-lesser degrades honestly to `VERIFIED_WITH_LIMITATIONS`
with explicit machine-readable limitation notes (EXECUTION_ONLY,
DEVICE_PROOF_INCOMPLETE, DEVICE_PROOF_NOT_APPLICABLE, repeatability,
interactive-UI skip).

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
(`TWIN_RESULT=… "hip": "x.y"`), and the v2 record carries `device-proof.json`
with `PROVEN_GPU`. GPU identity comes from authoritative sources (rocminfo /
torch device properties); the GFX architecture is never inferred from CUDA
capability numbers — if it cannot be programmatically confirmed it is left
unknown.

## Honesty rules

- No fabricated numbers, statuses, hardware, or commit IDs — ever.
- Inference is never reported as execution.
- Unexecuted things stay `NOT_TESTED` / `SKIPPED_RESOURCE` / `BLOCKED` /
  `NOT_APPLICABLE` with a recorded reason.
- Attempted ≠ catalogued: reports count real attempt records only
  (`cpu_attempted`, coverage %), never the default NOT_TESTED rows.
- Historical evidence is immutable: legacy v0.1 greens carry
  `historical_status` + `historical_evidence` and are
  `REVALIDATION_REQUIRED` until revalidated under schema v2.
