#!/usr/bin/env python3
"""v0.3 semantic adjudications (documented state surgery, force=True).

Evidence-linked, idempotent; adds provenance notes only — never fabricates a run.

1. whisper-asr-genai cpu -> stays BLOCKED_NETWORK, enriched provenance
   Under the 2b1600d pin the notebook's first install cell requires OpenVINO
   nightly (>=2026.5.0.dev20261005) from storage.openvinotoolkit.org (NPU-
   oriented upstream change). The nightly index and the notebook's sample
   video live on that host, which the runner egress proxy blocks (403). The
   attempt nevertheless executed the core ASR flow end-to-end on AMD CPU with
   the env's pre-satisfied stable OpenVINO 2026.4.1 (whisper-base FP16
   preconverted model, courtroom.wav + MLS Italian sample transcribed, perf
   metrics emitted). Sole fatal blocker: sample-video download for the gradio
   video->SRT demo. Outcome stays BLOCKED_NETWORK (external host), NOT a
   compatibility failure; core-inference progress recorded for triage.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ov_amd.scheduler import load_state, save_state  # noqa: E402


def adjudicate_whisper_cpu(state: dict) -> dict | None:
    rec = state.get("attempts", {}).get("whisper-asr-genai", {}).get("cpu")
    if not rec:
        return None
    if any("v0.3 network adjudication" in n for n in rec.get("notes", [])):
        return None  # idempotent
    note = (
        "v0.3 network adjudication: upstream 2b1600d makes the notebook require OpenVINO "
        "nightly >=2026.5.0.dev20261005 from storage.openvinotoolkit.org (NPU-oriented; "
        "index unreachable via runner egress, 403) and its sample video lives on the same "
        "host. Core CPU ASR flow nevertheless completed under pre-satisfied stable "
        "OpenVINO 2026.4.1 (whisper-base FP16 preconverted; courtroom.wav and MLS Italian "
        "samples transcribed with timestamps; perf metrics emitted) — see "
        f"{rec.get('evidence_dir')}/run-01/executed.ipynb cells 12-22. Sole fatal blocker "
        "is the external video asset for the gradio demo; classification stays "
        "BLOCKED_NETWORK (external host), not a compatibility failure."
    )
    rec.setdefault("notes", []).append(note)
    rec["outcome_reason"] = "EXTERNAL_HOST_UNREACHABLE"
    return {"workload": "whisper-asr-genai", "backend": "cpu", "action": "note+reason-refresh"}


def main() -> int:
    state = load_state()
    applied = [r for r in (adjudicate_whisper_cpu(state),) if r]
    if applied:
        save_state(state)
    for r in applied:
        print(r)
    print(f"applied {len(applied)} adjudication(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
