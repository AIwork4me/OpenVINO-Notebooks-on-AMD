# OpenVINO Notebooks on AMD v0.2 Final Report

> **Supersedes the interim report merged with PR #1.** PR #1 was merged at
> 2026-10-07T01:45Z while the reference machine was still finishing marathon
> passes 2–3 (they completed 02:02Z), the hostile release audit (03:0xZ), and
> the local finals (03:5xZ). This report carries the completed, frozen
> dataset; the interim version's 133/171 board was an honest mid-campaign
> snapshot, not the final state.

## Repository

```text
GitHub URL:    https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD
v0.2 PR:       https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/pull/1
completion PR: this branch (final dataset + hostile audit + WARN fixes +
               local finals); tag decision recorded at merge time — v0.2.0
               points at the interim snapshot, the completed closure gets
               the follow-up tag
```

## Upstream

```text
old pinned commit:   a8809170cc4fc6aa633fbb9c22214be67ac20b47 (2026-09-30)
new current commit:  329562e6031d1a989017d08697b0fabe5a989492 (2026-10-05)
changed notebooks:   13 (10 had validation records → revalidated under the
                     new pin where runner budgets allowed; honest reds kept
                     red: hunyuan-ocr DEPENDENCY, cosyvoice3-tts gated model)
snapshot integrity: 572/572 git-blobs, sha1-verified, zero failures;
                     manifest local_path is repo-relative (portability fix —
                     an absolute path from the fetching machine had blocked
                     the reference runner's pass-3 launch until fixed)
```

`latest` continued to advance during the sync window; the fetcher now
requires an explicit `--commit` so evidence can never bind to a moving
target.

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
OpenVINO 2026.4.x/2026.5.x (CPU validation environments; pin-era env
         rebuilds could resolve 2025.3.0 — see Known Limitations #5)
PyTorch  2.14.1+rocm7.14 (reference) / 2.9.1 (ROCm, +gitff65f5b) with
         hip 7.2.53211 (secondary)
```

## Reliability Closure (defects A–K)

| Defect | Status | Evidence |
|---|---|---|
| A mirror substitution delimiter corruption | **FIXED** | ov_amd/substitution.py (structured rules, no delimiters) + tests/test_substitution.py |
| B shared mutable venv | **FIXED** | ov_amd/env_manager.py per-workload keyed venvs + tests/test_env_manager.py |
| C absolute evidence links | **FIXED** | state records repo-relative; matrix + baseline links `../results/...` (GitHub-resolvable, audit-reverified) |
| D evidence from wrong python | **FIXED** | software-before/after bound to the workload interpreter; snapshot records python_bin |
| E empty device_used passes | **FIXED** | ev2 device-proof states; CPU VERIFIED requires PROVEN_CPU. The genai pipeline probe had an ordering defect (finder appended after PathFinder — never consulted); fixed, empirically verified with a real LLMPipeline, all 93 venv copies refreshed, and pass 3 recaptured proofs (kokoro, deepseek-r1) |
| F empty validation passes | **FIXED** | validation levels; `validation: {}` stays EXECUTION_ONLY, never green; 48 workloads gained L3 contracts during the campaign, each validated against real evidence before writing |
| G repeatability not aggregated | **FIXED** | aggregate.json (median + nearest-rank P95, successful/required); twin aggregator normalizes latency_s/total_s |
| H GPU evidence incomplete | **FIXED** | full v2 set for all GPU evidence incl. validation.json; tests/test_gpu_twin_evidence.py; hello-detection twin re-verified on the reference machine's own gfx1151 with PROVEN_GPU |
| I attempted = catalogued | **FIXED** | coverage from real attempt records: 171/171 = 100% CPU |
| J twin classification incomplete | **FIXED** | 160 WORKLOAD_TWIN / 10 OPENVINO_SPECIFIC / 1 CONCEPT_MAPPING; NOT_CLASSIFIED = 0 |
| K self-hosted CI queued forever | **FIXED** | runner online; amd-cpu-validation SUCCESS (incl. a live run during this closure); amd-rocm-validation SUCCESS; shared concurrency group; manual dispatch only |

## Catalog

```text
total:                     171
classification coverage:   100% (NOT_CLASSIFIED = 0)
```

## CPU (OpenVINO on Ryzen — completed three-pass marathon)

```text
attempted:               171 / 171 (100%)
L3 VERIFIED:             25  (PROVEN_CPU + contract + ≥3-run repeatability)
limited (VWL):           58  (machine-readable notes: repeatability 1-run
                             policy, EXECUTION_ONLY, device-proof gaps)
failed:                  87  (root causes clustered: 87 → 55 clusters,
                             compat vs environment separated in
                             reports/marathon-v2-root-causes.md)
not applicable:          1
```

Pass chronology: pass 1 (92 scheduled, resumed) → watcher flipped
device-probe-capped yellows → pass 2 (`--retry-failed`, 153) → pass 3
(contracts/pin/device-proof revalidations, 23). Classification fixes landed
between passes and measurably healed failures: gated-401 (MODEL_ACCESS),
subprocess-list git-clone (NETWORK), pip resolver-banner (never PACKAGE_CONFLICT
alone — 17 corpus reclassifications, zero real conflicts lost), console-script
FileNotFoundError (DEPENDENCY + optimum-intel remediation). The model-selection
honesty sweep pinned `deepseek-r1` to a real DeepSeek-R1-Distill model (its
widget defaulted headlessly to Qwen3-0.6B); the workload now runs
DeepSeek-R1-Distill-Qwen-7B with a captured genai_pipeline CPU proof.

## ROCm (PyTorch twins — Evidence Schema v2)

```text
applicable twins:   171 classified (160 WORKLOAD_TWIN)
implemented twins:  8
verified:           8 / 8 — PROVEN_GPU + WORKLOAD_CORRECTNESS + complete v2
                    evidence, all under the NEW pin 329562e6031d.
                    Platforms: 7 verified on gfx1100 (hip 7.2.53211, secondary
                    runner) and hello-detection additionally on the reference
                    machine's gfx1151 — per-record platform_id + per-evidence
                    hardware.json attribute every twin to its exact GPU.
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
seed is deliberately slim; upstream declarations take priority. Seed installs
are verified package-by-package. GPU twins use a bridged ROCm venv that never
lets uv re-resolve a conflicting torch.

## Evidence Schema

```text
2   (schema_version stamped in every evidence JSON; v0.1 evidence preserved
    as historical, never rewritten)
```

## Self-hosted CI

```text
runner:      ovamd-reference-runner — online
CPU workflow:  amd-cpu-validation — manual dispatch, SUCCESS on record
               (including a live 2h evidence-returning run during closure)
GPU workflow:  amd-rocm-validation — manual dispatch, SUCCESS
concurrency:  single group amd-reference-validation (CPU/GPU never overlap)
provisioning: pin-bound (warm snapshot commit must equal the repo pin; cold
              fetch uses --commit <manifest pin>)
```

## Tests

```text
pytest:                    147 passed
ruff:                      clean
hosted CI:                 PASS on this branch line
release audit:             RELEASE PASS (reports/release-audit-v0.2.md —
                           13/13 checklist + hostile probes; WARN findings
                           D1/D2/D3 fixed and re-verified, D4 documented)
engineering subagent:      PASS (majors addressed in follow-up commits)
scientific subagent:       PASS (zero fabricated/unverifiable greens)
security audit:            clean — no credentials/private data in tracked
                           files
```

## Known Limitations

1. 58 VERIFIED_WITH_LIMITATIONS carry explicit machine-readable limits
   (1-run repeatability policy for large models, EXECUTION_ONLY without
   contracts — 3d-pose-estimation and mobileclip-video-search outputs are
   3D/video widgets with no honestly checkable stable text).
2. CPU greens from before the re-pin carry over (64 rows): per-evidence
   `upstream.json` discloses the exact commit each run bound to; the catalog
   now points at the current pin (audit D1 fix).
3. v0.1-migration `historical_*` fields were consumed on revalidation; the
   migration trail lives in git history + reports/revalidation-migration.md.
4. `parler-tts` regressed red under the new pin: the rebuilt env resolved
   OpenVINO 2026.4.1 → 2025.3.0 and `BrgemmCPU` rejects f32×bf16 (same
   notebook sha as its previously green run — a pin-induced, honestly
   recorded regression).
5. Pin-era env resolution can downgrade OpenVINO below optimum-intel's
   floor (see #4) — dependency floors are not yet encoded in env building.
6. `vlm-chatbot-generate-api` references a notebook-dir image (`nyc.jpg`)
   the headless kernel cwd cannot see — left FAILED rather than patched
   blindly.
7. The hello-detection twin weight chain depends on github release assets;
   the HF mirror fallback is verified reachable but the successful local
   run was served by github during a network flap (URL + sha256 recorded;
   provenance never silently swapped).
8. State-machine transition table is documentation-grade; write paths do
   not yet mechanically enforce it (engineering review finding, follow-up).
9. Single-session GPU greens for gfx1100 (cross-session repetition left to
   scheduled CI).

## Upstream Issues (candidates to report)

1. `optimum-cli` invocation after notebooks `%pip uninstall optimum*` breaks
   on stacks where the git+https reinstall is network-blocked.
2. Gated HF repos (stabilityai SD family) block validation without tokens —
   ModelScope official mirrors used, provenance recorded.
3. `huggingface_hub`/`transformers`/`diffusers` version-check deadlocks.
4. `BrgemmCPU` f32×bf16 rejection (parler-tts decoder stage) on CPU plugin
   with mixed-precision graphs — upstream model conversion emits bf16 the
   plugin cannot pair with f32 inputs.
5. Notebooks referencing sibling data files by relative path assume a
   notebook-dir kernel cwd (nyc.jpg class) — breaks under
   launcher-cwd execution.

## Security

Audit complete (git grep + evidence JSON scan): no tokens, keys, private IPs,
usernames or absolute private paths in public artifacts. Diagnostic stderr
excerpts inside compatibility.json notes are policy-permitted.

## Git Status

Completion PR (this branch) carries the frozen dataset, the hostile audit
and the local finals; working tree otherwise clean and reproducible via
`python -m ov_amd report`.

READY FOR EXTERNAL REVIEW
