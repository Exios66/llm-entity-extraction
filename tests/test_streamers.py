"""Tests for the dataset streamers' pure parsing logic (no network)."""

import zipfile

from scripts.datasets.stream_legalbench_to_bt import (
    build_maud_classification_records,
    build_records,
    load_maud_labels,
    load_maud_rows,
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


def test_load_maud_rows_filters_data_type(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        all_rows = load_maud_rows(zf)
        main_rows = load_maud_rows(zf, "main")
        abridged = load_maud_rows(zf, "abridged")
    assert len(all_rows) == 3
    assert len(main_rows) == 3  # fixture rows are all 'main'
    assert abridged == []


def test_build_maud_classification_records_shape(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        rows = load_maud_rows(zf, "main")
        records = build_maud_classification_records(rows)
    assert len(records) == 3
    first = records[0]
    assert first["expected"] == {"doc_type": "Yes"}
    assert first["input"]["doc_text"] == "some text"
    assert first["input"]["filename"] == "maud_contract_0_1.txt"
    assert first["metadata"]["task"] == "Termination Clause"


def test_build_maud_classification_records_per_question_spaces(sample_maud_zip):
    with zipfile.ZipFile(sample_maud_zip) as zf:
        rows = load_maud_rows(zf, "main")
    records = build_maud_classification_records(rows)
    by_task = {}
    for r in records:
        task = r["metadata"]["task"]
        by_task[task] = r["input"]["metadata"]["valid_classes"]
    assert by_task["Termination Clause"] == ["Yes"]
    assert by_task["Anti-Assignment"] == ["No"]
    assert by_task["Change of Control"] == ["Yes"]
