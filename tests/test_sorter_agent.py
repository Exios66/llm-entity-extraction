"""Tests for the sorter agent's prompt resolution and parsing (LLM mocked)."""

import pytest

from agents.sorter_agent import DOC_CLASS_KEYS, SORTER_SCHEMA, SorterAgent


def test_system_prompt_uses_version():
    sorter = SorterAgent(prompt_version="sorter_v0")
    prompt = sorter.system_prompt()
    assert "contract" in prompt
    assert "court_opinion" in prompt


def test_schema_enum_matches_classes():
    enum = SORTER_SCHEMA["properties"]["doc_type"]["enum"]
    assert enum == DOC_CLASS_KEYS


def test_classify_returns_parsed_result(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "confidence": 0.92, "reasoning": "it is an agreement"},
    )
    doc_type, confidence, reasoning = sorter.classify("AGREEMENT text here")
    assert doc_type == "contract"
    assert confidence == 0.92
    assert "agreement" in reasoning


def test_classify_defaults_on_parse_error(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(sorter, "_call_structured", return_value={"_parse_error": True})
    doc_type, confidence, reasoning = sorter.classify("text")
    assert doc_type == "correspondence"
    assert confidence == 0.3


def test_classify_rejects_unknown_class(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "banana", "confidence": "high", "reasoning": ""},
    )
    doc_type, confidence, _ = sorter.classify("text")
    assert doc_type == "correspondence"
    assert confidence == 0.5


def test_classify_json_returns_dict(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "confidence": 0.9, "reasoning": "r"},
    )
    result = sorter.classify_json("text")
    assert result["doc_type"] == "contract"
    assert result["confidence"] == 0.9


def test_truncate_input_budget():
    sorter = SorterAgent()
    sorter._max_input_chars = 50
    truncated = sorter.truncate_input("x" * 200)
    assert len(truncated) < 200
    assert "truncated" in truncated
    short = sorter.truncate_input("short")
    assert short == "short"
