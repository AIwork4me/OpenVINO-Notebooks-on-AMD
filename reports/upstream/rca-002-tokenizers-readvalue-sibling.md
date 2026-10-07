# RCA-002 — openvino-tokenizers: ReadValue without sibling output on CPU plugin load

- **Workload:** `openvino-tokenizers` (CPU attempt, FAILED_COMPATIBILITY)
- **Evidence (current pin 5f0b2b5, revalidated 2026-10-07):** `results/openvino-tokenizers/20261007162645Z-cpu/`
  (positive `PROVEN_CPU` device proof, 6 probe events; runtime `openvino 2026.4.1-22982` stable)
- **Layer:** OpenVINO CPU plugin memory-node handling vs tokenizer IR state
- **Status:** reproduced twice on two AMD CPUs (Zen 5 reference runner; EPYC 9334);
  upstream's fix identified — delivered via OpenVINO nightly builds (upstream #3717)

## Error

```text
RuntimeError: Exception from src/inference/src/cpp/infer_request.cpp:224:
Exception from src/plugins/intel_cpu/src/graph.cpp:1628:
Node ReadValue_5627 of type ReadValue
Check 'outputNode' failed at src/plugins/intel_cpu/src/nodes/memory.cpp:487:
ReadValue node with name 'ReadValue_5627'  doesn't have sibling output
```

Raised from `CompiledModel.infer_request(...)` (tokenizer infer) after a
tokenizer IR converted by `openvino-tokenizers` loads successfully.

## Analysis

- ReadValue/Assign state pairs in the converted tokenizer IR lose their
  sibling-output relationship at CPU-plugin graph construction; the plugin's
  memory-layer check fails on plugin build `2026.4.1` (stable).
- Conversion itself succeeded (the failure is at first inference), so this is
  runtime/model-execution compatibility, not an export issue.
- Environment valid (isolated venv with upstream pins).

## Upstream resolution status (v0.2.2)

Upstream commit `1c991f4e08f8` ("Update openvino-tokenizers notebook to nightly
builds (#3717)") switched the notebook to OpenVINO **nightly** builds explicitly
to pick up the `connect_models` sink fix. The nightly index
(`storage.openvinotoolkit.org`) is refused by this validation network's egress
proxy (CONNECT 403), so the notebook's tolerant `%pip` resolver falls back to
the newest PyPI stable (`2026.4.1`) — which still contains the defect, and the
failure **reproduced on the current pin** (see evidence above).

- Resolution path: re-run on a network that can reach the nightly index once a
  stable release > 2026.4.1 containing the fix is published, then flip this row
  to the fixed runtime and record recovery.
- Until then FAILED_COMPATIBILITY remains the honest verdict for the runtime
  the notebook actually installs here.

## Reproduction path

`python -m ov_amd run openvino-tokenizers --device cpu`; failing infer visible
in the last run's `stderr.log` and `executed.ipynb`.

## Minimization target

Convert the same tokenizer with `ov.tokenizers.convert_tokenizer(...)`, save
IR, load on CPU, call infer in a standalone script. If it reproduces without
the notebook, attach IR + script to an openvino-tokenizers issue.

## Upstream material

Not yet ready (not minimized).
