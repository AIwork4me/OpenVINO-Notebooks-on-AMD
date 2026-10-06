# 3d-segmentation-point-clouds — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: EXECUTION_ONLY
- device proof: NOT_INFERENCE (supporting widget scan: 'AUTO')
- successful runs: 1/3 (see aggregate.json)
- last duration: 1.67s
- failure: -
- environment: `.venvs/cpu/0f1b5e28b61ecbc9` (reused=False)
- note: EXECUTION_ONLY: no workload correctness contract (validation: {})
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
- note: repeatability_not_established: fewer than 3 successful runs (resource-bounded policy)
