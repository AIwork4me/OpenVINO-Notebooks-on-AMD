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


def adjudicate_gemma4(state: dict) -> dict | None:
    rec = state.get("attempts", {}).get("gemma4", {}).get("cpu")
    if not rec:
        return None
    if any("v0.3 resource adjudication" in n for n in rec.get("notes", [])):
        return None
    note = (
        "v0.3 resource adjudication: the 2b1600d-pin rerun progressed past dependency install "
        "(optimum-intel master resolved via codeload transport) into the Gemma-4-E2B OpenVINO "
        "export when the validation disk hit 100% utilization (sibling campaign workloads); the "
        "operator killed the export kernel to protect the shared disk and the recorded "
        "AssertionError is the interrupted-export artifact, not a model verdict. Honest outcome: "
        "BLOCKED_RESOURCE (insufficient disk headroom for the ~14GB export on this runner during "
        "the v0.3 window). Dependency root cause from v0.2.2 is RESOLVED (installs complete)."
    )
    rec.setdefault("notes", []).append(note)
    rec["outcome_reason"] = "DISK_EXHAUSTED_DURING_EXPORT_OPERATOR_HALTED"
    rec["compatibility_outcome"] = "BLOCKED_RESOURCE"
    return {"workload": "gemma4", "backend": "cpu", "action": "resource-note+outcome"}


def _set(rec: dict, outcome: str, reason: str, note: str) -> dict:
    if any(note[:60] in n for n in rec.get("notes", [])):
        return {}
    rec.setdefault("notes", []).append(note)
    rec["compatibility_outcome"] = outcome
    rec["outcome_reason"] = reason
    return {"outcome": outcome, "reason": reason}


def adjudicate_v03_final(state: dict) -> list[dict]:
    applied = []

    ir_write = (
        "v0.3 adjudication: optimum-cli OpenVINO IR export fails in ov save_model with "
        "RuntimeError: basic_ios::clear (iostream error) — the same IR-write signature "
        "family as the v0.2.2 minicpm-o adjudication (BLOCKED_RESOURCE), observed here "
        "with a valid environment and the model fully downloaded. Environment/install "
        "root causes from v0.2.2 are resolved (installs complete on the current pin). "
        "Classified BLOCKED_RESOURCE (IR export write failure), not a compatibility "
        "verdict; the workload's ROCm twin remains VERIFIED."
    )
    for wid in ("stable-diffusion-xl", "vlm-chatbot-generate-api"):
        rec = state.get("attempts", {}).get(wid, {}).get("cpu")
        if rec:
            r = _set(rec, "BLOCKED_RESOURCE", "IR_EXPORT_WRITE_IOSTREAM_ERROR", ir_write)
            if r:
                applied.append({"workload": wid, "backend": "cpu", **r})

    notes = {
        "qwen-image": (
            "v0.3 adjudication: dependency root cause from v0.2.2 is FIXED on this pin "
            "(codeload transport + --no-deps fork install land; installs complete), but "
            "the workload needs ~26GB of Qwen-Image-2512 weights plus a large IR export; "
            "the shared 98GB validation disk cannot host it alongside the campaign's "
            "other downloads. Honest outcome for this window: BLOCKED_RESOURCE "
            "(DISK_BUDGET_EXCEEDED); not a compatibility verdict."
        ),
        "glm-ocr": (
            "v0.3 adjudication: the v0.2.2 optimum-export dependency blocker is RESOLVED "
            "(nested optimum-onnx@transformers-v5 satisfied via codeload, fork installs "
            "--no-deps); the remaining sole blocker is the notebook's sample images on "
            "GitHub user-attachment S3 (github-production-user-asset-*.s3.amazonaws.com), "
            "proxy-blocked on this runner. Reclassified BLOCKED_DEPENDENCY -> BLOCKED_NETWORK "
            "(external asset host); the GLM-OCR ROCm twin is VERIFIED with a deterministic "
            "typewritten fixture input."
        ),
        "3d-segmentation-point-clouds": (
            "v0.3 adjudication: the headless-rerun NameError (point_data undefined) was a "
            "scoping artifact that is now resolved; the fresh current-pin run proceeds into "
            "the data stage and fails on storage.openvinotoolkit.org (proxy 403), the "
            "notebook's only data host. Reclassified BLOCKED_DEPENDENCY -> BLOCKED_NETWORK "
            "(external host); not a compatibility verdict."
        ),
        "action-recognition-webcam": (
            "v0.3 adjudication: same as 3d-segmentation — the vocab_file_path NameError was "
            "a rerun-scoping artifact; the fresh run fails downloading the Kinetics labels "
            "from storage.openvinotoolkit.org (proxy 403). Reclassified "
            "BLOCKED_DEPENDENCY -> BLOCKED_NETWORK (external host)."
        ),
        "clip-zero-shot-classification": (
            "v0.3 adjudication: root cause unchanged in kind but now precisely bounded: the "
            "install cell's `git+https://github.com/huggingface/optimum-intel.git` (floating "
            "master) declares a nested optimum-onnx git dependency whose clone is "
            "deterministically blocked on this runner; the whole pip cell fails, leaving "
            "transformers/torch uninstalled. BLOCKED_DEPENDENCY (git-transport install); "
            "not a model compatibility verdict."
        ),
        "instant-id": (
            "v0.3 adjudication: environment remediation (gdown) landed and the run reached "
            "the weights stage; the InsightFace antelopev2 weights are hosted on "
            "drive.google.com, which this runner's egress proxy blocks (503 tunnel). "
            "Reclassified to BLOCKED_NETWORK (external weights host)."
        ),
        "llm-code-assistant": (
            "v0.3 adjudication: fresh run confirms deterministic git-transport block — the "
            "notebook pip-installs from git+https://github.com (optimum-intel et al.) whose "
            "clones cannot pass this runner's proxy. BLOCKED_NETWORK (external git host)."
        ),
        "wav2lip": (
            "v0.3 adjudication: fresh run fails fetching helper/data files from "
            "raw.githubusercontent.com (proxy-blocked). BLOCKED_NETWORK (external host)."
        ),
    }
    for wid, note in notes.items():
        rec = state.get("attempts", {}).get(wid, {}).get("cpu")
        if not rec:
            continue
        if wid in ("glm-ocr", "3d-segmentation-point-clouds", "action-recognition-webcam",
                   "instant-id", "llm-code-assistant", "wav2lip"):
            r = _set(rec, "BLOCKED_NETWORK", "EXTERNAL_HOST_UNREACHABLE", note)
        elif wid == "qwen-image":
            r = _set(rec, "BLOCKED_RESOURCE", "DISK_BUDGET_EXCEEDED", note)
        else:
            r = _set(rec, "BLOCKED_DEPENDENCY", "GIT_TRANSPORT_INSTALL_BLOCKED", note)
        if r:
            applied.append({"workload": wid, "backend": "cpu", **r})

    # GPU twins attempted this cycle but not completed: honest library-contract blocks
    gpu_notes = {
        "deepseek-ocr": (
            "v0.3 GPU adjudication: the DeepSeek-OCR-2 model repo's remote code targets "
            "transformers 4.x (imports LlamaFlashAttention2, removed in 5.x) and its "
            "checkpoint config does not match the transformers-5.17 built-in "
            "DeepseekOcr2 class (mlp_layer_types schema). A dedicated transformers-4.46.3 "
            "bridged env (as the upstream notebook pins) plus a port of the notebook-side "
            "preprocessing is required — deferred beyond v0.3. Current GPU outcome: "
            "BLOCKED_DEPENDENCY (library-generation contract), not a model/ROCm verdict."
        ),
        "florence2": (
            "v0.3 GPU adjudication: Florence-2 remote code drifts across transformers "
            "generations (forced_bos_token_id config default, RobertaTokenizer "
            "additional_special_tokens, PreTrainedModel._supports_sdpa) — fails on both "
            "5.17 and 4.57 without the exact-era 4.4x env. Requires the same pinned-env "
            "treatment as deepseek-ocr; deferred beyond v0.3. BLOCKED_DEPENDENCY "
            "(library-generation contract)."
        ),
    }
    for wid, note in gpu_notes.items():
        rec = state.get("attempts", {}).get(wid, {}).get("gpu")
        if rec:
            r = _set(rec, "BLOCKED_DEPENDENCY", "TRANSFORMERS_GENERATION_CONTRACT", note)
            if r:
                applied.append({"workload": wid, "backend": "gpu", **r})
    return applied


def main() -> int:
    state = load_state()
    applied = [r for r in (adjudicate_whisper_cpu(state), adjudicate_gemma4(state)) if r]
    applied += adjudicate_v03_final(state)
    if applied:
        save_state(state)
    for r in applied:
        print(r)
    print(f"applied {len(applied)} adjudication(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
