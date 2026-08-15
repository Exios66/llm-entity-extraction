"""Unit tests for ``sync_langfuse_datasets.py``'s pure record logic (no network).

The Langfuse client is stubbed; only the dataset-item mapping is exercised:
deterministic content-addressed ids (reruns UPSERT, never duplicate), the
label as ``expected_output``, and dry-run writing nothing.
"""

from __future__ import annotations

from scripts.eval.sync_langfuse_datasets import _sync_records
from src.braintrust_utils import _deterministic_record_id


def _records():
    return [
        {"input": {"doc_text": "James came first in his class.",
                    "prompt": "Q: {{text}} Is there hearsay?\nA:",
                    "filename": "hearsay_5.txt",
                    "metadata": {"task": "hearsay", "slice": "Non-assertive conduct"}},
         "expected": {"doc_type": "No"},
         "metadata": {"source": "legalbench", "task": "hearsay",
                      "valid_classes": ["No", "Yes"], "answer": "No"}},
        {"input": {"doc_text": "Ava screamed at the officer.",
                    "prompt": "Q: {{text}} Is there hearsay?\nA:",
                    "filename": "hearsay_6.txt",
                    "metadata": {"task": "hearsay", "slice": "Non-verbal hearsay"}},
         "expected": {"doc_type": "Yes"},
         "metadata": {"source": "legalbench", "task": "hearsay",
                      "valid_classes": ["No", "Yes"], "answer": "Yes"}},
    ]


class FakeClient:
    """Records create_dataset / create_dataset_item calls without any network."""

    def __init__(self):
        self.datasets: set[str] = set()
        self.items: list[dict] = []

    def create_dataset(self, *, name):
        self.datasets.add(name)

    def create_dataset_item(self, **kwargs):
        self.items.append(kwargs)


def test_sync_records_upserts_deterministic_items():
    client = FakeClient()
    records = _records()
    upserted, skipped = _sync_records(client, "mailroom-lb-hearsay", records, dry_run=False)
    assert upserted == 2
    assert skipped == 0
    assert "mailroom-lb-hearsay" in client.datasets
    assert len(client.items) == 2

    # Deterministic content-addressed ids: a rerun lands on the SAME ids.
    ids = [item["id"] for item in client.items]
    assert len(set(ids)) == 2
    assert ids[0] == _deterministic_record_id(records[0])
    client2 = FakeClient()
    _sync_records(client2, "mailroom-lb-hearsay", records, dry_run=False)
    assert client2.items[0]["id"] == ids[0]
    assert client2.items[1]["id"] == ids[1]

    # The item carries the filled prompt + the label as expected_output.
    assert client.items[0]["expected_output"] == "No"
    assert client.items[1]["expected_output"] == "Yes"
    assert client.items[0]["input"]["prompt"].endswith("Is there hearsay?\nA:")
    assert client.items[0]["metadata"]["valid_classes"] == ["No", "Yes"]


def test_sync_records_dry_run_writes_nothing():
    client = FakeClient()
    upserted, _ = _sync_records(client, "mailroom-lb-hearsay", _records(), dry_run=True)
    assert upserted == 2  # counted as "would upsert"
    assert client.items == []
    assert client.datasets == set()
