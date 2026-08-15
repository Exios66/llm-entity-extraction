"""Unit tests for the Braintrust dataset row-id helper (no network)."""

from __future__ import annotations

from src.braintrust_utils import _deterministic_record_id


def test_deterministic_id_stable_across_reruns():
    record = {
        "input": {"doc_text": "clause text", "filename": "hearsay_0.txt",
                  "metadata": {"task": "hearsay", "valid_classes": ["No", "Yes"]}},
        "expected": {"doc_type": "No"},
        "metadata": {"source": "legalbench", "task": "hearsay"},
    }
    first = _deterministic_record_id(record)
    second = _deterministic_record_id(record)
    assert first == second
    assert first.startswith("rec-")


def test_deterministic_id_content_addressed():
    record = {
        "input": {"doc_text": "clause text", "filename": "hearsay_0.txt"},
        "expected": {"doc_type": "No"},
    }
    changed = {
        "input": {"doc_text": "clause text", "filename": "hearsay_0.txt"},
        "expected": {"doc_type": "Yes"},
    }
    assert _deterministic_record_id(record) != _deterministic_record_id(changed)


def test_deterministic_id_distinct_records_distinct_ids():
    base = {"input": {"doc_text": "t", "filename": "f.txt"}, "expected": {"doc_type": "No"}}
    other = {"input": {"doc_text": "different", "filename": "f2.txt"}, "expected": {"doc_type": "No"}}
    assert _deterministic_record_id(base) != _deterministic_record_id(other)
