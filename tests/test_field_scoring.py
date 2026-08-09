"""Tests for the deterministic field-type-aware extraction scorer."""

import pytest

from src.field_scoring import (
    EntityListScore,
    ExtractionScoreResult,
    audit_list_field,
    get_field_types,
    is_entity_list,
    normalize_text,
    score_containment_field,
    score_date_field,
    score_entity_list,
    score_field,
    score_free_text_field,
    score_id_field,
    score_money_field,
    score_name_field,
    score_extraction,
    verify_list_items,
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
    # governing_law is a containment field: "Delaware" covers half the label's
    # content tokens ("State of Delaware") -> 0.5, inside the ambiguous band,
    # which is exactly the escalation signal.
    assert result.field_scores["governing_law"] == 0.5
    assert result.ambiguous_fields == ["governing_law"]
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


def test_score_date_ordinal_prose_forms():
    # CUAD ground truth writes "1st day of November, 2002" / "10th day of
    # January 2000" / "7th day of April, 2017"; the parser must canonicalize
    # them and match the model's ISO output.
    assert score_date_field("2002-11-01", "1st day of November, 2002") == 1.0
    assert score_date_field("2000-01-10", "10th day of January 2000") == 1.0
    assert score_date_field("2017-04-07", "7th day of April, 2017") == 1.0
    # Stray trailing artifact from the CUAD snippet ("2007 (").
    assert score_date_field("2007-04-01", "1st day of April, 2007 (") == 1.0


def test_score_containment_superset_not_penalized():
    expected = "This Agreement shall be governed by the laws of the State of Delaware."
    # The model returns the expected sentence PLUS venue language — the
    # substance is fully covered, so the score stays 1.0.
    predicted = (expected + " The venue shall be Wilmington. The prevailing party "
                            "shall recover its reasonable attorney's fees.")
    assert score_containment_field(predicted, expected) == 1.0
    # Truncating the expected text loses coverage.
    assert score_containment_field("governed by the laws of Delaware", expected) < 1.0
    assert score_containment_field("", expected) == 0.0


def test_score_entity_list_partial_gt_uses_recall():
    # Ground truth lists ONE party; the model correctly names both. F1 would
    # drop to 0.67 for a correct, complete extraction; partial-GT scoring
    # reports ground-truth coverage (recall) instead.
    result = score_entity_list("name", ["Acme Technologies, Inc.", "Beta LLC"],
                               ["Acme Technologies, Inc."], partial_gt=True)
    assert result.score == 1.0
    assert result.recall == 1.0
    assert result.precision == pytest.approx(0.5)  # still reported honestly
    assert result.f1 == pytest.approx(2 / 3)


def test_score_entity_list_partial_gt_role_words():
    # CUAD labels parties by role ("Shipper.", "Sponsor") instead of the
    # legal name; any named party instantiates the role.
    result = score_entity_list(
        "name",
        ["LOUISVILLE GAS AND ELECTRIC COMPANY, a Kentucky Corporation (\"Shipper\")",
         "TENNESSEE GAS PIPELINE COMPANY (\"Transporter\")"],
        ["Shipper."],
        partial_gt=True,
    )
    assert result.score == 1.0
    # A partial-GT list with no prediction at all still scores 0.
    assert score_entity_list("name", [], ["Shipper."], partial_gt=True).score == 0.0


def test_score_entity_list_fragment_answer_within_verbatim_item():
    # CUAD answers are fragments of the verbatim clause; the model extracts
    # the FULL clause. Token-F1 alone would miss this (Ritter 90-day case).
    fragment = "at any other time upon ninety (90) days' prior written notice of impending termination."
    full_clause = (
        "Sekisui may terminate this Agreement upon prior written notice (i) in the event "
        "of any failure of Qualigen to meet a milestone set forth in the Development Plan, "
        "or (ii) at any other time upon ninety (90) days' prior written notice of impending "
        "termination."
    )
    result = score_entity_list("free_text", [full_clause], [fragment])
    assert result.matched == 1
    assert result.score == 1.0
    # An unrelated clause covering few of the fragment's tokens still fails.
    result2 = score_entity_list("free_text",
                                ["If Qualigen does not pass such audit, Sekisui shall provide a list of remedial action items."],
                                [fragment])
    assert result2.matched == 0


def test_score_extraction_partial_gt_fields_from_taxonomy():
    # Contract fields configured as partial GT (parties) are scored by recall,
    # while F1 fields (a plain name field) keep F1 semantics.
    expected = {"parties": ["Acme Technologies, Inc."]}
    predicted = {"parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."]}
    result = score_extraction("contract", get_field_types("contract"), predicted, expected)
    assert result.entity_list_scores["parties"].score == 1.0
    assert result.field_scores["parties"] == 1.0


def test_score_extraction_containment_fields_from_taxonomy():
    expected = {"governing_law": "This Agreement shall be governed by the laws of the State of Delaware."}
    predicted = {"governing_law": (expected["governing_law"] +
                                   " The venue shall be Wilmington, Delaware. (Section 14)")}
    result = score_extraction("contract", get_field_types("contract"), predicted, expected)
    assert result.field_scores["governing_law"] == 1.0


def test_verify_list_items_grounded_vs_fabricated():
    doc = ("LOUISVILLE GAS AND ELECTRIC COMPANY (\"Shipper\") agrees that Transporter "
           "shall accept and receive daily on a firm basis such quantity of gas as "
           "Shipper makes available up to the Transportation Quantity.")
    flags = verify_list_items(
        ["Transporter shall accept and receive daily on a firm basis such quantity of gas "
         "as Shipper makes available up to the Transportation Quantity",
         "Acme Corporation shall pay Galacticomm one million dollars for hosting",
         "Shipper"],
        doc,
    )
    # Verbatim quote + role word grounded; the fabricated obligation is not.
    assert flags[0] is True
    assert flags[1] is False
    assert flags[2] is True


def test_audit_list_field_true_when_matched_or_grounded():
    doc = ("Acme Technologies, Inc., Beta Holdings Corp., and Sovereign State Bank of "
           "Ohio agree that Acme shall pay Beta the sum of one hundred thousand "
           "dollars for the services.")
    audit = audit_list_field(
        "name",
        ["Acme Technologies, Inc.", "Beta Holdings Corp.", "Sovereign State Bank of Ohio"],
        ["Acme Technologies, Inc."],  # partial GT: only one party labeled
        doc,
    )
    assert audit["n_predicted"] == 3
    assert audit["matched_gt"] == 1
    assert audit["verified_in_doc"] == 3  # all real parties grounded in the doc
    assert audit["true_items"] == 3
    assert audit["verified_precision"] == 1.0
    assert audit["hallucinated"] == 0
    assert audit["hallucination_rate"] == 0.0


def test_audit_list_field_catches_hallucination():
    doc = "Acme Technologies, Inc. and Beta Holdings Corp. agree on the services."
    audit = audit_list_field("name", ["Acme Technologies, Inc.", "Gamma Corp. of Nowhere"],
                             ["Acme Technologies, Inc."], doc)
    assert audit["matched_gt"] == 1
    assert audit["verified_in_doc"] == 1
    assert audit["true_items"] == 1
    assert audit["verified_precision"] == 0.5
    assert audit["hallucinated"] == 1
    assert audit["hallucination_rate"] == 0.5


def test_score_extraction_with_doc_text_produces_audit():
    doc_text = ("This Agreement between Acme Technologies, Inc. and Beta Holdings Corp. "
                "shall be governed by the laws of the State of Delaware. Acme shall pay "
                "Beta one hundred dollars per month.")
    predicted = {
        "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
        "governing_law": "governed by the laws of the State of Delaware",
    }
    expected = {
        "parties": ["Acme Technologies, Inc."],  # partial GT
        "governing_law": "This Agreement shall be governed by the laws of the State of Delaware.",
    }
    result = score_extraction("contract", get_field_types("contract"), predicted, expected,
                              doc_text=doc_text)
    audit = result.entity_list_audit["parties"]
    assert audit["verified_precision"] == 1.0
    assert audit["hallucination_rate"] == 0.0
    assert result.overall_verified_precision == 1.0
    # Without doc_text there is no audit.
    result2 = score_extraction("contract", get_field_types("contract"), predicted, expected)
    assert result2.entity_list_audit == {}


def test_score_extraction_audit_without_doc_text_reports_unverified():
    predicted = {"parties": ["Acme Technologies, Inc.", "Gamma Corp. of Nowhere"]}
    expected = {"parties": ["Acme Technologies, Inc."]}
    result = score_extraction("contract", get_field_types("contract"), predicted, expected)
    assert result.entity_list_audit == {}
    assert result.overall_verified_precision is None


def test_audit_covers_populated_fields_without_gt():
    # The model reports termination_clauses and a scalar governing_law that
    # the ground truth does NOT label. The factuality audit must still cover
    # them — overall_verified_precision is the mean over EVERYTHING reported.
    doc_text = ("This Agreement between Acme Technologies, Inc. and Beta Holdings "
                "Corp. may be terminated by either party for convenience upon sixty "
                "days written notice. The Agreement shall be governed by the laws "
                "of the State of Delaware.")
    predicted = {
        "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
        "termination_clauses": ["terminated for convenience upon sixty days written notice"],
        "governing_law": "governed by the laws of the State of Delaware",
    }
    expected = {"parties": ["Acme Technologies, Inc."]}  # no termination/GL GT
    result = score_extraction("contract", get_field_types("contract"), predicted, expected,
                              doc_text=doc_text)
    # termination_clauses (unlabeled by GT) is audited and grounded.
    assert "termination_clauses" in result.entity_list_audit
    assert result.entity_list_audit["termination_clauses"]["verified_precision"] == 1.0
    # governing_law scalar is audited and grounded (prose-verbatim).
    assert "governing_law" in result.entity_list_audit
    assert result.entity_list_audit["governing_law"]["verified_precision"] == 1.0
    # Overall = mean over parties (1.0), termination_clauses (1.0),
    # governing_law (1.0).
    assert result.overall_verified_precision == 1.0


def test_fabricated_unlabeled_content_drops_overall_verified_precision():
    # The model reports a parties list (grounded), an unlabeled termination
    # clause (grounded), but ALSO a fabricated scalar governing law that does
    # not exist in the document. The overall tracker must reflect the lie.
    doc_text = ("This Agreement between Acme Technologies, Inc. and Beta Holdings "
                "Corp. may be terminated by either party upon sixty days notice.")
    predicted = {
        "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
        "termination_clauses": ["terminated by either party upon sixty days notice"],
        "governing_law": "governed by the laws of the Republic of Zembla",
    }
    result = score_extraction("contract", get_field_types("contract"), predicted, {},
                              doc_text=doc_text)
    audit = result.entity_list_audit
    assert audit["governing_law"]["verified_precision"] == 0.0
    assert audit["governing_law"]["hallucinated"] == 1
    assert audit["parties"]["verified_precision"] == 1.0
    # 2 of 3 audited fields are true -> 0.6667, not a detached 1.0.
    assert result.overall_verified_precision == pytest.approx(2 / 3, abs=1e-4)


def test_scalar_date_verification_uses_prose_form():
    # An ISO date prediction must verify against the document's prose date.
    doc_text = "This Agreement shall become effective as of November 1, 2002."
    result = score_extraction("contract", get_field_types("contract"),
                              {"effective_date": "2002-11-01"}, {},
                              doc_text=doc_text)
    audit = result.entity_list_audit["effective_date"]
    assert audit["verified_in_doc"] == 1
    assert audit["verified_precision"] == 1.0


def test_scalar_date_verification_day_first_and_ocr_typos():
    # CUAD docs carry day-first prose AND OCR artifacts ("18t h day of August
    # 2014"); the predicted ISO date must still verify as grounded.
    doc_text = ("This Agreement is made as of this 18t h day of August 2014 "
                "(the \"Effective Date\").")
    result = score_extraction("contract", get_field_types("contract"),
                              {"effective_date": "2014-08-18"}, {},
                              doc_text=doc_text)
    audit = result.entity_list_audit["effective_date"]
    assert audit["verified_in_doc"] == 1
    assert audit["verified_precision"] == 1.0
    # A genuinely wrong/fabricated date is NOT grounded.
    result2 = score_extraction("contract", get_field_types("contract"),
                               {"effective_date": "2017-01-02"}, {},
                               doc_text=doc_text)
    assert result2.entity_list_audit["effective_date"]["verified_precision"] == 0.0
    assert result2.entity_list_audit["effective_date"]["hallucinated"] == 1


def test_score_category_presence_yes_no():
    from src.field_scoring import score_category_presence

    expectations = {
        "Non-Compete": {"expected": True, "answer": "The Distributor shall not compete with the Company.",
                        "field": "key_obligations"},
        "Exclusivity": {"expected": True, "answer": "exclusive dealing with the counterparty",
                        "field": "key_obligations"},
        "Audit Rights": {"expected": False, "answer": "", "field": "key_obligations"},
    }
    # Both labeled categories are covered by the extraction.
    predicted = {
        "key_obligations": [
            "The Distributor shall not compete with the Company during the Term.",
            "Company grants exclusive dealing rights to the counterparty.",
        ]
    }
    score, detail = score_category_presence(predicted, expectations, get_field_types("contract"))
    assert score == 1.0
    assert detail["Non-Compete"]["matched"] is True
    assert detail["Exclusivity"]["matched"] is True
    assert detail["Audit Rights"]["expected"] is False  # "No" answer: satisfied

    # A category the extraction misses lowers the presence score.
    score2, detail2 = score_category_presence(
        {"key_obligations": ["Some unrelated payment term."]}, expectations,
        get_field_types("contract"))
    assert score2 == 0.0
    assert detail2["Non-Compete"]["matched"] is False

    # No expected-True categories -> presence is trivially perfect.
    score3, _ = score_category_presence({}, {"Audit Rights": {"expected": False, "answer": "",
                                                              "field": "key_obligations"}},
                                        get_field_types("contract"))
    assert score3 == 1.0
