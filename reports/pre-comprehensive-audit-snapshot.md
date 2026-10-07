# Pre-Comprehensive-Audit Snapshot (frozen baseline)

Generated: 2026-10-07 — immediately before the comprehensive verification &
quality closure. All numbers below were **recomputed from raw data**
(`catalog/notebooks.yaml`, `catalog/compatibility.json`,
`results/marathon-state.json`, `workloads/*/workload.yaml`), not copied from
documentation.

## Identity

| Item | Value |
|---|---|
| `main` base SHA | `0f59781d97b3d10fa2e48cce3bf8845fb8ecec67` |
| Latest tag | `v0.2.1` (no GitHub Release objects exist yet) |
| Upstream pin | `329562e6031d1a989017d08697b0fabe5a989492` (`openvinotoolkit/openvino_notebooks` branch `latest`, 2026-10-05T16:50:18Z) |
| Upstream `latest` at snapshot time | `faf88d73c65671cf34b0813ae44ff28f852508d1` (2026-10-06T19:33:31Z) — upstream has moved; see `reports/current-upstream-delta.md` |

## Dataset (recomputed, all four mirrors agree)

```text
Total: 171

CPU:
VERIFIED: 25
VERIFIED_WITH_LIMITATIONS: 58
FAILED: 87
NOT_APPLICABLE: 1
attempted: 171 / 171  (100.0%)

GPU:
VERIFIED: 8
NOT_TESTED: 163

Twins:
WORKLOAD_TWIN: 160
OPENVINO_SPECIFIC: 10
CONCEPT_MAPPING: 1
```

## Failure-category distribution of the 87 FAILED rows (raw execution taxonomy)

```text
TIMEOUT: 20
DEPENDENCY: 17
UNKNOWN: 14
PACKAGE_CONFLICT: 11
MODEL_ACCESS: 8
OPENVINO_ERROR: 7
NETWORK: 6
CORRECTNESS_ERROR: 2
CONVERSION_ERROR: 1
LICENSE_RESTRICTION: 1
```

These are **execution** categories, not compatibility verdicts. This closure
introduces a separate `compatibility_outcome` dimension (BLOCKED_NETWORK /
BLOCKED_MODEL_ACCESS / BLOCKED_DEPENDENCY / BLOCKED_TIMEOUT / BLOCKED_RESOURCE /
FAILED_COMPATIBILITY) so external blockers are never presented as AMD/OpenVINO
compatibility failures.

## Platform attribution of existing evidence

All 171 attempt records carry `platform_id=ryzen-ai-max-395-radeon-8060s-gfx1151`
(primary validation runner). This closure re-audits evidence chains; any fresh
execution performed during the closure records the actual platform it ran on.
