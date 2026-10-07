# OpenVINO GPU Plugin on AMD Radeon — Device-Specific Compatibility Findings

This project validates **three distinct execution paths**. They are never
conflated:

```text
1. OpenVINO CPU plugin   on AMD Ryzen      (the CPU matrix — Pillar A)
2. OpenVINO GPU plugin   on AMD Radeon     (this report — device-specific findings)
3. ROCm / PyTorch        on AMD Radeon     (ROCm twins — Pillar B)
```

A failure of path 2 says nothing about path 1 or path 3. Rows in the CPU
compatibility matrix are derived only from attempts with positive CPU device
proof (or explicit CPU-attribution rules — see the device-attribution guard in
`ov_amd/outcomes.py`).

## Finding OVG-001 — `clEnqueueMapBuffer CL_INVALID_VALUE` at pipeline construction

- **Workload:** `qwen3` (`supplementary_materials/notebooks/qwen-3/qwen3.ipynb`)
- **Runtime:** OpenVINO GenAI `LLMPipeline(model_path, "GPU", scheduler_config=...)`
- **Device:** AMD Radeon (gfx1151) via the OpenVINO GPU (OpenCL) plugin
- **Plugin frame:** `src/plugins/intel_gpu/src/runtime/ocl/ocl_memory.cpp:74`
- **Error:**

```text
RuntimeError: Exception from src/inference/src/cpp/core.cpp:117:
Exception from src/inference/src/dev/plugin.cpp:54:
Exception from src/plugins/intel_gpu/src/runtime/ocl/ocl_memory.cpp:74:
[GPU] clEnqueueMapBuffer, error code: -30 CL_INVALID_VALUE
```

- **Evidence:** `results/qwen3/20261006T183929Z-cpu/run-01/` — device-proof
  records `genai_device_args: ["GPU"]`, `state: PROVEN_GPU` for the attempt
  that was *requested* as CPU (the upstream notebook hardcodes
  `device = "GPU"`; cells 8/14/22). GPU-plugin runs:
  `results/qwen3/20261001T102549Z-gpu` et al.
- **RCA:** `reports/upstream/rca-003-qwen3-clenqueue-mapbuffer-amd-gpu.md`
- **Interpretation:** constructing the speculative-decoding LLMPipeline with
  the OpenVINO GPU plugin on this Radeon (gfx1151, OpenCL) fails inside
  `clEnqueueMapBuffer` with `CL_INVALID_VALUE` — a GPU-plugin/driver-level
  incompatibility for this model's buffer mapping pattern.
- **Impact on the CPU row:** none. The v0.2.1 matrix recorded this as a CPU
  `FAILED_COMPATIBILITY`; that was a device-attribution defect, corrected in
  v0.2.2 (fresh CPU-forced run; see the qwen3 row and
  `reports/v0.2.2-release-report.md`).
- **Impact on the ROCm row:** none. The qwen3 ROCm/PyTorch twin on Radeon is
  independently VERIFIED (`PROVEN_GPU`, workload-correct, repeatable) — the
  PyTorch/ROCm stack runs the same model family fine on the same GPU.

## Finding OVG-002 — GPU-plugin inline-asm compile crash during NNCF quantization (kernel death)

- **Workload:** `ct-segmentation-quantize-nncf`
- **Runtime:** OpenVINO CPU+GPU (`MULTI:CPU,GPU`) compile during NNCF int8 quantization
- **Device:** AMD Radeon via the OpenVINO GPU (OpenCL) plugin
- **Error (run stderr tail):**

```text
<inline asm>:4:1: error: unknown directive
.implicit_PSEUDO_INPUT AA1 offset=256 size=4
<inline asm>:5:1: error: invalid instruction
mov (M1_NM,1) AA0(0,0)<1> AA1(0,0)<0>;1,0>
nbclient.exceptions.DeadKernelError: Kernel died
```

- **Evidence:** `results/ct-segmentation-quantize-nncf/20261006T192227Z-cpu/run-01/`
  (device_used GPU, proof AUTO_UNRESOLVED; recorded pre-attribution-fix)
- **Interpretation:** the OpenVINO GPU plugin's kernel codegen emitted Intel-GPU ISA
  assembly that the assembler rejected, crashing the Python kernel — a hard
  GPU-plugin failure on Radeon, not an OOM and not a CPU-plugin defect.
- **Impact on the CPU row:** the v0.2.1 `KERNEL_DEATH_UNDIAGNOSED` compatibility
  failure was device-misattributed; v0.2.2 re-runs the notebook with
  `device_list=["CPU"]` (documented pin) for a genuine CPU verdict.

## Finding OVG-003 — GPU-plugin inline-asm compile crash in the gpu-device notebook (kernel death)

- **Workload:** `gpu-device`
- **Runtime:** OpenVINO GPU plugin property walkthrough / model compile (`device = "GPU"` hardcoded)
- **Device:** AMD Radeon (gfx1151 reference runner) via the OpenCL plugin
- **Error (run stderr):** same class as OVG-002 — Intel-GPU ISA `.decl`/`.implicit_PSEUDO_INPUT`
  inline-asm directives rejected by the assembler, then `DeadKernelError`.
- **Evidence:** `results/gpu-device/20261006T220955Z-cpu/run-01/`
- **Interpretation:** identical GPU-plugin codegen crash family as OVG-002,
  triggered from the gpu-device walkthrough notebook.
- **CPU applicability adjudication (v0.2.2):** the notebook is GPU-purpose by
  construction (hardcoded `device = "GPU"` for property queries, compilation,
  cache/throughput experiments; only `core.available_devices` is
  backend-agnostic). There is no meaningful AMD CPU validation path — the CPU
  outcome is `NOT_APPLICABLE` with provenance, and this GPU-plugin behavior is
  the recorded result for the GPU dimension instead.

## Upstream-documented GPU-plugin constraints (informational)

- `gpt-oss-20b` is documented upstream as not supported with the OpenVINO GPU
  plugin (llm-chatbot model list note at the pinned snapshot).
