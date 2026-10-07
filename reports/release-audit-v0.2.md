# Release Audit — v0.2 (branch `codex/v0.2-validation-reliability`)

Auditor: hostile external reviewer, no prior participation. Method: every claim below was
re-measured against raw artifacts (`results/marathon-state.json`, evidence directories on disk,
git-tracked files, live GitHub Actions runs). Docs and generated summaries were treated as
claims, not facts.

Audit date: 2026-10-07. HEAD audited: `9090129` ("fix: baseline report platform column + zero
absolute-path evidence links").

## Verdict summary

The repository holds up under adversarial inspection. Recomputed counts match the raw state
exactly; every green row I sampled (and, for the structural invariants, every green row in the
state file) has real on-disk evidence with the v2 file set; the 4 CPU VERIFIED records are all
`PROVEN_CPU` + `WORKLOAD_CORRECTNESS` + `ok_runs >= 3` with non-empty validation contracts; all
8 GPU VERIFIED records carry `PROVEN_GPU`, hip `7.2.53211-e1a6bc5663`, `gcn_arch: gfx1100`,
platform `amd-epyc-9334-32-core-processor-gfx1100`; `compare hello-detection` emits
`"speedup": null` for WORKLOAD_TWIN; no credential material is tracked; REVALIDATION_REQUIRED
(10) and NOT_TESTED (38) are visible, not hidden. Minor defects found (7) are presentation- or
process-level and do not undermine trust in the compatibility claims. **RELEASE PASS** (with
documented caveats).

## Per-check findings

### 1. Product truthfulness (README vs raw state) — PASS

- README status block (lines 35–45) vs recomputed from `results/marathon-state.json`:
  CPU `VERIFIED 4 · VWL 35 · REVALIDATION_REQUIRED 10 · FAILED 83 · NOT_APPLICABLE 1 ·
  NOT_TESTED 38`, attempted `133/171` (77.8%); GPU `VERIFIED 8`. Recomputation
  (`collections.Counter` over `attempts[*].cpu/gpu.status`, absent ⇒ NOT_TESTED) matches all
  numbers exactly; catalog JSON counts and the compatibility.md table (12 ✅ = 4 CPU + 8 GPU,
  35 🟡, 10 🔵, 83 🔴, 201 ⏳ cells = 38 CPU + 163 GPU) agree.
- Status-model table and the disclaimer ("does not imply official hardware support…") are
  present (README lines 65–78).
- Slogan/positioning intact verbatim: "Validate and run OpenVINO Notebooks on AMD Ryzen CPUs,
  with matching ROCm-powered references for AMD Radeon GPUs." and "One AI workload. Two AMD
  paths." (README lines 8, 10).
- No overclaim found: README claims only what the state file shows, and the GPU line explicitly
  shows "8 verified" out of a 171-row catalog.

### 2. Evidence sampling (10 random green rows + all 4 CPU VERIFIED) — PASS

Random sample (seed 20261007) of green rows: hunyuan-translation, llm-question-answering,
convert-to-openvino, language-quantize-bert, tensorflow-object-detection-api-with-openvino,
tflite-to-openvino, surya-line-level-text-detection, fast-segment-anything, deepseek-r1 (GPU),
kokoro (GPU); plus exhaustive check of the 4 CPU VERIFIED (hello-world, hello-detection,
hello-segmentation, handwritten-ocr). For each:

- Evidence link resolves in-repo: yes (14/14 dirs exist under `results/<id>/<ts>-<backend>/`).
- v2 set present: `hardware.json`, `software.json` (GPU) / `software-before.json` +
  `software-after.json` (CPU), `upstream.json`, `validation.json`, `metrics.json`,
  `aggregate.json`, `device-proof.json`, `summary.md`; CPU execution evidence lives in
  `run-01..03/execution.json|device-proof.jsonl|stdout.log|stderr.log|executed.ipynb` per
  `docs/validation-policy.md` §"Evidence Schema v2" — consistent with the documented schema.
- CPU VERIFIED: `device-proof.json` `state == PROVEN_CPU` and `validation.json`
  `level == WORKLOAD_CORRECTNESS` on disk AND in the state file, for all 4.
- GPU VERIFIED: `device-proof.json` carries `hip: "7.2.53211-e1a6bc5663"` and
  `gcn_arch: "gfx1100"`; hip source is authoritative (`torch.version.hip`, arch from
  `torch.cuda.get_device_properties().gcnArchName` with rocminfo fallback — never inferred from
  CUDA capability; verified in `ov_amd/twin_lib.py:41-74`).
- Reality probe: hello-world `run-01/executed.ipynb` contains the literal contract string
  "flat-coated retriever" (16 cells, 8 code outputs) — the evidence is a real executed
  notebook, not a stub.

### 3. CPU proof honesty (scripted over the whole state file) — PASS

Script iterated all 133 attempt records: **zero** records with `status == VERIFIED` and
`device_proof != PROVEN_CPU` (GPU side: zero `VERIFIED` without `PROVEN_GPU`); **zero**
`VERIFIED` records with `validation_level == EXECUTION_ONLY`; all `VERIFIED` records are
`WORKLOAD_CORRECTNESS` on both sides. Additionally the on-disk `device-proof.json` was
cross-checked against the state file for every VERIFIED record — no divergence. Note (not a
defect per policy): some VWL greens carry `NOT_INFERENCE` (openvino_genai / conversion-only
notebooks bypass `compile_model`) or `EXECUTION_ONLY`; both are machine-disclosed in row notes
(e.g. "DEVICE_PROOF_NOT_OBSERVED…", "EXECUTION_ONLY: no workload correctness contract
(validation: {})") and aggregated in `reports/v0.2-pinned-baseline.md` ("Device-proof states
seen (CPU): PROVEN_CPU 31, NOT_INFERENCE 15, AUTO_UNRESOLVED 2, UNKNOWN 7").

### 4. GPU proof (all 8 records) — PASS

All 8 GPU VERIFIED (hello-detection, deepseek-r1, stable-diffusion-text-to-image, smolvlm2,
qwen3, whisper-asr-genai, kokoro, stable-diffusion-xl): `hardware.json.platform_id ==
"amd-epyc-9334-32-core-processor-gfx1100"`, `device-proof.state == PROVEN_GPU`,
`validation.json.level == WORKLOAD_CORRECTNESS`, state-file `platform_id` contains gfx1100.
Spot-checked evidence dirs deepseek-r1 and kokoro: identical
`hip = 7.2.53211-e1a6bc5663`, `gcn_arch = gfx1100`, `torch 2.9.1+gitff65f5b`, `rocm_dir
/opt/rocm` in `software.json`; all 8 pinned to upstream `329562e6031…` in `upstream.json`.

### 5. Correctness = green means workload correctness — PASS

All 4 CPU VERIFIED records: `ok_runs == 3` (required 3) with 3 `run-NN` dirs each;
`workloads/<id>/workload.yaml` has non-empty `validation:` contracts
(hello-world: `output_contains: [flat-coated retriever]` + finite numbers + min chars;
hello-detection: `output_contains: [value='CPU']`; hello-segmentation: output_not_contains
Traceback + min chars; handwritten-ocr: expected CJK string). VWL rows that lack contracts are
explicitly annotated `EXECUTION_ONLY` in catalog notes (spot-checked 6).

### 6. Benchmarks — PASS

`python3 -m ov_amd compare hello-detection` (run by auditor): emits
`comparison_policy: SIDE_BY_SIDE_ONLY, speedup_allowed: false` and
`"speedup": null` with the note "not an EXACT_TWIN (WORKLOAD_TWIN): direct speedup claims are
not valid…". `benchmarks/METHODOLOGY.md` §"Modes" discloses DEPLOYMENT vs CONTROLLED;
`docs/cpu-vs-gpu.md` repeats both modes and lists "what we never claim". Grep across public
artifacts found no speedup/faster-than claims for non-EXACT twins (the only EXACT_TWIN count is
0). The twin script honestly discloses NMS-on-CPU and records weights sha256 + serving URL.

### 7. Environment isolation — PASS

`ov_amd/env_manager.py`: venvs keyed by `env_key = sha256(backend, python, upstream commit,
dependency fingerprint)`; the dependency fingerprint hashes requirements*.txt next to the
notebook, all normalized `%pip/!pip install` lines extracted from notebook cells, per-workload
`extra_deps`, and the seed set — so notebook deps are included, and two workloads share an env
only when fingerprints are identical (`/workspace/.venvs/cpu/<env_key>/` observed in state
records). `ov_amd/executor.py:246-441`: remediation calls
`_pip_install_into(env.python, …)` — installs go into the workload's own venv python only;
`software-after.json` re-snapshots that same interpreter.

### 8. Reporting counts (recomputed) — PASS

README / compatibility.md / compatibility.json / marathon-progress.md / v0.2-pinned-baseline.md
all re-derived from `results/marathon-state.json` by the auditor: CPU 4/35/10/83/1/38, GPU 8,
twin 160/10/1, attempted 133 (77.8%). No mismatch. Catalog statuses vs state statuses: zero
mismatches across all 171×2 cells.

### 9. Link resolution — PASS (with a rendering caveat, see defect D2)

All 133 non-empty `[link](results/…)` targets in `catalog/compatibility.md` exist as
directories in the repo (100%). Caveat: links are repo-root-relative inside a file that lives
in `catalog/`, so GitHub's web UI would resolve them against `catalog/results/…`.

### 10. Upstream freshness — PASS

`upstream/openvino-notebooks.json` pins `329562e6031d1a989017d08697b0fabe5a989492`
(2026-10-05, sha1-verified blobs 572/572) — same pin recorded in `marathon-state.json`.
Evidence binding: all 8 GPU greens carry `upstream.json.commit = 329562e6031…`; the CPU greens
(4 VERIFIED + 35 VWL) are explicitly bound to the older pin `a8809170cc4f…` (with
`notebook_sha256` where applicable), which `reports/upstream-update-impact.md` documents: 8
upstream commits, 13 changed notebooks, changed workloads flipped to REVALIDATION_REQUIRED,
3 impacted-but-never-tested stay NOT_TESTED. The 10 current REVALIDATION_REQUIRED records all
carry preserved `historical_status` + `historical_evidence` pointing at real on-disk v0.1/v2
dirs (verified 10/10 exist), are rendered 🔵 (not green) in the matrix, and are excluded from
the green counts (recomputed above).

### 11. Twin integrity — PASS

Counts: 160 WORKLOAD_TWIN / 10 OPENVINO_SPECIFIC / 1 CONCEPT_MAPPING / 0 NOT_CLASSIFIED, 171
classified — identical in `catalog/notebooks.yaml`, `catalog/compatibility.json`, and the
matrix. Spot-checks (5): hello-detection WORKLOAD_TWIN is exactly the audit's reference case —
upstream OpenVINO detection vs ultralytics YOLOv8n same-task different-model, stated in the
twin script docstring and enforced by policy; pointpillars WORKLOAD_TWIN (LiDAR 3D detection,
OpenPCDet/mmdet3d rationale) plausible; hello-npu OPENVINO_SPECIFIC (Intel NPU API teaching
notebook) correct; physical-ai-robotics CONCEPT_MAPPING (notebook is a pointer to a
robot-arm tutorial repo, no code) correct; async-api OPENVINO_SPECIFIC (AsyncInferQueue API)
correct. `tests/test_twin_guard_and_counts.py` mechanically guards the counts and the
speedup ban.

### 12. Security — PASS

`git grep` over all 4,523 tracked files for GitHub/HF/OpenAI/AWS/Slack token formats, private
keys, `Authorization:/Bearer/password/secret/token =` assignments, private RFC1918 addresses:
no real credentials. Long base64 hits are notebook output images. No `.pem/.key/.env` files
tracked; `gh_2.101.0…tar.gz` and `.venvs/`, `.cache/` are untracked. `scripts/fetch_upstream.py`
reads `GH_TOKEN` from the environment — nothing hardcoded. Test IP `185.199.110.133` is a
GitHub Pages address.

### 13. CI honesty — PASS with caveat (see defect D1)

`.github/workflows/ci.yml`: hosted (`ubuntu-latest`), pytest + ruff + catalog-consistency
check. `amd-cpu-validation.yml` and `amd-rocm-validation.yml`: both `workflow_dispatch` only,
`runs-on: [self-hosted, amd64, …]`, both share `concurrency.group: amd-reference-validation`
with `cancel-in-progress: false` — exactly as claimed. Live `gh run list`: amd-rocm-validation
**completed success** on this branch 2026-10-07T09:08 (run 37440954714; one earlier failure and
one cancellation same day, visible, not hidden); amd-cpu-validation completed success on the
branch 2026-10-05. README carries only the ci.yml badge — no AMD badges advertising more than
reality. Caveat: hosted `ci` has never run on this branch (no PR exists; ci triggers on push to
main / PRs), so the badge reflects `main`, not this branch — see D1.

### 14. Known-limitations honesty — PASS

REVALIDATION_REQUIRED (10) appears verbatim in the README status block ("🔵 10 revalidation
required"), as 🔵 rows with preserved evidence links in compatibility.md, and in
v0.2-pinned-baseline.md. NOT_TESTED (38 CPU / 163 GPU) is in the README block ("⏳ 38 not
tested") and as ⏳ rows with `-` evidence. The deferral reason is recorded per-row ("queued for
the reference Ryzen runner"). Nothing green is smuggled out of the migration set.

## Defects found

All minor; none meet the FAIL bar (no fabricated data, no fake evidence, no unverifiable
green, no secret leak, no wrong counts).

- **D1 (minor, process):** hosted CI (`ci.yml`) has never executed on
  `codex/v0.2-validation-reliability` (workflow triggers: push to `main`, PRs; no PR open; last
  green ci on main is 2026-10-05, predating most v0.2 commits). Mitigation observed: auditor
  ran the same gates locally — `pytest -q`: 135 passed, 6 skipped; `ruff check .`: clean — and
  the substantive validation workflows (self-hosted) did complete success on the branch.
- **D2 (minor, presentation):** evidence links in `catalog/compatibility.md` are
  repo-root-relative (`results/…`) inside a file under `catalog/`; they resolve in a clone but
  would 404 when clicked in GitHub's web UI (which resolves relative to the file's directory).
- **D3 (minor, internal):** `catalog/compatibility.json` `last_tested` for the 6 GPU-verified
  rows stores the CPU `updated` date (e.g. hello-detection `2026-10-05` vs GPU `2026-10-07`);
  the rendered compatibility.md shows the correct max date, so the public artifact is right
  and only the intermediate JSON field is stale-biased.
- **D4 (minor, staleness):** `reports/final-report.md` is a v0.1-era artifact (1 VERIFIED /
  77 FAILED / different platform: gfx1151 Strix-Halo iGPU, PyTorch 2.14.1+rocm7.14) kept
  without a "superseded — see reports/v0.2-pinned-baseline.md" banner; it is dated and not
  linked from the README, but a reader landing on it could mistake it for current.
- **D5 (minor, coverage):** twin-classification rationale notes exist for only 81/171 entries
  in `catalog/notebooks.yaml` (hello-detection's rationale lives in the twin script docstring
  instead). Counts and classifications themselves are complete and consistent.
- **D6 (minor, wording):** `benchmarks/METHODOLOGY.md` comparison table says OPENVINO_SPECIFIC
  ⇒ "GPU NOT_APPLICABLE", while the matrix renders GPU as ⏳ NOT_TESTED for those rows — a
  doc-vs-rendering inconsistency about a non-green cell, not a claims issue.
- **D7 (observation, disclosed):** all 8 GPU greens come from a single gfx1100 machine
  (EPYC 9334 host) and all CPU greens from a single Ryzen AI Max+ 395 box; the "Radeon GPUs"
  phrasing is generic but every claim is per-evidence-dir hardware-bound, and
  v0.2-pinned-baseline.md discloses both platforms explicitly.

## Final verdict

The compatibility map is what it says it is: statuses recomputed from raw state match public
artifacts exactly, greens are backed by complete on-disk v2 evidence with positive device
proof and (for VERIFIED) workload-correctness contracts and repeatability, the migration set
is quarantined honestly, benchmark comparisons are twin-safety-gated, and no secret material
is exposed. The defects above are minor presentation/process caveats that do not undermine
trust.

RELEASE PASS
