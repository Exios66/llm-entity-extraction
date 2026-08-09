"""Tests for the LLM-as-judge agent (LLM mocked)."""

from agents.judge_agent import JudgeAgent


def test_judge_model_from_taxonomy():
    judge = JudgeAgent()
    assert judge.model == "deepseek/deepseek-v4-flash"  # taxonomy judge mapping


def test_judge_field_list_renders_schema():
    lines = JudgeAgent._field_list("contract")
    assert "parties" in lines
    assert "effective_date" in lines
    assert "court_opinion" not in lines


def test_judge_field_list_unknown_type():
    assert "(no schema registered" in JudgeAgent._field_list("banana")


def test_judge_taxonomy_spec_lists_classes():
    spec = JudgeAgent._taxonomy_spec()
    assert "contract" in spec
    assert "court_opinion" in spec


def test_judge_classification_parse_ok(mocker):
    judge = JudgeAgent()
    mocker.patch.object(
        judge,
        "_call_structured",
        return_value={"classification_correct": "correct", "classification_quality": 0.95,
                      "reasoning": "clearly a contract"},
    )
    verdict = judge.judge_classification("contract", "AGREEMENT between parties")
    assert verdict["classification_correct"] == "correct"
    assert verdict["classification_quality"] == 0.95


def test_judge_classification_parse_error_fallback(mocker):
    judge = JudgeAgent()
    mocker.patch.object(judge, "_call_structured", return_value={"_parse_error": True})
    verdict = judge.judge_classification("contract", "text")
    assert verdict["classification_correct"] == "ambiguous"
    assert verdict["classification_quality"] == 0.0


def test_judge_classification_clamps_label_and_score(mocker):
    judge = JudgeAgent()
    mocker.patch.object(
        judge,
        "_call_structured",
        return_value={"classification_correct": "banana", "classification_quality": 7.0, "reasoning": ""},
    )
    verdict = judge.judge_classification("contract", "text")
    assert verdict["classification_correct"] == "ambiguous"
    assert verdict["classification_quality"] == 1.0


def test_judge_completeness(mocker):
    judge = JudgeAgent()
    mocker.patch.object(
        judge,
        "_call_structured",
        return_value={"completeness": 0.8, "completeness_label": "partial", "reasoning": "missing value"},
    )
    verdict = judge.judge_completeness("contract", {"parties": ["Acme"]}, "AGREEMENT")
    assert verdict["completeness_label"] == "partial"
    assert verdict["completeness"] == 0.8


def test_judge_correctness(mocker):
    judge = JudgeAgent()
    mocker.patch.object(
        judge,
        "_call_structured",
        return_value={"extraction_correctness": 1.0, "extraction_correctness_label": "accurate",
                      "reasoning": "all supported"},
    )
    verdict = judge.judge_extraction_correctness("contract", {"parties": ["Acme"]}, "AGREEMENT")
    assert verdict["extraction_correctness_label"] == "accurate"
    assert verdict["extraction_correctness"] == 1.0
