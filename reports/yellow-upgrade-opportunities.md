# Yellow Upgrade Opportunities (generated)

Generated: 2026-10-07T09:30:06+00:00

Limitation-code distribution and the evidence-supported upgrade path per group. Upgrades are applied
only when existing evidence already satisfies the VERIFIED policy (see reclassify_outcomes.py).

| Limitation codes | Rows | Upgrade path |
|---|---|---|
| REPEATABILITY_NOT_ESTABLISHED | 13 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) |
| REPEATABILITY_NOT_ESTABLISHED+INTERACTIVE_UI_NOT_TESTED | 11 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) + inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) |
| REPEATABILITY_NOT_ESTABLISHED+INTERACTIVE_UI_NOT_TESTED+EXECUTION_ONLY | 8 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) + inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) + author a workload-correctness contract (preset or custom) and re-run; all 27 rows also lack repeatability, so a rerun is required regardless |
| REPEATABILITY_NOT_ESTABLISHED+EXECUTION_ONLY | 8 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) + author a workload-correctness contract (preset or custom) and re-run; all 27 rows also lack repeatability, so a rerun is required regardless |
| INTERACTIVE_UI_NOT_TESTED | 7 | inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) |
| INTERACTIVE_UI_NOT_TESTED+EXECUTION_ONLY | 7 | inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) + author a workload-correctness contract (preset or custom) and re-run; all 27 rows also lack repeatability, so a rerun is required regardless |
| REPEATABILITY_NOT_ESTABLISHED+INTERACTIVE_UI_NOT_TESTED+EXECUTION_ONLY+DEVICE_PROOF_INCOMPLETE | 2 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) + inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) + author a workload-correctness contract (preset or custom) and re-run; all 27 rows also lack repeatability, so a rerun is required regardless + rerun with the current probe (genai pipeline events now captured); auto-device is inherently AUTO_UNRESOLVED by design |
| INTERACTIVE_UI_NOT_TESTED+EXECUTION_ONLY+DEVICE_PROOF_INCOMPLETE | 2 | inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) + author a workload-correctness contract (preset or custom) and re-run; all 27 rows also lack repeatability, so a rerun is required regardless + rerun with the current probe (genai pipeline events now captured); auto-device is inherently AUTO_UNRESOLVED by design |
| REPEATABILITY_NOT_ESTABLISHED+INTERACTIVE_UI_NOT_TESTED+DEVICE_PROOF_INCOMPLETE | 1 | needs 2 additional successful runs on the reference Ryzen runner (resource-bounded single-run policy for large/huge tiers) + inherent to headless policy; upgrade only if UI tail is removable upstream (stop_after/skip refinement) + rerun with the current probe (genai pipeline events now captured); auto-device is inherently AUTO_UNRESOLVED by design |
| DEVICE_PROOF_INCOMPLETE | 1 | rerun with the current probe (genai pipeline events now captured); auto-device is inherently AUTO_UNRESOLVED by design |

## Rows needing only a reference-runner rerun (no contract authoring needed)

- **INTERACTIVE_UI_NOT_TESTED**: ace-step-music-generation, deepseek-r1, florence2, kokoro, fast-segment-anything, oneformer-segmentation, surya-line-level-text-detection
- **DEVICE_PROOF_INCOMPLETE**: auto-device

## Constraint discovered during this closure

The comprehensive-verification environment runs on AMD EPYC 9334, not the reference Ryzen AI Max 395
runner that produced the dataset. Re-running green/yellow rows here would silently change platform
attribution of the evidence, so upgrades that require new runs are queued for the reference runner
instead of being executed on different hardware. Evidence-chain audits, captured-output contract
re-evaluation, and two contract corrections (person-counting, stable-video-diffusion) were completed
without new runs.
