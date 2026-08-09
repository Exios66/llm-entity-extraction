"""Tests for the CUAD clause-QA -> contracts schema ground-truth mapping.

Covers the HF dataset-card specifics: the 41-category catalog, string vs
YES/NO answer formats, the category groups, and the contract-TYPE-driven
expected fields ("not all expected fields map to each document — the group
the document belongs to decides what fields to expect").
"""

from src.cuad_ground_truth import (
    CUAD_CATEGORIES,
    CUAD_CATEGORY_TO_FIELD,
    CUAD_STRING_CATEGORIES,
    CUAD_YES_NO_CATEGORIES,
    applicable_categories,
    build_expected_fields,
    build_presence_expectations,
    canonical_category,
    category_from_question,
    mapped_categories,
)


def _clause(question: str, answer: str) -> dict:
    return {"question": question, "answer": answer, "answer_start": 0}


def test_category_from_question():
    q = 'Highlight the parts (if any) of this contract related to "Governing Law" that should be reviewed...'
    assert category_from_question(q) == "Governing Law"
    assert category_from_question("no quotes here") == ""


def test_canonical_category_handles_aliases_and_casing():
    assert canonical_category("Governing Law") == "Governing Law"
    assert canonical_category("governing law") == "Governing Law"
    assert canonical_category("Affiliate IP License-Licensor") == "Affiliate License-Licensor"
    assert canonical_category("Price Restriction") == "Price Restrictions"
    assert canonical_category("Totally Unknown") is None


def test_catalog_has_41_categories_with_formats():
    assert len(CUAD_CATEGORIES) == 41
    assert set(CUAD_CATEGORY_TO_FIELD) == set(CUAD_CATEGORIES)
    # String-answer categories (8 + Warranty Duration) vs YES/NO (32).
    assert len(CUAD_STRING_CATEGORIES) == 9
    assert len(CUAD_YES_NO_CATEGORIES) == 32
    assert "Governing Law" in CUAD_STRING_CATEGORIES
    assert "Non-Compete" in CUAD_YES_NO_CATEGORIES


def test_catalog_groups_match_dataset_card():
    assert {"Agreement Date", "Effective Date", "Expiration Date",
            "Renewal Term", "Notice Period To Terminate Renewal"} <= set(
        [c for c, s in CUAD_CATEGORIES.items() if s["group"] == 1])
    assert {"Non-Compete", "Exclusivity", "No-Solicit Of Customers",
            "Competitive Restriction Exception"} <= set(
        [c for c, s in CUAD_CATEGORIES.items() if s["group"] == 2])
    assert {"Change Of Control", "Anti-Assignment"} <= set(
        [c for c, s in CUAD_CATEGORIES.items() if s["group"] == 3])
    assert {"License Grant", "Non-Transferable License",
            "Irrevocable Or Perpetual License"} <= set(
        [c for c, s in CUAD_CATEGORIES.items() if s["group"] == 4])
    assert {"Uncapped Liability", "Cap On Liability"} <= set(
        [c for c, s in CUAD_CATEGORIES.items() if s["group"] == 5])


def test_document_name_maps_to_its_own_field_not_obligations():
    # Per the dataset card, Document Name is its own category with a contract-
    # name answer — it must NOT pollute key_obligations with titles.
    labels = [
        _clause('...related to "Document Name" that...', "Web Hosting Agreement"),
        _clause('...related to "Parties" that...', "Acme Inc."),
    ]
    expected = build_expected_fields(labels)
    assert expected["document_name"] == "Web Hosting Agreement"
    assert "key_obligations" not in expected


def test_build_expected_fields_mapping():
    labels = [
        _clause('...related to "Governing Law" that...', "State of Delaware"),
        _clause('...related to "Effective Date" that...', "January 1, 2020"),
        _clause('...related to "Effective Date" that...', "as of the date hereof"),
        _clause('...related to "Parties" that...', "Acme Technologies, Inc."),
        _clause('...related to "Parties" that...', "Beta Holdings Corp."),
        _clause('...related to "Termination For Convenience" that...',
                "Either party may terminate this Agreement for convenience upon sixty days written notice."),
        _clause('...related to "Non-Compete" that...',
                "The Distributor shall not compete with the Company during the Term."),
    ]
    expected = build_expected_fields(labels)
    assert expected["governing_law"] == "State of Delaware"
    assert expected["effective_date"] == "January 1, 2020"  # first non-empty span
    assert expected["parties"] == ["Acme Technologies, Inc.", "Beta Holdings Corp."]
    assert expected["termination_clauses"] == [
        "Either party may terminate this Agreement for convenience upon sixty days written notice."
    ]
    # YES/NO categories fold into key_obligations as content.
    assert "key_obligations" in expected


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


def test_type_decides_expected_fields():
    # Per the dataset card, the group the document belongs to decides what
    # fields to expect: license-grant categories never occur in Transportation
    # agreements, and Non_Compete_Non_Solicit agreements carry few categories.
    transport = build_expected_fields([
        _clause('...related to "License Grant" that...', "Licensor grants a license."),
        _clause('...related to "Parties" that...', "Acme Inc."),
    ], doc_category="Transportation")
    assert "parties" in transport
    assert "key_obligations" not in transport  # License Grant not applicable

    nc = build_expected_fields([
        _clause('...related to "Exclusivity" that...', "exclusive dealing"),
        _clause('...related to "Termination For Convenience" that...', "terminate at will"),
    ], doc_category="Non_Compete_Non_Solicit")
    assert "key_obligations" not in nc  # Exclusivity not applicable to this type
    assert "termination_clauses" not in nc  # Termination For Convenience not applicable


def test_applicable_categories_unknown_type_is_all():
    assert len(applicable_categories(None)) == 41
    assert len(applicable_categories("Totally Unknown Folder")) == 41


def test_presence_expectations_yes_no_semantics():
    # YES/NO categories: labeled clause -> expected True (the extraction must
    # cover it); unlabeled -> expected False (answer "No"). Only applicable
    # categories are included.
    labels = [
        _clause('...related to "Non-Compete" that...', "No competing with the Company."),
        _clause('...related to "Parties" that...', "Acme Inc."),
    ]
    presence = build_presence_expectations(labels, doc_category="Co_Branding")
    assert presence["Non-Compete"]["expected"] is True
    assert presence["Non-Compete"]["answer"] == "No competing with the Company."
    assert presence["Exclusivity"]["expected"] is False  # no text -> answer "No"
    assert presence["Exclusivity"]["answer"] == ""
    assert "Parties" not in presence  # string category, not a presence question
    # Irrevocable Or Perpetual License is excluded for Co_Branding docs.
    assert "Irrevocable Or Perpetual License" not in presence
    # Warranty Duration is excluded for Co_Branding (type filter).
    assert "Warranty Duration" not in presence


def test_mapping_covers_41_cuad_categories():
    assert set(mapped_categories()) == {
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
