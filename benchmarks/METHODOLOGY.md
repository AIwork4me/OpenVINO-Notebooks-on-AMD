# Benchmark Methodology

All public numbers in this repository follow the rules below. Numbers without
a link to an evidence directory must be treated as unpublished.

## Measurement

- Wall-clock timing via `time.monotonic`/`perf_counter` boundaries around the
  measured region; process-level wall clock for notebook executions.
- Warmup ≥1 measured-then-discarded run where applicable; reported runs ≥3 (5
  where inexpensive). Median and P95 reported (nearest-rank P95; sample size
  always disclosed). Aggregates live in each attempt's `aggregate.json`
  (`successful_runs`, `required_runs`, `latencies_s`, `median_latency_s`,
  `p95_latency_s`, `repeatability_passed`).
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

## Modes (explicit, per benchmark)

- **DEPLOYMENT**: each path in its reasonable optimized configuration
  (e.g. CPU OpenVINO INT8 vs GPU ROCm BF16). Never described as
  apples-to-apples.
- **CONTROLLED**: matched precision/settings where feasible, disclosed per
  workload.

Every published benchmark block must disclose: model, model revision,
precision, batch, input shape/sequence length, warmup, number of runs, median,
P95, RAM/VRAM, OpenVINO version, PyTorch version, ROCm version, hardware.
Twin scripts emit these into `metrics.json`; the report generator carries them
forward.

## Comparisons (twin-safety enforced)

`python -m ov_amd compare <workload>` enforces the policy mechanically
(`ov_amd.benchmark.COMPARISON_POLICY`):

| Twin level | Published comparison | Direct speedup |
|---|---|---|
| EXACT_TWIN | quantitative, same model + revision + input, precision disclosed | **allowed** |
| WORKLOAD_TWIN | side-by-side numbers with the pipeline difference stated | **never** |
| CONCEPT_MAPPING | none | never |
| OPENVINO_SPECIFIC | GPU NOT_APPLICABLE | never |
| NOT_CLASSIFIED | none (must be classified first) | never |

Example: CPU path runs OpenVINO model A, GPU twin runs YOLOv8n for the same
task but a different model object → WORKLOAD_TWIN → side-by-side only; any
direct speedup claim for such rows is a reporting bug and fails review.

No EXACT_TWIN exists in the current dataset (twin levels: 160 WORKLOAD_TWIN,
10 OPENVINO_SPECIFIC, 1 CONCEPT_MAPPING) — therefore **CPU and GPU results in
this repository are deployment references, not direct benchmark comparisons**.

Generative outputs are compared by workload-appropriate correctness contracts
(`workloads/<id>/workload.yaml validation:`), never by universal pixel
equality or waveform identity.
