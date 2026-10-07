# stable-diffusion-v3 — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: EXECUTION_ONLY
- device proof: NOT_INFERENCE (supporting widget scan: 'CPU')
- successful runs: 1/1 (see aggregate.json)
- last duration: 250.74s
- failure: -
- environment: `.venvs/cpu/b9c2d468cf5a1848` (reused=False)
- note: EXECUTION_ONLY: no workload correctness contract (validation: {})
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
- note: repeatability_not_established: fewer than 3 successful runs (resource-bounded policy)
- note: CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (documented skip policy)
