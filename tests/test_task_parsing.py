"""Tests for the LegalBench task-mode eval answer parsing."""

from scripts.eval.run_classification_eval import _parse_task_answer


def test_parse_plain_letter():
    assert _parse_task_answer("A\n", ["A", "B", "C", "D"]) == "A"


def test_parse_letter_with_punctuation():
    assert _parse_task_answer("B.", ["A", "B", "C", "D"]) == "B"
    assert _parse_task_answer("C)", ["A", "B", "C", "D"]) == "C"


def test_parse_option_prefix():
    assert _parse_task_answer("Option D is correct", ["A", "B", "C", "D"]) == "D"


def test_parse_yes_no():
    assert _parse_task_answer("Yes\n", ["Yes", "No"]) == "Yes"
    assert _parse_task_answer("no", ["Yes", "No"]) == "No"


def test_parse_multiline_reasoning_then_answer():
    assert _parse_task_answer("The clause says Delaware law.\nAnswer: Yes", ["Yes", "No"]) == "Yes"


def test_parse_case_insensitive():
    assert _parse_task_answer("yes", ["Yes", "No"]) == "Yes"
    assert _parse_task_answer("a", ["A", "B"]) == "A"


def test_parse_no_match():
    assert _parse_task_answer("42", ["Yes", "No"]) == ""
    assert _parse_task_answer("", ["Yes", "No"]) == ""
    assert _parse_task_answer(None, ["Yes", "No"]) == ""
