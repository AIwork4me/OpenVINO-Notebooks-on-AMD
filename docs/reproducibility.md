# Reproducibility Guide

How to independently reproduce this project's validation results on AMD
hardware — and how to submit your own reproduced result.

## What "reproducible" means here

Every published result carries an evidence directory
(`results/<workload>/<timestamp>-<backend>/`) containing hardware/software
snapshots, the exact upstream pin, device-proof probe events, repeatability
aggregates, model identity + revision, and input provenance. A result is
*independently reproducible* when a third party can start from a fresh clone
and reach the same classification with the same model bytes and inputs.

## 1. Fresh checkout setup

```bash
git clone https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD.git
cd OpenVINO-Notebooks-on-AMD

uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]"
.venv-cpu/bin/python -m ov_amd doctor   # hardware/software/venv audit
```

Python **3.11+** is the package minimum; **3.12** is the validated reference
(the current upstream notebook stack also requires ≥3.11 — do not use 3.10).

## 2. Environment resolution

- The harness venv (`.venv-cpu`) only needs `pyyaml` + dev tools.
- Notebook execution uses **per-workload isolated venvs** (`.venvs/cpu/<key>/`)
  created from each notebook's declared dependencies and recorded in the
  evidence (`env.fingerprint`, `environment.lock.json`).
- ROCm twins run in bridged venvs over the system ROCm torch
  (`.venv-gpu`, and per-generation variants `.venv-gpu-tf446`,
  `.venv-gpu-tf457`, `.venv-gpu-tf5d06` when an official model repo pins a
  specific transformers generation). Which interpreter a twin used is recorded
  in `workloads/<id>/workload.yaml` (`gpu.python`) and the evidence
  `software.json`.

## 3. Model downloads

Models are resolved from the pinned revision at execution time:

- **HF-hosted models**: revision-pinned in every twin (`REVISION = "<sha>"` in
  `workloads/<id>/rocm/run.py`). On networks where huggingface.co is
  unreachable, the project's probed mirror transport (`HF_ENDPOINT`) is used
  and recorded — a transport substitution, never an identity substitution.
- **ModelScope mirror fallbacks** (deepseek-r1, SD-2.1, SDXL): recorded in the
  evidence with the mirror commit id.
- **Direct weights** (hello-detection yolov8n.pt): SHA-256 enforced at fetch
  time; the GitHub release asset and the official HF-org mirror were verified
  byte-identical.

## 4. Managed input assets (SHA-256)

Runtime input files are declared in [`assets/manifests/assets.yaml`](../assets/manifests/assets.yaml)
with a verified SHA-256, license, and source URL. Resolution order:

1. an explicit user-supplied path (`--input` / `OV_AMD_ASSET_<ID>`) — verified
   or hard-fail, never silently substituted
2. a repository-committed fixture (`assets/files/<id>`) — only for assets
   whose license permits redistribution
3. the managed cache (`.cache/assets/`) — verified; corrupt copies are
   quarantined
4. download from the declared source URLs — atomic temp file, hash-verified
   before promotion

Non-redistributable assets (e.g. `courtroom.wav`) are never committed; they
are downloaded and hash-verified at run time. Run a twin with an explicit
asset via `OV_AMD_ASSET_COURTROOM_ASR_WAV=/path/to/courtroom.wav`.

## 5. CPU path (OpenVINO on Ryzen)

```bash
.venv-cpu/bin/python -m ov_amd run <workload-id> --device cpu
.venv-cpu/bin/python -m ov_amd compare <workload-id>
# or the full resumable campaign:
.venv-cpu/bin/python scripts/run_marathon.py --cpu-only
```

Requires the pinned upstream snapshot: `.venv-cpu/bin/python
scripts/fetch_upstream.py` (codeload tarball; on throttled networks the
surgical blobs route is used — see `upstream/openvino-notebooks.json`).

## 6. ROCm path (PyTorch on Radeon)

Prerequisites: ROCm runtime with a HIP-enabled PyTorch visible to the
interpreter (verify: `python -c "import torch; print(torch.version.hip,
torch.cuda.is_available())"`), plus per-twin deps (each twin's imports are its
declaration). Run one twin:

```bash
mkdir -p /tmp/ev && cd /tmp/ev
.venv-gpu/bin/python <repo>/workloads/<id>/rocm/run.py --evidence-dir .
```

Or through the campaign runner (Evidence Schema v2 wrapper, repeatability
gate): `.venv-cpu/bin/python scripts/revalidate.py <id>` / `run_marathon.py
--gpu-only`. Some twins need their recorded transformers-generation venv
(`workload.yaml: gpu.python`).

## 7. Reusing caches

Model caches (`HF_HOME`, ModelScope, per-workload weights dirs) are
content-addressed and safe to reuse; every fetch re-verifies hashes where a
manifest exists. Deleting `.cache/` exercises the full cold-start path.

## 8. Hardware requirements

Reference validation hardware (recorded per evidence in `hardware.json`):
AMD EPYC 9334 + Radeon gfx1100 (48 GB), ROCm 6.16.13 driver / torch
2.9.1+hip. **Not every verified workload requires this class of hardware** —
model memory footprints are recorded in each evidence `metrics.json`
(`peak_gpu_memory_allocated_gb`). Conversely, a model verified here is not
guaranteed on smaller GPUs or other gfx architectures; one twin
(hello-detection) retains evidence from gfx1151 exactly as recorded.

## 9. Interpreting failures

- **BLOCKED_*** — external condition (network host, gated model, missing
  dependency, timeout, disk/RAM). Not an AMD CPU incompatibility.
- **FAILED_COMPATIBILITY** — reproduced runtime/model incompatibility on a
  valid environment (each carries an RCA under `reports/upstream/` or in the
  v0.3.1 final report).
- Network-dependent hosts known blocked on the reference runner:
  `storage.openvinotoolkit.org`, `raw.githubusercontent.com`,
  `dl.fbaipublicfiles.com`, qianwen OSS, GitHub user-attachment S3. Your
  network may differ — that is exactly why outcomes record the precise error.

## 10. Submitting an independently reproduced result

1. Reproduce the run (sections 5/6) on your AMD hardware; keep the evidence
   directory the runner writes.
2. Verify the evidence contract: device proof, ≥3 measured runs (or the
   documented single-run limitation), model identity + revision, input asset
   provenance block.
3. Open a PR adding `results/<workload>/<ts>-<backend>/` (evidence only —
   never hand-edit `marathon-state.json`; the maintainers re-ingest) and
   describe your hardware in the PR body. See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Known reproducibility limitations (honest record)

- `courtroom.wav`, `yolov8n.pt`, and some model weights download at run time
  from hosts that may be blocked on your network (section 9); the manifest
  gives the exact SHA-256 so any byte-identical copy you already have can be
  supplied explicitly.
- Historical evidence recorded before v0.3.1 does not carry the
  `metric_semantics` block or correctness grading; the RTF values in kokoro /
  whisper-asr-genai evidence recorded before v0.3.1 use the inverted
  definition (audio/inference) — new runs report standard RTF plus a separate
  `realtime_speed_factor`, and the semantics are stamped on every new
  evidence.
- The SD-2.1 checkpoint is HF-gated; the pinned ModelScope mirror commit is
  the recorded transport. An operator with HF access can pin HF explicitly
  (`OV_AMD_SD21_HF_REV`).
