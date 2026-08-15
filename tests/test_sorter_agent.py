"""Tests for the sorter agent's prompt resolution, subtype handling, and
parsing (LLM mocked)."""

import pytest
from langchain_core.messages import AIMessage

from agents.sorter_agent import (
    CONTRACT_SUBTYPES,
    CONTRACT_SUBTYPE_KEYS,
    DOC_CLASS_KEYS,
    SORTER_SCHEMA,
    SUBTYPE_UNKNOWN,
    SorterAgent,
    normalize_subtype,
    SUBTYPE_EQUIVALENCES,
    equivalent_subtypes,
)


class _FakeLLM:
    """Callable Runnable stand-in returning an AIMessage with usage."""

    def __init__(self, content, usage_metadata, cost=0.01):
        self._content = content
        self._usage = usage_metadata
        self._cost = cost

    def __call__(self, *args, **kwargs):
        return AIMessage(
            content=self._content,
            usage_metadata=self._usage,
            response_metadata={"cost": self._cost},
        )

    def bind(self, **kwargs):
        return self


def test_call_llm_captures_usage(mocker):
    """Plain-text completions (the LegalBench task-mode path) must carry
    token/cost accounting like the structured + vision paths."""
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "llm",
        return_value=_FakeLLM(
            content="Yes",
            usage_metadata={"input_tokens": 120, "output_tokens": 3, "total_tokens": 123},
            cost=0.0004,
        ),
    )
    text = sorter._call_llm("Q: is this hearsay?\nA:")
    assert text == "Yes"
    assert sorter._last_usage == {
        "prompt_tokens": 120,
        "completion_tokens": 3,
        "total_tokens": 123,
        "cost": 0.0004,
    }


def test_call_llm_non_string_content(mocker):
    """AIMessage content that is not a plain str still returns text."""
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "llm",
        return_value=_FakeLLM(
            content=[{"type": "text", "text": "No"}],
            usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        ),
    )
    assert sorter._call_llm("Q:\nA:") == "No"


def test_system_prompt_uses_version():
    sorter = SorterAgent(prompt_version="sorter_v0")
    prompt = sorter.system_prompt()
    assert "contract" in prompt
    assert "court_opinion" in prompt


def test_system_prompt_v1_includes_contract_subtypes():
    sorter = SorterAgent(prompt_version="sorter_v1")
    prompt = sorter.system_prompt()
    assert "license" in prompt
    assert "non_compete_no_solicit" in prompt
    assert "contract_subtype" in prompt


def test_schema_enum_matches_classes():
    enum = SORTER_SCHEMA["properties"]["doc_type"]["enum"]
    assert enum == DOC_CLASS_KEYS
    # The subgroup dimension: nullable enum of the 25 subtypes + "other".
    subtype = SORTER_SCHEMA["properties"]["contract_subtype"]
    assert subtype["type"] == ["string", "null"]
    assert len(subtype["enum"]) == len(CONTRACT_SUBTYPES) + 1
    assert SUBTYPE_UNKNOWN in subtype["enum"]


def test_classify_returns_parsed_result_with_subtype(mocker):
    sorter = SorterAgent(prompt_version="sorter_v1")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "contract_subtype": "license",
                      "confidence": 0.92, "reasoning": "it is an agreement"},
    )
    doc_type, contract_subtype, confidence, reasoning = sorter.classify("AGREEMENT text here")
    assert doc_type == "contract"
    assert contract_subtype == "license"
    assert confidence == 0.92
    assert "agreement" in reasoning


def test_classify_defaults_on_parse_error(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(sorter, "_call_structured", return_value={"_parse_error": True})
    doc_type, contract_subtype, confidence, reasoning = sorter.classify("text")
    assert doc_type == "correspondence"
    assert contract_subtype == SUBTYPE_UNKNOWN
    assert confidence == 0.3


def test_classify_rejects_unknown_class(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "banana", "confidence": "high", "reasoning": ""},
    )
    doc_type, contract_subtype, confidence, _ = sorter.classify("text")
    assert doc_type == "correspondence"
    assert contract_subtype == SUBTYPE_UNKNOWN
    assert confidence == 0.5


def test_classify_json_returns_dict(mocker):
    sorter = SorterAgent(prompt_version="sorter_v0")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "contract", "contract_subtype": "co_branding",
                      "confidence": 0.9, "reasoning": "r"},
    )
    result = sorter.classify_json("text")
    assert result["doc_type"] == "contract"
    assert result["contract_subtype"] == "co_branding"
    assert result["confidence"] == 0.9


def test_classify_subtype_null_for_non_contract(mocker):
    sorter = SorterAgent(prompt_version="sorter_v1")
    mocker.patch.object(
        sorter,
        "_call_structured",
        return_value={"doc_type": "correspondence", "contract_subtype": "license",
                      "confidence": 0.8, "reasoning": "a letter"},
    )
    result = sorter.classify_json("text")
    assert result["doc_type"] == "correspondence"
    assert result["contract_subtype"] == SUBTYPE_UNKNOWN  # subtype only for contracts


def test_normalize_subtype_aliases_and_labels():
    assert normalize_subtype("license") == "license"
    assert normalize_subtype("License_Agreements") == "license"
    assert normalize_subtype("License Agreement") == "license"
    assert normalize_subtype("Joint Venture _ Filing") == "joint_venture"
    assert normalize_subtype("Non_Compete_Non_Solicit") == "non_compete_no_solicit"
    assert normalize_subtype("Affiliate Agreement") == "affiliate"
    assert normalize_subtype("totally unknown") == SUBTYPE_UNKNOWN
    assert normalize_subtype(None) == SUBTYPE_UNKNOWN
    assert normalize_subtype("") == SUBTYPE_UNKNOWN


def test_equivalent_subtypes_family_classes():
    # Exact keys are trivially equivalent.
    assert equivalent_subtypes("license", "license")
    assert equivalent_subtypes("reseller", "reseller")
    # The defensible family pairs recovered from the subtype-eval failures.
    assert equivalent_subtypes("reseller", "distributor")
    assert equivalent_subtypes("distributor", "reseller")
    assert equivalent_subtypes("maintenance", "license")
    assert equivalent_subtypes("development", "license")
    assert equivalent_subtypes("affiliate", "joint_venture")
    # Distinct families are NOT equivalent.
    assert not equivalent_subtypes("license", "franchise")
    assert not equivalent_subtypes("development", "supply")
    assert not equivalent_subtypes("reseller", "marketing")
    assert not equivalent_subtypes("license", "other")
    # Every equivalence class is a pair of registered subtype keys.
    for cls in SUBTYPE_EQUIVALENCES:
        assert len(cls) == 2
        for key in cls:
            assert key in CONTRACT_SUBTYPE_KEYS


def test_truncate_input_budget():
    sorter = SorterAgent()
    sorter._max_input_chars = 50
    truncated = sorter.truncate_input("x" * 200)
    assert len(truncated) < 200
    assert "truncated" in truncated
    short = sorter.truncate_input("short")
    assert short == "short"


def test_truncate_input_head_tail_window():
    sorter = SorterAgent()
    sorter._max_input_chars = 100
    text = "HEAD" + "x" * 200 + "TAIL"
    truncated = sorter.truncate_input(text)
    assert sorter._last_truncated is True
    assert truncated.startswith("HEAD")  # opening portion kept
    assert truncated.rstrip().endswith("TAIL")  # closing portion kept
    assert "document truncated" in truncated
    pre = truncated[: truncated.find("[... document truncated")].strip("\n")
    post = truncated[truncated.rfind("...]\n\n") + 5:].strip("\n")
    assert len(pre) + len(post) == 100  # exactly the budget of content, marker excluded

    sorter2 = SorterAgent()
    sorter2._max_input_chars = 100
    assert sorter2.truncate_input("short") == "short"
    assert sorter2._last_truncated is False


def test_subtype_option_list_complete_and_precise():
    import re

    # The prompt's list of available guesses MUST match the schema enum EXACTLY
    # (all 25 families + "other") — a subtype the model can output must be
    # visible in the option list, and nothing in the option list may be
    # rejected by the schema. (sorter_v0 predates the subtype dimension and
    # has no subgroup section — it is exempt; v1-v3 predate the precision fix
    # and omit "other" from the list, which v4 repairs.)
    enum = set(SORTER_SCHEMA["properties"]["contract_subtype"]["enum"])
    for version in ("sorter_v1", "sorter_v2", "sorter_v3"):
        prompt = SorterAgent(prompt_version=version).system_prompt()
        section = prompt.split("Contract subgroups:")[-1]
        listed = set(re.findall(r"- (\w+):", section.split("Return a JSON object")[0]))
        assert listed == enum - {"other"}, \
            f"{version}: prompt options {listed} != schema enum minus 'other'"
    for version in ("sorter_v4", "sorter_v5", "sorter_v6"):
        prompt = SorterAgent(prompt_version=version).system_prompt()
        section = prompt.split("VALID CONTRACT SUBTYPE KEYS")[1]
        listed = set(re.findall(r"- (\w+):", section.split("Return a JSON object")[0]))
        assert listed == enum, f"{version}: prompt options {listed} != schema enum {enum}"
        assert "other" in listed, f"{version}: 'other' must be an explicit option"

    # Every CUAD corpus folder must normalize to a key that IS in the prompt
    # option list (the sorter can never be asked to guess a class it was not
    # given as an option).
    cuad_folders = [
        "Affiliate_Agreements", "Agency Agreements", "Co_Branding", "Collaboration",
        "Consulting Agreements", "Development", "Distributor", "Endorsement",
        "Endorsement Agreement", "Franchise", "Hosting", "IP", "Joint Venture",
        "Joint Venture _ Filing", "License_Agreements", "Maintenance", "Manufacturing",
        "Marketing", "Non_Compete_Non_Solicit", "Outsourcing", "Promotion", "Reseller",
        "Service", "Sponsorship", "Strategic Alliance", "Supply", "Transportation",
        "Affiliate Agreement",
    ]
    prompt = SorterAgent(prompt_version="sorter_v4").system_prompt()
    section = prompt.split("VALID CONTRACT SUBTYPE KEYS")[1].split("Return a JSON object")[0]
    options = set(re.findall(r"- (\w+):", section))
    for folder in cuad_folders:
        assert normalize_subtype(folder) in options, \
            f"folder {folder!r} -> {normalize_subtype(folder)!r} not in sorter options"


def test_sorter_v6_derived_and_rule_banners():
    """v6 is a STRICT derivation of v5 (base untouched) that adds the
    data-backed rules for the 509-contract full-CUAD run's miss clusters."""

    from src.prompts import SORTER_PROMPT_V5, SORTER_PROMPT_V6, get_prompt

    assert SORTER_PROMPT_V6 != SORTER_PROMPT_V5
    # v5 is never mutated: v6 shares v5's exact opening, keeps every rule the
    # derivation did NOT touch, and only rewrites the two targeted spans.
    assert SORTER_PROMPT_V6.startswith(SORTER_PROMPT_V5[:200])
    assert "VALID CONTRACT SUBTYPE KEYS" in SORTER_PROMPT_V6
    untouched_rule = SORTER_PROMPT_V5.split("10. DEVELOPMENT PREFERENCE")[0].split(
        "11. SUBTYPE CONFIDENCE")[0]
    assert untouched_rule in SORTER_PROMPT_V6
    # The rule-10 sentence was refined in v6 — so full containment no longer
    # holds; the original sentence must still exist in the untouched v5.
    assert "even when the commercial machinery occupies more words." in SORTER_PROMPT_V5
    assert get_prompt("sorter_v6") is SORTER_PROMPT_V6

    v6 = SORTER_PROMPT_V6
    for banner in (
        "12. SEC JOINT FILING AGREEMENTS",
        "13. MAINTENANCE PREFERENCE",
        "14. HOSTING is not LICENSE and not DEVELOPMENT",
        "15. REMARKETING is MARKETING",
        "16. MARKETING CORE GUARD",
        "17. ANNEX INHERITANCE",
        "EXCEPT when the agreement's operative core is an operating/commercial family",
    ):
        assert banner in v6, f"missing v6 rule: {banner}"

    # The v5 prompt predates every v6 rule.
    for banner in ("12. SEC JOINT FILING", "17. ANNEX INHERITANCE"):
        assert banner not in SORTER_PROMPT_V5

    # The strict key discipline rule survives the derivation (option list intact).
    assert "STRICT KEY DISCIPLINE" in v6
