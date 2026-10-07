# RCA-002 — openvino-tokenizers: ReadValue without sibling output on CPU plugin load

- **Workload:** `openvino-tokenizers` (CPU attempt, FAILED_COMPATIBILITY)
- **Evidence:** `results/openvino-tokenizers/20261006T*/cpu` (see state row)
- **Layer (preliminary):** OpenVINO CPU plugin memory-node handling vs tokenizer IR state
- **Status:** candidate — single reproduction; not yet minimized

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
  memory-layer check fails on AMD-relevant plugin build `2026.4.1`.
- Conversion itself succeeded (the failure is at first inference), so this is
  runtime/model-execution compatibility, not an export issue.
- Environment valid (isolated venv with upstream pins).

## Reproduction path

`python -m ov_amd run openvino-tokenizers --device cpu`; failing infer visible
in the last run's `stderr.log` and `executed.ipynb`.

## Minimization target

Convert the same tokenizer with `ov.tokenizers.convert_tokenizer(...)`, save
IR, load on CPU, call infer in a standalone script. If it reproduces without
the notebook, attach IR + script to an openvino-tokenizers issue.

## Upstream material

Not yet ready (not minimized).
