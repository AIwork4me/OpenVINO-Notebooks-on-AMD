# Comprehensive Verification Final Report

Generated: 2026-10-07 — comprehensive verification & quality closure (v0.2.2 candidate).

## Repository

| Item | Value |
|---|---|
| `main` base | `0f59781d97b3d10fa2e48cce3bf8845fb8ecec67` (post-v0.2.1 audit closure) |
| Feature branch | `codex/comprehensive-verification-quality-closure` |
| Final candidate SHA | see merge commit / release tag `v0.2.2` |

## Upstream

| Item | Value |
|---|---|
| Pinned commit | `329562e6031d1a989017d08697b0fabe5a989492` (2026-10-05, branch `latest`) |
| Upstream `latest` at closure | `faf88d73c65671cf34b0813ae44ff28f852508d1` (9 commits, 18 files ahead) |
| Delta handling | pin unchanged (evidence stays pin-coherent); re-pin scope recorded in `reports/current-upstream-delta.md`: 3 changed notebooks (llm-chatbot, llm-chatbot-generate-api, openvino-tokenizers), 2 new catalog candidates (pyannote-audio ×2), and upstream's `download_file` corruption fix relevant to the RCA-004 cluster |

## AMD CPU Coverage

```text
171 / 171 OpenVINO Notebooks have an AMD CPU validation outcome
100% catalog coverage
```

> **100% coverage means every catalogued notebook has been attempted and
> classified on AMD Ryzen. It does not mean every notebook passed.**

| Outcome | Count | Share |
|---|---|---|
| ✅ VERIFIED | 25 | 14.6% |
| 🟡 VERIFIED_WITH_LIMITATIONS | 60 | 35.1% |
| 🌐 BLOCKED_NETWORK | 6 | 3.5% |
| 🔐 BLOCKED_MODEL_ACCESS | 4 | 2.3% |
| 📦 BLOCKED_DEPENDENCY | 37 | 21.6% |
| ⏱️ BLOCKED_TIMEOUT (stage-aware) | 22 | 12.9% |
| 💾 BLOCKED_RESOURCE | 11 | 6.4% |
| 🧩 FAILED_COMPATIBILITY | 5 | 2.9% |
| ➖ NOT_APPLICABLE | 1 | 0.6% |

Successful-execution coverage: **85/170 eligible (50.0%)** — a distinct metric
from catalog coverage, computed as (VERIFIED + VERIFIED_WITH_LIMITATIONS) /
(catalog − NOT_APPLICABLE).

## Verification performed (this closure)

| Audit | Scope | Result |
|---|---|---|
| Dataset baseline (Gate 1) | 4 mirrors × 171 rows | PASS after mirror-sync fix (9 status + 53 twin drifts repaired at the generator level) |
| Full 171-entry integrity audit | every row: identity, pin, evidence, v2 completeness, proof, repeatability, outcomes, sanitization, timestamps | 168 OK / 3 WARN (pre-repin evidence on changed notebooks; revalidation queued) / 0 critical |
| All-green hostile audit (Gate 5) | all 25 VERIFIED | PASS — every row: PROVEN_CPU with real probe events, L3 contract passed, ≥3 runs, complete v2 evidence, pin/sha coherence, AMD hardware; 3 legacy rows' platform_id backfilled from hardware.json |
| All-yellow quality audit (Gate 6) | all 60 LIMITED | PASS — every row has machine-readable limitation codes; none masks failed correctness or missing inference; 0 under-classified |
| Failure reclassification (Gate 3) | all 87 FAILED | PASS — signature-first, evidence-log-driven; UNKNOWN eliminated; stale execution categories corrected |
| State machine (Gate 8) | 110 transition pairs + writer bypass hunt | PASS — mechanical enforcement, invalid writes raise, documented surgery hatches only |
| README truthfulness (Gate 4) | README | PASS |
| Security/OSS (Gate 11) | whole tree | PASS |
| Regression coverage (Gate 12) | 16 historical defects | PASS after adding manifest-sync + CellTimeoutError-precedence tests |
| Upstream currentness (Gate 10) | pin vs latest | PASS |

Fresh execution proof (closure machine, AMD EPYC 9334): `hugging-face-hub`
notebook executed end-to-end through the harness — PROVEN_CPU with 3 compile
events, validation contract passed, scratch evidence in
`results/smoke-hugging-face-hub-closure/` (does not alter dataset rows —
attribution to the reference Ryzen runner preserved).

## Reclassification (Objective D)

Before: **87 generic FAILED** rows carrying only execution categories
(TIMEOUT 20, DEPENDENCY 17, UNKNOWN 14, PACKAGE_CONFLICT 11, MODEL_ACCESS 8,
OPENVINO_ERROR 7, NETWORK 6, CORRECTNESS_ERROR 2, CONVERSION_ERROR 1,
LICENSE_RESTRICTION 1) — every one presented as a red failure.

After (developer-facing compatibility outcomes):

```text
VERIFIED                    25
VERIFIED_WITH_LIMITATIONS   60   (+2 recovered via evidence-based contract correction)
BLOCKED_NETWORK              6
BLOCKED_MODEL_ACCESS         4
BLOCKED_DEPENDENCY          37
BLOCKED_TIMEOUT             22   (stage-aware: CONVERSION_EXPORT / MODEL_DOWNLOAD / DEPENDENCY_INSTALL / INFERENCE / UI_DEMO)
BLOCKED_RESOURCE            11
FAILED_COMPATIBILITY         5   (each with an RCA record)
NOT_APPLICABLE               1
```

Honesty corrections made along the way:

- 2 rows were hidden failures of stale contracts, not workloads
  (person-counting, stable-video-diffusion) — corrected contracts re-evaluated
  against captured outputs, upgraded to yellow with provenance notes.
- 2 rows were CellTimeoutError misclassified by log-grep rule order
  (controlnet-stable-diffusion PACKAGE_CONFLICT→TIMEOUT,
  wan2.1-text-to-video NETWORK→TIMEOUT); classifier order fixed + regression
  tests.
- 9 adjudicated rows carry documented, evidence-linked verdicts (upstream
  rerun-scoping bugs, datasets/transformers/protobuf drift, harness-relative
  assets, NPU-absent hardware).
- hello-segmentation's weak contract strengthened and re-evaluated (still
  green, now with figure-rendering + device markers).
- 1 kernel-death pair retained as honest FAILED_COMPATIBILITY (undiagnosed).

## Environment

- Per-workload isolated venvs keyed by (backend, python, upstream pin,
  dependency fingerprint) — 117 distinct envs across the dataset; shared-venv
  contamination impossible by construction (regression-tested).
- `environment.lock.json` now written into every evidence dir (live full lock
  going forward; honest recorded-snapshot partial locks backfilled for
  historical evidence — 178 dirs).
- Optimum CLI health contract: preflight + bounded single-target remediation +
  machine-readable evidence; proven end-to-end on a fresh venv (missing →
  remediated → `optimum-cli --help` exit 0), evidence
  `results/optimum-health-proof/`.
- Notebook-relative resource semantics: sibling data assets (images/json/…)
  pre-seeded into the kernel cwd with a conservative allowlist + 64 MB cap;
  regression-tested; affected workloads (paddleocr_vl,
  vlm-chatbot-generate-api) queued for revalidation on the reference runner.

## CI

| Workflow | Status at closure |
|---|---|
| Hosted `ci` (tests + ruff + generated-artifact checks) | green on `main` (21 runs) |
| `amd-cpu-validation` (self-hosted) | run #3 **success** on `main` (2026-10-07T02:49Z); concurrency `amd-reference-validation`, `cancel-in-progress: false` |
| `amd-rocm-validation` (self-hosted) | run #4 **success** (2026-10-06T09:08Z); same concurrency group — CPU/GPU never overlap |
| `ingest-validation-evidence` | **BLOCKED by runner git-egress outage** (see INGEST-RESULT below) — workflow logic proven piecewise: resilient checkout success + 75 min of resumable download progress on record; 6 dispatches logged |

### INGEST-RESULT — operational limitation (runner git-egress outage), workflow proven piecewise

Six dispatches against the real artifacts of run `37563821402`
(cpu-evidence 180 MB + marathon-state) during this closure:

| Run | Outcome | What it proved |
|---|---|---|
| 37602875728 | cancelled | `actions/checkout` hangs for hours on the runner's github.com route (diagnosis) |
| 37607950131 | cancelled | same hang confirmed on retry |
| 37610065109 | cancelled (old 90-min job cap) | **resilient checkout SUCCESS via site-mirror fallback** (the fix works); **resumable download ran 75 min with progress** before the pre-fix job cap killed it |
| 37621297425 | cancelled | dispatched before the per-attempt fetch-timeout fix; checkout TCP hang again |
| 37628494427 | failure (fast, clean) | hardened checkout worked as designed: per-attempt timeouts fired; **both transports refused from the runner** (egress outage began ~13:34Z) |
| 37630021723 | failure (fast, clean) | identical — runner git egress down entirely |

Verdict: **BLOCKED by runner infrastructure** (git egress outage during the
closure window), not by workflow logic. Piecewise proof on record: the
resilient checkout step succeeded (run 37610065109) and the resumable download
made real progress through the very throttling it was built for (75 min,
Range-resumed). Workflow hardening shipped this closure: site-mirror fallback
with an **API SHA pin** (mirror-delivered trees must match github.com's main),
per-attempt fetch timeouts, 150-minute window sized for the bounded resumable
download, and idempotent evidence overlay. A dispatch once the runner's egress
recovers completes the proof; the operator runbook is the workflow itself.

## ROCm (Pillar B)

All 8 VERIFIED GPU twins audited — no sampling:

| Workload | Proof | Level | Repeatability | Platform attribution |
|---|---|---|---|---|
| hello-detection | PROVEN_GPU | WORKLOAD_CORRECTNESS | 5/3 | Ryzen AI Max 395 + Radeon (gfx1151) |
| deepseek-r1 | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | EPYC 9334 + Radeon (gfx1100) |
| stable-diffusion-text-to-image | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |
| smolvlm2 | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |
| qwen3 | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |
| whisper-asr-genai | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |
| kokoro | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |
| stable-diffusion-xl | PROVEN_GPU | WORKLOAD_CORRECTNESS | 3/3 | gfx1100 runner |

Twin classification 171/171 (160 WORKLOAD_TWIN / 10 OPENVINO_SPECIFIC /
1 CONCEPT_MAPPING); no EXACT_TWIN exists, so no CPU-vs-GPU speedup claims are
publishable — CPU and GPU results are deployment references
(benchmarks/METHODOLOGY.md enforces mechanically).

## Quality improvements (this closure)

1. Central public-artifact sanitizer (unix/windows/workspace prefixes,
   URL-safe) + regression tests; leaks removed from generated summaries and
   state notes; evidence summaries sanitized at the generator.
2. Two-dimension status taxonomy (`execution_status` × `compatibility_outcome`)
   with signature-first root-cause refinement; BLOCKED_* never blamed on
   AMD/OpenVINO.
3. Mechanical state-machine enforcement (`InvalidStateTransition`) at every
   writer, explicit `force` hatch for documented surgery.
4. Stage-aware timeout classification (DEPENDENCY_INSTALL / MODEL_DOWNLOAD /
   CONVERSION_EXPORT / UI_DEMO / INFERENCE) recorded at runtime and derived
   for historical evidence.
5. Manifest mirrors (`workloads/*/workload.yaml`) regenerated from source of
   truth and kept in sync by `python -m ov_amd report`; consistency
   regression-tested.
6. Classifier rule-order fixes (CellTimeoutError precedence; NLTK/datasets/
   protobuf drift rules).
7. Notebook-relative data-asset pre-seeding.
8. Optimum CLI health contract.
9. `environment.lock.json` evidence metadata.
10. README hero coverage + "what 100% means" + generated-metrics staleness
    guards; category summary + outcome columns in the matrix.
11. `doctor`/`list` coverage summaries; `list --status` filtering by outcome.
12. Issue templates for the full taxonomy (compat report, compat issue,
    blocked environment, upstream candidate).
13. Full-audit tooling committed (`scripts/full_integrity_audit.py`,
    `scripts/reclassify_outcomes.py`) — rerunnable.
14. 65 new tests (147 → 212), including dataset-level guarantees (no UNKNOWN
    outcomes, manifest/state agreement, README freshness).

## Upstream candidates

Genuine compatibility issues with RCA records (minimization pending reference
runner — nothing speculative filed upstream):

- `reports/upstream/rca-001-parler-tts-brgemm-f32-bf16.md` — OpenVINO CPU
  plugin snippets brgemm rejects f32×bf16 inputs.
- `reports/upstream/rca-002-tokenizers-readvalue-sibling.md` — CPU plugin
  memory-node sibling-output check fails on converted tokenizer IR (note:
  upstream changed this notebook after our pin — revalidate at re-pin).
- `reports/upstream/rca-003-qwen3-clenqueue-mapbuffer-amd-gpu.md` — OpenVINO
  GPU plugin on AMD Radeon fails at runtime (clEnqueueMapBuffer -30).
- `reports/upstream/rca-004-empty-weights-cluster.md` — artifact-corruption
  cluster (NOT compatibility failures); upstream's `download_file` fix
  (`f1958fc8`) addresses the mechanism — retry cluster after re-pin.
- `reports/upstream/rca-005-kernel-deaths-undiagnosed.md` — two kernel deaths
  retained honestly as compatibility failures pending post-mortem.

## Known limitations

1. **Revalidation debt**: 3 rows carry pre-repin evidence on content that
   changed with the v0.2 re-pin (llm-rag-langchain, ltx-video,
   segment-anything-2-video) — queued with failure-retry remediation; and the
   3 notebooks changed upstream after the current pin (see delta report) will
   need revalidation at the next re-pin.
2. **Closure-environment constraints**: the comprehensive pass ran on AMD
   EPYC 9334, not the reference Ryzen AI Max 395 runner. Rows were NOT
   re-executed here to avoid silently changing platform attribution;
   evidence-chain audits, captured-output re-evaluation, and one scratch smoke
   run (PROVEN_CPU) stand in. `storage.openvinotoolkit.org` is egress-blocked
   on the closure machine (hello-world/openvino-api smokes classified
   BLOCKED_NETWORK by the harness — correctly).
3. **Timeout rows carry wall-clock stages**, not instrumented phase timers
   for historical evidence (runtime instrumentation now records stages for
   future runs).
4. **Yellow upgrades needing new runs** (41 repeatability-limited, 27
   execution-only, 6 device-proof-incomplete) require the reference runner —
   see `reports/yellow-upgrade-opportunities.md`.
5. **Failure recovery at scale** (optimum-cli cluster reruns, artifact
   re-downloads, gated models) is deliberately out of scope for this closure
   (v0.3 per the roadmap); the health contract and classifier fixes are in
   place so retries can be trusted.
6. **Artifact-ingest proof run**: the ingest workflow's logic is proven
   piecewise (checkout fallback success; resumable download progress) but no
   single end-to-end green run completed during the closure window because the
   self-hosted runner's git egress went down mid-verification (6 dispatches
   logged, last two failing fast-and-clean by design). Queued as an
   operational follow-up when the runner recovers; see INGEST-RESULT.

## Security

PASS — no credentials in the tracked tree; public summaries carry no
machine-local paths; workflows use scoped GITHUB_TOKEN only; LICENSE /
THIRD_PARTY / SECURITY / CONTRIBUTING / CODE_OF_CONDUCT intact and consistent
with the taxonomy (Gate 11).

## Final audit

PASS — all subagent gates green (dataset baseline, hygiene, taxonomy, green,
yellow, state machine, README, security/OSS, regression coverage, upstream
currentness). Release verdict from the independent hostile release audit:
see `RELEASE VERDICT` in the release notes — **RELEASE PASS**.
