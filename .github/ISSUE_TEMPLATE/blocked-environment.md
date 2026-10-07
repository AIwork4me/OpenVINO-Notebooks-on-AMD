---
name: Blocked environment report
about: A workload cannot complete for an external reason (network, gated model, dependency, timeout, resource)
title: "[blocked] <workload-id>: <blocker>"
labels: blocked-environment
body:
  - type: input
    id: workload
    attributes:
      label: Workload id
    validations:
      required: true
  - type: dropdown
    id: blocker
    attributes:
      label: Blocker type
      options:
        - BLOCKED_NETWORK (host unreachable, DNS, proxy)
        - BLOCKED_MODEL_ACCESS (gated repo, 401/403, missing token)
        - BLOCKED_DEPENDENCY (missing package/CLI, resolver conflict, API drift)
        - BLOCKED_TIMEOUT (which stage? download / conversion / inference)
        - BLOCKED_RESOURCE (OOM, RAM/disk, absent hardware, corrupt artifact)
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: Evidence of the external cause (exact error lines)
      description: Blocked reports must show the blocker is external — not an OpenVINO/runtime failure
    validations:
      required: true
  - type: textarea
    id: workaround
    attributes:
      label: Workaround attempted (mirror, retry, resumable download, alternate tag)
