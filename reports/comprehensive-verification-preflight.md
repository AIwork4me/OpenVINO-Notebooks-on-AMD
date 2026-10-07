# Comprehensive Verification — Preflight

Generated: 2026-10-07 (start of comprehensive verification & quality closure)

## Repository

| Item | Value |
|---|---|
| Remote | `github.com/AIwork4me/OpenVINO-Notebooks-on-AMD` (pushed via a site git mirror; the public canonical URL is the github.com one) |
| `main` HEAD | `0f59781d97b3d10fa2e48cce3bf8845fb8ecec67` |
| Latest tags | `v0.2.1`, `v0.2.0`, `v0.1-validation-baseline` |
| GitHub Releases | none exist yet (tags only) |
| Work branch | `codex/comprehensive-verification-quality-closure` |
| Working tree | clean at start |

## Upstream pin (recomputed from data, not docs)

| Item | Value |
|---|---|
| Pinned commit | `329562e6031d1a989017d08697b0fabe5a989492` (2026-10-05T16:50:18Z) |
| Consistent in | `catalog/notebooks.yaml`, `catalog/compatibility.json`, `results/marathon-state.json`, `upstream/openvino-notebooks.json`, `workloads/*/workload.yaml` |
| Upstream `latest` now | `faf88d73c65671cf34b0813ae44ff28f852508d1` (2026-10-06T19:33:31Z) — **upstream moved; delta analysis required** |

## Counts (independently recomputed from all four mirrors)

Sources cross-checked: `catalog/notebooks.yaml`, `catalog/compatibility.json`,
`results/marathon-state.json`, `workloads/*/workload.yaml`.

- Catalog entries: **171** (no duplicates; ID sets identical across catalog, compat rows, state attempts, workload manifests)
- CPU attempts recorded: **171/171 (100.0%)**

| CPU status | Count |
|---|---|
| VERIFIED | 25 |
| VERIFIED_WITH_LIMITATIONS | 58 |
| FAILED | 87 |
| NOT_APPLICABLE | 1 |

| GPU status | Count |
|---|---|
| VERIFIED | 8 |
| NOT_TESTED | 163 |

| Twin level | Count |
|---|---|
| WORKLOAD_TWIN | 160 |
| OPENVINO_SPECIFIC | 10 |
| CONCEPT_MAPPING | 1 |

All mirrors agree; no orphan rows, no missing manifests.

## GitHub Actions history (actual, via API)

| Workflow | Runs | Latest outcome |
|---|---|---|
| `ci` (hosted) | 21 | success on `main` @ 2026-10-07T07:02Z |
| `amd-cpu-validation` (self-hosted) | 3 | **success** on `main` @ 2026-10-07T02:49Z (run #3) |
| `amd-rocm-validation` (self-hosted) | 4 | **success** on branch @ 2026-10-06T09:08Z (run #4) |
| `ingest-validation-evidence` | 2 | #1 failure, #2 cancelled — **must be proven operational this closure** |

## Environment (reused, not rebuilt)

- Per-workload venvs under `.venvs/` (fingerprinted), GPU env `.venv-gpu/`
- Evidence trees under `results/<id>/<ts>-<backend>/`
- Upstream snapshot cache `.cache/upstream` (572 files, sha1-verified)
- Marathon state `results/marathon-state.json` (171 attempts, resumable)

## Preflight verdict

Baseline dataset is internally consistent. Upstream has moved past the pin
(impact analysis in `reports/current-upstream-delta.md`). Ingest workflow lacks
a green run. Proceeding to freeze snapshot and independent dataset audit.
