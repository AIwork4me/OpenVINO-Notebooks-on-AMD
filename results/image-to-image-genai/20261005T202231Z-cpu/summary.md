# image-to-image-genai — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: WORKLOAD_CORRECTNESS
- device proof: NOT_INFERENCE (supporting widget scan: 'CPU')
- successful runs: 1/1 (see aggregate.json)
- last duration: 78.69s
- failure: -
- environment: `.venvs/cpu/72b537b71f8963ba` (reused=False)
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
- note: repeatability_not_established: fewer than 3 successful runs (resource-bounded policy)
- note: CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (documented skip policy)
