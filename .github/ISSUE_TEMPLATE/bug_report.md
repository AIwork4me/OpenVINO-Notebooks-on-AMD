---
name: Bug report
about: Something in the harness, docs or data is wrong
title: "[bug] "
labels: bug
body:
  - type: textarea
    id: what
    attributes:
      label: What happened?
    validations:
      required: true
  - type: textarea
    id: expect
    attributes:
      label: What did you expect?
  - type: textarea
    id: repro
    attributes:
      label: Steps to reproduce
      placeholder: python -m ov_amd ...
  - type: textarea
    id: env
    attributes:
      label: Environment (python -m ov_amd doctor)
