"""Correctness-check evaluation tests."""

from ov_amd.correctness import check_finite_numbers, cosine_similarity, evaluate


def test_evaluate_pass_default():
    res = evaluate({"output_finite_numbers": False}, "some output", {"ok": True, "n_skipped": 0})
    assert res["passed"] is True
    assert res["checks"]["no_cell_error"] is True


def test_evaluate_output_contains():
    res = evaluate({"output_contains": [r"tiger cat", r"prob=\d"]}, "a tiger cat prob=0.42", {"ok": True, "n_skipped": 0})
    assert res["passed"] is True


def test_evaluate_output_contains_fail():
    res = evaluate({"output_contains": [r"missing"]}, "nothing here", {"ok": True, "n_skipped": 0})
    assert res["passed"] is False
    assert res["checks"]["output_contains"]["missing"] is False


def test_evaluate_not_contains():
    res = evaluate({"output_not_contains": [r"nan"]}, "clean", {"ok": True, "n_skipped": 0})
    assert res["passed"] is True
    res = evaluate({"output_not_contains": [r"nan"]}, "has nan inside", {"ok": True, "n_skipped": 0})
    assert res["passed"] is False


def test_evaluate_cell_error_fails():
    res = evaluate({}, "", {"ok": False})
    assert res["passed"] is False


def test_finite_numbers():
    assert check_finite_numbers("loss: 0.31")
    assert not check_finite_numbers("no numbers here")
    assert not check_finite_numbers("loss nan")


def test_min_output_chars():
    assert evaluate({"min_output_chars": 10}, "0123456789abc", {"ok": True})["passed"]
    assert not evaluate({"min_output_chars": 100}, "short", {"ok": True})["passed"]


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9
    assert cosine_similarity([1.0], [1.0, 2.0]) != cosine_similarity([1.0], [1.0, 2.0])  # nan != nan
