"""Structured, URL-safe notebook cell substitution rules.

Defect A (v0.1): substitution rules were encoded as "PATTERN:REPLACEMENT"
strings and parsed with str.partition(":"), which corrupts any pattern that
itself contains ':' — e.g. every https:// URL. The '||' delimiter was a
stopgap; v0.2 removes delimiter encoding entirely.

Rules are structured objects (Substitution), serialized as JSON for the
notebook executor process boundary:

    Substitution(pattern=r"https://huggingface\\.co", replacement="https://hf-mirror.com")

    subs_to_json([s])  -> '[{"pattern": "...", "replacement": "..."}]'

The pattern is always a regular expression; the replacement is plain text
(re.sub replacement syntax). No delimiter parsing happens anywhere.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Substitution:
    """One cell-source rewrite rule: regex pattern -> literal replacement."""

    pattern: str
    replacement: str

    def to_dict(self) -> dict[str, str]:
        return {"pattern": self.pattern, "replacement": self.replacement}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Substitution:
        if "pattern" not in d or "replacement" not in d:
            raise ValueError(f"substitution needs 'pattern' and 'replacement': {d!r}")
        return cls(pattern=str(d["pattern"]), replacement=str(d["replacement"]))


def subs_to_json(subs: list[Substitution]) -> str:
    """Serialize for the executor CLI boundary (--subs-json)."""

    return json.dumps([s.to_dict() for s in subs])


def subs_from_json(raw: str) -> list[Substitution]:
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("subs json must be a list of {pattern, replacement}")
    return [Substitution.from_dict(d) for d in parsed]


def apply_substitutions(source: str, subs: list[Substitution]) -> tuple[str, int]:
    """Apply all rules to one cell source. Returns (new_source, n_occurrences)."""

    n = 0
    out = source
    for s in subs:
        out, k = re.subn(s.pattern, s.replacement, out)
        n += k
    return out, n
