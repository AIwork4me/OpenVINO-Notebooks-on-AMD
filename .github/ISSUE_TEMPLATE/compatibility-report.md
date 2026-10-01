---
name: Compatibility report
about: Report a workload result on your AMD hardware
title: "[compat] <workload-id> on <cpu/gpu>"
labels: compatibility
body:
  - type: input
    id: workload
    attributes:
      label: Workload id
      placeholder: hello-world
    validations:
      required: true
  - type: dropdown
    id: device
    attributes:
      label: Device path
      options: [Ryzen CPU / OpenVINO, Radeon GPU / ROCm]
    validations:
      required: true
  - type: textarea
    id: hw
    attributes:
      label: Hardware + software (python -m ov_amd doctor output)
    validations:
      required: true
  - type: dropdown
    id: status
    attributes:
      label: Result
      options: [VERIFIED, VERIFIED_WITH_LIMITATIONS, FAILED, BLOCKED, SKIPPED_RESOURCE]
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Logs / evidence
      description: Attach stdout/stderr or evidence dir contents
