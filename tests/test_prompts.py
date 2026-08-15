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


def test_sorter_v7_data_backed_rules():
    from src.prompts import SORTER_PROMPT_V6, SORTER_PROMPT_V7

    # v7 is a strict derivation of v6: the base is untouched, the derived
    # prompt adds the three rules for the v6 509-doc confusion clusters.
    assert SORTER_PROMPT_V7 != SORTER_PROMPT_V6
    assert SORTER_PROMPT_V7.startswith(SORTER_PROMPT_V6[:300])
    assert "sorter_v7" in PROMPT_VERSIONS

    v7 = SORTER_PROMPT_V7
    assert "18. CONSORTIUM O&M IS MAINTENANCE" in v7
    assert "submarine-cable consortium" in v7
    assert "19. DEVELOPMENT OVER LICENSE" in v7
    assert "delivery mechanism for developed products" in v7
    assert "20. PROMOTION GUARD" in v7
    assert "not marketing and not distributor" in v7
    # The option list is intact and the rule set ends before it.
    assert "VALID CONTRACT SUBTYPE KEYS" in v7
    # v6 predates the three rules.
    assert "CONSORTIUM O&M IS MAINTENANCE" not in SORTER_PROMPT_V6
    assert "PROMOTION GUARD" not in SORTER_PROMPT_V6


def test_sorter_v8_remaining_clusters():
    from src.prompts import SORTER_PROMPT_V7, SORTER_PROMPT_V8

    # v8 is a strict derivation of v7: the base is untouched, the derived
    # prompt adds the two rules for the v7 243-doc residual clusters.
    assert SORTER_PROMPT_V8 != SORTER_PROMPT_V7
    assert SORTER_PROMPT_V8.startswith(SORTER_PROMPT_V7[:300])
    assert "sorter_v8" in PROMPT_VERSIONS

    v8 = SORTER_PROMPT_V8
    assert "21. DEVELOPMENT VERSUS COLLABORATION, LICENSE, AND FRANCHISE STRUCTURES" in v8
    assert "Collaborative Development and Commercialization Agreement" in v8
    assert "Franchise Development Agreement" in v8
    assert "22. INTELLECTUAL PROPERTY AGREEMENTS ARE ip" in v8
    assert "not route them to license or to joint_venture" in v8
    assert "VALID CONTRACT SUBTYPE KEYS" in v8
    # v7 predates the two rules.
    assert "21. DEVELOPMENT VERSUS COLLABORATION" not in SORTER_PROMPT_V7
    assert "INTELLECTUAL PROPERTY AGREEMENTS ARE ip" not in SORTER_PROMPT_V7


def test_sorter_v9_title_wins_rules():
    from src.prompts import SORTER_PROMPT_V8, SORTER_PROMPT_V9

    # v9 is a strict derivation of v8: the base is untouched, the derived
    # prompt adds the three title-vs-machinery rules for the v8 residuals.
    assert SORTER_PROMPT_V9 != SORTER_PROMPT_V8
    assert SORTER_PROMPT_V9.startswith(SORTER_PROMPT_V8[:300])
    assert "sorter_v9" in PROMPT_VERSIONS

    v9 = SORTER_PROMPT_V9
    assert "23. PROMOTION TITLE WINS" in v9
    assert "COLOGUARD PROMOTION AGREEMENT" in v9
    assert "24. OUTSOURCING TITLE WINS" in v9
    assert "MANUFACTURING OUTSOURCING AGREEMENT" in v9
    assert "25. CUSTOMIZATION SCHEDULES ARE MAINTENANCE" in v9
    assert "Customization Schedule" in v9
    assert "VALID CONTRACT SUBTYPE KEYS" in v9
    # v8 predates the three rules.
    assert "23. PROMOTION TITLE WINS" not in SORTER_PROMPT_V8
    assert "OUTSOURCING TITLE WINS" not in SORTER_PROMPT_V8
    assert "CUSTOMIZATION SCHEDULES ARE MAINTENANCE" not in SORTER_PROMPT_V8


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


def test_contracts_v19_worked_examples_and_span_discipline():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V18,
        CONTRACTS_SPECIALIST_PROMPT_V19,
    )

    # v19 is a strict derivation of v18: the base is untouched, the derived
    # prompt adds the worked span examples (license-grant shapes drawn from
    # the residual misses) and the one-item-per-requirement span discipline.
    assert CONTRACTS_SPECIALIST_PROMPT_V19 != CONTRACTS_SPECIALIST_PROMPT_V18
    assert CONTRACTS_SPECIALIST_PROMPT_V19.startswith(CONTRACTS_SPECIALIST_PROMPT_V18[:300])
    assert "contracts_specialist_v19" in PROMPT_VERSIONS

    v19 = CONTRACTS_SPECIALIST_PROMPT_V19
    # Worked span examples: positive license shapes + verified negatives.
    assert "WORKED SPAN EXAMPLES" in v19
    assert "grants and assigns by means of present assignment" in v19
    assert "restrictions ON the licensed rights are License Grant items" in v19
    assert "options to license or acquire rights ARE items" in v19
    assert "NEGATIVE examples" in v19
    assert "trademark-hygiene" in v19
    assert "one operative requirement, one item" in v19
    # Span discipline: dedupe duty against repeats and sentence/fragment pairs.
    assert "SPAN DISCIPLINE" in v19
    assert "never emit a clause" in v19
    assert "drop the redundant copies" in v19
    # The v18 catalog and exclusion guard are intact.
    assert "mirroring the CUAD clause categories 1:1" in v19
    assert "never excluded because of WHERE it sits" in v19
    # v18 predates the worked examples.
    v18 = CONTRACTS_SPECIALIST_PROMPT_V18
    assert "WORKED SPAN EXAMPLES" not in v18
    assert "SPAN DISCIPLINE" not in v18


def test_contracts_v20_non_obligation_field_fidelity():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V19,
        CONTRACTS_SPECIALIST_PROMPT_V20,
    )

    # v20 is a strict derivation of v19: the base is untouched, the derived
    # prompt adds the four non-obligation field rules from the v19 per-field
    # failure audit (renewal_terms, term_length, governing_law,
    # termination_clauses).
    assert CONTRACTS_SPECIALIST_PROMPT_V20 != CONTRACTS_SPECIALIST_PROMPT_V19
    assert CONTRACTS_SPECIALIST_PROMPT_V20.startswith(CONTRACTS_SPECIALIST_PROMPT_V19[:300])
    assert "contracts_specialist_v20" in PROMPT_VERSIONS

    v20 = CONTRACTS_SPECIALIST_PROMPT_V20
    # renewal_terms: evergreen clauses + deal-terms tables.
    assert "EVERGREEN CLAUSES" in v20
    assert "shall continue in full force and effect thereafter" in v20
    assert "DEAL-TERMS TABLES" in v20
    # term_length: defined-Term sentences carve out of the existing
    # no-definitions rule.
    assert "DEFINED-TERM SENTENCES" in v20
    assert "DEFINES THE TERM ITSELF" in v20
    assert "do NOT answer with the definition of a defined term" in v20
    # governing_law: regulatory-jurisdiction sentences included.
    assert "regulatory-jurisdiction" in v20
    assert "Canadian Radio-television and Telecommunications" in v20
    # termination_clauses: redacted sections still count via heading+marker.
    assert "REDACTED SECTIONS" in v20
    assert "Termination for\n     Convenience. [***]." in v20 or "Termination for Convenience. [***]." in v20
    # v19's worked examples and span discipline are intact.
    assert "WORKED SPAN EXAMPLES" in v20
    assert "SPAN DISCIPLINE" in v20
    # v19 predates the field rules.
    v19 = CONTRACTS_SPECIALIST_PROMPT_V19
    assert "EVERGREEN CLAUSES" not in v19
    assert "DEFINED-TERM SENTENCES" not in v19
    assert "REDACTED SECTIONS" not in v19


def test_contracts_v21_merge_arm():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V20,
        CONTRACTS_SPECIALIST_PROMPT_V21,
    )

    # v21 is the v20 prompt TEXT at reasoning_effort=none (the merge arm:
    # v19's ko content + v20's four field rules, with the max-reasoning
    # parse-error risk retired). The prompt is identical to v20; the
    # version key + reasoning param are the experiment identity.
    assert CONTRACTS_SPECIALIST_PROMPT_V21 == CONTRACTS_SPECIALIST_PROMPT_V20
    assert "contracts_specialist_v21" in PROMPT_VERSIONS
    v21 = CONTRACTS_SPECIALIST_PROMPT_V21
    assert "WORKED SPAN EXAMPLES" in v21
    assert "SPAN DISCIPLINE" in v21
    assert "EVERGREEN CLAUSES" in v21
    assert "DEFINED-TERM SENTENCES" in v21
    assert "REDACTED SECTIONS" in v21


def test_contracts_v22_ko_recovery_rules():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V21,
        CONTRACTS_SPECIALIST_PROMPT_V22,
    )

    # v22 is a strict derivation of v21: the base is untouched, the derived
    # prompt fixes the ko regression (ellipsis abbreviation + over-dedupe).
    assert CONTRACTS_SPECIALIST_PROMPT_V22 != CONTRACTS_SPECIALIST_PROMPT_V21
    assert CONTRACTS_SPECIALIST_PROMPT_V22.startswith(CONTRACTS_SPECIALIST_PROMPT_V21[:300])
    assert "contracts_specialist_v22" in PROMPT_VERSIONS

    v22 = CONTRACTS_SPECIALIST_PROMPT_V22
    # Verbatim completeness: no ellipsis abbreviation, no truncated quotes.
    assert "VERBATIM COMPLETENESS" in v22
    assert "NEVER abbreviate with ellipses" in v22
    assert "never truncate a quote" in v22
    # Dedupe narrowed: overlapping wording is NOT duplication.
    assert "overlapping wording is NOT duplication" in v22
    assert "drop only exact repeats and sentence/fragment" in v22
    assert "never a distinct requirement whose wording" in v22
    # All prior content intact.
    assert "WORKED SPAN EXAMPLES" in v22
    assert "EVERGREEN CLAUSES" in v22
    assert "DEFINED-TERM SENTENCES" in v22
    # v21 predates the ko-recovery rules.
    v21 = CONTRACTS_SPECIALIST_PROMPT_V21
    assert "VERBATIM COMPLETENESS" not in v21
    assert "overlapping wording is NOT duplication" not in v21


def test_contracts_v23_residual_34_examples():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V22,
        CONTRACTS_SPECIALIST_PROMPT_V23,
    )

    # v23 is a strict derivation of v22: the base is untouched, the derived
    # prompt adds the second worked-example set built from the 34 residual
    # spans (v18-matched, v22-missed) and sharpens the trademark negative.
    assert CONTRACTS_SPECIALIST_PROMPT_V23 != CONTRACTS_SPECIALIST_PROMPT_V22
    assert CONTRACTS_SPECIALIST_PROMPT_V23.startswith(CONTRACTS_SPECIALIST_PROMPT_V22[:300])
    assert "contracts_specialist_v23" in PROMPT_VERSIONS

    v23 = CONTRACTS_SPECIALIST_PROMPT_V23
    # Recurring missed shapes from the residual 34.
    assert "audited-financial-statement delivery IS an Audit Rights item" in v23
    assert "Fox will remit all VGSL Revenue to Licensee" in v23
    assert "all-requirements supply" in v23
    assert "joint trademark registration" in v23
    assert "sell-off revenues subject to royalties" in v23
    assert "at cost without markup" in v23
    # The trademark negative is sharpened, not removed.
    assert "mark-HYGIENE duties" in v23
    assert "mark-OWNERSHIP-USE restrictions" in v23
    assert "mark non-tarnishment" in v23
    assert "NEGATIVE examples" in v23
    # All prior content intact.
    assert "VERBATIM COMPLETENESS" in v23
    assert "WORKED SPAN EXAMPLES" in v23
    assert "EVERGREEN CLAUSES" in v23
    # v22 predates the v2 examples.
    v22 = CONTRACTS_SPECIALIST_PROMPT_V22
    assert "audited-financial-statement delivery" not in v22
    assert "mark-HYGIENE duties" not in v22


def test_contracts_v24_reasoning_and_format_discipline():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V23,
        CONTRACTS_SPECIALIST_PROMPT_V24,
    )

    # v24 is a strict derivation of v23: the base is untouched, the derived
    # prompt adds the reasoning-before-output duty and the metrics-aligned
    # format discipline (canonical parseable forms for the regression
    # diagnostics; format-level only — the master labels CSV never reaches
    # the model).
    assert CONTRACTS_SPECIALIST_PROMPT_V24 != CONTRACTS_SPECIALIST_PROMPT_V23
    assert CONTRACTS_SPECIALIST_PROMPT_V24.startswith(CONTRACTS_SPECIALIST_PROMPT_V23[:300])
    assert "contracts_specialist_v24" in PROMPT_VERSIONS

    v24 = CONTRACTS_SPECIALIST_PROMPT_V24
    # Reasoning duty: reason through each field's evidence BEFORE finalizing,
    # emit summary + per-field entries, produced first, never scored.
    assert "REASONING BEFORE OUTPUT" in v24
    assert "`reasoning` field of the JSON" in v24
    assert "`section_ref`" in v24
    assert "it is never part of the clause text, is never scored" in v24
    assert "reasoning: object" in v24
    # Metrics-aligned format discipline (canonical parseable forms).
    assert "canonical duration phrase" in v24
    assert "two (2) years" in v24
    assert "PLAIN currency phrase" in v24
    assert "regression error" in v24
    # No leakage: the prompt never names the master-labels source.
    assert "master" not in v24.lower()
    # Commentary ban now scoped to outside the reasoning field.
    assert "never emit commentary outside the `reasoning` field" in v24
    # Rule numbering stays sequential after the insert (4 reasoning,
    # 5 format, 9 truncation) and ALL prior content is intact.
    assert "4. REASONING BEFORE OUTPUT" in v24
    assert "5. FORMAT DISCIPLINE" in v24
    assert "9. TRUNCATION-AWARE COMPLETENESS" in v24
    assert "VERBATIM COMPLETENESS" in v24
    assert "NEGATIVE examples" in v24
    # v23 predates the reasoning duty and format rules.
    v23 = CONTRACTS_SPECIALIST_PROMPT_V23
    assert "REASONING BEFORE OUTPUT" not in v23
    assert "canonical duration phrase" not in v23
    assert "never emit commentary outside" not in v23


def test_contracts_v25_additive_term_length_prefix():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V24,
        CONTRACTS_SPECIALIST_PROMPT_V25,
    )

    # v25 is a strict derivation of v24 fixing the containment regression
    # flagged on KANBAN-016: the canonical duration phrase is an ADDITIVE
    # prefix — the full verbatim clause (opener first) must follow; the
    # model must never start the quote at the duration phrase (the CUAD
    # ground-truth span is often the clause's OPENING fragment).
    assert CONTRACTS_SPECIALIST_PROMPT_V25 != CONTRACTS_SPECIALIST_PROMPT_V24
    assert CONTRACTS_SPECIALIST_PROMPT_V25.startswith(CONTRACTS_SPECIALIST_PROMPT_V24[:300])
    assert "contracts_specialist_v25" in PROMPT_VERSIONS

    v25 = CONTRACTS_SPECIALIST_PROMPT_V25
    assert "ADDITIVE and NEVER replaces the clause's own" in v25
    assert "NEVER start the quote at the duration phrase" in v25
    assert "NEVER drop, reorder, or abridge the clause opener" in v25
    assert "often the clause's OPENING fragment" in v25
    assert "EXAMPLE — for a clause reading" in v25
    # The rest of the v24 content is intact (reasoning duty, formats).
    assert "REASONING BEFORE OUTPUT" in v25
    assert "PLAIN currency phrase" in v25
    # v24 predates the additive-prefix clarification.
    v24 = CONTRACTS_SPECIALIST_PROMPT_V24
    assert "ADDITIVE and NEVER replaces" not in v24
    assert "clause opener" not in v24


def test_contracts_v26_no_template_leakage():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V25,
        CONTRACTS_SPECIALIST_PROMPT_V26,
    )

    # v26 kills the v25 worked-example TEMPLATE LEAKAGE: the verbatim example
    # clause made the model copy its sentence structure into documents with
    # DIFFERENT openers (Ritter "The initial term...", Phasebio "The term of
    # this Agreement (the "Term")..."). v26 shows openers as short variants
    # the model must match to THIS document's wording, and forbids reusing
    # the instructions' wording.
    assert CONTRACTS_SPECIALIST_PROMPT_V26 != CONTRACTS_SPECIALIST_PROMPT_V25
    assert CONTRACTS_SPECIALIST_PROMPT_V26.startswith(CONTRACTS_SPECIALIST_PROMPT_V25[:300])
    assert "contracts_specialist_v26" in PROMPT_VERSIONS

    v26 = CONTRACTS_SPECIALIST_PROMPT_V26
    assert "ADDITIVE and NEVER replaces the clause's own" in v26
    assert "NEVER start the quote at the duration phrase" in v26
    assert "says in THIS document" in v26
    assert "The initial term of this Agreement shall commence..." in v26
    assert 'The term of this Agreement (the "Term") will' in v26
    assert "never reuse wording from these instructions" in v26
    # The full verbatim worked example is GONE — that was the leakage vector.
    assert "EXAMPLE — for a clause reading" not in v26
    assert "shall remain effective for two (2) years from and after the" not in v26
    v25 = CONTRACTS_SPECIALIST_PROMPT_V25
    assert "EXAMPLE — for a clause reading" in v25
    assert "never reuse wording from these instructions" not in v25


def test_contracts_v27_multi_item_family_sections():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V26,
        CONTRACTS_SPECIALIST_PROMPT_V27,
    )

    # v27 = v26 + ONE rule (KANBAN-004): family SECTIONS are multi-item. The
    # v22/v23 50-doc runs + the v23-v26 sample5 series all show the same
    # key_obligations cluster — the model quotes ONE sentence per family
    # section while the GT holds 3-10 DISTINCT requirement sentences from it
    # (sim-matrix classification: ~60-70% of misses are NEAR, sim 0.35-0.59,
    # e.g. Ritter emitted insurance-procurement but not primary-of-all-
    # purposes/additional-insured; ~0 of the audit section's 10 GT spans).
    assert CONTRACTS_SPECIALIST_PROMPT_V27 != CONTRACTS_SPECIALIST_PROMPT_V26
    assert CONTRACTS_SPECIALIST_PROMPT_V27.startswith(
        CONTRACTS_SPECIALIST_PROMPT_V26[:300]
    )
    assert "contracts_specialist_v27" in PROMPT_VERSIONS

    v27 = CONTRACTS_SPECIALIST_PROMPT_V27
    # The multi-item family-section rule is present and explicit.
    assert "A FAMILY SECTION IS MULTI-ITEM" in v27
    assert "EACH distinct requirement sentence is its OWN item" in v27
    assert "3-10 spans from ONE insurance, audit/records, license" in v27
    assert "primary-of-all-purposes sentence" in v27
    assert "NEVER collapse a section into its first or most prominent sentence" in v27
    assert "INCOMPLETE — go back and emit the remaining requirement sentences" in v27
    # The rule sits inside the EXHAUSTIVENESS paragraph of the v10 family
    # catalog, so the family scope is untouched (only listed families count).
    assert "EXHAUSTIVENESS WITHIN THE FAMILIES" in v27
    assert "belonging to a listed family" in v27
    # Unchanged v26 discipline: term_length opener variants + no leakage,
    # reasoning trace, formats.
    assert "never reuse wording from these instructions" in v27
    assert "says in THIS document" in v27
    assert "REASONING BEFORE OUTPUT" in v27
    assert "PLAIN currency phrase" in v27
    # v26 predates the rule.
    v26 = CONTRACTS_SPECIALIST_PROMPT_V26
    assert "A FAMILY SECTION IS MULTI-ITEM" not in v26


def test_contracts_v28_multi_item_sharpened():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V27,
        CONTRACTS_SPECIALIST_PROMPT_V28,
    )

    # v28 = v27 + two trace lessons from the v27 A/B (chunked pair: v27
    # 0.9535 vs v26 0.8944; residuals were Ritter -1 span and a Cardax
    # precision drop from definitional-fragment items): (1) only OPERATIVE
    # requirement sentences are items — definitional sentences ("any X
    # Property or improvements thereto which are used...") never are;
    # (2) the completion re-scan only ADDS items, never removes/replaces.
    assert CONTRACTS_SPECIALIST_PROMPT_V28 != CONTRACTS_SPECIALIST_PROMPT_V27
    assert CONTRACTS_SPECIALIST_PROMPT_V28.startswith(
        CONTRACTS_SPECIALIST_PROMPT_V27[:300]
    )
    assert "contracts_specialist_v28" in PROMPT_VERSIONS

    v28 = CONTRACTS_SPECIALIST_PROMPT_V28
    assert "A FAMILY SECTION IS MULTI-ITEM" in v28
    assert "EACH distinct requirement sentence is its OWN item" in v28
    assert "NEVER collapse a section into its first or most prominent sentence" in v28
    # The sharpening: operative-vs-definitional criterion + additive re-scan.
    assert "A requirement sentence is OPERATIVE language" in v28
    assert "A DEFINITIONAL or descriptive" in v28
    assert "NEVER an item" in v28
    assert "RE-SCAN every family-" in v28
    assert "the re-scan only ADDS items" in v28
    assert "never removes or replaces one" in v28
    # v27 predates the sharpening; v26 predates the whole rule.
    v27 = CONTRACTS_SPECIALIST_PROMPT_V27
    assert "NEVER an item" not in v27
    assert "the re-scan only ADDS items" not in v27
    # Unchanged discipline: family scope, term_length, reasoning, formats.
    assert "belonging to a listed family" in v28
    assert "never reuse wording from these instructions" in v28
    assert "REASONING BEFORE OUTPUT" in v28
    assert "PLAIN currency phrase" in v28


def test_contracts_v29_coc_definition_carveout():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V28,
        CONTRACTS_SPECIALIST_PROMPT_V29,
    )

    # v29 = v28 + ONE refinement: per-span diff on the 4 regressed 50-doc docs
    # found a rule-driven regression — v28's "X means ... is NEVER an item"
    # suppressed the Change-of-Control DEFINITION spans on Ediets (1.00 ->
    # 0.45/0.40), but the CoC family's clause text IS its definition (corpus:
    # 3 of 121 CoC docs are definitional). The carve-out restores family
    # definitions as items while keeping section-glossary fragments excluded.
    assert CONTRACTS_SPECIALIST_PROMPT_V29 != CONTRACTS_SPECIALIST_PROMPT_V28
    assert CONTRACTS_SPECIALIST_PROMPT_V29.startswith(
        CONTRACTS_SPECIALIST_PROMPT_V28[:300]
    )
    assert "contracts_specialist_v29" in PROMPT_VERSIONS

    v29 = CONTRACTS_SPECIALIST_PROMPT_V29
    assert "A DEFINITIONAL sentence is an" in v29
    assert "item ONLY when the definition itself is the family clause" in v29
    assert 'the Change of' in v29 and 'Control' in v29
    assert "such definitions ARE items" in v29
    # Glossary fragments remain excluded.
    assert "Definitional fragments that describe a" in v29
    assert "defined term's COMPONENTS" in v29
    assert "are NEVER items" in v29
    # The broad v28 phrasing is gone; v28 predates the carve-out.
    v28 = CONTRACTS_SPECIALIST_PROMPT_V28
    assert "A DEFINITIONAL or descriptive" in v28
    assert "A DEFINITIONAL sentence is an" not in v28
    assert "item ONLY when the definition itself is the family clause" not in v28


def test_contracts_v30_chunk_mode_scalar_quoting():
    from src.prompts import (
        CONTRACTS_SPECIALIST_PROMPT_V29,
        CONTRACTS_SPECIALIST_PROMPT_V30,
    )

    # v30 = v29 + ONE rule closing the chunked-mode x term_length gap: chunked
    # v26 collapsed term_length on all three term docs (Ritter prefix-only
    # "five (5) years" 1.0->0.1765; Phasebio null 1.0->0.0; Ediets opener
    # dropped 1.0->0.3333) because CHUNK DUTY's "quote the VISIBLE operative
    # language faithfully and stop at what you can see" licensed the
    # relaxation. v30: scalar fields keep their exact quoting rules in every
    # chunk; prefix-only or null term_length with the clause visible is a miss.
    assert CONTRACTS_SPECIALIST_PROMPT_V30 != CONTRACTS_SPECIALIST_PROMPT_V29
    assert CONTRACTS_SPECIALIST_PROMPT_V30.startswith(
        CONTRACTS_SPECIALIST_PROMPT_V29[:300]
    )
    assert "contracts_specialist_v30" in PROMPT_VERSIONS

    v30 = CONTRACTS_SPECIALIST_PROMPT_V30
    assert "SCALAR fields keep" in v30
    assert "their exact field rules IN EVERY CHUNK" in v30
    assert "the FULL verbatim clause, opener first" in v30
    assert "prefix-" in v30 and "never acceptable" in v30
    assert "a null" in v30 and "is a MISS" in v30
    assert "visible portion including its opener" in v30
    # Chunk duty + term_length discipline both intact; v29 predates the rule.
    assert "CHUNK DUTY" in v30
    assert "canonical duration phrase" in v30
    v29 = CONTRACTS_SPECIALIST_PROMPT_V29
    assert "SCALAR fields keep" not in v29
