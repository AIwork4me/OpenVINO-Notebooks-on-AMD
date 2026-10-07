## OpenVINO Notebooks on AMD v0.2 — Validation Reliability Closure

### Why v0.2 was necessary

An external review of the v0.1 campaign (frozen at tag `v0.1-validation-baseline`,
commit d7562f7) identified defects A–K that made some green checks untrustworthy:
a shared mutable venv that let one notebook's `%pip install` poison later
validations, mirror-substitution rules that corrupted notebook cells, evidence
collected from the wrong Python, empty `device_used` accepted as CPU proof,
empty `validation: {}` promoted to full VERIFIED, repeatability claimed with
`runs_ok: 0`, GPU twins with three-file evidence, reporting that equated
"catalogued" with "attempted", 70/171 twins unclassified, and self-hosted CI
queued forever.

### What changed

**Evidence Schema v2** (`ov_amd/ev2.py`): every evidence file carries
`schema_version: 2`. Per-attempt layout with `run-NN/` subdirectories,
`software-before/after.json` bound to the actual workload interpreter,
`aggregate.json` (successful/required runs, median, nearest-rank P95),
`device-proof.json` from a transparent kernel-side probe, `model.json`,
`upstream.json` with notebook sha256.

**Positive device proof** (`ov_amd/device_probe.py`): a `.pth`-installed probe
in every per-workload venv records `Core.compile_model` calls — the runtime's
`EXECUTION_DEVICES` property where available, else the explicit device
argument — plus `openvino_genai` pipeline device args (they compile in C++).
Widget text scans are supporting evidence only. CPU `VERIFIED` requires
`PROVEN_CPU`; GPU/AUTO/mixed/absent evidence degrades to explicit limitation
notes, never to green.

**Validation levels**: L1 `EXECUTION_ONLY` / L2 `DEVICE_VERIFIED` /
L3 `WORKLOAD_CORRECTNESS`. `VERIFIED` requires L3 + `PROVEN_CPU` + 3 successful
runs. `validation: {}` stays L1 and can never render green. Explicit
correctness contracts were authored for every green workload
(`workloads/<id>/workload.yaml validation:`).

**Per-workload environment isolation** (`ov_amd/env_manager.py`): venvs keyed
by (backend, Python, pinned upstream commit, dependency fingerprint of the
notebook's own requirements + `%pip` declarations). Notebooks mutate only
their own env. Seed installs are verified (a uv partial-install bug was caught
and now fails loudly).

**URL-safe substitutions** (`ov_amd/substitution.py`): structured
`{pattern, replacement}` rules over JSON; no delimiter parsing anywhere.
Regression battery covers ports, queries, regex metacharacters, git+https,
non-HF hosts.

**Reporting honesty**: attempted ≠ catalogued (coverage percentages),
notes sanitized, all evidence links repo-relative and verified to exist,
twin comparison policy mechanically enforced (`WORKLOAD_TWIN` forbids speedup).

**100% twin classification** with notebook-semantic reasoning recorded (three
review rounds corrected 12 misclassifications).

**Legacy v0.1 greens**: 24 records were marked `REVALIDATION_REQUIRED` with
`historical_status`/`historical_evidence` preserved at migration time (see
`reports/revalidation-migration.md`); those fields were consumed as each
record was revalidated during the marathon, so the current state file keeps
only live records — the migration trail stays in git history and the
migration report.

**Self-hosted CI**: runner `ovamd-reference-runner` registered and online
(systemd user service); CPU and ROCm workflows use a shared
`amd-reference-validation` concurrency group (CPU/GPU share one SoC);
the CPU smoke workflow completed successfully on the runner and produced a
fully evidence-backed `hello-world` VERIFIED from a cold checkout.

### Marathon v2 results (final counts, recomputed from raw state)

CPU (OpenVINO on Ryzen; passes 1–2 under pin a8809170, pass 3 under the
re-pinned 329562e6031d): attempted **171/171** (100%) — ✅ 25 VERIFIED
(L3 contract + PROVEN_CPU + ≥3-run repeatability) · 🟡 58
VERIFIED_WITH_LIMITATIONS (explicit machine-readable limits) · 🔴 87
FAILED · ➖ 1 N/A. Failure taxonomy: `reports/marathon-v2-root-causes.md`
(87 failures → 55 clusters, compat vs environment separated).

GPU (ROCm twins, **all 8 revalidated under Evidence Schema v2 on gfx1100**,
pin 329562e6031d): ✅ 8 VERIFIED (PROVEN_GPU via hip 7.2.53211 + authoritative
gcnArchName, WORKLOAD_CORRECTNESS, complete v2 evidence sets).

Upstream re-pinned a8809170 → 329562e6031d (572/572 sha1-verified blobs;
13 changed notebooks → migration handled honestly; 3 never-validated stay
NOT_TESTED rather than fake "revalidation"). Full matrix:
`catalog/compatibility.md`; baseline: `reports/v0.2-pinned-baseline.md`
(dual-platform attribution on every green row).

### CI state

- Hosted unit/lint/consistency CI: passing on this branch.
- AMD CPU workflow: manual-dispatch, executed successfully on the self-hosted runner.
- AMD ROCm workflow: manual-dispatch, same concurrency group; schedule triggers
  were removed until continuous validation is re-enabled deliberately
  (scheduled runs without a runner queued indefinitely — defect K).

### Known limitations

- LLM notebooks driving `openvino_genai` pipelines compile internally; the
  probe records their device argument, but notebooks where it could not be
  captured are capped at `VERIFIED_WITH_LIMITATIONS` with
  `DEVICE_PROOF_NOT_OBSERVED`.
- Expensive workloads validated with a single run are capped at
  `VERIFIED_WITH_LIMITATIONS` (`repeatability_not_established`).
- huggingface.co is unreachable on the reference network; HF traffic uses a
  mirror (recorded in engineering decisions).
- Gated models (e.g. `stabilityai/stable-diffusion-3-medium-diffusers`) remain
  blocked by model access.
- v0.1-migration `historical_*` fields were consumed on revalidation; the
  trail lives in git history + `reports/revalidation-migration.md`.
- Under the re-pin, `parler-tts` regressed red (OpenVINO resolved 2026.4.1 →
  2025.3.0 in the rebuilt env; `BrgemmCPU` rejects f32×bf16) and two
  pin-impacted workloads (`hunyuan-ocr`, `cosyvoice3-tts`) fail on
  dependency/gated-model grounds — documented in
  `reports/marathon-v2-root-causes.md`.
- `vlm-chatbot-generate-api` references a notebook-dir image (`nyc.jpg`) the
  headless kernel cwd cannot see — left FAILED rather than patched blindly.

### Release audit

Independent hostile release audit (Step 32): **RELEASE PASS** —
`reports/release-audit-v0.2.md`. Its minor findings (D1–D7) were addressed
in follow-up commits where applicable (matrix link resolution `../results/`,
stale v0.1 report archived).

### Step-33 note

`python -m ov_amd run hello-world --device cpu` re-verified on the gfx1100
secondary runner fails before any inference (blocked egress to
storage.openvinotoolkit.org) — recorded as an environment constraint, not a
compatibility verdict; the reference-machine VERIFIED record stands.
