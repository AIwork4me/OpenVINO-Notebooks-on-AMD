# RCA-001 — Parler-TTS: OpenVINO CPU plugin rejects f32×bf16 BrgemmCPU node

- **Workload:** `parler-tts-text-to-speech` (CPU attempt, FAILED_COMPATIBILITY)
- **Evidence:** `results/parler-tts-text-to-speech/20261007T011344Z-cpu/`
- **Layer (preliminary):** OpenVINO CPU plugin / oneDNN snippets (brgemm.cpp)
- **Status:** candidate — reproduced once on reference runner; not yet minimized

## Error

```text
RuntimeError: Exception from src/inference/src/cpp/core.cpp:126:
Exception from src/common/snippets/src/op/brgemm.cpp:135:
BrgemmCPU node has incompatible input element types: f32 and bf16
```

Raised from `ov.Core.compile_model(...)` inside the notebook's optimized
(kvantized bf16) Parler-TTS export. Device: CPU plugin on AMD Ryzen AI Max 395
(openvino `2026.4.1` line, see evidence `software-after.json`).

## Analysis

- The exported model mixes f32 and bf16 inputs into one BrgemmCPU (snippets)
  node. The snippets brgemm kernel requires uniform input element types on this
  CPU plugin build; the CPU plugin (oneDNN on AMD Zen 5) rejects the mix at
  graph construction.
- The workload environment was valid (per-workload venv, upstream requirements
  installed; conversion by optimum-cli completed; failure occurs at compile,
  after conversion).
- Not environment/network/model-access related: genuine runtime compatibility
  failure → classified FAILED_COMPATIBILITY.

## Reproduction path

1. `python -m ov_amd run parler-tts-text-to-speech --device cpu` on the
   reference runner (env auto-builds from the notebook's requirements).
2. Evidence of the failing compile: last run `stderr.log` + `executed.ipynb`.

## Minimization target (next step, requires reference runner)

Convert the Parler-TTS decoder with optimum-cli `--weight-format bf16`, load
with `ov.Core().compile_model(model, "CPU")` in a 5-line script, attach the IR.
Then bisect: plugin build (`OPENVINO_LOG_LEVEL=5`), `ov.Type` of the failing
node inputs, oneDNN CPU caps (`ONEDNN_MAX_CPU_ISA`).

## Upstream material

Not yet ready to file upstream (not minimized). When minimized: candidate for
openvinotoolkit/openvino (snippets/brgemm input-type check) with the IR
attached.
