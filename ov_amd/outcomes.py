"""Developer-facing compatibility outcome taxonomy (two-dimension status).

Execution status (what the runner observed) and compatibility outcome (what a
developer should conclude about AMD/OpenVINO support) are distinct dimensions:

    execution_status: FAILED + failure_category: MODEL_ACCESS
    compatibility_outcome: BLOCKED_MODEL_ACCESS
      -> "cannot conclude anything about AMD CPU support; the model repo is
          gated and no token was available"

    execution_status: FAILED + failure_category: OPENVINO_ERROR
    compatibility_outcome: FAILED_COMPATIBILITY
      -> "the environment was valid and the OpenVINO runtime itself failed"

A green/yellow execution status maps 1:1. A red execution status never maps to
a compatibility failure unless the failure category is a runtime/model
execution category — external blockers (network, gated models, missing
packages, timeouts, resources) are BLOCKED_* instead, so AMD/OpenVINO is never
blamed for failures it did not cause.
"""

from __future__ import annotations

import re
from enum import Enum


class CompatibilityOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFIED_WITH_LIMITATIONS = "VERIFIED_WITH_LIMITATIONS"
    BLOCKED_NETWORK = "BLOCKED_NETWORK"
    BLOCKED_MODEL_ACCESS = "BLOCKED_MODEL_ACCESS"
    BLOCKED_DEPENDENCY = "BLOCKED_DEPENDENCY"
    BLOCKED_TIMEOUT = "BLOCKED_TIMEOUT"
    BLOCKED_RESOURCE = "BLOCKED_RESOURCE"
    FAILED_COMPATIBILITY = "FAILED_COMPATIBILITY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_TESTED = "NOT_TESTED"


OUTCOME_ICONS = {
    CompatibilityOutcome.VERIFIED.value: "✅",
    CompatibilityOutcome.VERIFIED_WITH_LIMITATIONS.value: "🟡",
    CompatibilityOutcome.BLOCKED_NETWORK.value: "🌐",
    CompatibilityOutcome.BLOCKED_MODEL_ACCESS.value: "🔐",
    CompatibilityOutcome.BLOCKED_DEPENDENCY.value: "📦",
    CompatibilityOutcome.BLOCKED_TIMEOUT.value: "⏱️",
    CompatibilityOutcome.BLOCKED_RESOURCE.value: "💾",
    CompatibilityOutcome.FAILED_COMPATIBILITY.value: "🧩",
    CompatibilityOutcome.NOT_APPLICABLE.value: "➖",
    CompatibilityOutcome.NOT_TESTED.value: "⏳",
}

BLOCKED_OUTCOMES = {
    CompatibilityOutcome.BLOCKED_NETWORK,
    CompatibilityOutcome.BLOCKED_MODEL_ACCESS,
    CompatibilityOutcome.BLOCKED_DEPENDENCY,
    CompatibilityOutcome.BLOCKED_TIMEOUT,
    CompatibilityOutcome.BLOCKED_RESOURCE,
}

# execution failure_category -> (outcome, default reason)
_CATEGORY_OUTCOME: dict[str, tuple[CompatibilityOutcome, str]] = {
    "NETWORK": (CompatibilityOutcome.BLOCKED_NETWORK, "NETWORK_UNREACHABLE"),
    "DOWNLOAD": (CompatibilityOutcome.BLOCKED_NETWORK, "DOWNLOAD_TRANSPORT"),
    "EXTERNAL_SERVICE": (CompatibilityOutcome.BLOCKED_NETWORK, "EXTERNAL_SERVICE"),
    "MODEL_ACCESS": (CompatibilityOutcome.BLOCKED_MODEL_ACCESS, "GATED_OR_RESTRICTED_MODEL"),
    "LICENSE_RESTRICTION": (CompatibilityOutcome.BLOCKED_MODEL_ACCESS, "LICENSE_RESTRICTED_MODEL"),
    "DEPENDENCY": (CompatibilityOutcome.BLOCKED_DEPENDENCY, "MISSING_OR_BROKEN_DEPENDENCY"),
    "PACKAGE_CONFLICT": (CompatibilityOutcome.BLOCKED_DEPENDENCY, "PACKAGE_RESOLUTION_CONFLICT"),
    "PYTHON_VERSION": (CompatibilityOutcome.BLOCKED_DEPENDENCY, "PYTHON_VERSION_REQUIREMENT"),
    "INTERACTIVE_ONLY": (CompatibilityOutcome.BLOCKED_DEPENDENCY, "INTERACTIVE_UI_NOT_TESTED"),
    "TIMEOUT": (CompatibilityOutcome.BLOCKED_TIMEOUT, "TIMEOUT"),
    "OOM": (CompatibilityOutcome.BLOCKED_RESOURCE, "OUT_OF_MEMORY"),
    "RAM_LIMIT": (CompatibilityOutcome.BLOCKED_RESOURCE, "RAM_LIMIT"),
    "VRAM_LIMIT": (CompatibilityOutcome.BLOCKED_RESOURCE, "VRAM_LIMIT"),
    "DISK_LIMIT": (CompatibilityOutcome.BLOCKED_RESOURCE, "DISK_LIMIT"),
    "OPENVINO_ERROR": (CompatibilityOutcome.FAILED_COMPATIBILITY, "OPENVINO_RUNTIME"),
    "CONVERSION_ERROR": (CompatibilityOutcome.FAILED_COMPATIBILITY, "CONVERSION"),
    "INFERENCE_ERROR": (CompatibilityOutcome.FAILED_COMPATIBILITY, "INFERENCE"),
    "CORRECTNESS_ERROR": (CompatibilityOutcome.FAILED_COMPATIBILITY, "CORRECTNESS"),
    "UPSTREAM_BUG": (CompatibilityOutcome.FAILED_COMPATIBILITY, "UPSTREAM"),
}

# Signature refinements for UNKNOWN categories (and reason precision). Applied
# to the concatenated notes / error head; first match wins.
_SIGNATURES: list[tuple[str, CompatibilityOutcome, str]] = [
    (
        r"FileNotFoundError[^\n]*'(optimum-cli|ovc)'|"
        r"Could not import optimum(-intel)?|ImportError: Could not import optimum-intel|"
        r"Unexpected dependency in optimum-intel/setup\.py",
        CompatibilityOutcome.BLOCKED_DEPENDENCY,
        "OPTIMUM_CLI_MISSING_OR_BROKEN",
    ),
    (
        r"Authentication token does not exist|GatedRepoError|gated repo|"
        r"Access to model [^\s]+ is (restricted|denied)|you are not in the authorized list",
        CompatibilityOutcome.BLOCKED_MODEL_ACCESS,
        "GATED_OR_RESTRICTED_MODEL",
    ),
    (
        r"Empty weights data in bin file|PytorchStreamReader failed reading zip archive|"
        r"Can not open file [^\n]*\.(bin|xml)|"
        r"No such file or directory[^\n]*\.safetensors|"
        r"KeyError: '(blocks|model)\.[^\n]*weight'",
        CompatibilityOutcome.BLOCKED_RESOURCE,
        "MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT",
    ),
    (
        r"drive\.google\.com|ConnectTimeout|Connection error\.|getaddrinfo failed|"
        r"RemoteDisconnected|Could not resolve host|host unreachable",
        CompatibilityOutcome.BLOCKED_NETWORK,
        "EXTERNAL_HOST_UNREACHABLE",
    ),
    (
        r"FULL_DEVICE_NAME|\bNPU\b",
        CompatibilityOutcome.BLOCKED_RESOURCE,
        "REQUIRED_HARDWARE_ABSENT",
    ),
    (
        r"NameError: name '(demo|gr)' is not defined",
        CompatibilityOutcome.BLOCKED_DEPENDENCY,
        "INTERACTIVE_UI_TEARDOWN_AFTER_SKIP",
    ),
    (
        r"clEnqueueMapBuffer|CL_INVALID_VALUE",
        CompatibilityOutcome.FAILED_COMPATIBILITY,
        "OPENVINO_RUNTIME",
    ),
]

_TIMEOUT_STAGE_RULES: list[tuple[str, str]] = [
    (r"### Installation|%pip|pip install|Successfully installed|Collecting ", "DEPENDENCY_INSTALL"),
    (r"Convert|Optimum-CLI|optimum-cli|Compress|Quantiz|NNCF|nncf|export openvino", "CONVERSION_EXPORT"),
    (r"Download|weights|dataset|DownloadFile|huggingface", "MODEL_DOWNLOAD"),
    (r"gradio|demo\.launch|webcam|VideoCapture", "UI_DEMO"),
]

_CELL_MARKER_RE = re.compile(r"\[cell (\d+) (?:START|DONE)[^\]]*\]\s*(.*)")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def classify_timeout_stage(stdout: str, stderr: str = "") -> str:
    """Best-effort stage identification for a timed-out attempt.

    Returns one of DEPENDENCY_INSTALL, MODEL_DOWNLOAD, CONVERSION_EXPORT,
    UI_DEMO, INFERENCE, or UNKNOWN_STAGE — based on the last cell marker /
    log activity before the wall clock expired.
    """

    text = _ANSI_RE.sub("", f"{stdout}\n{stderr}")
    markers = _CELL_MARKER_RE.findall(text)
    if markers:
        _, last_src = markers[-1]
        window = last_src[:400]
        for pat, stage in _TIMEOUT_STAGE_RULES:
            if re.search(pat, window, re.I):
                return stage
        # a mid-notebook cell that matched no rule: the notebook was executing
        # ordinary content cells — model load / inference territory
        return "INFERENCE"
    for pat, stage in _TIMEOUT_STAGE_RULES:
        if re.search(pat, text[-2000:], re.I):
            return stage
    return "UNKNOWN_STAGE"


def derive_outcome(
    execution_status: str,
    failure_category: str = "",
    notes: str = "",
    timeout_stage: str = "",
) -> tuple[CompatibilityOutcome, str]:
    """Map (execution_status, failure_category, evidence text) to the
    developer-facing outcome plus a machine-readable reason."""

    if execution_status == "VERIFIED":
        return CompatibilityOutcome.VERIFIED, ""
    if execution_status == "VERIFIED_WITH_LIMITATIONS":
        return CompatibilityOutcome.VERIFIED_WITH_LIMITATIONS, ""
    if execution_status == "NOT_APPLICABLE":
        return CompatibilityOutcome.NOT_APPLICABLE, ""
    if execution_status in ("NOT_TESTED", "QUEUED", "RUNNING", "REVALIDATION_REQUIRED"):
        return CompatibilityOutcome.NOT_TESTED, ""
    if execution_status in ("BLOCKED", "SKIPPED_RESOURCE"):
        return CompatibilityOutcome.BLOCKED_RESOURCE, failure_category or "RUNNER_RESOURCE_GUARD"

    # execution_status == FAILED. Root-cause-first: specific signatures in the
    # recorded error text outrank the coarse execution category (misclassified
    # categories are corrected, e.g. MODEL_ACCESS rows whose error is actually
    # a datasets API drift, or PACKAGE_CONFLICT rows with empty model weights).
    text = _ANSI_RE.sub("", notes or "")
    if failure_category != "TIMEOUT":
        for pat, outcome, reason in _SIGNATURES:
            if re.search(pat, text):
                return outcome, reason
    else:
        for pat, outcome, reason in _SIGNATURES:
            if re.search(pat, text) and outcome is CompatibilityOutcome.BLOCKED_TIMEOUT:
                return outcome, reason
        stage = timeout_stage or "UNKNOWN_STAGE"
        return CompatibilityOutcome.BLOCKED_TIMEOUT, f"TIMEOUT_{stage}"
    mapped = _CATEGORY_OUTCOME.get(failure_category)
    if mapped:
        return mapped
    if failure_category in ("ROCM_UNAVAILABLE", "ROCM_UNSUPPORTED", "GPU_ARCH"):
        return CompatibilityOutcome.BLOCKED_RESOURCE, failure_category
    # UNKNOWN with no matching signature: adjudication required — surfaced as
    # FAILED_COMPATIBILITY with explicit UNKNOWN reason so it can never hide
    return CompatibilityOutcome.FAILED_COMPATIBILITY, "UNKNOWN_ADJUDICATION_REQUIRED"


def outcome_blocked(outcome: str) -> bool:
    return outcome in {o.value for o in BLOCKED_OUTCOMES}
