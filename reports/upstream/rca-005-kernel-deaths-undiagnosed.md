# RCA-005 — Undiagnosed kernel deaths (ct-segmentation-quantize-nncf, gpu-device)

- **Workloads:** `ct-segmentation-quantize-nncf`, `gpu-device` (CPU attempts,
  FAILED_COMPATIBILITY, reason KERNEL_DEATH_UNDIAGNOSED / OPENVINO_RUNTIME_DEVICE_ENUM)
- **Evidence:** `results/ct-segmentation-quantize-nncf/20261006T192227Z-cpu/`,
  `results/gpu-device/20261006T220955Z-cpu/`
- **Layer:** unresolved — kernel process died without a Python-level traceback
- **Status:** open; kept as compatibility failures because the environment was
  valid and the failure is not attributable to any external blocker

## Signature

```text
nbclient.exceptions.DeadKernelError: Kernel died
```

- ct-segmentation: during NNCF quantization (memory/compute-heavy). No OOM
  lines captured; RAM guard did not trigger.
- gpu-device: during OpenVINO device enumeration with an AMD Radeon iGPU
  present (the notebook's purpose is listing devices). Adjacent to RCA-003
  (GPU plugin on AMD) — plausibly the same plugin-vs-driver layer, crashing
  hard instead of raising.

## Honesty note

These stay FAILED_COMPATIBILITY precisely because nothing external blocked
them and no alternative cause is proven. They are NOT counted as blocked. If
post-mortem shows OOM (kernel log) they must move to BLOCKED_RESOURCE; if the
GPU-plugin link is confirmed, gpu-device merges into RCA-003.

## Verification queued (reference runner)

1. Rerun under `OV_AMD_WALL_CAP` with kernel-core-pattern capture (dmesg tail
   recorded into evidence).
2. gpu-device: rerun with the iGPU hidden (`HSA_OVERRIDE_GFX_VERSION`/
   device filter) to split CPU-plugin vs GPU-plugin attribution.
