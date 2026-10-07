# RCA-003 — Qwen3 (OpenVINO GenAI LLMPipeline): clEnqueueMapBuffer CL_INVALID_VALUE via GPU plugin on AMD Radeon

- **Workload:** `qwen3` (CPU-path attempt, FAILED_COMPATIBILITY)
- **Evidence:** `results/qwen3/20261006T183929Z-cpu/`
- **Layer (preliminary):** OpenVINO GPU plugin (OpenCL) executing on AMD Radeon
  iGPU (gfx1151) — the notebook's device resolution picked the GPU on the CPU
  validation path; the CPU plugin was not the failing component
- **Status:** candidate — single reproduction; not yet minimized

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
- Outcome kept as FAILED_COMPATIBILITY with reason OPENVINO_RUNTIME_CL_MAP; the
  CPU-path revalidation of this notebook is queued with failure-retry
  remediation (device pinning is already the harness default for
  `device_widget` notebooks; this notebook passes its own device argument).

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
