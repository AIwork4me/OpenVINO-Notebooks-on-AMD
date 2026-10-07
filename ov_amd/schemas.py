"""Core data models, enums and the status machine for the validation harness."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Lifecycle status for a workload on one device path (cpu/gpu)."""

    NOT_TESTED = "NOT_TESTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFIED = "VERIFIED"
    VERIFIED_WITH_LIMITATIONS = "VERIFIED_WITH_LIMITATIONS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED_RESOURCE = "SKIPPED_RESOURCE"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


#: Allowed transitions of the status machine. Anything not listed is invalid.
STATUS_TRANSITIONS: dict[Status, set[Status]] = {
    Status.NOT_TESTED: {Status.QUEUED, Status.NOT_APPLICABLE, Status.SKIPPED_RESOURCE, Status.NOT_TESTED},
    Status.QUEUED: {Status.RUNNING, Status.SKIPPED_RESOURCE, Status.BLOCKED, Status.NOT_TESTED},
    Status.RUNNING: {
        Status.VERIFIED,
        Status.VERIFIED_WITH_LIMITATIONS,
        Status.FAILED,
        Status.BLOCKED,
        Status.SKIPPED_RESOURCE,
        Status.REVALIDATION_REQUIRED,
        Status.RUNNING,
    },
    Status.VERIFIED: {Status.REVALIDATION_REQUIRED, Status.VERIFIED, Status.RUNNING},
    Status.VERIFIED_WITH_LIMITATIONS: {Status.REVALIDATION_REQUIRED, Status.VERIFIED_WITH_LIMITATIONS, Status.RUNNING},
    Status.FAILED: {Status.RUNNING, Status.REVALIDATION_REQUIRED, Status.FAILED},
    Status.BLOCKED: {Status.RUNNING, Status.BLOCKED},
    Status.SKIPPED_RESOURCE: {Status.RUNNING, Status.SKIPPED_RESOURCE},
    Status.REVALIDATION_REQUIRED: {Status.RUNNING, Status.REVALIDATION_REQUIRED},
    Status.NOT_APPLICABLE: {Status.NOT_APPLICABLE},
}


def transition_ok(current: Status, new: Status) -> bool:
    return new in STATUS_TRANSITIONS[current]


class FailureCategory(str, Enum):
    NETWORK = "NETWORK"
    DOWNLOAD = "DOWNLOAD"
    DEPENDENCY = "DEPENDENCY"
    PYTHON_VERSION = "PYTHON_VERSION"
    PACKAGE_CONFLICT = "PACKAGE_CONFLICT"
    MODEL_ACCESS = "MODEL_ACCESS"
    LICENSE_RESTRICTION = "LICENSE_RESTRICTION"
    UPSTREAM_BUG = "UPSTREAM_BUG"
    OPENVINO_ERROR = "OPENVINO_ERROR"
    CONVERSION_ERROR = "CONVERSION_ERROR"
    INFERENCE_ERROR = "INFERENCE_ERROR"
    CORRECTNESS_ERROR = "CORRECTNESS_ERROR"
    OOM = "OOM"
    RAM_LIMIT = "RAM_LIMIT"
    VRAM_LIMIT = "VRAM_LIMIT"
    DISK_LIMIT = "DISK_LIMIT"
    TIMEOUT = "TIMEOUT"
    ROCM_UNAVAILABLE = "ROCM_UNAVAILABLE"
    ROCM_UNSUPPORTED = "ROCM_UNSUPPORTED"
    GPU_ARCH = "GPU_ARCH"
    INTERACTIVE_ONLY = "INTERACTIVE_ONLY"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
    UNKNOWN = "UNKNOWN"


class TwinLevel(str, Enum):
    EXACT_TWIN = "EXACT_TWIN"
    WORKLOAD_TWIN = "WORKLOAD_TWIN"
    CONCEPT_MAPPING = "CONCEPT_MAPPING"
    OPENVINO_SPECIFIC = "OPENVINO_SPECIFIC"
    NOT_CLASSIFIED = "NOT_CLASSIFIED"


class PriorityTier(int, Enum):
    """Marathon scheduling tier (0 = cheapest / highest scheduling priority)."""

    P0_FOUNDATIONAL = 0
    P1_HIGH_VALUE = 1
    P2_MEDIUM = 2
    P3_HEAVY = 3
    P4_EXTREME = 4


TERMINAL_STATUSES = {
    Status.VERIFIED,
    Status.VERIFIED_WITH_LIMITATIONS,
    Status.FAILED,
    Status.BLOCKED,
    Status.SKIPPED_RESOURCE,
    Status.NOT_APPLICABLE,
}

STATUS_ICONS = {
    Status.VERIFIED.value: "✅",
    Status.VERIFIED_WITH_LIMITATIONS.value: "🟡",
    Status.FAILED.value: "🔴",
    Status.BLOCKED.value: "⚫",
    Status.REVALIDATION_REQUIRED.value: "🔵",
    Status.NOT_TESTED.value: "⏳",
    Status.NOT_APPLICABLE.value: "➖",
    Status.QUEUED.value: "⏳",
    Status.RUNNING.value: "⏳",
    Status.SKIPPED_RESOURCE.value: "⚫",
}


@dataclass
class NotebookEntry:
    """One discovered upstream notebook in the catalog."""

    id: str
    title: str
    category: str
    upstream_path: str  # relative path inside the upstream repo
    upstream_url: str  # GitHub blob URL
    requirements_path: str | None = None
    priority: int = PriorityTier.P2_MEDIUM.value
    workload_type: str = "unknown"  # llm / vision / asr / tts / image-gen / ocr / api ...
    est_weight: str = "medium"  # small / medium / large / huge
    cpu_meaningful: bool = True
    gpu_meaningful: bool = False
    twin_level: str = TwinLevel.NOT_CLASSIFIED.value
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NotebookEntry:
        return cls(**d)


@dataclass
class ExecutionInfo:
    start: str = ""
    end: str = ""
    duration_s: float = 0.0
    exit_code: int | None = None
    retry_count: int = 0
    status: str = Status.NOT_TESTED.value
    failure_category: str = ""
    stage: str = ""  # pipeline stage at failure (e.g. TIMEOUT_CONVERSION_EXPORT)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class AttemptRecord:
    """Evidence record for one execution attempt."""

    workload_id: str
    backend: str  # cpu | gpu
    timestamp: str
    execution: ExecutionInfo = field(default_factory=ExecutionInfo)
    validation: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    device_used: str = ""
    patch_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "backend": self.backend,
            "timestamp": self.timestamp,
            "execution": self.execution.to_dict(),
            "validation": self.validation,
            "metrics": self.metrics,
            "device_used": self.device_used,
            "patch_notes": self.patch_notes,
        }
