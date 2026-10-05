"""Structured substitution rules (Defect A regression battery)."""

import pytest

from ov_amd.substitution import Substitution, apply_substitutions, subs_from_json, subs_to_json


def test_roundtrip():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    assert subs_from_json(subs_to_json(subs)) == subs


def test_url_with_port_and_query():
    """The v0.1 ':' delimiter produced '//huggingface\\.co :https://...' garbage."""
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    out, n = apply_substitutions("u = 'https://huggingface.co:443/foo?rev=main&q=a:b'", subs)
    assert n == 1
    assert out == "u = 'https://hf-mirror.com:443/foo?rev=main&q=a:b'"


def test_plain_urls():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    out, _ = apply_substitutions("https://huggingface.co/foo", subs)
    assert out == "https://hf-mirror.com/foo"


def test_ports_443():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    out, _ = apply_substitutions("https://huggingface.co:443/foo", subs)
    assert out == "https://hf-mirror.com:443/foo"


def test_regex_special_chars_in_pattern():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    out, _ = apply_substitutions("https://huggingfaceXco", subs)
    assert out == "https://huggingfaceXco"  # escaped dot must not match


def test_multiple_urls_one_cell():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    src = "a='https://huggingface.co/m1'\nb='https://huggingface.co/m2'"
    out, n = apply_substitutions(src, subs)
    assert n == 2 and "hf-mirror.com/m1" in out and "hf-mirror.com/m2" in out


def test_non_hf_hosts_untouched():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    src = "\n".join(
        [
            "git+https://github.com/foo",
            "https://raw.githubusercontent.com/foo/bar",
            "https://storage.openvinotoolkit.org/repo",
        ]
    )
    out, n = apply_substitutions(src, subs)
    assert n == 0 and out == src


def test_git_plus_https_github_untouched():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    src = "pip install git+https://github.com/openvinotoolkit/openvino.genai"
    out, n = apply_substitutions(src, subs)
    assert n == 0 and out == src


def test_pip_install_line_rewritten():
    subs = [Substitution(pattern=r"https://huggingface\.co", replacement="https://hf-mirror.com")]
    out, _ = apply_substitutions("%pip install https://huggingface.co/x/whl", subs)
    assert out.startswith("%pip install https://hf-mirror.com/x/whl")


def test_replacement_containing_colon_is_safe():
    """Replacement text containing ':' must never be re-parsed as a rule."""
    subs = [Substitution(pattern="HOST", replacement="https://hf-mirror.com")]
    out, _ = apply_substitutions("base = 'HOST'", subs)
    assert out == "base = 'https://hf-mirror.com'"


def test_from_dict_rejects_delimiter_strings():
    with pytest.raises(ValueError):
        subs_from_json('"PATTERN:REPLACEMENT"')
    with pytest.raises(ValueError):
        subs_from_json('[{"pattern": "a"}]')  # missing replacement
