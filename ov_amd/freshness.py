"""Structured upstream-freshness analysis (v0.3.1 Step 4.2).

Replaces the old regex-extraction monitor logic. Consumes the GitHub compare
API JSON (pin...head) plus the project catalog and the pinned snapshot, and
classifies the delta into:

    ADDED                          — new upstream notebooks MISSING from the catalog
    MODIFIED                       — catalogued notebooks whose content changed
    REMOVED                        — catalogued notebooks whose path disappeared
    RENAMED                        — catalogued notebooks that moved
    AFFECTED_BY_SHARED_HELPER      — catalogued notebooks importing changed utils/ helpers
    UNAFFECTED                     — everything else in the catalog

The analysis is pure (JSON in -> report out) so the CI workflow and the test
suite drive the same code path; tests feed synthetic compare fixtures
(including the vjepa-2.1 add that the old monitor missed).
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SHARED_HELPER_DIRS = ("utils/",)
_HELPER_MODULES = (
    "notebook_utils", "pip_helper", "cmd_helper", "genai_helper", "llm_config",
    "model_upcast_utils", "ipython_exit", "skip_kernel_extension", "engine3js",
)
HELPER_IMPORT_PATTERNS = tuple(
    pattern
    for m in _HELPER_MODULES
    for pattern in (re.compile(rf"\bfrom\s+{re.escape(m)}\b"), re.compile(rf"\bimport\s+{re.escape(m)}\b"))
) + (
    re.compile(r"\bfrom\s+(utils[\w.]*)\s+import"),
    re.compile(r"\bimport\s+(utils[\w.]*)"),
    re.compile(r"from\s+\.\./\.\./utils/[\w./]+"),  # sibling-relative helper layout
)


def notebook_dirs_from_path(path: str) -> str | None:
    """Map an upstream file path to its notebook directory key."""
    parts = Path(path).parts
    if path.endswith(".ipynb"):
        if len(parts) >= 2 and parts[0] == "notebooks":
            return parts[1]
        if "supplementary_materials" in parts:
            # supplementary_materials/notebooks/<dir>/<nb>.ipynb OR
            # supplementary_materials/notebooks/<nb>.ipynb (flat)
            idx = parts.index("notebooks")
            rest = parts[idx + 1 : -1]
            return rest[0] if rest else f"@flat:{parts[-1]}"
    return None


@dataclass
class DeltaReport:
    pin: str
    head: str
    commits: int = 0
    added_missing: list[str] = field(default_factory=list)  # NEW notebooks not in catalog
    modified: list[str] = field(default_factory=list)  # affected workload ids
    removed: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)
    shared_helper_files: list[str] = field(default_factory=list)
    affected_by_shared_helper: list[str] = field(default_factory=list)
    dependency_policy_files: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    raw_files: int = 0

    @property
    def is_current(self) -> bool:
        return self.pin == self.head

    def sections(self) -> dict[str, list[str]]:
        return {
            "ADDED": sorted(self.added_missing),
            "MODIFIED": sorted(self.modified),
            "REMOVED": sorted(self.removed),
            "RENAMED": sorted(self.renamed),
            "AFFECTED_BY_SHARED_HELPER": sorted(self.affected_by_shared_helper),
            "UNAFFECTED": sorted(self.unchanged),
        }

    def markdown(self) -> str:
        s = self.sections()
        lines = [
            f"### Upstream freshness: `{'CURRENT' if self.is_current else 'ADVANCED'}` ({self.commits} commits, {self.raw_files} changed files)",
            f"`{self.pin[:12]}` → `{self.head[:12]}`",
            "",
        ]
        icons = {"ADDED": "🆕", "MODIFIED": "✏️", "REMOVED": "🗑️", "RENAMED": "🔀", "AFFECTED_BY_SHARED_HELPER": "🧰", "UNAFFECTED": "✔️"}
        for name, items in s.items():
            icon = icons[name]
            if name == "UNAFFECTED":
                lines.append(f"- {icon} **{name}**: {len(items)} catalog entries")
            else:
                shown = ", ".join(items[:40]) if items else "(none)"
                more = f" … +{len(items) - 40} more" if len(items) > 40 else ""
                lines.append(f"- {icon} **{name}** ({len(items)}): {shown}{more}")
        if self.shared_helper_files:
            lines.append("")
            lines.append("Changed shared helpers: " + ", ".join(f"`{f}`" for f in self.shared_helper_files[:10]))
        if self.dependency_policy_files:
            lines.append("")
            lines.append("Dependency-policy files changed: " + ", ".join(f"`{f}`" for f in self.dependency_policy_files[:10]))
        if self.added_missing:
            lines.append("")
            lines.append(
                "**Action required:** newly added upstream notebooks are missing from the catalog — "
                "run discovery + classification + a real validation attempt before the next release."
            )
        return "\n".join(lines)


def helper_importing_dirs(snapshot_root: Path) -> set[str]:
    """Notebook dirs (notebooks/<dir>) whose .ipynb/.py import shared helpers."""
    affected: set[str] = set()
    nb_root = snapshot_root / "notebooks"
    if not nb_root.is_dir():
        return affected
    for nb_file in nb_root.rglob("*"):
        if nb_file.suffix not in {".ipynb", ".py"} or ".ipynb_checkpoints" in str(nb_file):
            continue
        try:
            text = nb_file.read_text(errors="ignore")
        except OSError:
            continue
        if any(p.search(text) for p in HELPER_IMPORT_PATTERNS):
            rel = nb_file.relative_to(nb_root)
            affected.add(rel.parts[0] if len(rel.parts) > 1 else f"@flat:{rel.name}")
    return affected


def analyze(
    pin: str,
    head: str,
    compare: dict,
    catalog: dict,
    snapshot_root: Path | None = None,
) -> DeltaReport:
    """Build a DeltaReport from a GitHub compare-API payload and the catalog."""
    rep = DeltaReport(pin=pin, head=head, commits=int(compare.get("total_commits", 0) or 0))
    workload_of_dir: dict[str, str] = {}
    catalog_dirs: set[str] = set()
    for entry in catalog.get("notebooks", []):
        wid, path = entry["id"], entry.get("upstream_path", "")
        d = notebook_dirs_from_path(path)
        if d:
            catalog_dirs.add(d)
            workload_of_dir.setdefault(d, wid)

    helper_changed = False
    for f in compare.get("files", []):
        rep.raw_files += 1
        name = f.get("filename", "")
        status = f.get("status", "")
        if any(name.startswith(p) for p in SHARED_HELPER_DIRS):
            helper_changed = True
            rep.shared_helper_files.append(name)
            continue
        if fnmatch.fnmatch(name, "requirements*.txt") or name.startswith(".docker/Pipfile"):
            rep.dependency_policy_files.append(name)
            continue
        d = notebook_dirs_from_path(name)
        prev_d = notebook_dirs_from_path(f.get("previous_filename", "")) if f.get("previous_filename") else None
        if status == "removed":
            if d in catalog_dirs:
                rep.removed.append(workload_of_dir[d])
            continue
        _ = prev_d  # renamed handled below
        if status == "renamed" and prev_d and prev_d != d:
            if prev_d in catalog_dirs:
                rep.renamed.append(f"{workload_of_dir[prev_d]} -> {name}")
                continue
            # previous dir was not catalogued: fall through so the new
            # destination is still evaluated (added-missing detection)
        if d is None:
            continue  # CI/docs/infra-only change
        if d in catalog_dirs:
            rep.modified.append(workload_of_dir[d])
        elif status in {"added", "renamed"}:
            rep.added_missing.append(f"{d} ({name})")

    if helper_changed and snapshot_root is not None:
        helper_dirs = helper_importing_dirs(snapshot_root)
        rep.affected_by_shared_helper = sorted(
            workload_of_dir[d] for d in catalog_dirs if d in helper_dirs
        )
    elif helper_changed:
        rep.affected_by_shared_helper = ["(all — snapshot unavailable for precise scoping)"]

    rep.modified = list(dict.fromkeys(rep.modified))
    rep.removed = list(dict.fromkeys(rep.removed))
    renamed_ids = {entry.split(" -> ")[0] for entry in rep.renamed}
    touched = set(rep.modified) | set(rep.removed) | renamed_ids | set(rep.affected_by_shared_helper)
    rep.unchanged = [entry["id"] for entry in catalog.get("notebooks", []) if entry["id"] not in touched]
    return rep


def load_catalog(path: Path) -> dict:
    import yaml

    return yaml.safe_load(Path(path).read_text()) or {}


def fetch_compare(pin: str, head: str) -> dict:
    import subprocess

    r = subprocess.run(
        ["gh", "api", f"repos/openvinotoolkit/openvino_notebooks/compare/{pin}...{head}"],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        raise RuntimeError(f"gh api compare: {r.stderr[:200]}")
    return json.loads(r.stdout)
