"""Central sanitizer for generated public artifacts.

Public summaries (catalog/compatibility.{json,md}, reports/failures.md,
reports/marathon-progress.md, README generated block, release summaries) must
not leak machine-local checkout paths. Raw diagnostic evidence (stdout.log /
stderr.log inside results/) is intentionally exempt: it records what the
process actually printed.

Handled path shapes (all reduced to repo-relative):

    /home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venvs/...   -> .venvs/...
    /workspace/OpenVINO-Notebooks-on-AMD/results/...         -> results/...
    /any/where/OpenVINO-Notebooks-on-AMD/results/...         -> results/...
    C:\\Users\\<u>\\...\\OpenVINO-Notebooks-on-AMD\\results\\...   -> results\\...

URLs are never rewritten: a match is only valid when not preceded by a word
character or URL-ish context, so
``https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD/actions`` survives
untouched while stack-trace paths are reduced.
"""

from __future__ import annotations

import re

REPO_DIR_NAME = "OpenVINO-Notebooks-on-AMD"

# A repo checkout rooted anywhere on a unix-like filesystem. The lookbehind
# blocks matches glued to a hostname (github.com/.../OpenVINO-Notebooks-on-AMD).
_UNIX_REPO_PREFIX = re.compile(rf"(?<![\w.:/-])/(?:[\w.-]+/)*{re.escape(REPO_DIR_NAME)}/")

# Windows checkout: optional drive letter, then any directory chain.
_WIN_REPO_PREFIX = re.compile(
    rf"(?<![\w])(?:[A-Za-z]:\\)?(?:[^\s\"'/\\\\]+\\)*{re.escape(REPO_DIR_NAME)}\\",
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def sanitize_public_text(text: str | None) -> str:
    """Reduce machine-local repo paths inside free text (notes, log excerpts)."""

    if not text:
        return ""
    text = _ANSI_RE.sub("", text)
    text = _UNIX_REPO_PREFIX.sub("", text)
    text = _WIN_REPO_PREFIX.sub("", text)
    return text


def sanitize_public_path(p: str | None) -> str | None:
    """Reduce a stored evidence reference to repo-relative form."""

    if not p:
        return None
    if p.startswith(("http://", "https://")):
        return p
    return sanitize_public_text(p)
