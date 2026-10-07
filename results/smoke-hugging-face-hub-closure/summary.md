# Smoke re-verification (comprehensive closure)

Run on the closure machine (AMD EPYC 9334) during the comprehensive verification
quality pass — scratch evidence only, does NOT update marathon-state or any
catalog row (the 171-row dataset remains attributed to the reference Ryzen
runner).

- notebook: notebooks/hugging-face-hub/hugging-face-hub.ipynb @ 329562e
- execution: OK, 47.7s wall
- device proof: PROVEN_CPU (3 compile events, execution_devices=[CPU])
- validation contract: passed
- harness features exercised: notebook-relative sibling asset pre-seed,
  device-probe hooks, correctness evaluation, outcome classification
- environment note: storage.openvinotoolkit.org is egress-blocked on this
  machine (hello-world/openvino-api smokes classified BLOCKED_NETWORK
  correctly by the harness — recorded, not retried)
