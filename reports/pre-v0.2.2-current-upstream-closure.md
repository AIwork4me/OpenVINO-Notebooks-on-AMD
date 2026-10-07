# Pre-v0.2.2 Current-Upstream Closure — Baseline Record

Recorded before any upstream pin change. Historical evidence is preserved untouched;
this file exists so the new release can never be made to look better by rewriting the past.

## Repository baseline (2026-10-07T14:2xZ)

```text
main HEAD:            bf9f74f (docs: regenerate artifacts on main post-merge)
branch:               main (clean working tree)
tags:                 v0.1-validation-baseline, v0.2.0, v0.2.1
upstream pin:         329562e6031d1a989017d08697b0fabe5a989492 (2026-10-05T16:50:18Z)
catalog total:        171
CPU attempted:        171 / 171 (100.0% catalog coverage)
CPU outcomes:         25 VERIFIED · 60 VERIFIED_WITH_LIMITATIONS · 80 BLOCKED · 5 FAILED_COMPATIBILITY · 1 NOT_APPLICABLE
GPU (ROCm twins):     8 VERIFIED (attempted 8/171)
twin classification:  171/171 — 160 WORKLOAD_TWIN · 10 OPENVINO_SPECIFIC · 1 CONCEPT_MAPPING
tests:                214 passed (pytest), ruff clean
```

## 5 FAILED_COMPATIBILITY rows on the old pin

```text
ct-segmentation-quantize-nncf   KERNEL_DEATH_UNDIAGNOSED   device proof AUTO_UNRESOLVED
gpu-device                      OPENVINO_RUNTIME_DEVICE_ENUM device proof AUTO_UNRESOLVED
openvino-tokenizers             OPENVINO_RUNTIME            device proof PROVEN_CPU
parler-tts-text-to-speech       OPENVINO_RUNTIME            device proof PROVEN_CPU
qwen3                           OPENVINO_RUNTIME_CL_MAP     device proof PROVEN_GPU   ← semantic defect: GPU-plugin failure recorded as CPU compatibility failure
```

## CI baseline

```text
hosted ci (main):                 success (run 37634604062, 2026-10-07T14:11Z)
amd-cpu-validation (self-hosted): success (run 37563821402, 2h43m, 2026-10-07T02:49Z)
amd-rocm-validation (self-hosted): success (run 37440954714, 6m29s, 2026-10-06T09:08Z)
ingest-validation-evidence:       failure (runs 37630021723 / 37628494427) — self-hosted
                                  runner github.com git-egress outage; known limitation,
                                  recorded in reports/ (6 dispatches, piecewise proof)
```

## True current upstream (queried at execution time)

```text
openvinotoolkit/openvino_notebooks @ latest:
  5f0b2b5f63fd84e91f5c4e87f9bf9d13141a1e9b (2026-10-07T12:14:36Z)
  "[Dependencies] Update selector dependencies to the latest compatible version (#3721)"

pin 329562e → 5f0b2b5: ahead_by = 10 commits, 21 files (2 notebooks added,
3 notebooks modified, 2 shared helpers modified, rest CI/selector/docs/tests).
Full classified delta: reports/v0.2.2-upstream-delta.md
```

## Non-goals for this closure

- No redesign of Evidence Schema v2, marathon runner, outcome taxonomy, or CI topologies.
- No modification of historical evidence directories or pre-v0.2.2 status records.
- No hardcoded catalog counts (171/173 never appear as literals in generation code).
