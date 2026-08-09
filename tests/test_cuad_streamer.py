"""Tests for the CUAD streamer's pure parsing logic (no network)."""

import json

from scripts.datasets.stream_cuad_to_bt import build_records, parse_contracts


def _sample_cuad_json() -> bytes:
    data = {
        "data": [
            {
                "title": "ACME_2024_EX-10.1_DISTRIBUTOR AGREEMENT",
                "paragraphs": [
                    {
                        "context": "This Distributor Agreement is made between ACME Inc. and Beta LLC.",
                        "qas": [
                            {"id": "q1", "question": "What is the effective date?", "answers": []}
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
            {
                "title": "SHORT",
                "paragraphs": [{"context": "tiny", "qas": []}],
            },
        ]
    }
    return json.dumps(data).encode("utf-8")


def test_parse_contracts_joins_and_dedupes():
    contracts = parse_contracts(_sample_cuad_json(), min_chars=50)
    assert len(contracts) == 1  # the short one is filtered by min_chars
    big = contracts[0]
    assert big["title"].startswith("ACME_")
    assert big["paragraphs"] == 2  # duplicate paragraph dropped
    assert big["qa_count"] == 1
    assert big["chars"] == len(big["doc_text"])


def test_parse_contracts_min_chars_filters_all():
    contracts = parse_contracts(_sample_cuad_json(), min_chars=10_000)
    assert contracts == []


def test_build_records_shape():
    contracts = parse_contracts(_sample_cuad_json(), min_chars=50)
    records = build_records(contracts)
    assert len(records) == 1
    record = records[0]
    assert record["expected"] == {"doc_type": "contract"}
    assert record["input"]["filename"] == "ACME_2024_EX-10.1_DISTRIBUTOR AGREEMENT.txt"
    assert record["metadata"]["source"] == "cuad_v1"
    assert record["metadata"]["license"] == "CC BY 4.0"
