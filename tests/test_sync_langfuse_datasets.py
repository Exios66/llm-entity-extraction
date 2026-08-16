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

    def flush(self):
        pass

    def shutdown(self):
        pass


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


def _cuad_corpus(tmp_path):
    """A minimal local CUAD mirror: one contract (CUAD_v1.json) + its PDF in
    the nested Part_II/License_Agreements tree, filenames mirroring HF so
    ``_norm(stem) == _norm(title)`` matches."""
    import json

    cuad_dir = tmp_path / "cuad"
    pdf_dir = (cuad_dir / "CUAD_v1" / "full_contract_pdf"
               / "Part_II" / "License_Agreements")
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "Acme_License_Agreement.pdf").write_bytes(b"fake-pdf")
    data = {"data": [{
        "title": "Acme License Agreement",
        "paragraphs": [{
            "context": "This License Agreement between Acme and Beta sets the terms.",
            "qas": [{"question": "What is the term?",
                     "answers": [{"text": "2 years", "answer_start": 12}]}],
        }],
    }]}
    (cuad_dir / "CUAD_v1.json").write_text(json.dumps(data), encoding="utf-8")
    return cuad_dir


def test_sync_cuad_mirrors_local_corpus(monkeypatch, tmp_path):
    """``--cuad`` mirrors the LOCAL corpus into ``mailroom-cuad-contracts`` as
    TEXT rows (offline: doc_text + clause QA + category metadata), upserted with
    deterministic ids — the Langfuse twin of streaming the corpus to Braintrust."""

    from scripts.eval import sync_langfuse_datasets

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-fake")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-fake")
    monkeypatch.setenv("LANGFUSE_PROJECT", "llm-dojo")
    client = FakeClient()
    monkeypatch.setattr(sync_langfuse_datasets, "Langfuse", lambda **kwargs: client)

    cuad_dir = _cuad_corpus(tmp_path)
    report = sync_langfuse_datasets._sync_cuad(tmp_path / "langfuse.env", cuad_dir, dry_run=False)

    assert report["skipped_env"] is False
    assert report["datasets"] == 1
    assert report["items"] == 1
    assert "mailroom-cuad-contracts" in client.datasets
    assert len(client.items) == 1
    item = client.items[0]
    assert item["dataset_name"] == "mailroom-cuad-contracts"
    assert item["expected_output"] == "contract"
    assert item["input"]["doc_text"].startswith("This License Agreement")
    assert item["input"]["metadata"]["category"] == "License_Agreements"
    assert item["input"]["metadata"]["page_count"] == 0  # text rows carry no page images
    assert item["metadata"]["source"] == "cuad_v1"


def _merged_docclass_dump(tmp_path):
    """A minimal MERGED docclass dump: one row per docclass corpus, in the flat
    streamer-dump shape ``build_docclass_merged.py`` writes."""
    import json

    path = tmp_path / "docclass_merged.jsonl"
    rows = [
        {"filename": "Acme License Agreement", "doc_text": "LICENSE AGREEMENT " * 50,
         "prompt": "", "expected": "contract", "expected_subclass": None,
         "metadata": {"source_dataset": "mailroom-cuad-contracts-full"}},
        {"filename": "merger_1.txt", "doc_text": "AGREEMENT AND PLAN OF MERGER " * 50,
         "prompt": "", "expected": "merger_agreement", "expected_subclass": "all_cash",
         "metadata": {"source_dataset": "data/maud/contracts.jsonl"}},
        {"filename": "bylaws.htm", "doc_text": "BYLAWS OF ACME INC. " * 50,
         "prompt": "", "expected": "corporate_record", "expected_subclass": "bylaws",
         "metadata": {"source_dataset": "data/s1_corporate_records/corporate-records.jsonl"}},
    ]
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return path


def test_sync_docclass_merged_single_dataset(monkeypatch, tmp_path):
    """``--docclass`` mirrors the MERGED docclass corpus as ONE Langfuse
    dataset (``mailroom-docclass``) with all three corpora's rows — the
    single-dataset surface the hierarchical sorter eval consumes."""

    from scripts.eval import sync_langfuse_datasets

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-fake")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-fake")
    monkeypatch.setenv("LANGFUSE_PROJECT", "llm-dojo")
    client = FakeClient()
    monkeypatch.setattr(sync_langfuse_datasets, "Langfuse", lambda **kwargs: client)

    dump = _merged_docclass_dump(tmp_path)
    report = sync_langfuse_datasets._sync_local_dumps(
        tmp_path / "langfuse.env", {"mailroom-docclass": dump}, dry_run=False)

    assert report["skipped_env"] is False
    assert report["datasets"] == 1
    assert report["items"] == 3
    assert client.datasets == {"mailroom-docclass"}
    assert len(client.items) == 3

    by_output = {item["expected_output"]: item for item in client.items}
    assert set(by_output) == {"contract", "merger_agreement", "corporate_record"}
    # The doc_subclass GT rides in the input metadata (the docclass dimension).
    merger = by_output["merger_agreement"]
    assert merger["input"]["metadata"]["expected_subclass"] == "all_cash"
    assert merger["metadata"]["source_dataset"] == "data/maud/contracts.jsonl"
