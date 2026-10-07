# llm-chatbot-generate-api — CPU attempt (evidence schema v2)

- status: **VERIFIED_WITH_LIMITATIONS**
- validation level: EXECUTION_ONLY
- device proof: NOT_INFERENCE (supporting widget scan: 'CPU')
- successful runs: 3/3 (see aggregate.json)
- last duration: 11.37s
- failure: -
- environment: `.venvs/cpu/dd6e72d7066b48ff` (reused=False)
- note: EXECUTION_ONLY: no workload correctness contract (validation: {})
- note: DEVICE_PROOF_NOT_OBSERVED: no OpenVINO compile_model call was captured by the probe (notebooks driving openvino_genai pipelines or conversion-only code bypass the Python Core API; positive device execution therefore unproven)
- note: CORE_INFERENCE_VERIFIED; INTERACTIVE_UI_NOT_TESTED (documented skip policy)
