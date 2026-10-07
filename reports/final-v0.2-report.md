# OpenVINO Notebooks on AMD v0.2 Final Report

## Repository

```text
GitHub URL:    https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD
main commit:   ab7ce2daf22ad2c4cb29cc8828b4b1a2d0970c45
release tag:   v0.2.0
PR URL:        https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/pull/1
```

## Upstream

```text
old pinned commit:   a8809170cc4fc6aa633fbb9c22214be67ac20b47 (2026-09-30)
new current commit:  329562e6031d1a989017d08697b0fabe5a989492 (2026-10-05)
changed notebooks:   13 (10 had validation records → quarantined; 3 never
                     validated → stay NOT_TESTED, first-attempt under new pin)
snapshot integrity: 572/572 git-blobs, sha1-verified, zero failures
```

`latest` continued to advance during the sync window (observed `f19782b9`,
`f1958fc8`); the fetcher now requires an explicit `--commit` so evidence can
never bind to a moving target.

## Reference Hardware (two platforms, per-evidence attribution)

```text
primary:   AMD Ryzen AI Max+ PRO 395 (16C/32T) + Radeon 8060S (gfx1151)
           94 GiB shared RAM · Ubuntu 24.04 · kernel 6.17          — CPU marathon
secondary: AMD EPYC 9334 (128 threads) + Radeon gfx1100 dGPU
           503 GiB RAM · ROCm 7.2 userspace                        — ROCm twins
```

## Software

```text
Python   3.12.3 (reference validation Python; requires-python >=3.11)
OpenVINO 2026.4.x (CPU validation environments)
PyTorch  2.14.1+rocm7.14 (reference) / 2.9.1+hip7.2.53211 (secondary)
ROCm     7.2.x on both validation platforms
```

## Reliability Closure (defects A–K)

| Defect | Status | Evidence |
|---|---|---|
| A mirror substitution delimiter corruption | **FIXED** | ov_amd/substitution.py (structured rules, no delimiters) + tests/test_substitution.py |
| B shared mutable venv | **FIXED** | ov_amd/env_manager.py per-workload keyed venvs + tests/test_env_manager.py |
| C absolute evidence links | **FIXED** | state records repo-relative; matrix links `../results/...` (GitHub-resolvable); public artifacts scanned clean |
| D evidence from wrong python | **FIXED** | software-before/after bound to the workload interpreter; snapshot records python_bin |
| E empty device_used passes | **FIXED** | ev2 device-proof states; CPU VERIFIED requires PROVEN_CPU (probe uses EXECUTION_DEVICES runtime property) |
| F empty validation passes | **FIXED** | validation levels; `validation: {}` stays EXECUTION_ONLY, never green |
| G repeatability not aggregated | **FIXED** | aggregate.json (median + nearest-rank P95, successful/required); twin aggregator normalizes latency_s/total_s |
| H GPU evidence incomplete | **FIXED** | full v2 set for all GPU evidence incl. validation.json; tests/test_gpu_twin_evidence.py |
| I attempted = catalogued | **FIXED** | coverage percentages from real attempt records (133/171 = 77.8% CPU) |
| J twin classification incomplete | **FIXED** | 160 WORKLOAD_TWIN / 10 OPENVINO_SPECIFIC / 1 CONCEPT_MAPPING; NOT_CLASSIFIED = 0 |
| K self-hosted CI queued forever | **FIXED** | runner `ovamd-reference-runner` online; amd-cpu-validation SUCCESS; amd-rocm-validation SUCCESS (6m29s); shared concurrency group `amd-reference-validation`; schedule triggers removed until deliberate re-enable |

## Catalog

```text
total:                     171
classification coverage:   100% (NOT_CLASSIFIED = 0)
```

## CPU (OpenVINO on Ryzen — pinned baseline + re-pin quarantine)

```text
attempted:               133 / 171 (77.8%)
L3 VERIFIED:             4   (PROVEN_CPU + contract + 3-run repeatability)
limited (VWL):           35  (all with machine-readable limitation notes)
failed:                  83  (root causes clustered: 83 → 32 clusters,
                             compat vs environment separated in
                             reports/marathon-v2-root-causes.md)
blocked / resource skip: 0
revalidation required:   10  (upstream re-pin migration set, deferred with
                             explicit notes — large/gated models)
not applicable:          1
not tested:              38  (explicit: no attempt record)
coverage:                77.8%
```

## ROCm (PyTorch twins — Evidence Schema v2)

```text
applicable twins:   171 classified (160 WORKLOAD_TWIN)
implemented twins:  8
verified:           8 / 8 — PROVEN_GPU (hip 7.2.53211, authoritative
                    gcnArchName gfx1100) + WORKLOAD_CORRECTNESS + complete v2
                    evidence, all under the NEW pin 329562e6031d
failed:             0
not tested:         remaining twin implementations (classification exists;
                    implementation deliberately not promised)
```

WORKLOAD_TWIN never emits direct speedup (`compare` returns `speedup: null`
with the prohibition note); zero EXACT_TWINs exist, so no speedup claim can
appear anywhere today.

## Environment Isolation

Per-workload venvs at `.venvs/<backend>/<env-key>/` keyed by
sha256(backend, python, pinned upstream commit, dependency fingerprint) where
the fingerprint covers the notebook's own requirements*.txt + %pip
declarations + seed spec. Notebooks mutate only their own environment; the
seed is deliberately slim (no torch tax for notebooks that don't need it);
upstream declarations take priority. Seed installs are verified package-by-
package (a uv partial-install bug is caught loudly). GPU twins use a bridged
ROCm venv that never lets uv re-resolve a conflicting torch.

## Evidence Schema

```text
2   (schema_version stamped in every evidence JSON; v0.1 evidence preserved
    as historical, never rewritten)
```

## Self-hosted CI

```text
runner:      ovamd-reference-runner — online (labels: self-hosted, Linux,
             X64, amd64, amd-cpu, amd-gpu, rocm, gfx1151, ryzen-ai-max-395)
CPU workflow:  amd-cpu-validation — manual dispatch, SUCCESS on record
GPU workflow:  amd-rocm-validation — manual dispatch, SUCCESS (6m29s)
concurrency:  single group amd-reference-validation, cancel-in-progress
             false — CPU/GPU validation can never overlap
provisioning: pin-bound (warm snapshot commit must equal the repo pin; cold
             fetch uses --commit <manifest pin>)
```

## Tests

```text
pytest:                    141 passed, 6 skipped
ruff:                      clean
hosted CI (PR #1):         PASS
release audit:             RELEASE PASS (reports/release-audit-v0.2.md)
engineering subagent:      PASS  (majors addressed in follow-up commits:
                             GPU green gate, pin-bound CI, env rebuild
                             identity, defect-H regression tests)
scientific subagent:       PASS  (zero fabricated/unverifiable greens; zero
                             silent downgrades; history preserved)
security audit:            clean — no credentials/private data in 4,500+
                             tracked files (token/key/IP/private-path scan)
```

## Known Limitations

1. 38 NOT_TESTED workloads (mostly large/huge models) — explicit, never
   silently green; the campaign stopped where runner budgets did.
2. 10 REVALIDATION_REQUIRED (upstream re-pin migration) deferred to the
   reference Ryzen runner — the secondary runner's egress cannot fetch
   gated/multi-GB models honestly.
3. CPU greens bind the previous pin (unchanged notebooks carry over; policy
   disclosed per-row via upstream.json) — the re-pin quarantine is explicit.
4. genai-pipeline notebooks whose internal compile cannot be probed stay at
   VWL with DEVICE_PROOF_NOT_OBSERVED (positive proof policy, by design).
5. State-machine transition table is documentation-grade; write paths do not
   yet mechanically enforce it (engineering review finding, follow-up).
6. Single-session GPU greens for gfx1100 (repeatability satisfied within one
   evidence set; cross-session repetition left to scheduled CI).

## Upstream Issues (candidates to report)

1. `optimum-cli` invocation after notebooks `%pip uninstall optimum*` breaks
   on stacks where the git+https reinstall is network-blocked
   (openvino-tokenizers class).
2. Gated HF repos (stabilityai SD family) block validation without tokens —
   ModelScope official mirrors used, provenance recorded.
3. `huggingface_hub`/`transformers`/`diffusers` version-check deadlocks
   (diffusers 0.40 imports a hub≥1.0 symbol while pinning <1.0).

## Security

Audit complete (git grep + evidence JSON scan): no tokens, keys, private IPs,
usernames or absolute private paths in public artifacts. Diagnostic stderr
excerpts inside compatibility.json notes are policy-permitted.

## Git Status

Clean. Generated artifacts committed and reproducible via
`python -m ov_amd report`.

READY FOR EXTERNAL REVIEW
