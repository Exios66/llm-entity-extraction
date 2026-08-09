"""Tests for the sorter agent's prompt resolution, subtype handling, and
parsing (LLM mocked)."""

import pytest

from agents.sorter_agent import (
    CONTRACT_SUBTYPES,
    DOC_CLASS_KEYS,
    SORTER_SCHEMA,
    SUBTYPE_UNKNOWN,
    SorterAgent,
    normalize_subtype,
)


def test_system_prompt_uses_version():
    sorter = SorterAgent(prompt_version="sorter_v0")
    prompt = sorter.system_prompt()
    assert "contract" in prompt
    assert "court_opinion" in prompt


def test_system_prompt_v1_includes_contract_subtypes():
    sorter = SorterAgent(prompt_version="sorter_v1")
    prompt = sorter.system_prompt()
    assert "license" in prompt
    assert "non_compete_no_solicit" in prompt
    assert "contract_subtype" in prompt


def test_schema_enum_matches_classes():
    enum = SORTER_SCHEMA["properties"]["doc_type"]["enum"]
    assert enum == DOC_CLASS_KEYS
    # The subgroup dimension: nullable enum of the 25 subtypes + "other".
    subtype = SORTER_SCHEMA["properties"]["contract_subtype"]
    assert subtype["type"] == ["string", "null"]
    assert len(subtype["enum"]) == len(CONTRACT_SUBTYPES) + 1
    assert SUBTYPE_UNKNOWN in subtype["enum"]


def test_classify_returns_parsed_result_with_subtype(mocker):
    sorter = SorterAgent(prompt_version="sorter_v1")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "contract_subtype": "license",
                      "confidence": 0.92, "reasoning": "it is an agreement"},
    )
    doc_type, contract_subtype, confidence, reasoning = sorter.classify("AGREEMENT text here")
    assert doc_type == "contract"
    assert contract_subtype == "license"
    assert confidence == 0.92
    assert "agreement" in reasoning


def test_classify_defaults_on_parse_error(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(sorter, "_call_structured", return_value={"_parse_error": True})
    doc_type, contract_subtype, confidence, reasoning = sorter.classify("text")
    assert doc_type == "correspondence"
    assert contract_subtype == SUBTYPE_UNKNOWN
    assert confidence == 0.3


def test_classify_rejects_unknown_class(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "banana", "confidence": "high", "reasoning": ""},
    )
    doc_type, contract_subtype, confidence, _ = sorter.classify("text")
    assert doc_type == "correspondence"
    assert contract_subtype == SUBTYPE_UNKNOWN
    assert confidence == 0.5


def test_classify_json_returns_dict(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "contract_subtype": "co_branding",
                      "confidence": 0.9, "reasoning": "r"},
    )
    result = sorter.classify_json("text")
    assert result["doc_type"] == "contract"
    assert result["contract_subtype"] == "co_branding"
    assert result["confidence"] == 0.9


def test_classify_subtype_null_for_non_contract(mocker):
    sorter = SorterAgent(prompt_version="sorter_v1")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "correspondence", "contract_subtype": "license",
                      "confidence": 0.8, "reasoning": "a letter"},
    )
    result = sorter.classify_json("text")
    assert result["doc_type"] == "correspondence"
    assert result["contract_subtype"] == SUBTYPE_UNKNOWN  # subtype only for contracts


def test_normalize_subtype_aliases_and_labels():
    assert normalize_subtype("license") == "license"
    assert normalize_subtype("License_Agreements") == "license"
    assert normalize_subtype("License Agreement") == "license"
    assert normalize_subtype("Joint Venture _ Filing") == "joint_venture"
    assert normalize_subtype("Non_Compete_Non_Solicit") == "non_compete_no_solicit"
    assert normalize_subtype("Affiliate Agreement") == "affiliate"
    assert normalize_subtype("totally unknown") == SUBTYPE_UNKNOWN
    assert normalize_subtype(None) == SUBTYPE_UNKNOWN
    assert normalize_subtype("") == SUBTYPE_UNKNOWN


def test_truncate_input_budget():
    sorter = SorterAgent()
    sorter._max_input_chars = 50
    truncated = sorter.truncate_input("x" * 200)
    assert len(truncated) < 200
    assert "truncated" in truncated
    short = sorter.truncate_input("short")
    assert short == "short"
