"""Dedicated test suite for the EVALUATOR (JudgeAgent): the offline
LLM-as-a-judge over classification, completeness, and extraction correctness.

Covers the judge's full contract for each dimension:
- STEPS: the exact user message it builds (task spec / expected fields /
  extracted data / source document text) and the schema it submits.
- CHOICES: enum label validation (invalid labels coerced to the fallback),
  numeric clamping to [0, 1].
- REASONING: the judge's reasoning is passed through verbatim.
- SCORING: quality/completeness/correctness values are bounded and survive
  malformed model output (parse errors degrade to the documented fallback).
All LLM calls are mocked — the suite is network-free.
"""

from __future__ import annotations

import pytest

from agents.judge_agent import (
    CLASSIFICATION_LABELS,
    CORRECTNESS_LABELS,
    LABELS,
    JudgeAgent,
)
from agents.base_agent import build_structured_schema


@pytest.fixture
def judge():
    return JudgeAgent(model="qwen/qwen3.7-flash")  # skip taxonomy model swap


def _mock_structured(mocker, result: dict):
    """Patch _call_structured to return ``result`` and return the captured call."""
    captured = {}

    def fake(self, user_message, json_schema=None, **kwargs):
        captured["user_message"] = user_message
        captured["json_schema"] = json_schema
        captured["kwargs"] = kwargs
        return dict(result)

    mocker.patch.object(JudgeAgent, "_call_structured", fake)
    return captured


# ---------------------------------------------------------------------------
# Classification judge
# ---------------------------------------------------------------------------

def test_classification_steps_and_scoring(judge, mocker):
    captured = _mock_structured(mocker, {
        "classification_correct": "correct",
        "classification_quality": "0.92",
        "reasoning": "The document is an executed agreement with party definitions.",
    })
    out = judge.judge_classification("contract", "THIS AGREEMENT between Acme and Beta.", "title says agreement")

    # Steps: task spec + assigned class + classifier reasoning + source text.
    assert "Assigned classification: contract" in captured["user_message"]
    assert "Classifier reasoning: title says agreement" in captured["user_message"]
    assert "contract (Contract / Agreement)" in captured["user_message"]
    assert "THIS AGREEMENT between Acme and Beta." in captured["user_message"]
    # The judge submits the classification schema with the classification prompt.
    assert captured["json_schema"]["properties"]["classification_correct"]["enum"] == CLASSIFICATION_LABELS
    assert captured["kwargs"]["system_prompt"] == __import__("src.prompts", fromlist=["get_prompt"]).get_prompt("judge-classification")
    assert captured["kwargs"]["temperature"] == 0.0

    # Scoring: label + bounded numeric quality + verbatim reasoning.
    assert out["classification_correct"] == "correct"
    assert out["classification_quality"] == pytest.approx(0.92)
    assert out["reasoning"] == "The document is an executed agreement with party definitions."


def test_classification_invalid_label_coerced(judge, mocker):
    _mock_structured(mocker, {"classification_correct": "banana", "classification_quality": 2.0})
    out = judge.judge_classification("contract", "text")
    assert out["classification_correct"] == "ambiguous"
    assert out["classification_quality"] == 1.0  # clamped to [0, 1]


def test_classification_parse_error_fallback(judge, mocker):
    mocker.patch.object(JudgeAgent, "_call_structured",
                        return_value={"_parse_error": True, "_raw": "oops"})
    out = judge.judge_classification("contract", "text")
    assert out == {"classification_correct": "ambiguous", "classification_quality": 0.0,
                   "reasoning": "judge output failed to parse"}


# ---------------------------------------------------------------------------
# Completeness judge
# ---------------------------------------------------------------------------

def test_completeness_steps_choices_and_scoring(judge, mocker):
    captured = _mock_structured(mocker, {
        "completeness": "0.75",
        "completeness_label": "partial",
        "reasoning": "Missing renewal_terms; governing_law absent from source.",
    })
    extracted = {"parties": ["Acme"], "governing_law": None}
    out = judge.judge_completeness("contract", extracted, "long document text")

    # Steps: doc type + expected field list from the schema + extracted data + source.
    assert "Document type: contract" in captured["user_message"]
    assert "parties:" in captured["user_message"] and "key_obligations:" in captured["user_message"]
    assert "{'parties': ['Acme'], 'governing_law': None}" in captured["user_message"]
    assert "long document text" in captured["user_message"]
    assert captured["json_schema"]["properties"]["completeness_label"]["enum"] == LABELS
    assert captured["kwargs"]["system_prompt"] == __import__("src.prompts", fromlist=["get_prompt"]).get_prompt("judge")

    assert out["completeness"] == pytest.approx(0.75)
    assert out["completeness_label"] == "partial"
    assert out["reasoning"] == "Missing renewal_terms; governing_law absent from source."


def test_completeness_invalid_label_and_clamping(judge, mocker):
    _mock_structured(mocker, {"completeness": "-1", "completeness_label": "N/A"})
    out = judge.judge_completeness("contract", {}, "text")
    assert out["completeness"] == 0.0  # clamped
    assert out["completeness_label"] == "incomplete"  # fallback label


def test_completeness_parse_error_fallback(judge, mocker):
    mocker.patch.object(JudgeAgent, "_call_structured", return_value={"_parse_error": True})
    out = judge.judge_completeness("contract", {}, "text")
    assert out["completeness"] == 0.0
    assert out["completeness_label"] == "incomplete"
    assert out["reasoning"] == "judge output failed to parse"


# ---------------------------------------------------------------------------
# Correctness judge
# ---------------------------------------------------------------------------

def test_correctness_steps_choices_and_scoring(judge, mocker):
    captured = _mock_structured(mocker, {
        "extraction_correctness": "1.0",
        "extraction_correctness_label": "accurate",
        "reasoning": "Every populated value is grounded in the source.",
    })
    out = judge.judge_extraction_correctness("contract", {"effective_date": "2020-01-09"}, "source text")

    assert "Document type: contract" in captured["user_message"]
    assert "{'effective_date': '2020-01-09'}" in captured["user_message"]
    assert "source text" in captured["user_message"]
    assert captured["json_schema"]["properties"]["extraction_correctness_label"]["enum"] == CORRECTNESS_LABELS
    assert captured["kwargs"]["system_prompt"] == __import__("src.prompts", fromlist=["get_prompt"]).get_prompt("judge-correctness")

    assert out["extraction_correctness"] == 1.0
    assert out["extraction_correctness_label"] == "accurate"
    assert out["reasoning"] == "Every populated value is grounded in the source."


def test_correctness_invalid_label_and_clamping(judge, mocker):
    _mock_structured(mocker, {"extraction_correctness": "7", "extraction_correctness_label": "??"})
    out = judge.judge_extraction_correctness("contract", {}, "text")
    assert out["extraction_correctness"] == 1.0  # clamped
    assert out["extraction_correctness_label"] == "partial"  # fallback label


def test_correctness_parse_error_fallback(judge, mocker):
    mocker.patch.object(JudgeAgent, "_call_structured", return_value={"_parse_error": True})
    out = judge.judge_extraction_correctness("contract", {}, "text")
    assert out["extraction_correctness"] == 0.0
    assert out["extraction_correctness_label"] == "inaccurate"
    assert out["reasoning"] == "judge output failed to parse"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_truncate_budget():
    assert JudgeAgent._truncate("short") == "short"
    long_text = "x" * 20000
    truncated = JudgeAgent._truncate(long_text, max_chars=1000)
    assert len(truncated) < 2000
    assert "document truncated" in truncated
    assert truncated.startswith("x" * 1000)


def test_field_list_renders_schema(judge):
    field_list = JudgeAgent._field_list("contract")
    assert "document_name" in field_list
    assert "parties" in field_list
    assert "governing_law" in field_list
    assert JudgeAgent._field_list("no_such_doc_type") == "(no schema registered for this doc type)"


def test_taxonomy_spec_renders_classes(judge):
    spec = JudgeAgent._taxonomy_spec()
    assert "contract" in spec
    assert "correspondence" in spec


def test_judge_default_model_from_taxonomy(mocker):
    # Without an explicit model, the judge resolves the taxonomy's judge
    # agent mapping (never the raw sorter default).
    from src.taxonomy import load_taxonomy
    expected = load_taxonomy().get("agents", {}).get("judge", {}).get("model")
    judge = JudgeAgent()
    assert judge.model == expected


def test_judge_schema_is_structured():
    # Every judge dimension submits a strict JSON schema (no free-form output).
    schema = build_structured_schema({"classification_correct": {"type": "string"}})
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
