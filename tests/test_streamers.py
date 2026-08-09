"""Tests for the dataset streamers' pure parsing logic (no network)."""

import zipfile

from scripts.datasets.stream_legalbench_to_bt import (
    build_records,
    load_maud_labels,
    stream_contracts,
)


def test_maud_zip_members(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        members = stream_contracts(zf)
    assert members == ["data/contracts/contract_0.txt", "data/contracts/contract_1.txt"]


def test_maud_labels_parsed_per_contract(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        labels = load_maud_labels(zf, cap=10)
    assert len(labels["contract_0"]) == 2
    assert labels["contract_0"][0]["label"] == "Yes"
    assert labels["contract_1"][0]["question"].startswith("Change of control")


def test_maud_labels_capped(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        labels = load_maud_labels(zf, cap=1)
    assert len(labels["contract_0"]) == 1


def test_build_records_shapes(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        members = stream_contracts(zf)
        labels = load_maud_labels(zf, cap=10)
        records = build_records(zf, members, labels, limit=0)
    assert len(records) == 2
    record = records[0]
    assert record["input"]["filename"] == "contract_0_merger_agreement.txt"
    assert record["expected"] == {"doc_type": "contract"}
    assert record["expected_output"]["maud_label_count"] == 2
    assert "agreement" in record["input"]["doc_text"].lower()


def test_build_records_limit(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        members = stream_contracts(zf)
        records = build_records(zf, members, {}, limit=1)
    assert len(records) == 1
    assert records[0]["metadata"]["maud_label_count"] == 0
