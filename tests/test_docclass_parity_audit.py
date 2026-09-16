"""KANBAN-101 — machine-checkable docclass parity audit (Phase 1 acceptance).

Guards cross-repo prompt alignment, schema↔prompt option lists for champion
and pilot surfaces, and metric-name parity between the entity runner,
SCORING.md §7, and the score-emitter docclass helpers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.sorter_agent import (
    DOC_SUBCLASS_KEYS,
    DOCCLASS_SCHEMA,
    DOCCLASS_PILOT_SCHEMA,
    SorterAgent,
    DOCCLASS_CLASSES,
)
from src.prompts import get_prompt
from src.prompts_docclass import (
    DOCCLASS_PROMPT_VERSIONS,
    _DOCCONTEXT_V1,
    _PILOT_CONTEXT,
)
from src.score_emitter import DOCCLASS_DASHBOARD_METRICS, DOCCLASS_HEADLINE_METRICS


# Mailroom reference fragments (byte-compatible with entity _DOCCONTEXT_V1).
_MAILROOM_CORRESPONDENCE_LINE = "correspondence ->"
_MAILROOM_INSURANCE_LINE = "insurance_claim ->"


def test_doccontext_v1_includes_correspondence_and_insurance_subclasses():
    assert _MAILROOM_CORRESPONDENCE_LINE in _DOCCONTEXT_V1
    assert _MAILROOM_INSURANCE_LINE in _DOCCONTEXT_V1
    for key in ("demand", "attorney_demand", "carrier", "pde", "outpatient", "inpatient"):
        assert key in _DOCCONTEXT_V1


def test_pilot_context_is_strict_superset_of_extended_v1_context():
    for fragment in ("correspondence ->", "insurance_claim ->", "merger_agreement ->"):
        assert fragment in _PILOT_CONTEXT
    assert "pilot classification mode" in _PILOT_CONTEXT


def test_contracts_docclass_v1_carries_mailroom_cuad_maud_rules():
    prompt = DOCCLASS_PROMPT_VERSIONS["contracts_specialist_docclass_v1"]
    for fragment in (
        "CUAD families",
        "MAUD mergers",
        "cuad_clauses",
        "maud_clauses",
    ):
        assert fragment in prompt


def test_insurance_docclass_v1_carries_hub_and_evidence_rules():
    prompt = DOCCLASS_PROMPT_VERSIONS["insurance_claims_specialist_docclass_v1"]
    assert "pde" in prompt and "inpatient" in prompt
    assert "EVIDENCE-ONLY VISIBILITY" in prompt


def test_champion_and_pilot_prompts_list_all_schema_subclass_keys():
    enum = set(DOCCLASS_SCHEMA["properties"]["doc_subclass"]["enum"])
    pilot_enum = set(DOCCLASS_PILOT_SCHEMA["properties"]["doc_subclass"]["enum"])
    assert enum == set(DOC_SUBCLASS_KEYS)

    # HUB-041 lineage split: the mailroom-named v8 lineages teach the full
    # enum incl. the LOB tokens (property/auto); every docclass version
    # frozen BEFORE the v8 corpus (v7 champion, pilot v3) predates them,
    # is never mutated, and is expected to carry the pre-v8 key set only.
    lob_tokens = {"property", "auto"}
    pre_v8_keys = [k for k in DOC_SUBCLASS_KEYS if k not in lob_tokens]

    champion = SorterAgent(
        prompt_version="sorter_docclass_v7",
        doc_classes=DOCCLASS_CLASSES,
        schema=DOCCLASS_SCHEMA,
    ).system_prompt()
    for key in pre_v8_keys:
        assert key in champion, f"sorter_docclass_v7 missing {key!r}"

    pilot = get_prompt("sorter_docclass_pilot_v3")
    for key in (k for k in pilot_enum if k not in lob_tokens):
        assert key in pilot, f"sorter_docclass_pilot_v3 missing {key!r}"

    mailroom_champion = SorterAgent(
        prompt_version="sorter_mailroom_v0",
        doc_classes=DOCCLASS_CLASSES,
        schema=DOCCLASS_SCHEMA,
    ).system_prompt()
    for key in DOC_SUBCLASS_KEYS:
        assert key in mailroom_champion, f"sorter_mailroom_v0 missing {key!r}"

    mailroom_pilot = get_prompt("sorter_mailroom_pilot_v0")
    for key in pilot_enum:
        assert key in mailroom_pilot, f"sorter_mailroom_pilot_v0 missing {key!r}"

    # DMR-015 mailroom_prompts lineage (mailroom-corpus v8): every sorter
    # surface teaches the full six-token insurance subclass set.
    for key, full_enum in (
        ("sorter_mailroom_prompts_v0", enum),
        ("sorter_mailroom_prompts_vision_v0", enum),
        ("sorter_mailroom_prompts_pilot_v0", pilot_enum),
    ):
        p = get_prompt(key)
        for skey in full_enum:
            assert skey in p, f"{key} missing {skey!r}"


def test_mailroom_prompts_lineage_teaches_all_six_tokens():
    """DMR-015: every {agent}_mailroom_prompts_v0 variant (specialists,
    reviewer, arbiter, judges, boss) teaches the v8 six-token insurance
    subclass set — the renamed mailroom-corpus corpus."""
    six_tokens = {"carrier", "pde", "outpatient", "inpatient", "property", "auto"}
    keys = [
        "contracts_specialist_mailroom_prompts_v0",
        "corporate_records_specialist_mailroom_prompts_v0",
        "due_diligence_specialist_mailroom_prompts_v0",
        "correspondence_specialist_mailroom_prompts_v0",
        "compliance_specialist_mailroom_prompts_v0",
        "court_opinions_specialist_mailroom_prompts_v0",
        "insurance_claims_specialist_mailroom_prompts_v0",
        "reviewer_mailroom_prompts_v0",
        "arbiter_mailroom_prompts_v0",
        "judge_mailroom_prompts_v0",
        "judge_classification_mailroom_prompts_v0",
        "judge_correctness_mailroom_prompts_v0",
        "boss_mailroom_prompts_v0",
    ]
    for key in keys:
        p = get_prompt(key)
        for token in six_tokens:
            assert token in p, f"{key} missing {token!r}"


def test_scoring_md_documents_docclass_metric_names():
    text = Path("docs/SCORING.md").read_text(encoding="utf-8")
    section = text.split("## 7. Docclass hierarchical metrics")[1].split("## 8.")[0]
    for name in DOCCLASS_HEADLINE_METRICS:
        assert name in section, f"SCORING.md §7 missing {name!r}"
    assert "3,302 rows" in section
    assert "8 primary classes" in section or "8-class" in section


def test_score_emitter_docclass_metric_names_match_runner():
    runner_src = Path("scripts/eval/run_langfuse_docclass_eval.py").read_text(encoding="utf-8")
    for name in DOCCLASS_HEADLINE_METRICS:
        assert f'"{name}"' in runner_src
    assert set(DOCCLASS_HEADLINE_METRICS).issubset(set(DOCCLASS_DASHBOARD_METRICS))


def test_classify_failure_none_subclass_is_not_subclass_miss():
    from src.dojo_compat import classify_failure

    assert classify_failure(True, None, None) is None


def test_pilot_schema_aligns_with_active_pilot_prompt_vocabulary():
    """hub#51: the pilot schema's doc_subclass enum must match what the ACTIVE
    pilot sorter prompt (the mailroom lineage) actually teaches. The frozen
    pre-v8 docclass pilot lineage (v0..v3) is expected to carry the pre-v8 key
    set only (pinned separately below) — the schema speaks for the live surface.
    """
    pilot_enum = set(DOCCLASS_PILOT_SCHEMA["properties"]["doc_subclass"]["enum"])
    assert pilot_enum == set(DOC_SUBCLASS_KEYS)

    # The ACTIVE pilot sorter (mailroom lineage, v8+ LOB) teaches every token
    # the pilot schema can emit.
    mailroom_pilot = get_prompt("sorter_mailroom_pilot_v0")
    for key in pilot_enum:
        assert key in mailroom_pilot, f"sorter_mailroom_pilot_v0 missing {key!r}"

    # The frozen docclass pilot lineage predates the LOB tokens: it must teach
    # the pre-v8 key set and NEVER claim property/auto (pinned, not mutated).
    frozen = get_prompt("sorter_docclass_pilot_v3")
    lob = {"property", "auto"}
    for key in pilot_enum - lob:
        assert key in frozen, f"sorter_docclass_pilot_v3 missing {key!r}"
    assert "property" not in frozen.split("INSURANCE CLAIM SUBCLASS")[1][:600]


def test_prompts_name_real_fallback_other_never_unknown():
    """hub#51: the doc_subclass fallback key is `other`; `unknown` is not a
    schema token and must never be taught as one. Every docclass prompt that
    instructs against the fallback must name `other`, and no registered prompt
    text may contain the phantom `unknown` token."""
    from src.prompts_docclass import DOCCLASS_PROMPT_VERSIONS

    fallback_key = "other"
    samples = ["sorter_docclass_v7", "sorter_docclass_pilot_v3",
               "judge_docclass_v1", "judge_classification_docclass_v1",
               "arbiter_docclass_v1", "boss_docclass_v1"]
    for name in samples:
        text = DOCCLASS_PROMPT_VERSIONS[name]
        # the fallback key is taught; the phantom `unknown` token either never
        # appears or appears ONLY as an explicit prohibition (never a valid
        # option the model is invited to emit)
        assert fallback_key in text, f"{name} must teach the `other` fallback"
        if "unknown" in text:
            assert "not a valid token" in text, f"{name} must name `unknown` only as a prohibition"
