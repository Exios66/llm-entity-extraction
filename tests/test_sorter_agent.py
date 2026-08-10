"""Tests for the sorter agent's prompt resolution, subtype handling, and
parsing (LLM mocked)."""

import pytest

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
    for version in ("sorter_v4", "sorter_v5"):
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
