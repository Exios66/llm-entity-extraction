"""Tests for the CUAD streamer's pure logic (no network)."""

import json

from scripts.datasets.stream_cuad_to_bt import (
    build_records,
    category_of,
    load_clause_labels,
    stem_of,
)


def _sample_cuad_json() -> bytes:
    data = {
        "data": [
            {
                "title": "ACME_2024_EX-10.1_DISTRIBUTOR AGREEMENT",
                "paragraphs": [
                    {
                        "context": "This Distributor Agreement is made between ACME Inc. and Beta LLC.",
                        "qas": [
                            {"id": "q1", "question": "What is the effective date?",
                             "answers": [{"text": "January 1, 2024", "answer_start": 10}]}
                        ],
                    },
                    {
                        "context": "Section 2. Termination. Either party may terminate on 30 days notice.",
                        "qas": [],
                    },
                    # duplicate context must be dropped on join
                    {
                        "context": "This Distributor Agreement is made between ACME Inc. and Beta LLC.",
                        "qas": [],
                    },
                ],
            },
        ]
    }
    return json.dumps(data).encode("utf-8")


def test_load_clause_labels_parsing(monkeypatch):
    def fake_get(url, **kwargs):
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return json.loads(_sample_cuad_json())

        return Resp()

    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt.requests.get", fake_get)
    labels = load_clause_labels()
    assert len(labels) == 1
    entry = labels["acme2024ex101distributoragreement"]
    assert entry["title"].startswith("ACME_")
    assert "Termination" in entry["doc_text"]
    assert entry["doc_text"].count("This Distributor Agreement is made") == 1  # deduped
    assert entry["clauses"][0]["question"] == "What is the effective date?"
    assert entry["clauses"][0]["answer"] == "January 1, 2024"


def test_category_and_stem():
    path = "CUAD_v1/full_contract_pdf/Part_I/Franchise/BUFFALO_FRANCHISE.PDF"
    assert category_of(path) == "Franchise"
    assert stem_of(path) == "BUFFALO_FRANCHISE"


def test_build_records_shapes(monkeypatch):
    pdf_path = "CUAD_v1/full_contract_pdf/Part_I/Franchise/BUFFALO_FRANCHISE.PDF"

    def fake_stream(pdf_path):
        return b"fake-pdf-bytes"

    def fake_render(pdf_bytes, pages_per_doc, target_size, max_pages=20):
        return [b"page1-png", b"page2-png"]

    class FakeAttachment:
        def __init__(self, data, filename, content_type):
            self.reference = {"filename": filename, "content_type": content_type}

    def fake_attachment(png_bytes, filename, api_key):
        return FakeAttachment(png_bytes, filename, "image/png")

    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt.stream_pdf", fake_stream)
    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt.render_pdf_pages", fake_render)
    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt._attachment", fake_attachment)

    labels = {"buffalofranchise": {
        "title": "BUFFALO FRANCHISE",
        "doc_text": "full contract text",
        "clauses": [{"question": "q", "answer": "a", "answer_start": 0}],
    }}
    records = build_records([pdf_path], pages_per_doc="all", target_size=(1024, 1024),
                            api_key="fake", clause_labels=labels)
    assert len(records) == 1  # ONE row per document, all pages inside
    first = records[0]
    assert first["input"]["document_id"] == "cuad_BUFFALO_FRANCHISE"
    assert first["input"]["metadata"]["source_file"] == pdf_path
    assert first["input"]["doc_text"] == "full contract text"
    assert first["input"]["metadata"]["category"] == "Franchise"
    assert first["expected"]["doc_type"] == "contract"
    assert first["expected"]["clause_count"] == 1
    assert first["expected"]["clause_labels"] == [{"question": "q", "answer": "a", "answer_start": 0}]
    assert first["expected"]["expected_fields"] == {}  # "q" is not a mapped CUAD category
    assert first["expected_output"]["clause_count"] == 1
    assert len(first["input"]["pages"]) == 2  # both pages as attachments
    assert first["input"]["metadata"]["page_count"] == 2
    assert first["input"]["image"].reference["filename"].endswith("page0001.png")
    assert first["metadata"]["page_count"] == 2
    assert first["input"]["metadata"]["placeholder"] is False


def test_build_records_without_labels(monkeypatch):
    pdf_path = "CUAD_v1/full_contract_pdf/Part_I/Franchise/BUFFALO_FRANCHISE.PDF"

    def fake_stream(pdf_path):
        return b"fake-pdf-bytes"

    def fake_render(pdf_bytes, pages_per_doc, target_size, max_pages=20):
        return [b"page1-png"]

    class FakeAttachment:
        def __init__(self, data, filename, content_type):
            self.reference = {"filename": filename, "content_type": content_type}

    def fake_attachment(png_bytes, filename, api_key):
        return FakeAttachment(png_bytes, filename, "image/png")

    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt.stream_pdf", fake_stream)
    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt.render_pdf_pages", fake_render)
    monkeypatch.setattr("scripts.datasets.stream_cuad_to_bt._attachment", fake_attachment)
    records = build_records([pdf_path], pages_per_doc="all", target_size=(1024, 1024), api_key="fake")
    assert records[0]["input"]["doc_text"] is None
    assert records[0]["expected_output"]["clause_count"] == 0
    assert len(records[0]["input"]["pages"]) == 1
