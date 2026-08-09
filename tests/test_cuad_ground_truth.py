"""Tests for the CUAD clause-QA -> contracts schema ground-truth mapping."""

from src.cuad_ground_truth import (
    CUAD_CATEGORY_TO_FIELD,
    build_expected_fields,
    category_from_question,
)


def _clause(question: str, answer: str) -> dict:
    return {"question": question, "answer": answer, "answer_start": 0}


def test_category_from_question():
    q = 'Highlight the parts (if any) of this contract related to "Governing Law" that should be reviewed...'
    assert category_from_question(q) == "Governing Law"
    assert category_from_question("no quotes here") == ""


def test_build_expected_fields_mapping():
    labels = [
        _clause('...related to "Governing Law" that...', "State of Delaware"),
        _clause('...related to "Effective Date" that...', "January 1, 2020"),
        _clause('...related to "Effective Date" that...', "as of the date hereof"),
        _clause('...related to "Parties" that...', "Acme Technologies, Inc."),
        _clause('...related to "Parties" that...', "Beta Holdings Corp."),
        _clause('...related to "Termination For Convenience" that...',
                "Either party may terminate this Agreement for convenience upon sixty days written notice."),
    ]
    expected = build_expected_fields(labels)
    assert expected["governing_law"] == "State of Delaware"
    assert expected["effective_date"] == "January 1, 2020"  # first non-empty span
    assert expected["parties"] == ["Acme Technologies, Inc.", "Beta Holdings Corp."]
    assert expected["termination_clauses"] == [
        "Either party may terminate this Agreement for convenience upon sixty days written notice."
    ]
    assert "key_obligations" not in expected  # no obligation categories present


def test_build_expected_fields_dedupes():
    labels = [
        _clause('...related to "Parties" that...', "Acme Inc."),
        _clause('...related to "Parties" that...', "Acme Inc."),
    ]
    expected = build_expected_fields(labels)
    assert expected["parties"] == ["Acme Inc."]


def test_build_expected_fields_ignores_empty_and_unknown():
    labels = [
        _clause('...related to "Governing Law" that...', ""),
        _clause('...related to "Totally Unknown Category" that...', "something"),
        {"question": "", "answer": "x"},
    ]
    assert build_expected_fields(labels) == {}


def test_build_expected_fields_none():
    assert build_expected_fields(None) == {}
    assert build_expected_fields([]) == {}


def test_mapping_covers_41_cuad_categories():
    assert len(CUAD_CATEGORY_TO_FIELD) == 41
    assert set(CUAD_CATEGORY_TO_FIELD) == {
        "Agreement Date", "Effective Date", "Expiration Date", "Governing Law",
        "Parties", "Renewal Term", "Notice Period To Terminate Renewal",
        "Termination For Convenience", "Audit Rights", "Cap On Liability",
        "Change Of Control", "Competitive Restriction Exception", "Covenant Not To Sue",
        "Exclusivity", "Insurance", "Ip Ownership Assignment",
        "Irrevocable Or Perpetual License", "Joint Ip Ownership", "Liquidated Damages",
        "Minimum Commitment", "Most Favored Nation", "No-Solicit Of Customers",
        "No-Solicit Of Employees", "Non-Compete", "Non-Disparagement",
        "Non-Transferable License", "Post-Termination Services", "Price Restrictions",
        "Revenue/Profit Sharing", "Rofr/Rofo/Rofn", "Source Code Escrow",
        "Third Party Beneficiary", "Uncapped Liability", "Unlimited/All-You-Can-Eat-License",
        "Volume Restriction", "Warranty Duration", "License Grant", "Anti-Assignment",
        "Affiliate License-Licensee", "Affiliate License-Licensor", "Document Name",
    }
