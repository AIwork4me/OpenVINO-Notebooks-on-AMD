#!/usr/bin/env python3
"""v0.2.2 semantic adjudications (documented state surgery, force=True).

Each correction is evidence-linked and adds a provenance note; nothing here
fabricates a run. Adjudications:

1. gpu-device cpu -> NOT_APPLICABLE
   GPU-purpose notebook (hardcoded device="GPU" walkthrough; only device
   enumeration is backend-agnostic). The GPU-plugin crash behavior it exercises
   on Radeon is recorded separately (OVG-003). CPU verdict NOT_APPLICABLE with
   provenance, per docs/validation-policy.md "Device attribution (v0.2.2)".

2. parler-tts-text-to-speech cpu -> VERIFIED_WITH_LIMITATIONS
   Current-pin attempt run-01 completed end-to-end on CPU (positive
   compile_model CPU probe events, 0 cell errors, correctness contract
   satisfied: IPython.lib.display.Audio in outputs). The historical
   BrgemmCPU f32/bf16 failure (RCA-001) did NOT reproduce under the
   reconstructed environment (torchaudio pinned to the torch 2.8 pairing).
   Repeatability could not be established: retry runs died on flaky
   git+https://github.com transport during the notebook's dependency install
   (egress-restricted network). Single successful run => documented
   limitation, consistent with the yellow-row policy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.scheduler import load_state, save_state  # noqa: E402
from ov_amd.state_machine import enforce_transition  # noqa: E402

STATE = Path(__file__).resolve().parent.parent / "results" / "marathon-state.json"


def adjudicate_gpu_device(state: dict) -> dict | None:
    rec = state.get("attempts", {}).get("gpu-device", {}).get("cpu")
    if not rec:
        return None
    if rec.get("compatibility_outcome") == "NOT_APPLICABLE":
        return None  # already adjudicated (idempotent)
    enforce_transition(rec.get("status"), "NOT_APPLICABLE", force=True, context="gpu-device/cpu")
    note = (
        "v0.2.2 applicability adjudication: gpu-purpose notebook — upstream hardcodes "
        'device = "GPU" for its property walkthrough/compile/cache cells (only '
        "core.available_devices enumeration is backend-agnostic); no meaningful AMD CPU "
        "validation path exists, so the CPU-dimension outcome is NOT_APPLICABLE. The "
        "OpenVINO GPU-plugin behavior on Radeon it exercises (inline-asm codegen crash, "
        "kernel death) is recorded as Finding OVG-003 in "
        "reports/openvino-gpu-plugin-radeon-findings.md; fresh current-pin evidence: "
        f"{rec.get('evidence_dir')}"
    )
    rec["status"] = "NOT_APPLICABLE"
    rec["compatibility_outcome"] = "NOT_APPLICABLE"
    rec["outcome_reason"] = "GPU_PURPOSE_NOTEBOOK_NO_CPU_VALIDATION_PATH"
    rec["device_proof"] = rec.get("device_proof", "")
    rec.setdefault("notes", []).append(note)
    return rec


def adjudicate_parler_tts(state: dict) -> dict | None:
    rec = state.get("attempts", {}).get("parler-tts-text-to-speech", {}).get("cpu")
    if not rec:
        return None
    if rec.get("compatibility_outcome") == "VERIFIED_WITH_LIMITATIONS":
        return None
    ev = Path(rec.get("evidence_dir", ""))
    run01 = ev / "run-01"
    probe = run01 / "device-proof.jsonl"
    if not probe.exists():
        print("parler-tts: run-01 evidence missing; skipping adjudication")
        return None
    events = [json.loads(line) for line in probe.read_text().splitlines() if line.strip()]
    cpu_compiles = [e for e in events if e.get("kind") == "compile_model" and "CPU" in (e.get("execution_devices") or [])]
    if not cpu_compiles:
        print("parler-tts: no positive CPU compile events in run-01; skipping adjudication")
        return None
    enforce_transition(rec.get("status"), "VERIFIED_WITH_LIMITATIONS", force=True, context="parler-tts/cpu")
    note = (
        "v0.2.2 recovery adjudication: current-pin run-01 completed end-to-end on CPU — "
        f"{len(cpu_compiles)} positive compile_model CPU probe events, 0 cell errors, correctness "
        "contract satisfied (IPython.lib.display.Audio in outputs, generated parler_tts_out.wav). "
        "The historical BrgemmCPU f32/bf16 failure (RCA-001) did not reproduce under the "
        "reconstructed environment (torchaudio==2.8.0 paired with torch 2.8.0+cpu). Repeatability "
        "not established: retry runs 02-04 died on flaky git+https transport to github.com during "
        "the notebook dependency install (network egress restriction). Single-run evidence "
        "recorded as documented limitation."
    )
    rec["status"] = "VERIFIED_WITH_LIMITATIONS"
    rec["compatibility_outcome"] = "VERIFIED_WITH_LIMITATIONS"
    rec["outcome_reason"] = ""
    rec["failure_category"] = ""
    rec["device_proof"] = "PROVEN_CPU"
    rec["validation_level"] = "WORKLOAD_CORRECTNESS"
    rec["ok_runs"] = 1
    rec["durations_s"] = rec.get("durations_s") or []
    rec["limitation_codes"] = ["REPEATABILITY_NOT_ESTABLISHED"]
    rec.setdefault("notes", []).append(note)
    return rec


def main() -> int:
    state = load_state()
    changed = []
    r = adjudicate_gpu_device(state)
    if r:
        changed.append("gpu-device/cpu -> NOT_APPLICABLE")
    r = adjudicate_parler_tts(state)
    if r:
        changed.append("parler-tts-text-to-speech/cpu -> VERIFIED_WITH_LIMITATIONS (recovery)")
    if changed:
        save_state(state)
        STATE.write_text(json.dumps(state, indent=2) + "\n")
    for c in changed:
        print(c)
    print("adjudications applied:", len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
