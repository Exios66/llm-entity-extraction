"""Regression tests for sorter / specialist parsing defects (LLM mocked)."""

from langchain_core.messages import AIMessage

from agents.sorter_agent import (
    DOCCLASS_CLASS_KEYS,
    DOCCLASS_CLASSES,
    DOCCLASS_SCHEMA,
    SorterAgent,
    normalize_doc_subclass,
)
from agents.specialist_agents import (
    CONTRACTS_SCHEMA,
    SPECIALIST_SCHEMAS,
    ContractsSpecialist,
    InsuranceClaimsSpecialist,
    _SpecialistBase,
    get_specialist,
)
from src.classifier import clean_prediction, extract_confidence


def _docclass_sorter():
    return SorterAgent(doc_classes=DOCCLASS_CLASSES, schema=DOCCLASS_SCHEMA)


def test_vision_label_with_spaces_maps_to_extended_key():
    raw = ("<reasoning>Plan of merger, not a contract for services.</reasoning>\n"
           "<label>Merger Agreement</label>\n<confidence>90</confidence>")
    out = _docclass_sorter()._parse_vision_output(raw, DOCCLASS_CLASS_KEYS)
    assert out["doc_type"] == "merger_agreement"
    assert out["invalid_label"] is False


def test_vision_unknown_tag_label_is_invalid_not_a_reasoning_word():
    # Used to scan the reasoning, find "contract", and report success.
    raw = ("<reasoning>Looks like a contract dispute memo.</reasoning>\n"
           "<label>banana</label>\n<confidence>80</confidence>")
    out = _docclass_sorter()._parse_vision_output(raw, DOCCLASS_CLASS_KEYS)
    assert out["doc_type"] is None
    assert out["invalid_label"] is True


def test_clean_prediction_normalizes_tag_label():
    assert clean_prediction("<label>Corporate Record</label>") == "corporate_record"


def test_scoped_subclass_accepts_display_label():
    assert normalize_doc_subclass("Demand Letter", "correspondence") == "demand"
    assert normalize_doc_subclass("Memorandum", "correspondence") == "memo"
    assert normalize_doc_subclass("nonsense", "correspondence") == "other"


def test_extract_confidence_formats():
    assert extract_confidence("<confidence>0.92</confidence>") == 0.92
    assert extract_confidence("<confidence>95%</confidence>") == 0.95
    assert extract_confidence("<confidence>87.5</confidence>") == 0.875
    assert extract_confidence("<confidence>85</confidence>") == 0.85
    # A non-numeric tag must not fall through to a stray trailing digit.
    assert extract_confidence("<confidence>high</confidence>\nSteps:\n1") is None


def test_split_chunks_keeps_document_order():
    text = "PARA_A intro\n\n" + "B" * 25 + "\n\nPARA_C end"
    chunks = _SpecialistBase._split_chunks(text, 20, 0)
    assert chunks[0] == "PARA_A intro"
    joined = "".join(chunks)
    assert joined.index("PARA_A") < joined.index("B") < joined.index("PARA_C")


def test_registry_covers_taxonomy_specialists():
    assert isinstance(get_specialist("insurance_claim", api_key="x"), InsuranceClaimsSpecialist)
    assert isinstance(get_specialist("merger_agreement", api_key="x"), ContractsSpecialist)
    assert SPECIALIST_SCHEMAS["merger_agreement"] is CONTRACTS_SCHEMA


class _ListContentLLM:
    def invoke(self, *args, **kwargs):
        return AIMessage(content=[
            {"type": "text", "text": "<label>contract</label>\n"},
            {"type": "text", "text": "<confidence>90</confidence>"},
        ])

    def bind(self, **kwargs):
        return self


def test_vision_call_joins_list_content(mocker):
    sorter = _docclass_sorter()
    mocker.patch.object(sorter, "llm", return_value=_ListContentLLM())
    out = sorter._call_vision_multi("sys", "user", [("aGVsbG8=", "png")])
    assert out == "<label>contract</label>\n<confidence>90</confidence>"
