"""Tests for the deterministic field-type-aware extraction scorer."""

import pytest

from src.field_scoring import (
    EntityListScore,
    ExtractionScoreResult,
    get_field_types,
    is_entity_list,
    normalize_text,
    score_date_field,
    score_entity_list,
    score_field,
    score_free_text_field,
    score_id_field,
    score_money_field,
    score_name_field,
    score_extraction,
)


def test_normalize_text_strips_suffixes_and_punct():
    assert normalize_text("Global Technologies, Ltd.") == "GLOBAL TECHNOLOGIES"
    assert normalize_text("Acme Corp") == "ACME"
    assert normalize_text("John Smith, Esq.") == "JOHN SMITH"


def test_score_id_exact_after_normalize():
    assert score_id_field("sec-file-001", "SEC FILE 001") == 1.0
    assert score_id_field("123", "456") == 0.0


def test_score_date_canonicalization():
    assert score_date_field("March 3, 2024", "03/03/2024") == 1.0
    assert score_date_field("2024-03-03", "2024-03-03") == 1.0
    assert score_date_field("March 3, 2024", "March 4, 2024") == 0.0


def test_score_money_parse_and_tolerance():
    assert score_money_field("$218,440.00", "218440.00") == 1.0
    assert score_money_field("$250,001", "$250,000") == 0.0  # exact amounts
    assert score_money_field("1.2M", "1200000") == 1.0
    # Unparseable prose falls back to fuzzy, never 0.
    assert score_money_field("not stated", "not stated") == 1.0


def test_score_name_fuzzy():
    assert score_name_field("Acme Technologies, Inc.", "Acme Technologies Incorporated") >= 0.9
    assert score_name_field("Northwind Logistics Corporation", "HarborPoint Holdings, Inc.") < 0.8


def test_score_name_disjoint_tokens_not_rescued_by_jaro():
    # "BETA" vs a long unrelated name must NOT match via bare Jaro-Winkler
    # (~0.62 without the disjoint-token guard).
    assert score_name_field("Beta Holdings Corp.", "Sovereign State Bank of Ohio") < 0.5
    assert score_name_field("Beta", "Sovereign State Bank of Ohio") < 0.5


def test_score_free_text_token_f1():
    assert score_free_text_field("payment within ten days", "Payment within 10 days") >= 0.5
    assert score_free_text_field("", "something") == 0.0


def test_score_entity_list_bipartite():
    pred = ["Acme Technologies, Inc.", "Beta Logistics Holdings LLC", "Gamma Distribution Corp."]
    exp = ["Gamma Distribution Corporation", "Acme Technologies Incorporated", "Sovereign State Bank of Ohio"]
    result = score_entity_list("name", pred, exp)
    assert isinstance(result, EntityListScore)
    assert result.matched == 2  # Acme + Gamma match; Beta is extra
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(2 / 3)
    assert result.f1 == pytest.approx(2 / 3)


def test_score_entity_list_reordered():
    pred = ["Alpha LLC", "Beta LLC", "Gamma LLC"]
    exp = ["Beta LLC", "Gamma LLC", "Alpha LLC"]
    result = score_entity_list("name", pred, exp)
    assert result.f1 == 1.0  # reordering must not hurt


def test_score_entity_list_empty():
    assert score_entity_list("name", [], []).f1 == 1.0
    assert score_entity_list("name", [], ["A"]).f1 == 0.0
    assert score_entity_list("name", ["A"], []).f1 == 0.0


def test_is_entity_list():
    assert is_entity_list("entity_list")
    assert is_entity_list("entity_list:name")
    assert not is_entity_list("name")


def test_get_field_types_from_taxonomy():
    types = get_field_types("contract")
    assert types["parties"] == "entity_list:name"
    assert types["effective_date"] == "date"
    assert types["governing_law"] == "name"
    assert types["termination_clauses"] == "entity_list:free_text"
    assert types["key_obligations"] == "entity_list:free_text"


def test_score_extraction_skips_null_expectations():
    expected = {
        "governing_law": "State of Delaware",
        "effective_date": None,  # not a requirement
        "parties": ["Acme Inc.", "Beta LLC"],
    }
    predicted = {
        "governing_law": "Delaware",
        "effective_date": "2024-01-01",
        "parties": ["Acme Incorporated", "Beta LLC"],
    }
    result = score_extraction("contract", get_field_types("contract"), predicted, expected)
    assert isinstance(result, ExtractionScoreResult)
    assert "effective_date" not in result.field_scores  # null expectation skipped
    assert result.field_scores["governing_law"] > 0.9
    assert result.entity_list_scores["parties"].f1 == 1.0
    assert result.overall_score is not None


def test_score_extraction_missing_field_scores_zero():
    expected = {"governing_law": "State of Delaware"}
    result = score_extraction("contract", get_field_types("contract"), {}, expected)
    assert result.field_scores["governing_law"] == 0.0
    assert result.overall_score == 0.0


def test_score_extraction_ambiguous_band_flags_fields():
    expected = {"governing_law": "State of Delaware"}
    # A partial paraphrase ("Delaware law governs") lands inside the band.
    result = score_extraction("contract", get_field_types("contract"),
                              {"governing_law": "Delaware law governs"}, expected)
    assert result.ambiguous_fields == ["governing_law"]
    assert result.needs_judge_review is True


def test_score_field_dispatch():
    assert score_field("date", "2024-01-01", "01/01/2024") == 1.0
    assert isinstance(score_field("entity_list:name", ["a"], ["a"]), EntityListScore)
