# Preflight System Audit (generated 2026-10-01)

## Available resources

| Resource | Value |
|---|---|
| CPU | AMD RYZEN AI MAX+ PRO 395 w/ Radeon 8060S — 16C/32T, ≤5.19 GHz |
| RAM | 94 GiB total (≈90 GiB available at start) |
| Swap | 8 GiB |
| Disk | 1.9 TB volume, 1.3 TB free (29% used) |
| OS | Ubuntu 24.04.4 LTS, kernel 6.17.0-1032-oem |
| Python | 3.12.3 (system); venvs provisioned via uv |
| GPU | AMD Radeon Graphics (Strix Halo iGPU), gfx1151, rocminfo OK, rocm-smi OK |
| NPU | RyzenAI-npu5 (aie2p) enumerated by rocminfo |
| ROCm | 7.2.1 at /opt/rocm |
| Git / gh | git 2.43.0; gh 2.45.0 authenticated as AIwork4me (repo+workflow scopes) |

## Network reachability (HTTP status from this host)

| Endpoint | Status |
|---|---|
| api.github.com | 200 ✅ |
| github.com (clone) | working ✅ |
| pypi.org | 200 ✅ |
| storage.openvinotoolkit.org | 200 ✅ |
| huggingface.co | **unreachable (000) ❌** |
| hf-mirror.com | 200 ✅ (used as HF_ENDPOINT transport mirror — decision D2) |
| modelscope.cn | 302→200 ✅ |

## Detected limitations & risk assessment

1. **huggingface.co blocked** → all HF traffic routed via `HF_ENDPOINT=https://hf-mirror.com`;
   ModelScope fallback where notebooks allow. Recorded per-attempt.
2. **No torch/openvino in system Python** → dedicated venvs (`.venv-cpu` baseline +
   on-demand installs; `.venv-gpu` ROCm PyTorch for twins).
3. **OpenVINO device enumeration must be confirmed on AMD** — preflight records
   `core.available_devices` per evidence dir; device honesty policy D8 applies
   (AUTO could select NPU/GPU if enumerated).
4. **ROCm torch wheel availability for gfx1151** to be probed before GPU twins
   (official index reachable; fallback HSA override only if wheels lack gfx1151).
5. **Large-model workloads** (>30 GB weights) impractical on 94 GB shared CPU/iGPU
   RAM → guarded by SKIPPED_RESOURCE policy.
6. GitHub git endpoint historically flaky on this network — probe before push.

## Verdict

Environment suitable for the full campaign: CPU sweep immediately; ROCm twins
after wheel provisioning. Bounded retries + checkpointing protect against
transient network events.
