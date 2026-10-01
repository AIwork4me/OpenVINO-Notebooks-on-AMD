# Benchmark Methodology

All public numbers in this repository follow the rules below. Numbers without
a link to an evidence directory must be treated as unpublished.

## Measurement

- Wall-clock timing via `time.monotonic`/`perf_counter` boundaries around the
  measured region; process-level wall clock for notebook executions.
- Warmup ≥1 measured-then-discarded run; reported runs ≥3 (5 where
  inexpensive). Median and P95 reported (P95 over small samples = second
  largest; sample size always disclosed).
- Peak RSS via `/proc/self/status` (`VmHWM`) sampling in twin scripts; GPU
  memory via `torch.cuda.max_memory_allocated()` + rocm-smi where used.
- CPU execution: OpenVINO as configured by the upstream notebook (FP32/INT8),
  32 threads (full Ryzen AI Max+ 395 CCD), `OMP_NUM_THREADS` recorded in every
  evidence dir.
- GPU execution: PyTorch ROCm, BF16/FP16 as declared per twin; power/thermal
  state not artificially fixed (system default governor) — disclosed here once.

## Metrics per task family

| Family | Metrics |
|---|---|
| LLM | TTFT, TPOT, prefill tokens/s, decode tokens/s |
| VLM | vision encode time, TTFT, decode tokens/s |
| OCR | page latency, pages/min, CER where practical |
| ASR | latency, RTF, WER/CER where practical |
| TTS | TTFA where meaningful, RTF, generated duration |
| Image generation | s/image, steps/s, peak memory |
| Vision | latency, FPS, task metric where practical |
| All | model load time, peak RAM/VRAM, run count, median, P95, correctness |

## Modes

- **DEPLOYMENT**: each path in its reasonable optimized configuration
  (CPU OpenVINO INT8 vs GPU ROCm BF16). Not apples-to-apples and never
  described as such.
- **CONTROLLED**: matched precision/settings, disclosed per workload.

## Comparisons

- CPU↔GPU numbers come from the same pinned upstream commit / model revision
  whenever the twin level is EXACT_TWIN; for WORKLOAD_TWIN the pipeline
  difference is stated next to the numbers.
- Generative outputs are compared by workload-appropriate correctness, never
  by universal pixel equality.
