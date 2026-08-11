"""CUAD v1 clause categories -> contracts schema ground truth (per HF spec).

CUAD v1 (The Atticus Project, https://huggingface.co/datasets/theatticusproject/cuad)
annotates each contract with 41 clause-category questions. Per the dataset
card's CATEGORY LIST:

- 8 categories ask for STRING answers (contract name, parties, dates, renewal
  term, notice period, governing law); Warranty Duration additionally asks for
  a duration (months/years). These map onto the contracts specialist's schema
  fields and are scored as content.
- The remaining 32 categories expect a YES/NO answer: if there is a segment of
  text corresponding to the category the answer is "Yes" (the segment is the
  clause context), otherwise "No". These are scored BOTH as content (the
  labeled clause text becomes an expected list item) AND as binary PRESENCE
  expectations (the extraction must include each labeled category's clause).
  (The dataset card says "33 out of 41" are Yes/No and "8" are strings, but the
  category table lists Warranty Duration with a numeric answer format — this
  module classifies by the table: 9 string-type, 32 Yes/No.)
- Categories are grouped (Groups 1-5) where clauses overlap or build on each
  other: Group 1 = Agreement/Effective/Expiration Date + Renewal Term + Notice
  to Terminate Renewal; Group 2 = Non-Compete/Exclusivity/No-Solicit of
  Customers/Competitive Restriction Exception; Group 3 = Change of Control +
  Anti-Assignment; Group 4 = the license-grant family; Group 5 = liability caps.
- NOT all categories map to every document: the contract TYPE (the CUAD folder
  the PDF came from, e.g. "License_Agreements", "Non_Compete_Non_Solicit")
  decides which categories are applicable. ``CUAD_TYPE_EXCLUDED_CATEGORIES``
  records, per type, the categories that never occur in that type's documents
  (computed from all 510 CUAD v1 contracts), so a document's expected fields
  are derived ONLY from categories applicable to its type.

    build_expected_fields(clause_labels, doc_category) -> expected_fields
    build_presence_expectations(clause_labels, doc_category) -> yes/no presence
"""

from __future__ import annotations

import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Canonical category catalog (names exactly as quoted in CUAD_v1.json)
# ---------------------------------------------------------------------------

ANSWER_STRING = "string"
ANSWER_YES_NO = "yes_no"

# category -> {"answer_format", "group", "field"}
# ``field``: contracts-schema field the category's clause text maps to for
# content scoring (None = the schema has no home for this category; its
# labels are presence-tracked but not content-scored).
CUAD_CATEGORIES: dict[str, dict] = {
    "Document Name":                       {"answer_format": ANSWER_STRING, "group": None, "field": "document_name"},
    "Parties":                             {"answer_format": ANSWER_STRING, "group": None, "field": "parties"},
    "Agreement Date":                      {"answer_format": ANSWER_STRING, "group": 1, "field": "effective_date"},
    "Effective Date":                      {"answer_format": ANSWER_STRING, "group": 1, "field": "effective_date"},
    "Expiration Date":                     {"answer_format": ANSWER_STRING, "group": 1, "field": "term_length"},
    "Renewal Term":                        {"answer_format": ANSWER_STRING, "group": 1, "field": "renewal_terms"},
    "Notice Period To Terminate Renewal":  {"answer_format": ANSWER_STRING, "group": 1, "field": "renewal_terms"},
    "Governing Law":                       {"answer_format": ANSWER_STRING, "group": None, "field": "governing_law"},
    "Warranty Duration":                   {"answer_format": ANSWER_STRING, "group": None, "field": None},
    "Most Favored Nation":                 {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Non-Compete":                         {"answer_format": ANSWER_YES_NO, "group": 2, "field": "key_obligations"},
    "Exclusivity":                         {"answer_format": ANSWER_YES_NO, "group": 2, "field": "key_obligations"},
    "No-Solicit Of Customers":             {"answer_format": ANSWER_YES_NO, "group": 2, "field": "key_obligations"},
    "Competitive Restriction Exception":   {"answer_format": ANSWER_YES_NO, "group": 2, "field": "key_obligations"},
    "No-Solicit Of Employees":             {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Non-Disparagement":                   {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Termination For Convenience":         {"answer_format": ANSWER_YES_NO, "group": None, "field": "termination_clauses"},
    "Rofr/Rofo/Rofn":                      {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Change Of Control":                   {"answer_format": ANSWER_YES_NO, "group": 3, "field": "key_obligations"},
    "Anti-Assignment":                     {"answer_format": ANSWER_YES_NO, "group": 3, "field": "key_obligations"},
    "Revenue/Profit Sharing":              {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Price Restrictions":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Minimum Commitment":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Volume Restriction":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Ip Ownership Assignment":             {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Joint Ip Ownership":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "License Grant":                       {"answer_format": ANSWER_YES_NO, "group": 4, "field": "key_obligations"},
    "Non-Transferable License":            {"answer_format": ANSWER_YES_NO, "group": 4, "field": "key_obligations"},
    "Affiliate License-Licensor":          {"answer_format": ANSWER_YES_NO, "group": 4, "field": "key_obligations"},
    "Affiliate License-Licensee":          {"answer_format": ANSWER_YES_NO, "group": 4, "field": "key_obligations"},
    "Unlimited/All-You-Can-Eat-License":   {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Irrevocable Or Perpetual License":    {"answer_format": ANSWER_YES_NO, "group": 4, "field": "key_obligations"},
    "Source Code Escrow":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Post-Termination Services":           {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Audit Rights":                        {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Uncapped Liability":                  {"answer_format": ANSWER_YES_NO, "group": 5, "field": "key_obligations"},
    "Cap On Liability":                    {"answer_format": ANSWER_YES_NO, "group": 5, "field": "key_obligations"},
    "Liquidated Damages":                  {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Insurance":                           {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Covenant Not To Sue":                 {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
    "Third Party Beneficiary":             {"answer_format": ANSWER_YES_NO, "group": None, "field": "key_obligations"},
}

# Aliases: dataset-card spelling variants of the JSON's quoted names.
CATEGORY_ALIASES = {
    "Affiliate Ip License-Licensor": "Affiliate License-Licensor",
    "Affiliate Ip License-Licensee": "Affiliate License-Licensee",
    "Right Of First Refusal, Offer Or Negotiation (Rofr/Rofo/Rofn)": "Rofr/Rofo/Rofn",
    "Unlimited/All-You-Can-Eat License": "Unlimited/All-You-Can-Eat-License",
    "Price Restriction": "Price Restrictions",
    "Notice To Terminate Renewal": "Notice Period To Terminate Renewal",
    "Non-Solicit Of Customers": "No-Solicit Of Customers",
    "Non-Solicit Of Employees": "No-Solicit Of Employees",
}

# Backward-compatible category -> field view (41 entries).
CUAD_CATEGORY_TO_FIELD = {name: spec["field"] for name, spec in CUAD_CATEGORIES.items()}

# String- vs Yes/No-answer categories (per the category table above).
CUAD_STRING_CATEGORIES = {
    name for name, spec in CUAD_CATEGORIES.items() if spec["answer_format"] == ANSWER_STRING
}
CUAD_YES_NO_CATEGORIES = set(CUAD_CATEGORIES) - CUAD_STRING_CATEGORIES

# HF Groups (clauses that overlap/build on each other).
CUAD_GROUPS: dict[int, set[str]] = defaultdict(set)
for name, spec in CUAD_CATEGORIES.items():
    if spec["group"] is not None:
        CUAD_GROUPS[spec["group"]].add(name)

# ---------------------------------------------------------------------------
# Contract TYPE -> applicable categories
# ---------------------------------------------------------------------------
#
# The contract type is the CUAD folder the PDF lives in. NOT all 41 categories
# occur in every type's documents (e.g. license-grant categories never appear
# in Transportation agreements; Non_Compete_Non_Solicit agreements carry only
# 12 of the 41). This table records, per type, the categories that NEVER occur
# in that type's documents — computed from all 510 CUAD v1 contracts — so a
# document's expected fields are driven by the group/type it belongs to.
# ``field``-mapped categories absent from a type are not expected.

CUAD_TYPE_EXCLUDED_CATEGORIES: dict[str, set[str]] = {
    "Affiliate_Agreements": {"Affiliate License-Licensor", "Irrevocable Or Perpetual License",
                             "Most Favored Nation", "Price Restrictions", "Source Code Escrow",
                             "Third Party Beneficiary", "Unlimited/All-You-Can-Eat-License"},
    "Agency Agreements": {"Affiliate License-Licensor", "Competitive Restriction Exception",
                          "Covenant Not To Sue", "Ip Ownership Assignment",
                          "Irrevocable Or Perpetual License", "Joint Ip Ownership",
                          "Most Favored Nation", "No-Solicit Of Employees",
                          "Non-Disparagement", "Non-Transferable License", "Price Restrictions",
                          "Source Code Escrow", "Uncapped Liability",
                          "Unlimited/All-You-Can-Eat-License", "Volume Restriction"},
    "Co_Branding": {"Irrevocable Or Perpetual License", "No-Solicit Of Employees",
                    "Non-Disparagement", "Source Code Escrow", "Third Party Beneficiary",
                    "Warranty Duration"},
    "Collaboration": {"No-Solicit Of Customers", "Price Restrictions", "Source Code Escrow",
                      "Unlimited/All-You-Can-Eat-License"},
    "Consulting Agreements": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                              "Audit Rights", "Covenant Not To Sue", "Joint Ip Ownership",
                              "Minimum Commitment", "Most Favored Nation",
                              "Non-Transferable License", "Price Restrictions",
                              "Rofr/Rofo/Rofn", "Source Code Escrow", "Third Party Beneficiary",
                              "Uncapped Liability", "Unlimited/All-You-Can-Eat-License",
                              "Warranty Duration"},
    "Development": {"Price Restrictions", "Source Code Escrow", "Third Party Beneficiary"},
    "Distributor": {"Source Code Escrow", "Third Party Beneficiary",
                    "Unlimited/All-You-Can-Eat-License"},
    "Endorsement": {"Affiliate License-Licensor", "Liquidated Damages", "Most Favored Nation",
                    "No-Solicit Of Customers", "No-Solicit Of Employees", "Price Restrictions",
                    "Source Code Escrow", "Uncapped Liability", "Warranty Duration"},
    "Endorsement Agreement": {"Affiliate License-Licensor", "Irrevocable Or Perpetual License",
                              "Joint Ip Ownership", "No-Solicit Of Customers",
                              "No-Solicit Of Employees", "Non-Disparagement",
                              "Non-Transferable License", "Notice Period To Terminate Renewal",
                              "Price Restrictions", "Renewal Term", "Rofr/Rofo/Rofn",
                              "Source Code Escrow", "Uncapped Liability", "Warranty Duration"},
    "Franchise": {"Joint Ip Ownership", "Most Favored Nation", "Price Restrictions",
                  "Source Code Escrow", "Unlimited/All-You-Can-Eat-License",
                  "Warranty Duration"},
    "Hosting": {"Affiliate License-Licensor", "Most Favored Nation", "Non-Disparagement",
                "Rofr/Rofo/Rofn"},
    "IP": {"Competitive Restriction Exception", "Liquidated Damages", "Most Favored Nation",
           "No-Solicit Of Customers", "No-Solicit Of Employees",
           "Notice Period To Terminate Renewal", "Price Restrictions", "Renewal Term",
           "Source Code Escrow", "Uncapped Liability", "Volume Restriction",
           "Warranty Duration"},
    "Joint Venture": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                      "Cap On Liability", "Competitive Restriction Exception",
                      "Covenant Not To Sue", "Irrevocable Or Perpetual License",
                      "Liquidated Damages", "Most Favored Nation", "No-Solicit Of Customers",
                      "No-Solicit Of Employees", "Non-Disparagement",
                      "Non-Transferable License", "Price Restrictions", "Source Code Escrow",
                      "Termination For Convenience", "Third Party Beneficiary",
                      "Uncapped Liability", "Unlimited/All-You-Can-Eat-License",
                      "Volume Restriction", "Warranty Duration"},
    "Joint Venture _ Filing": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                               "Change Of Control", "Covenant Not To Sue",
                               "Irrevocable Or Perpetual License", "Joint Ip Ownership",
                               "License Grant", "Liquidated Damages", "No-Solicit Of Customers",
                               "No-Solicit Of Employees", "Non-Disparagement",
                               "Non-Transferable License", "Notice Period To Terminate Renewal",
                               "Price Restrictions", "Renewal Term", "Revenue/Profit Sharing",
                               "Source Code Escrow", "Uncapped Liability",
                               "Unlimited/All-You-Can-Eat-License", "Volume Restriction",
                               "Warranty Duration"},
    "License_Agreements": {"Competitive Restriction Exception", "No-Solicit Of Customers",
                           "No-Solicit Of Employees", "Source Code Escrow",
                           "Warranty Duration"},
    "Maintenance": {"Affiliate License-Licensor", "Competitive Restriction Exception",
                    "Most Favored Nation", "No-Solicit Of Customers", "Non-Disparagement"},
    "Manufacturing": {"Most Favored Nation", "Non-Disparagement", "Revenue/Profit Sharing",
                      "Source Code Escrow", "Third Party Beneficiary",
                      "Unlimited/All-You-Can-Eat-License"},
    "Marketing": {"Affiliate License-Licensor", "Most Favored Nation", "Price Restrictions",
                  "Source Code Escrow", "Unlimited/All-You-Can-Eat-License"},
    "Non_Compete_Non_Solicit": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                                "Audit Rights", "Cap On Liability", "Change Of Control",
                                "Covenant Not To Sue", "Exclusivity", "Insurance",
                                "Ip Ownership Assignment", "Irrevocable Or Perpetual License",
                                "Joint Ip Ownership", "License Grant", "Liquidated Damages",
                                "Minimum Commitment", "Most Favored Nation",
                                "No-Solicit Of Customers", "Non-Disparagement",
                                "Non-Transferable License", "Notice Period To Terminate Renewal",
                                "Post-Termination Services", "Price Restrictions",
                                "Renewal Term", "Source Code Escrow",
                                "Termination For Convenience", "Third Party Beneficiary",
                                "Uncapped Liability", "Unlimited/All-You-Can-Eat-License",
                                "Volume Restriction", "Warranty Duration"},
    "Outsourcing": {"Affiliate License-Licensee", "Competitive Restriction Exception",
                    "Joint Ip Ownership", "No-Solicit Of Customers", "Non-Compete",
                    "Non-Disparagement"},
    "Promotion": {"Irrevocable Or Perpetual License", "Joint Ip Ownership",
                  "No-Solicit Of Customers", "Non-Disparagement", "Price Restrictions",
                  "Source Code Escrow", "Third Party Beneficiary",
                  "Unlimited/All-You-Can-Eat-License"},
    "Reseller": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                 "Joint Ip Ownership", "Most Favored Nation", "No-Solicit Of Customers",
                 "Price Restrictions", "Rofr/Rofo/Rofn"},
    "Service": {"Most Favored Nation", "Price Restrictions", "Source Code Escrow",
                "Unlimited/All-You-Can-Eat-License", "Volume Restriction",
                "Warranty Duration"},
    "Sponsorship": {"Affiliate License-Licensor", "Irrevocable Or Perpetual License",
                    "Liquidated Damages", "No-Solicit Of Customers",
                    "No-Solicit Of Employees", "Source Code Escrow",
                    "Unlimited/All-You-Can-Eat-License"},
    "Strategic Alliance": {"Price Restrictions"},
    "Supply": {"Affiliate License-Licensor", "No-Solicit Of Customers",
               "Non-Disparagement", "Source Code Escrow", "Third Party Beneficiary",
               "Unlimited/All-You-Can-Eat-License"},
    "Transportation": {"Affiliate License-Licensee", "Affiliate License-Licensor",
                       "Ip Ownership Assignment", "Irrevocable Or Perpetual License",
                       "Joint Ip Ownership", "License Grant", "No-Solicit Of Employees",
                       "Non-Disparagement", "Non-Transferable License",
                       "Source Code Escrow", "Third Party Beneficiary",
                       "Unlimited/All-You-Can-Eat-License"},
}

# Type folder aliases (variants observed in the CUAD tree).
TYPE_ALIASES = {
    "Affiliate Agreement": "Affiliate_Agreements",
}

# Canonical sorter subtype key -> the CUAD folder name(s) that map to it
# (reverse of the folder->key aliases in ``agents/sorter_agent.py``; a few
# keys cover multiple folders, e.g. endorsement and joint_venture). This is
# what lets the chained handoff cue the specialist with the field scope of
# the PREDICTED subtype (production-identical: no ground-truth leakage).
SUBTYPE_CUAD_FOLDERS: dict[str, list[str]] = {
    "affiliate": ["Affiliate_Agreements"],
    "agency": ["Agency Agreements"],
    "co_branding": ["Co_Branding"],
    "collaboration": ["Collaboration"],
    "consulting": ["Consulting Agreements"],
    "development": ["Development"],
    "distributor": ["Distributor"],
    "endorsement": ["Endorsement", "Endorsement Agreement"],
    "franchise": ["Franchise"],
    "hosting": ["Hosting"],
    "ip": ["IP"],
    "joint_venture": ["Joint Venture", "Joint Venture _ Filing"],
    "license": ["License_Agreements"],
    "maintenance": ["Maintenance"],
    "manufacturing": ["Manufacturing"],
    "marketing": ["Marketing"],
    "non_compete_no_solicit": ["Non_Compete_Non_Solicit"],
    "outsourcing": ["Outsourcing"],
    "promotion": ["Promotion"],
    "reseller": ["Reseller"],
    "service": ["Service"],
    "sponsorship": ["Sponsorship"],
    "strategic_alliance": ["Strategic Alliance"],
    "supply": ["Supply"],
    "transportation": ["Transportation"],
    "other": [],
}

# Contracts-schema fields, in the order the handoff cue lists them.
_HANDOFF_FIELD_ORDER = [
    "document_name", "parties", "effective_date", "term_length",
    "renewal_terms", "governing_law", "key_obligations", "termination_clauses",
]

_ALL_CATEGORIES = set(CUAD_CATEGORIES)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


# Normalized lookup covering canonical names AND alias spellings (so
# "Affiliate IP License-Licensor" and "Affiliate Ip License-Licensor" both
# resolve to "Affiliate License-Licensor").
_NORM_LOOKUP: dict[str, str] = {}


def _build_norm_lookup() -> None:
    for name in _ALL_CATEGORIES:
        _NORM_LOOKUP[_normalize(name)] = name
    for alias, name in CATEGORY_ALIASES.items():
        _NORM_LOOKUP.setdefault(_normalize(alias), name)


_build_norm_lookup()


_NORM_CATEGORY_CACHE: dict[str, str] = {}


def canonical_category(name: str) -> str | None:
    """Resolve a (possibly aliased/mis-cased) category name to its canonical
    CUAD_v1.json name, or None when unknown."""
    name = (name or "").strip()
    if name in CUAD_CATEGORIES:
        return name
    if name in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[name]
    key = _normalize(name)
    if key in _NORM_CATEGORY_CACHE:
        return _NORM_CATEGORY_CACHE[key] or None
    resolved = _NORM_LOOKUP.get(key)
    _NORM_CATEGORY_CACHE[key] = resolved or ""
    return resolved


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


def applicable_categories(doc_category: str | None) -> set[str]:
    """Categories applicable to a document of ``doc_category`` (the CUAD
    folder/type). Unknown types are treated as all-41 (no filtering).
    """
    if not doc_category:
        return set(_ALL_CATEGORIES)
    type_key = TYPE_ALIASES.get(doc_category, doc_category)
    excluded = CUAD_TYPE_EXCLUDED_CATEGORIES.get(type_key)
    if excluded is None:
        return set(_ALL_CATEGORIES)
    return _ALL_CATEGORIES - excluded


def build_subtype_handoff(subtype: str | None) -> str:
    """Build the subtype-scoped extraction cue for the chained handoff.

    A pure function of the PREDICTED sorter subtype: the schema field groups
    the specialist should expect for that contract family (per the CUAD
    dataset card, "the group a document belongs to decides what fields to
    expect"), grouped by the CUAD categories that map to each field, plus the
    categories that NEVER apply to the family (the specialist must not invent
    them). Only category/field NAMES are passed — never ground-truth answers —
    so the cue is production-identical and leaks nothing.

    Returns an empty string for the fallback/unknown subtype (no narrowing).
    """
    subtype = str(subtype or "").strip().lower()
    folders = SUBTYPE_CUAD_FOLDERS.get(subtype) or []
    if not folders:
        return ""
    applicable: set[str] = set()
    for folder in folders:
        applicable |= applicable_categories(folder)

    fields: dict[str, list[str]] = defaultdict(list)
    presence_only: list[str] = []
    for category in sorted(applicable):
        field = CUAD_CATEGORIES[category]["field"]
        if field is None:
            presence_only.append(category)
        else:
            fields[field].append(category)

    excluded = sorted(_ALL_CATEGORIES - applicable)
    lines = [f"Expected field groups for this {subtype} agreement family:"]
    for field in _HANDOFF_FIELD_ORDER:
        if field in fields:
            lines.append(f"- {field}: {', '.join(fields[field])}")
    if presence_only:
        lines.append(f"- presence-only clauses (tracked, not extracted): "
                     f"{', '.join(presence_only)}")
    if excluded:
        lines.append("Not expected in this family — do not invent clauses for: "
                     f"{', '.join(excluded)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Expected-fields derivation
# ---------------------------------------------------------------------------

_LIST_FIELDS = {"parties", "termination_clauses", "key_obligations"}


def _labeled_categories(clause_labels: list[dict] | None) -> dict[str, list[str]]:
    """Category -> non-empty answer spans (canonical category names only)."""
    by_category: dict[str, list[str]] = defaultdict(list)
    for label in clause_labels or []:
        question = str(label.get("question") or "")
        answer = str(label.get("answer") or "").strip()
        if not answer:
            continue
        category = canonical_category(category_from_question(question))
        if category is None:
            continue
        if answer not in by_category[category]:
            by_category[category].append(answer)
    return by_category


def build_expected_fields(clause_labels: list[dict] | None,
                          doc_category: str | None = None) -> dict:
    """Derive a contracts-schema ``expected_fields`` dict from CUAD clause QA.

    Args:
        clause_labels: The dataset's ``clause_labels`` list — each item is
            ``{"question": ..., "answer": <span text>, ...}``.
        doc_category: The contract TYPE (CUAD folder, e.g. "License_Agreements").
            Only categories applicable to that type count as expected —
            "NOT all expected fields map to each document: the group the
            document belongs to decides what fields to expect". None = all
            categories applicable.

    Returns:
        Expected fields in the schema shape. Scalar fields take the first
        non-empty answer span; list fields aggregate all non-empty answer
        spans (deduplicated). Fields with no mapped answers are absent, so
        score_extraction skips them (no ground truth -> not a requirement).
    """
    applicable = applicable_categories(doc_category)
    aggregated: dict[str, list[str]] = defaultdict(list)
    for category, answers in _labeled_categories(clause_labels).items():
        if category not in applicable:
            continue
        field = CUAD_CATEGORIES[category]["field"]
        if field is None:
            continue
        aggregated[field].extend(answers)

    expected: dict = {}
    for field, answers in aggregated.items():
        if not answers:
            continue
        if field in _LIST_FIELDS:
            expected[field] = answers
        else:
            expected[field] = answers[0]
    return expected


def build_presence_expectations(clause_labels: list[dict] | None,
                                doc_category: str | None = None) -> dict:
    """Per-category YES/NO presence expectations for the document.

    Per the CUAD dataset card, 32 of the 41 categories expect a Yes/No
    answer: labeled clause text found -> "Yes" (expected True, with the
    clause text the extraction must cover); no text found -> "No"
    (expected False — satisfied unless the model fabricates the clause,
    which the factuality guard catches). Only categories applicable to the
    document's type are included.

    Returns ``{category: {"expected": bool, "answer": str, "field": str}}``.
    """
    applicable = applicable_categories(doc_category)
    labeled = _labeled_categories(clause_labels)
    expectations: dict[str, dict] = {}
    for category in sorted(applicable):
        spec = CUAD_CATEGORIES[category]
        if spec["answer_format"] != ANSWER_YES_NO:
            continue
        answers = labeled.get(category) or []
        expectations[category] = {
            "expected": bool(answers),
            "answer": answers[0] if answers else "",
            "field": spec["field"] or "key_obligations",
        }
    return expectations


def mapped_categories() -> dict[str, str]:
    """Return the category->field mapping (exposed for reports/tests)."""
    return dict(CUAD_CATEGORY_TO_FIELD)
