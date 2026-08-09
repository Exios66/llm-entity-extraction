"""CUAD clause categories -> contracts schema fields (ground truth mapping).

CUAD v1 (The Atticus Project) annotates each contract with 41 clause-category
questions whose answers are verbatim spans of the contract ("the labeled
extracted information"). This module maps those categories onto the contracts
specialist's schema fields so the specialist's entity extraction can be scored
against CUAD ground truth:

    build_expected_fields(clause_labels) -> expected_fields dict in the
    schema shape (parties, effective_date, term_length, termination_clauses,
    governing_law, key_obligations, contract_value, renewal_terms).

Only categories with a defensible mapping count as expected fields; unmapped
schema fields are skipped (per score_extraction's rule that null expectations
are not requirements). A category's answer spans are aggregated into the
mapped field's ground-truth value.
"""

from __future__ import annotations

from collections import defaultdict

# CUAD clause category (the quoted name in the question) -> contract schema field.
# Categories with a direct correspondence are mapped; the remaining CUAD
# categories (e.g. License Grant, Source Code Escrow) describe clause presence,
# not one of the schema's eight fields, and are intentionally not scored.
CUAD_CATEGORY_TO_FIELD = {
    "Agreement Date": "effective_date",
    "Effective Date": "effective_date",
    "Expiration Date": "term_length",
    "Governing Law": "governing_law",
    "Parties": "parties",
    "Renewal Term": "renewal_terms",
    "Notice Period To Terminate Renewal": "renewal_terms",
    "Termination For Convenience": "termination_clauses",
    # Obligation-type categories fold into key_obligations.
    "Audit Rights": "key_obligations",
    "Cap On Liability": "key_obligations",
    "Change Of Control": "key_obligations",
    "Competitive Restriction Exception": "key_obligations",
    "Covenant Not To Sue": "key_obligations",
    "Exclusivity": "key_obligations",
    "Insurance": "key_obligations",
    "Ip Ownership Assignment": "key_obligations",
    "Irrevocable Or Perpetual License": "key_obligations",
    "Joint Ip Ownership": "key_obligations",
    "Liquidated Damages": "key_obligations",
    "Minimum Commitment": "key_obligations",
    "Most Favored Nation": "key_obligations",
    "No-Solicit Of Customers": "key_obligations",
    "No-Solicit Of Employees": "key_obligations",
    "Non-Compete": "key_obligations",
    "Non-Disparagement": "key_obligations",
    "Non-Transferable License": "key_obligations",
    "Post-Termination Services": "key_obligations",
    "Price Restrictions": "key_obligations",
    "Revenue/Profit Sharing": "key_obligations",
    "Rofr/Rofo/Rofn": "key_obligations",
    "Source Code Escrow": "key_obligations",
    "Third Party Beneficiary": "key_obligations",
    "Uncapped Liability": "key_obligations",
    "Unlimited/All-You-Can-Eat-License": "key_obligations",
    "Volume Restriction": "key_obligations",
    "Warranty Duration": "key_obligations",
    "License Grant": "key_obligations",
    "Anti-Assignment": "key_obligations",
    "Affiliate License-Licensee": "key_obligations",
    "Affiliate License-Licensor": "key_obligations",
    "Document Name": "key_obligations",
}

# Contract schema fields that are list-valued in the specialist schema.
_LIST_FIELDS = {
    "parties", "termination_clauses", "key_obligations",
}


def category_from_question(question: str) -> str:
    """Extract the CUAD category name from the annotation question.

    Questions look like: 'Highlight the parts (if any) of this contract
    related to "Governing Law" that should be reviewed...' — the category is
    the quoted name. Returns '' when no category is present.
    """
    start = question.find('"')
    end = question.find('"', start + 1) if start != -1 else -1
    if start == -1 or end == -1:
        return ""
    return question[start + 1:end].strip()


def build_expected_fields(clause_labels: list[dict] | None) -> dict:
    """Derive a contracts-schema ``expected_fields`` dict from CUAD clause QA.

    Args:
        clause_labels: The dataset's ``clause_labels`` list — each item is
            ``{"question": ..., "answer": <span text>, ...}``.

    Returns:
        Expected fields in the schema shape. Scalar fields take the first
        non-empty answer span; list fields aggregate all non-empty answer
        spans (deduplicated). Fields with no mapped answers are absent, so
        score_extraction skips them (no ground truth -> not a requirement).
    """
    aggregated: dict[str, list[str]] = defaultdict(list)
    for label in clause_labels or []:
        question = str(label.get("question") or "")
        answer = str(label.get("answer") or "").strip()
        if not answer:
            continue
        category = category_from_question(question)
        if not category:
            continue
        field = CUAD_CATEGORY_TO_FIELD.get(category)
        if field is None:
            continue
        if answer not in aggregated[field]:
            aggregated[field].append(answer)

    expected: dict = {}
    for field, answers in aggregated.items():
        if not answers:
            continue
        if field in _LIST_FIELDS:
            expected[field] = answers
        else:
            expected[field] = answers[0]
    return expected


def mapped_categories() -> dict[str, str]:
    """Return the category->field mapping (exposed for reports/tests)."""
    return dict(CUAD_CATEGORY_TO_FIELD)
