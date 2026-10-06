# Engineering Decisions

Autonomous decisions made during the campaign, in priority order:
correctness → scientific integrity → reproducibility → upstream compatibility →
maintainability → developer usability → coverage → performance → convenience.

## D1 — Package named `ov_amd` instead of a `harness/` directory

The CLI contract is `python -m ov_amd …`. A directory named `harness` cannot be
invoked as a module without a package alias, so the harness modules
(`hardware.py`, `environment.py`, `executor.py`, `notebook_runner.py`,
`benchmark.py`, `correctness.py`, `reporting.py`, `scheduler.py`, `schemas.py`)
live in the top-level package `ov_amd/`.

## D2 — Hugging Face access via mirror endpoint

`huggingface.co` is not reachable from this network (preflight evidence:
`reports/preflight.md`). The harness therefore sets
`HF_ENDPOINT=https://hf-mirror.com` for all notebook kernels. Model weights are
byte-identical (same repo, same revision); downloads remain source-verified by
the hub client. ModelScope is used as an additional fallback when a notebook
allows it. Every source substitution is recorded in the evidence directory.

## D3 — Upstream executed from a pinned clone, never mirrored into this repo

`.cache/upstream` (gitignored) holds the shallow clone of
`openvinotoolkit/openvino_notebooks` at the pinned commit recorded in
`upstream/openvino-notebooks.json`. The catalog stores paths + URLs + notebook
SHA-256. This repo only contains wrappers, patches, twins and evidence.

## D4 — Cell-level patches instead of rewritten notebooks

When a notebook contains interactive/UI-only code (Gradio launches, webcam
widgets), the runner applies *documented cell patches* configured in
`workloads/<id>/workload.yaml`:

- `skip_cells_matching` — UI-only cells are skipped and tagged in the executed notebook
- `stop_after_cell_matching` — execution stops after a named cell
- `cell_subs` — narrow regex substitution (e.g. forcing `device = "CPU"`)

Every patch is recorded in the run result (`patch_notes`) and demotes the result
to `VERIFIED_WITH_LIMITATIONS` (`CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED`).
No patch silently rewrites model logic.

## D5 — Repeatability policy

`VERIFIED` requires ≥3 successful executions. Cheap workloads (small/medium)
run 3 times. Expensive workloads (large/huge) run once and are marked
`VERIFIED_WITH_LIMITATIONS` with the explicit note "single successful run
(resource-bounded); 3-run policy not met" — never silently VERIFIED.

## D6 — Shared baseline venv + targeted installs (not per-notebook venvs)

Hundreds of per-notebook venvs are impractical on disk and time. The CPU
baseline venv (`.venv-cpu`) covers the common stack; on a `DEPENDENCY` failure
the runner installs the notebook's own upstream `requirements*.txt` (or the
exact missing package) into the shared venv — bounded to 2 remediations per
workload — and records every install in `marathon-state.json:installed_extras`.
Package conflicts that would corrupt the baseline are recorded as
`BLOCKED / PACKAGE_CONFLICT`.

## D7 — GPU twins are Python scripts, not notebooks

`workloads/<id>/rocm/run.py` contains the twin implementation; any notebook can
call the same code. Core logic must not live exclusively inside `.ipynb`.
A twin prints `TWIN_RESULT={"ok": true, "hip": "<version>", "metrics": {...}}`;
`hip` must be non-null or the run cannot be VERIFIED (no fake GPU validation).

## D8 — Device honesty on CPU validation

OpenVINO `AUTO` could select an NPU/GPU if present; the harness detects the
device actually used from executed outputs (`device_used`) and stores it in the
evidence. Workloads whose selection cannot be pinned receive a `cell_subs`
patch forcing `CPU`, which is recorded and demotes the status if it changes
behavior. The preflight `openvino devices` list is part of every evidence dir.

## D9 — Tiered wall-clock timeouts

small 10 min / medium 30 / large 60 / huge 90 (configurable per workload).
Timeouts kill the whole process group so kernel children (downloads, servers)
cannot leak. One reduced/extended retry is allowed for timeouts on cheap
workloads only; otherwise the failure is recorded.

## D10 — Evidence contract

Every attempt writes `results/<workload>/<timestamp>-<backend>/` with
hardware.json, software.json, upstream.json, execution.json, metrics.json,
stdout.log, stderr.log, executed.ipynb, summary.md. Failures are preserved —
they are project value, not garbage.

## D11 — Upstream transport: GitHub Git Blobs API, sha1-verified

On this network: `git clone`/codeload is throttled to ~47KB/s and
`raw.githubusercontent.com` stalls after an initial burst, while
authenticated `api.github.com` is fast and stable. Upstream snapshots are
therefore fetched through the Git Blobs API (one request per file, gh-token
authenticated, well within the 5000/h limit). Each blob is verified against
the tree's git blob SHA-1 before writing — the transport mirror cannot
tamper content. `scripts/fetch_upstream.py` is resumable (size+sha checks).

## D12 — PyTorch for ROCm twins comes from the rocm7.14 wheel index

Per operator instruction (2026-10-01), GPU twins use
`pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm7.14`
against system ROCm 7.2.1 on gfx1151. Verified by `torch.version.hip` +
`torch.cuda.is_available()` before any twin is allowed to report VERIFIED.

## D13 — Global default socket timeout (75s)

Many upstream notebooks call `requests.get()`/`urlopen()` without a timeout.
On this network a blocked CDN turns that into an infinite hang that stalls a
cell until the wall clock. The venv `.pth` hook sets
`socket.setdefaulttimeout(75)` so such cells fail fast and classify as
NETWORK. Side effect (accepted, recorded): gradio servers blocking on accept
also fail after 75s — those cells are UI-only and covered by the skip policy
(D4/§22) anyway.

## D14 — Evidence transport slimming

Evidence directories keep everything on disk, but git carries only the
lightweight contract files (hardware/software/upstream/execution/validation/
metrics JSON, stdout/stderr logs, summary). `executed.ipynb` copies and
generated media stay local: 100+ attempts produced >9 GB of executed
notebooks + partial model blobs, unpushable at this network's ~47KB/s
upstream (a single intermediate history reached 9.2 GiB and had to be
squashed). The evidence contract (§19) remains satisfied by the JSON+logs;
full artifacts are re-generable via `python -m ov_amd run <id>`.

## D15 — Cell substitution delimiter

The generic cell substitution used a `PAT:REP` string, which is ambiguous for
patterns containing `:` (e.g. `https://...`): the first-colon split turned the
huggingface.co mirror rewrite into a catastrophic "https → garbage"
replacement. Delimiter is now `PAT||REP`; affected attempts were re-run.

## D16 — Per-campaign HF endpoint probing (v0.2)

`HF_ENDPOINT` is no longer hardcoded to hf-mirror.com. Validation runners
have different egress policies: the reference network cannot reach
huggingface.co at all (D2), while the gfx1100 secondary runner reaches
huggingface.co directly and gets 429-rate-limited *by the mirror*. The
endpoint is therefore probed per campaign run (`environment.resolve_hf_endpoint`):
explicit `OV_AMD_HF_ENDPOINT` override > live probe of both endpoints >
recorded ambient `HF_ENDPOINT` hint. The choice and both probe results are
written into every metrics.json. Mirror source rewriting (D2) activates only
when the mirror is the selected transport.

## D17 — git+https transport rewrite on proxied runners (v0.2)

Notebooks installing `git+https://github.com/...` dependencies fail on
runners whose git CONNECT to github.com is blocked (a site git-wrapper forces
gh-proxy.org there, which 403s). `environment.resolve_git_transport` probes
with a real shallow clone (exactly what pip does, including the wrapper) and
records the outcome; when direct clone is unavailable the executor applies
structured substitutions rewriting `git+https://github.com/O/R.git[@ref]` to
`https://codeload.github.com/O/R/tar.gz/[ref|HEAD]` — same repo, same ref,
pure transport change, no delimiter encoding.

## D18 — Slim execution seed (v0.2)

The per-workload seed dropped transformers/sentence-transformers/optimum:
they drag the full torch stack into every environment while a minority of
notebooks need it (on throttled runners each env build paid a multi-hour
torch download for nothing). Notebooks declare extras via their own
requirements*.txt — installed at build time best-effort with a recorded
seed-only fallback — or via %pip cells executing inside the isolated venv,
where mutation is safe by design. Upstream declarations take priority over
any harness golden set.

## D19 — Weights/input provenance on restricted runners (v0.2)

Some official distribution hosts are unreachable from specific runners
(storage.openvinotoolkit.org, raw.githubusercontent.com, github release
assets). Twins and harness fetches carry explicit fallback chains limited to
official or well-known mirrors of the SAME asset (user-images.githubusercontent.com
notebook assets, HF community/official mirrors such as spacy/en_core_web_sm
and kadirnar/yolov8n-v8.0, ModelScope mirrors for gated HF repos). The URL
that actually served each file, and its sha256 where practical, are recorded
in evidence; provenance is never silently swapped.

## D20 — Multi-platform evidence identity (v0.2)

The campaign now spans two AMD platforms (Ryzen AI Max+395/gfx1151 reference
runner; EPYC 9334/gfx1100 secondary runner). Every attempt record carries
`platform_id` (CPU model + authoritative GPU arch from gcnArchName/rocminfo —
never derived from CUDA capability numbers, which mislabel gfx1100 as
"gfx110" and gfx1151 as "gfx115"). Generated reports group results by
platform; a green claim is always traceable to the exact hardware that
produced it.
