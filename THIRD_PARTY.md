# Third-Party Notices

## OpenVINO Notebooks (openvinotoolkit/openvino_notebooks)

This project executes notebooks from the upstream repository at a pinned
commit (see `upstream/openvino-notebooks.json`). OpenVINO Notebooks is
copyright its authors and licensed under its own terms (Apache-2.0) — this
repository's license does not override it, and attribution requirements for
modified files are respected. We do not mirror upstream content; the pinned
clone lives outside the repository in `.cache/` (gitignored).

## OpenVINO / openvino-genai / NNCF

© Intel Corporation and contributors, Apache-2.0.

## PyTorch / ROCm stacks

PyTorch: BSD-style, © Meta Platforms and contributors. ROCm: MIT/© Advanced
Micro Devices, Inc. GPU twins use the official PyTorch ROCm builds; `torch.cuda`
APIs are the documented interface to AMD GPUs under ROCm.

## Models

Model weights executed by workloads (LLM/VLM/ASR/TTS/diffusion/…) remain under
their own licenses (e.g. Apache-2.0, Llama community license, Qwen Apache-2.0,
OpenRAIL, Coqui MPL…). Nothing in this repository's license changes model
licenses. `workloads/<id>/workload.yaml` records `model.license` where known.

## Datasets & test assets

Dataset licenses remain independent of this repository. Small fixtures inside
`tests/data/` are synthetic or attributed.

## Transport mirrors

Where `huggingface.co` is unreachable, weights are fetched via transport
mirrors (`hf-mirror.com`) or ModelScope for the same repo/revision;
substitutions are recorded per attempt in the evidence directories.
