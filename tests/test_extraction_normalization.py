"""Tests for extraction normalization (every schema field guaranteed)."""

import pytest

from agents.specialist_agents import CONTRACTS_SCHEMA, normalize_extraction


def test_normalize_fills_missing_fields():
    result = normalize_extraction({"parties": ["Acme Inc."]}, CONTRACTS_SCHEMA)
    assert result["parties"] == ["Acme Inc."]
    assert result["effective_date"] is None
    assert result["term_length"] is None
    assert result["termination_clauses"] == []
    assert result["governing_law"] is None
    assert result["key_obligations"] == []
    assert result["contract_value"] is None
    assert result["renewal_terms"] is None
    assert result["confidence"] == 0.0


def test_normalize_keeps_present_values():
    result = normalize_extraction(
        {"governing_law": "State of Delaware", "confidence": 0.9,
         "termination_clauses": ["Either party may terminate"]},
        CONTRACTS_SCHEMA,
    )
    assert result["governing_law"] == "State of Delaware"
    assert result["confidence"] == 0.9
    assert result["termination_clauses"] == ["Either party may terminate"]


def test_normalize_empty_string_to_null():
    result = normalize_extraction({"governing_law": ""}, CONTRACTS_SCHEMA)
    assert result["governing_law"] is None


def test_normalize_handles_none_input():
    assert normalize_extraction(None, CONTRACTS_SCHEMA)["parties"] == []
    assert normalize_extraction({}, CONTRACTS_SCHEMA)["confidence"] == 0.0


def test_specialist_extract_normalizes(mocker):
    from agents.specialist_agents import ContractsSpecialist

    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v2")
    mocker.patch.object(
        specialist,
        "_call_structured",
        return_value={"parties": ["Acme Inc."]},  # confidence etc. omitted by the model
    )
    result = specialist.extract("contract text")
    # Confidence is backfilled from the share of fields actually found (1/8).
    assert result["confidence"] == pytest.approx(0.125)
    assert result["key_obligations"] == []
    assert result["parties"] == ["Acme Inc."]


def test_specialist_prompt_version(mocker):
    from agents.specialist_agents import ContractsSpecialist

    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v2")
    assert "COMPLETENESS IS THE PRIORITY" in specialist.system_prompt()
    assert specialist.prompt_version == "contracts_specialist_v2"
