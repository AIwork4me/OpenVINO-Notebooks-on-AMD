"""README generated-metrics must never be stale (comprehensive verification §40).

CI regenerates the block; if a data change lands without regenerating, this
test fails rather than shipping stale marketing numbers.
"""

from __future__ import annotations

from ov_amd.environment import REPO_ROOT
from ov_amd.reporting import README, README_BEGIN, README_END, build_compatibility


def test_readme_generated_block_is_current() -> None:
    text = README.read_text()
    assert README_BEGIN in text and README_END in text, "README generated markers missing"
    block = text.split(README_BEGIN, 1)[1].split(README_END, 1)[0]
    compat = build_compatibility()
    c = compat["counts"]
    oc = c["cpu_outcomes"]
    sec = c["cpu_successful_execution_coverage"]
    blocked = sum(oc.get(k, 0) for k in
                  ("BLOCKED_NETWORK", "BLOCKED_MODEL_ACCESS", "BLOCKED_DEPENDENCY", "BLOCKED_TIMEOUT", "BLOCKED_RESOURCE"))
    expected_fragments = [
        f"AMD CPU Coverage: {c['cpu_attempted']}/{c['total']} OpenVINO Notebooks attempted on AMD Ryzen",
        f"{c['cpu_attempt_coverage_pct']}% catalog coverage",
        f"✅ {oc.get('VERIFIED', 0)} Verified",
        f"🟡 {oc.get('VERIFIED_WITH_LIMITATIONS', 0)} Verified with limitations",
        f"🚧 {blocked} Blocked",
        f"🧩 {oc.get('FAILED_COMPATIBILITY', 0)} Compatibility failures",
        f"➖ {oc.get('NOT_APPLICABLE', 0)} Not applicable",
        f"**{sec['verified'] + sec['verified_with_limitations']}/{sec['eligible_total']}** of eligible notebooks ({sec['pct']}%)",
        "It does not mean every notebook passed",
    ]
    missing = [f for f in expected_fragments if f not in block]
    assert not missing, f"README generated block stale; missing: {missing} — run `python -m ov_amd report`"


def test_readme_has_what_100_means_section() -> None:
    text = README.read_text()
    assert "100% catalog coverage" in text and "100% pass rate" in text
    assert "Blocked" in text and "Compatibility failure" in text


def test_readme_quickstart_commands_resolve() -> None:
    text = README.read_text()
    for cmd in ("python -m ov_amd doctor", "python -m ov_amd list", "python -m ov_amd run hello-world --device cpu"):
        assert cmd in text
    assert (REPO_ROOT / "docs" / "validation-policy.md").exists()
