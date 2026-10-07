---
name: Compatibility issue
about: A workload fails with a real OpenVINO/runtime error on AMD (not an environment blocker)
title: "[compat-issue] <workload-id>: <one-line error>"
labels: compatibility-issue
body:
  - type: input
    id: workload
    attributes:
      label: Workload id
    validations:
      required: true
  - type: dropdown
    id: layer
    attributes:
      label: Suspected layer
      options:
        - OpenVINO runtime
        - OpenVINO CPU plugin
        - OpenVINO GPU plugin
        - openvino-tokenizers / genai
        - Optimum / optimum-intel
        - Model conversion
        - Upstream notebook
        - Model artifact
        - Not sure (maintainers will triage)
    validations:
      required: true
  - type: textarea
    id: error
    attributes:
      label: Exact error (last ~20 stderr lines)
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Minimal reproduction (script + model IR if possible)
      description: Issues without a minimization are queued behind ones with one
  - type: textarea
    id: env
    attributes:
      label: Environment (python -m ov_amd doctor + workload venv lock)
