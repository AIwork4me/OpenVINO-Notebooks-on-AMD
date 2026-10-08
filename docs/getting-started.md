# Getting Started

## Prerequisites

- Linux x86_64, **Python 3.11+** (3.12 is the validated reference; the current
  upstream notebook stack also requires ≥3.11 — 3.10 is NOT supported)
- [uv](https://docs.astral.sh/uv/) (or plain pip/venv)
- For GPU twins: a ROCm installation with a supported AMD GPU. Results in this
  repository were recorded on two platforms, each pinned in the evidence's
  `hardware.json`: gfx1100 (Radeon, 48 GB; ROCm 6.16.13 driver, torch
  2.9.1+hip) for 19 of the 20 verified twins and gfx1151 (Radeon 8060S) for
  hello-detection. A model verified on one gfx architecture is not guaranteed
  on another — every row records the platform it actually ran on.

## Set up the CPU validation environment

```bash
git clone https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD.git
cd OpenVINO-Notebooks-on-AMD

uv venv .venv-cpu --python 3.12
uv pip install --python .venv-cpu/bin/python -e ".[dev]" \
    openvino openvino-genai openvino-tokenizers nncf optimum \
    "transformers>=4.51" diffusers accelerate safetensors huggingface_hub \
    sentencepiece pillow opencv-python matplotlib pandas tqdm scipy \
    scikit-learn scikit-image gradio onnx onnxruntime \
    nbconvert nbclient nbformat ipykernel jupyter_client
uv pip install --python .venv-cpu/bin/python torch --index-url https://download.pytorch.org/whl/cpu
```

## Get the upstream notebooks (pinned)

```bash
git clone --depth 1 https://github.com/openvinotoolkit/openvino_notebooks.git .cache/upstream
python scripts/discover_upstream.py     # writes upstream/ + catalog/notebooks.yaml
```

## Daily commands

```bash
.venv-cpu/bin/python -m ov_amd doctor   # audit hardware, venvs, upstream pin
.venv-cpu/bin/python -m ov_amd list                   # every catalog entry + status
.venv-cpu/bin/python -m ov_amd info <workload>        # entry, config, attempts, evidence
.venv-cpu/bin/python -m ov_amd run <workload> --device cpu
.venv-cpu/bin/python -m ov_amd run <workload> --device gpu
python -m ov_amd compare <workload>     # CPU vs GPU metrics
python -m ov_amd report                 # regenerate catalog/compatibility.*
python scripts/run_marathon.py --resume # unattended campaign
```

## Network notes

If `huggingface.co` is unreachable, the harness automatically uses
`HF_ENDPOINT=https://hf-mirror.com` (weights are identical; the endpoint is a
transport mirror). Override by exporting `HF_ENDPOINT` yourself.
