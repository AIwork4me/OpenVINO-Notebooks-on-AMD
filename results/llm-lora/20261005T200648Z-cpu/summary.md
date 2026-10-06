# llm-lora — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: WORKLOAD_CORRECTNESS
- device proof: NOT_INFERENCE (supporting widget scan: 'CPU')
- successful runs: 3/3 (see aggregate.json)
- last duration: 18.31s
- failure: -
- environment: `.venvs/cpu/d375b21c5bccf759` (reused=False)
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
