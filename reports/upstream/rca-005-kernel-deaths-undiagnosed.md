# RCA-005 — Kernel deaths, resolved as OpenVINO GPU-plugin codegen crashes (v0.2.2)

- **Workloads:** `ct-segmentation-quantize-nncf`, `gpu-device` (CPU attempts,
  v0.2.1: FAILED_COMPATIBILITY, reason KERNEL_DEATH_UNDIAGNOSED / OPENVINO_RUNTIME_DEVICE_ENUM)
- **Evidence (v0.2.1):** `results/ct-segmentation-quantize-nncf/20261006T192227Z-cpu/`,
  `results/gpu-device/20261006T220955Z-cpu/`
- **Evidence (current pin):** `results/gpu-device/20261007164858Z-cpu/` (fresh
  reproduction + kernel-death-diagnosis.json) and the ct-segmentation current-pin
  row (CPU-pinned re-run)
- **Layer (v0.2.2, RESOLVED):** OpenVINO **GPU plugin** kernel codegen — both
  deaths show Intel-GPU ISA inline-asm emitted for a Radeon and rejected by the
  assembler, hard-crashing the Python kernel
- **Status:** resolved attribution — see OV G findings OVG-002/OVG-003 in
  `reports/openvino-gpu-plugin-radeon-findings.md`

## Signature

```text
nbclient.exceptions.DeadKernelError: Kernel died
```

with, in stderr:

```text
<inline asm>:1:2: error: unknown directive
        .decl AA0 v_type=G type=ud num_elts=1
<inline asm>:4:1: error: unknown directive
.implicit_PSEUDO_INPUT AA1 offset=256 size=4
```

## Resolution (v0.2.2)

- **Attribution:** both notebooks reached the OpenVINO GPU plugin on the Radeon
  (ct-segmentation via its explicit `MULTI:CPU,GPU` device list; gpu-device via
  its hardcoded `device = "GPU"` walkthrough). The plugin's codegen emits
  Intel-GPU ISA assembly; the assembler rejects it; the kernel dies inside the
  native code — no Python traceback, no OOM.
- **Not OOM:** the v0.2.2 kernel-death diagnostics (cgroup memory.events +
  memory.peak + PSI, written per failing run as `kernel-death-diagnosis.json`)
  show zero container OOM events for the fresh gpu-device reproduction. The
  node-wide `/proc/vmstat` oom_kill counter is unscoped and non-attributive.
- **Consequent corrections:**
  - `gpu-device`: CPU-dimension outcome adjudicated `NOT_APPLICABLE`
    (GPU-purpose notebook; no meaningful CPU validation path), GPU-plugin
    crash recorded as OVG-003.
  - `ct-segmentation-quantize-nncf`: re-run with a documented
    `device_list=["CPU"]` pin so the CPU path is genuinely exercised; the
    GPU-plugin crash is recorded as OVG-002. The v0.2.1
    KERNEL_DEATH_UNDIAGNOSED compatibility failure was a device-attribution
    defect (the dying device was the GPU plugin, not the CPU).

## Honesty note

The v0.2.1 rows stayed FAILED_COMPATIBILITY because nothing external blocked
them and no cause was proven. v0.2.2 proves the cause from stderr signatures +
scoped OOM counters; the mis-attribution is corrected, and the class can never
recur silently (device-attribution guard + kernel-death diagnostics).

## Verification queued (reference runner)

1. Rerun under `OV_AMD_WALL_CAP` with kernel-core-pattern capture (dmesg tail
   recorded into evidence).
2. gpu-device: rerun with the iGPU hidden (`HSA_OVERRIDE_GFX_VERSION`/
   device filter) to split CPU-plugin vs GPU-plugin attribution.
