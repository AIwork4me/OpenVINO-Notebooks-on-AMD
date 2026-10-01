# FAQ

**Is this a fork of OpenVINO Notebooks?**
No. Upstream is executed from a pinned shallow clone; this repo contains only
wrappers, patches, twins, evidence and metadata.

**Does OpenVINO officially support AMD CPUs?**
This project makes no such claim. We report *community validation by this
project* on specific documented hardware/software. "Verified" means reproduced
successfully here — not certified by OpenVINO, Intel, AMD, or model authors.

**Why does the GPU code use `torch.cuda.*` on AMD?**
PyTorch on ROCm exposes AMD GPUs through the CUDA-compatible API surface. This
is the official, expected usage; `torch.version.hip` is checked and recorded as
proof of real ROCm execution.

**A notebook shows 🟡 VERIFIED_WITH_LIMITATIONS — what changed?**
Read the attempt `notes` and `patch_notes` in its evidence directory: skipped
UI-only cells, forced device selection, single repeatability run, or a
documented lower-precision retry. Every deviation is explicit.

**Why are some models downloaded from hf-mirror.com or ModelScope?**
`huggingface.co` is unreachable from this campaign's network. Mirrors serve
byte-identical weights for the same repo/revision; substitutions are recorded.

**Can I re-run a single workload?**
`python -m ov_amd run <workload> --device cpu|gpu`. For campaigns:
`python scripts/run_marathon.py --resume`.

**How is the compatibility matrix produced?**
Generated from `results/marathon-state.json` — never hand-edited. Run
`python -m ov_amd report` or `python scripts/generate_catalog.py`.
