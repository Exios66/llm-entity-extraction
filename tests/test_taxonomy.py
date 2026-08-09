"""Tests for taxonomy loading and agent config resolution."""

from src.taxonomy import agent_config, doc_class_by_key, doc_class_keys, doc_class_labels, load_taxonomy


def test_doc_classes_match_prompts():
    keys = doc_class_keys()
    assert keys == [
        "contract", "corporate_record", "due_diligence",
        "correspondence", "compliance_filing", "court_opinion",
    ]


def test_doc_class_labels():
    labels = doc_class_labels()
    assert labels["contract"] == "Contract / Agreement"
    assert labels["court_opinion"] == "Court Opinion"


def test_doc_class_by_key():
    entry = doc_class_by_key("contract")
    assert entry["specialist"] == "contracts_specialist"
    assert "field_types" in entry
    assert doc_class_by_key("banana") is None


def test_agent_config_defaults():
    cfg = agent_config("sorter")
    assert cfg["model"] == "qwen/qwen3.7-flash"
    assert cfg["max_input_chars"] == 12000
    judge = agent_config("judge")
    assert judge["model"] == "deepseek/deepseek-v4-flash"
    assert agent_config("no_such_agent") == {}


def test_load_taxonomy_has_confidence_gates():
    taxonomy = load_taxonomy()
    confidence = taxonomy.get("confidence", {})
    assert confidence["high"] == 0.95
    assert confidence["low"] == 0.70
