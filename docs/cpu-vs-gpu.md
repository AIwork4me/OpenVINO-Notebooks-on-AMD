# CPU vs GPU: What Is Compared, and What Is Not

## Two AMD paths

| Path | Runtime | Device | Typical precision |
|---|---|---|---|
| Ryzen CPU | OpenVINO (as used by the upstream notebook) | AMD Ryzen CPU | FP32 / INT8 when the notebook does it |
| Radeon GPU | PyTorch on ROCm | AMD Radeon (gfx…​) | BF16/FP16 as configured |

On PyTorch-ROCm, `torch.cuda` APIs are the **official and expected** way to
address AMD GPUs — this is not a CUDA mislabel.

## Benchmark modes

- **DEPLOYMENT** — each path in its reasonable optimized configuration
  (e.g. CPU OpenVINO INT8 vs GPU ROCm BF16). *Not* apples-to-apples.
- **CONTROLLED** — precision/settings matched as closely as reasonably
  possible. Only called apples-to-apples when they truly are.

Public numbers always link `benchmarks/METHODOLOGY.md` and the evidence
directory they came from.

## What we never claim

- No universal "OpenVINO vs ROCm" winner statement — comparisons are
  per-workload, per-configuration, with disclosed settings.
- No pixel-exact or token-exact cross-runtime equality requirements for
  generative models; correctness is workload-appropriate (see
  validation-policy.md).
