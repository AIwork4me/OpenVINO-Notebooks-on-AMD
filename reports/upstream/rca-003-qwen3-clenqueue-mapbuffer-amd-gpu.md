# RCA-003 — Qwen3 (OpenVINO GenAI LLMPipeline): clEnqueueMapBuffer CL_INVALID_VALUE via GPU plugin on AMD Radeon

- **Workload:** `qwen3`
- **Evidence (GPU-plugin failure):** `results/qwen3/20261006T183929Z-cpu/` (device proof
  PROVEN_GPU for a CPU-requested attempt — the upstream notebook hardcodes
  `device = "GPU"`; cells 8/14/22)
- **Evidence (CPU recovery, current pin 5f0b2b5):** `results/qwen3/20261007172217Z-cpu/` —
  the notebook completed end-to-end on CPU with a documented minimal device pin
  (`device = "CPU"`), positive CPU device proof, speculative-decoding generations
  produced; outcome VERIFIED_WITH_LIMITATIONS (single-run policy for large models)
- **Layer:** OpenVINO GPU plugin (OpenCL) executing on AMD Radeon — NOT the CPU plugin
- **Status:** RESOLVED (v0.2.2 device-attribution correction):
  - the v0.2.1 "CPU FAILED_COMPATIBILITY" was a mis-attributed GPU-plugin failure;
  - the genuine CPU path VERIFIES on AMD (EPYC 9334, openvino 2026.4.1);
  - the GPU-plugin-on-Radeon finding is retained separately as OVG-001 in
    `reports/openvino-gpu-plugin-radeon-findings.md`.

## Error

```text
[GPU] clEnqueueMapBuffer, error code: -30 CL_INVALID_VALUE
```

Raised inside `ov_genai.LLMPipeline` construction/first inference.

## Analysis

- OpenVINO's GPU plugin is implemented against Intel OpenCL extensions; on AMD
  Radeon (gfx1151 via ROCm's OpenCL/PAL) a buffer-map call returns
  CL_INVALID_VALUE (-30), which surfaces as a runtime error rather than a
  graceful "device unsupported" message.
- This is a genuine data point for "OpenVINO GPU plugin on AMD Radeon" — the
  plugin advertises the device, then fails at runtime. The CPU plugin path for
  this notebook was not exercised to completion (device selection picked GPU).
- v0.2.1 recorded this as a CPU compatibility failure — a device-attribution
  defect (the outcome guard in `ov_amd/outcomes.py` now makes that class of
  mis-attribution impossible: a PROVEN_GPU cpu attempt can never yield a CPU
  compatibility verdict).
- v0.2.2 re-ran the notebook with the documented `device = "CPU"` pin: the CPU
  path works (see recovery evidence above). The ROCm/PyTorch twin for qwen3 on
  Radeon remains independently VERIFIED — three separate execution paths, three
  separate results.

## Reproduction path

`python -m ov_amd run qwen3 --device cpu` on the reference runner (Ryzen AI Max
395 + Radeon 8060S). Failing stage: `stderr.log` of the last run.

## Minimization target

`ov_genai.LLMPipeline(model_dir, device="GPU")` on the converted Qwen3 IR in a
5-line script on the iGPU; capture the CL error plus
`clinfo` output. Layer attribution then splits cleanly: plugin-vs-driver.

## Upstream material

Not yet ready (not minimized). Candidate for openvino docs ("GPU plugin
support matrix on non-Intel OpenCL") rather than a code bug.
