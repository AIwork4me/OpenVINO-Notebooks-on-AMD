---
name: Upstream candidate
about: Report an issue that should be filed against openvino_notebooks / openvino / openvino-tokenizers
title: "[upstream] <short description>"
labels: upstream-candidate
body:
  - type: dropdown
    id: repo
    attributes:
      label: Target repository
      options:
        - openvinotoolkit/openvino_notebooks
        - openvinotoolkit/openvino
        - openvinotoolkit/openvino_tokenizers
        - huggingface/optimum-intel
        - other
    validations:
      required: true
  - type: textarea
    id: case
    attributes:
      label: Case (workload + evidence dir in this repo)
      description: Link the RCA file under reports/upstream/ if one exists
    validations:
      required: true
  - type: textarea
    id: minimized
    attributes:
      label: Minimized reproduction (required before filing — no speculative upstream bugs)
    validations:
      required: true
  - type: textarea
    id: draft
    attributes:
      label: Draft upstream issue text
