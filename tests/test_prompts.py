"""Tests for the versioned prompt registry."""

import pytest

from src.prompts import (
    DEFAULT_PROMPT_VERSION,
    PROMPT_TEMPLATES,
    PROMPT_VERSIONS,
    get_prompt,
    list_prompts,
)


def test_all_prompt_keys_exist():
    assert "sorter" in PROMPT_VERSIONS
    assert "sorter_v0" in PROMPT_VERSIONS
    assert "sorter_v1" in PROMPT_VERSIONS
    assert "sorter_v2" in PROMPT_VERSIONS
    assert "contracts_specialist" in PROMPT_VERSIONS
    assert "contracts_specialist_v1" in PROMPT_VERSIONS
    assert "contracts_specialist_v2" in PROMPT_VERSIONS
    assert "contracts_specialist_v3" in PROMPT_VERSIONS
    assert "contracts_specialist_v4" in PROMPT_VERSIONS
    assert "contracts_specialist_v5" in PROMPT_VERSIONS
    assert "corporate_records_specialist" in PROMPT_VERSIONS
    assert "due_diligence_specialist" in PROMPT_VERSIONS
    assert "correspondence_specialist" in PROMPT_VERSIONS
    assert "compliance_specialist" in PROMPT_VERSIONS
    assert "court_opinions_specialist" in PROMPT_VERSIONS
    assert "judge" in PROMPT_VERSIONS
    assert "judge-classification" in PROMPT_VERSIONS
    assert "judge-correctness" in PROMPT_VERSIONS
    assert "boss" in PROMPT_VERSIONS
    assert "reporter" in PROMPT_VERSIONS


def test_sorter_v2_hybrid_and_endorsement_rules():
    prompt = get_prompt("sorter_v2")
    assert "HYBRID AGREEMENTS" in prompt
    assert "SUBTYPE CONFIDENCE" in prompt
    # The endorsement description (injected via {{contract_subtypes}}) is
    # broadened beyond celebrity deals to include product/insurance riders.
    from agents.sorter_agent import SorterAgent

    rendered = SorterAgent(prompt_version="sorter_v2").system_prompt()
    assert "endorsement riders" in rendered
    assert "{{contract_subtypes}}" in prompt


def test_extractor_v5_truncation_and_full_clause_rules():
    prompt = get_prompt("contracts_specialist_v5")
    assert "TRUNCATION-AWARE COMPLETENESS" in prompt
    assert "ninety (90) days" in prompt  # full termination clause incl. riders
    assert "Governing Law" in prompt
    # v5 keeps v4's Yes/No category enumeration.
    assert "anti-assignment" in prompt
    assert "third-party beneficiary" in prompt


def test_contracts_v2_is_completeness_first():
    prompt = get_prompt("contracts_specialist_v2")
    assert "COMPLETENESS IS THE PRIORITY" in prompt
    assert "one item per distinct obligation" in prompt.lower()
    assert "operative language" in prompt.lower()
    assert "confidence" in prompt


def test_sorter_prompt_mentions_classes():
    prompt = get_prompt("sorter")
    for cls in ("contract", "corporate_record", "due_diligence", "court_opinion"):
        assert cls in prompt


def test_get_prompt_unknown_raises():
    with pytest.raises(KeyError):
        get_prompt("does_not_exist")


def test_list_prompts_sorted():
    versions = list_prompts()
    assert versions == sorted(versions)
    assert "sorter" in versions


def test_prompt_templates_matches_registry():
    assert PROMPT_TEMPLATES() == PROMPT_VERSIONS


def test_default_prompt_version_is_sorter():
    assert DEFAULT_PROMPT_VERSION == "sorter"


def test_judge_prompts_are_distinct():
    judge = get_prompt("judge")
    cls = get_prompt("judge-classification")
    corr = get_prompt("judge-correctness")
    assert judge != cls != corr


def test_contracts_v12_field_accuracy_and_rescan_rules():
    from src.prompts import CONTRACTS_SPECIALIST_PROMPT_V11, CONTRACTS_SPECIALIST_PROMPT_V12

    # v12 is a strict derivation of v11: the base is untouched, the derived
    # prompt adds the field-accuracy and re-scan duties.
    assert CONTRACTS_SPECIALIST_PROMPT_V12 != CONTRACTS_SPECIALIST_PROMPT_V11
    assert CONTRACTS_SPECIALIST_PROMPT_V12.startswith(CONTRACTS_SPECIALIST_PROMPT_V11[:300])
    assert "contracts_specialist_v12" in PROMPT_VERSIONS

    v12 = CONTRACTS_SPECIALIST_PROMPT_V12
    # Effective-date rule: defined-term preference, full date phrase.
    assert 'DEFINES an "Effective Date"' in v12
    assert "the defined term wins" in v12
    # Governing-law verbatim-in-full duty (containment fix).
    assert "VERBATIM and IN FULL" in v12
    assert "conflict-of-laws qualifier" in v12
    # Re-scan duty names the families the 5-doc sample missed.
    assert "RE-SCAN DUTY" in v12
    for family in ("volume restrictions", "caps on liability", "uncapped liability",
                   "audit rights", "third-party beneficiary", "change of control",
                   "anti-assignment"):
        assert family in v12, f"v12 missing re-scan family {family}"
    # Truncation honesty: never fabricate for the omitted middle.
    assert "never fabricate a clause for it" in v12
    # v11 predates the new rules.
    v11 = CONTRACTS_SPECIALIST_PROMPT_V11
    assert "RE-SCAN DUTY" not in v11
    assert "VERBATIM and IN FULL" not in v11


def test_contracts_v18_family_fidelity_catalog():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V17,
        CONTRACTS_SPECIALIST_PROMPT_V18,
    )

    # v18 is a strict derivation of v17: the base is untouched, the derived
    # prompt replaces the terse family list with the shape-level catalog and
    # narrows the exclusion rule. The v17 grain (length-anchored, 10-25
    # words) is kept unchanged.
    assert CONTRACTS_SPECIALIST_PROMPT_V18 != CONTRACTS_SPECIALIST_PROMPT_V17
    assert CONTRACTS_SPECIALIST_PROMPT_V18.startswith(CONTRACTS_SPECIALIST_PROMPT_V17[:300])
    assert "contracts_specialist_v18" in PROMPT_VERSIONS

    v18 = CONTRACTS_SPECIALIST_PROMPT_V18
    # The 26-item CUAD-mirroring catalog with operative shapes is present.
    assert "mirroring the CUAD clause categories 1:1" in v18
    for family in ("Anti-Assignment", "Change Of Control", "Exclusivity", "Non-Compete",
                   "No-Solicit Of Customers", "No-Solicit Of Employees",
                   "Non-Disparagement", "Most-Favored-Nation", "ROFR/ROFO/ROFN",
                   "Revenue/Profit Sharing", "Price Restrictions", "Minimum Commitment",
                   "Volume Restriction", "IP Ownership Assignment",
                   "Joint IP Ownership", "License Grant", "Source Code Escrow",
                   "Post-Termination Services", "Audit Rights", "Uncapped Liability",
                   "Cap On Liability", "Liquidated Damages", "Insurance",
                   "Covenant Not To Sue", "Third Party Beneficiary"):
        assert f"{family}:" in v18, f"v18 missing catalog entry {family}"
    # Data-backed shapes for the families the 50-doc decomposition missed.
    assert "in no event shall either party be liable" in v18
    assert "elects not to prosecute or maintain" in v18
    assert "Change in Control" in v18
    # Family-term definitions are items even though general definitions are not.
    assert "definitions ARE the category's" in v18
    assert "operative text, even though general definitions are not items" in v18
    # Exclusion rule narrowed: family clauses inside indemnity/damages sections count.
    assert "never excluded because of WHERE it sits" in v18
    assert "pure indemnification obligations" in v18
    # The v17 length-anchored grain is intact.
    assert "typically 10-25 words" in v18
    # v17 predates the catalog.
    v17 = CONTRACTS_SPECIALIST_PROMPT_V17
    assert "mirroring the CUAD clause categories 1:1" not in v17
