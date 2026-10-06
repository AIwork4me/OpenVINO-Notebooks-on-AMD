# convert-to-openvino — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: EXECUTION_ONLY
- device proof: NOT_INFERENCE (supporting widget scan: 'GPU')
- successful runs: 3/3 (see aggregate.json)
- last duration: 47.62s
- failure: -
- environment: `.venvs/cpu/14c79f40de9d556c` (reused=True)
- note: EXECUTION_ONLY: no workload correctness contract (validation: {})
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
