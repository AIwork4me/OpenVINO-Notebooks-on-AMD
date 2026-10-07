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
(`ov_amd/schemas.py:STATUS_TRANSITIONS`) that is **mechanically enforced at
every write** (`ov_amd/state_machine.py` raises `InvalidStateTransition`;
state surgery must pass `force=True` explicitly).

## Compatibility outcomes (developer-facing, separate dimension)

Execution status records what the runner observed; the compatibility outcome
records what a developer should conclude. Every terminal attempt carries both
(`compatibility_outcome` + machine-readable `outcome_reason` in
`results/marathon-state.json` and in the generated matrix):

| Outcome | Meaning | Icon |
|---|---|---|
| `VERIFIED` / `VERIFIED_WITH_LIMITATIONS` | mirrors the execution status | ✅ / 🟡 |
| `BLOCKED_NETWORK` | host unreachable / transport failure | 🌐 |
| `BLOCKED_MODEL_ACCESS` | gated or restricted model repo, missing token | 🔐 |
| `BLOCKED_DEPENDENCY` | missing package/CLI, resolver conflict, library API drift | 📦 |
| `BLOCKED_TIMEOUT` | wall/cell timeout, stage-aware reason (`TIMEOUT_CONVERSION_EXPORT`, `TIMEOUT_MODEL_DOWNLOAD`, …) | ⏱️ |
| `BLOCKED_RESOURCE` | OOM/RAM/disk, absent required hardware, corrupt or incomplete model artifact | 💾 |
| `FAILED_COMPATIBILITY` | valid environment, real runtime/model execution failure (OpenVINO plugin rejection, conversion/runtime incompatibility, correctness failure) | 🧩 |
| `NOT_APPLICABLE` | no executable content or no useful path for this backend | ➖ |

Rules (enforced by `ov_amd/outcomes.py`, audited by
`tests/test_outcomes.py`):

- A network timeout, gated model, missing CLI, or truncated download is **never**
  presented as an AMD/OpenVINO compatibility failure.
- Root-cause-first: specific error signatures in evidence logs outrank the
  coarse log-classifier category when they conflict (misclassifications are
  corrected, with a note preserving the original label).
- `FAILED_COMPATIBILITY` requires evidence tying the failure to runtime/model
  execution in a valid environment; each carries a root-cause record under
  `reports/upstream/` when genuine.
- No row may keep outcome reason `UNKNOWN_ADJUDICATION_REQUIRED` — the dataset
  test fails if any does.

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

## Device attribution (v0.2.2)

Three execution paths exist and are never conflated:

```text
OpenVINO CPU plugin  on AMD Ryzen    -> the CPU matrix
OpenVINO GPU plugin  on AMD Radeon   -> device-specific findings (reports/openvino-gpu-plugin-radeon-findings.md)
ROCm / PyTorch       on AMD Radeon   -> ROCm twins (gpu_* columns)
```

- A cpu-backend attempt whose device proof is `PROVEN_GPU` can never yield an
  AMD CPU compatibility verdict: the outcome guard in `ov_amd/outcomes.py`
  maps such failures to `NOT_TESTED` + `DEVICE_ATTRIBUTION_INVALID_GPU_PLUGIN`
  and requires CPU-forced revalidation (documented minimal `cell_subs` pins
  for notebooks that hardcode `device = "GPU"`).
- OpenVINO GPU-plugin-on-Radeon behavior (e.g. `clEnqueueMapBuffer
  CL_INVALID_VALUE` on gfx1151) is recorded as a separate device-specific
  finding with its own evidence links — it is neither a CPU result nor a ROCm
  result.
- GPU-purpose notebooks (e.g. `gpu-device`, which hardcodes `device = "GPU"`
  for its property walkthrough) adjudicate to `NOT_APPLICABLE` on the CPU
  dimension with a provenance note; the GPU-plugin behavior they exercise is
  captured in the findings report instead.

## Upstream freshness (v0.2.2)

The pin is a commit, never a moving branch. `scripts/check_upstream_freshness.py`
(networked, run as its own workflow) compares the pin against upstream `latest`
and records `reports/upstream-freshness.json`; README generation renders that
committed record (`CURRENT` / `UPSTREAM AHEAD BY N COMMITS`) without network.
When upstream is ahead, changed-notebook scopes are marked
`REVALIDATION_REQUIRED` with provenance — historical statuses are never
silently rewritten.

## Honesty rules

- No fabricated numbers, statuses, hardware, or commit IDs — ever.
- Inference is never reported as execution.
- Unexecuted things stay `NOT_TESTED` / `SKIPPED_RESOURCE` / `BLOCKED` /
  `NOT_APPLICABLE` with a recorded reason.
- Attempted ≠ catalogued: reports count real attempt records only
  (`cpu_attempted`, coverage %), never the default NOT_TESTED rows.
- **Catalog coverage ≠ pass rate**: 173/173 coverage means every catalogued
  notebook has an AMD CPU validation outcome; verified/limited/blocked/
  compatibility-failure counts are always reported alongside, and the README
  states the distinction explicitly.
- Historical evidence is immutable: legacy v0.1 greens carry
  `historical_status` + `historical_evidence` and are
  `REVALIDATION_REQUIRED` until revalidated under schema v2.
- Evidence is validated at the recorded upstream pin; a pin move marks changed
  notebooks for revalidation (see `reports/v0.2.2-upstream-delta.md (current) and reports/current-upstream-delta.md (pre-repin historical record)`) —
  rows are never invalidated retroactively while the pin is unchanged.
