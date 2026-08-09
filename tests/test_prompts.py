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
    assert "contracts_specialist" in PROMPT_VERSIONS
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
