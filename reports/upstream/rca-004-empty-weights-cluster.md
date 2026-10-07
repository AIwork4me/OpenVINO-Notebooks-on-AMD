# RCA-004 — "Empty weights data in bin file" cluster (model artifact integrity)

- **Workloads:** `flux.1-image-generation`, `muse-glimmer`, `qwen3.8-mtp`,
  `gemma4`, `llm-code-assistant` (empty .bin), plus the corrupt-archive family
  `freevc-voice-conversion`, `yoloe-26-open-vocabulary`,
  `bernini-r-image-video` (missing/short checkpoint), `minicpm-o-omnimodal-chatbot`
  (missing safetensors shard), `multimodal-rag-llamaindex` (missing converted
  .bin), `fastdraft_deepseek` (missing model dir)
- **Outcomes:** all BLOCKED_RESOURCE / MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT —
  deliberately NOT classified as compatibility failures
- **Layer:** download/export artifact integrity (transport + conversion
  outputs), not the OpenVINO runtime

## Signature

```text
Check 'm_weights_provider' failed at src/core/xml_util/src/xml_deserialize_util.cpp:887:
Empty weights data in bin file or bin file cannot be found!
```

or

```text
RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory
```

## Analysis

- Common shape: the notebook downloads/exports a model and then loads it; the
  weights file is empty, truncated, or absent at load time. The IR (.xml)
  exists, so conversion "succeeded" far enough to write it; the weights side is
  short/zero bytes. On the reference network (throttled egress), large HF
  downloads silently truncating mid-transfer is the leading hypothesis; a
  secondary hypothesis is optimum-cli export writing an empty .bin when the
  source checkpoint itself was truncated.
- The OpenVINO runtime behaves correctly: it refuses to load an empty weights
  blob.
- These are NOT AMD/OpenVINO compatibility failures; they are artifact-integrity
  blockers on the reference network. All affected rows carry outcome
  BLOCKED_RESOURCE with reason MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT.

## Verification queued (v0.3 failure-retry, reference runner)

1. Re-download with resumable transport (hf_transfer / direct endpoint on an
   unthrottled runner) and verify `sha256` + non-zero size before conversion.
2. If the artifact still loads empty from a verified download, escalate the
   specific workload to FAILED_COMPATIBILITY with a minimized export/load
   script.

## Upstream material

None (not an upstream defect at this evidence level).
