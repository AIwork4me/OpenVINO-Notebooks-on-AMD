"""OpenVINO Notebooks on AMD — validation harness.

One AI workload. Two AMD paths: OpenVINO on Ryzen CPUs, ROCm on Radeon GPUs.
"""

from ov_amd.schemas import (
    AttemptRecord,
    ExecutionInfo,
    FailureCategory,
    NotebookEntry,
    PriorityTier,
    Status,
    TwinLevel,
    transition_ok,
)

__version__ = "0.3.1"

__all__ = [
    "AttemptRecord",
    "ExecutionInfo",
    "FailureCategory",
    "NotebookEntry",
    "PriorityTier",
    "Status",
    "TwinLevel",
    "transition_ok",
    "__version__",
]
