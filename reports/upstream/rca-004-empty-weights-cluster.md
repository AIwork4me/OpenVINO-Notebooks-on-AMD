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
- **v0.2.2 status:** upstream fixed the root transport defect in
  `download_file()` (commit `f1958fc8c94a`, "Fix download_file() reusing a
  corrupted file after an interrupted download (#3667)" — atomic `.part` +
  `enforce_content_length`). The 8-workload evidence-derived cluster was
  re-attempted on the current pin under the fixed helper; see
  "Recovery results (v0.2.2)" below.

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

## Root cause (confirmed upstream)

Interrupted downloads left a partial file on disk; the pre-fix
`download_file()` treated any existing file as complete and reused it
(`if filepath.exists(): return`), so a truncated multi-GB weights blob sailed
through to model load. The upstream fix streams to `<name>.part` with the
transport-enforced content length and atomically replaces the destination — a
partial artifact can no longer masquerade as a complete one.

## Recovery results (v0.2.2, current pin 5f0b2b5)

```text
flux.1-image-generation   RECOVERED → VERIFIED_WITH_LIMITATIONS (clean 8.7GB re-download,
                          notebook completed, positive CPU device proof)
llm-code-assistant        corruption RESOLVED (clean ~15GB download + optimum conversion);
                          row now blocks later at a foreign-repo raw fetch (chat_sample.py
                          from openvino.genai) → BLOCKED_NETWORK (egress-restricted network)
gemma4                    corruption RESOLVED path entered; row now blocks at a GitHub
                          LFS asset download (github.com tunnel-blocked) → BLOCKED_NETWORK
qwen3.8-mtp               row blocks at storage.openvinotoolkit.org sample fetch
                          (proxy-refused host) → BLOCKED_NETWORK
freevc-voice-conversion   row blocks at storage.openvinotoolkit.org checkpoint fetch
                          (proxy-refused host) → BLOCKED_NETWORK
muse-glimmer              re-run with snapshot-asset preseeding (nyc.jpg) — see matrix
minicpm-o-omnimodal-      fresh ~17.4GB download succeeded (old missing-shard failure gone);
chatbot                   the run then hit an IR WRITE failure at ov.save_model (basic_ios iostream
                          error; read_model + compress had succeeded) — the PT->OV copy pattern needs
                          ~35GB workdir and exhausted this runner's disk budget → BLOCKED_RESOURCE /
                          MODEL_FILE_IO_FAILURE_SAVE_OR_LOAD (Gate-5-corrected attribution)
yoloe-26-open-vocabulary  re-attempted under current pin — see matrix
```

The later-stage network blocks above are a property of this validation
runner's egress allowlist (github.com CONNECT, storage.openvinotoolkit.org,
raw.githubusercontent.com are refused), not of the artifacts; on a runner with
those hosts reachable the recovered downloads are expected to complete as the
flux.1 recovery demonstrated.

## Verification queued (v0.3 failure-retry, reference runner)

1. Re-download with resumable transport (hf_transfer / direct endpoint on an
   unthrottled runner) and verify `sha256` + non-zero size before conversion.
2. If the artifact still loads empty from a verified download, escalate the
   specific workload to FAILED_COMPATIBILITY with a minimized export/load
   script.

## Upstream material

None (not an upstream defect at this evidence level).
