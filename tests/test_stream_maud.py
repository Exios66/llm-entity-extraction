"""Network-free tests for the MAUD streamer (scripts/datasets/stream_maud_to_bt.py).

The streamer builds the ``mailroom-maud-contracts`` dataset (GT
merger_agreement + consideration-type subclass) and the per-question
classification dataset from the MAUD v1 zip. These tests exercise the record
builders against a small FAKE zip — no network, no Braintrust.
"""

from __future__ import annotations

import io
import json
import zipfile

from scripts.datasets.stream_maud_to_bt import (
    build_classification_records,
    build_contract_records,
    normalize_consideration,
    per_contract_categories,
    per_contract_consideration,
    write_local_jsonl,
)

CSV_HEADER = ("data_type,contract_name,text,answer,label,question,subquestion,"
              "text_type,id,category")

FAKE_ROWS = [
    # contract_0: all-cash consideration + MAE rows
    dict(data_type="main", contract_name="contract_0", text="The Merger Consideration shall be $1,000,000,000 in cash.",
         answer="All Cash", label="0", question="What is the type of consideration?",
         subquestion="", text_type="Type of Consideration", id="q1",
         category="General Information"),
    dict(data_type="main", contract_name="contract_0",
         text="Material Adverse Effect means any change in the business...",
         answer="Yes", label="0",
         question="Does the definition of Material Adverse Effect include a general economic condition carve-out?",
         subquestion="", text_type="MAE Definition", id="q2",
         category="Material Adverse Effect"),
    # contract_1: mixed consideration with election
    dict(data_type="main", contract_name="contract_1",
         text="Each share of Company Common Stock shall be converted into the right to receive $10.00 in cash and 0.5 shares of Parent Common Stock.",
         answer="Mixed Cash/Stock: Election", label="1",
         question="What is the type of consideration?", subquestion="",
         text_type="Type of Consideration", id="q3", category="General Information"),
    dict(data_type="main", contract_name="contract_1",
         text="The Company shall not solicit alternative acquisition proposals.",
         answer="No", label="1", question="Is the Company permitted to solicit?",
         subquestion="", text_type="No-Shop", id="q4",
         category="Deal Protection and Related Provisions"),
    # contract_2: no consideration answer (subclass -> other)
    dict(data_type="main", contract_name="contract_2",
         text="The representations and warranties shall survive for 18 months.",
         answer="No", label="2", question="Do R&Ws survive for 24 months?",
         subquestion="", text_type="Accuracy of Target R&W Closing Condition", id="q5",
         category="Conditions to Closing"),
]


def _fake_zip(tmp_path) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_text = CSV_HEADER + "\n" + "\n".join(
            ",".join(str(r[k]) for k in ("data_type", "contract_name", "text", "answer",
                                         "label", "question", "subquestion", "text_type",
                                         "id", "category"))
            for r in FAKE_ROWS
        )
        zf.writestr("data/MAUD_train.csv", csv_text)
        zf.writestr("data/contracts/contract_0.txt", "AGREEMENT AND PLAN OF MERGER among X, Y and Z... " * 50)
        zf.writestr("data/contracts/contract_1.txt", "AGREEMENT AND PLAN OF MERGER by and among A, B and C... " * 50)
        zf.writestr("data/contracts/contract_2.txt", "PLAN AND AGREEMENT OF MERGER... " * 50)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_normalize_consideration():
    assert normalize_consideration("All Cash") == "all_cash"
    assert normalize_consideration("All Stock") == "all_stock"
    assert normalize_consideration("Mixed Cash/Stock") == "mixed_cash_stock"
    assert normalize_consideration("Mixed Cash/Stock: Election") == "mixed_cash_stock_election"
    assert normalize_consideration(None) == "other"
    assert normalize_consideration("") == "other"
    assert normalize_consideration("Unknown Value") == "other"


def test_per_contract_consideration_from_rows():
    got = per_contract_consideration(FAKE_ROWS)
    assert got["contract_0"] == "all_cash"
    assert got["contract_1"] == "mixed_cash_stock_election"
    # contract_2 has no consideration answer: absent from the map, and the
    # record builder defaults it to "other".
    assert "contract_2" not in got


def test_per_contract_categories_metadata():
    got = per_contract_categories(FAKE_ROWS)
    assert got["contract_0"]["Material Adverse Effect"] == 1
    assert got["contract_1"]["Deal Protection and Related Provisions"] == 1


def test_build_contract_records(tmp_path):
    texts = {
        "contract_0": "AGREEMENT AND PLAN OF MERGER " * 100,
        "contract_1": "AGREEMENT AND PLAN OF MERGER " * 100,
        "contract_2": "PLAN AND AGREEMENT OF MERGER " * 100,
    }
    consideration = {"contract_0": "all_cash", "contract_1": "mixed_cash_stock_election",
                     "contract_2": "other"}
    categories = {"contract_0": {"Material Adverse Effect": 1}}
    records = build_contract_records(texts, consideration, categories, limit=0)
    assert len(records) == 3
    for r in records:
        assert r["expected"]["doc_type"] == "merger_agreement"
        assert r["metadata"]["source"] == "maud_v1"
    by_contract = {r["metadata"]["contract"]: r for r in records}
    assert by_contract["contract_0"]["expected"]["doc_subclass"] == "all_cash"
    assert by_contract["contract_1"]["expected"]["doc_subclass"] == "mixed_cash_stock_election"
    assert by_contract["contract_2"]["expected"]["doc_subclass"] == "other"
    assert by_contract["contract_0"]["input"]["metadata"]["maud_categories"] == {"Material Adverse Effect": 1}
    # deterministic ordering + limit
    limited = build_contract_records(texts, consideration, categories, limit=2)
    assert len(limited) == 2


def test_build_classification_records():
    records = build_classification_records(FAKE_ROWS, split="train")
    assert len(records) == 5
    by_id = {r["input"]["metadata"]["maud_id"]: r for r in records}
    q1 = by_id["q1"]
    assert q1["expected"]["doc_type"] == "All Cash"
    # answer space per question family: q1's space is just its own answer here
    assert "All Cash" in q1["input"]["metadata"]["valid_classes"]
    q4 = by_id["q4"]
    assert q4["metadata"]["category"] == "Deal Protection and Related Provisions"
    assert q4["input"]["metadata"]["task"] == "No-Shop"
    assert q4["metadata"]["split"] == "train"
    assert "contract_0" in q1["input"]["filename"]


def test_write_local_jsonl_shape(tmp_path):
    records = build_contract_records(
        {"contract_0": "text " * 100}, {"contract_0": "all_cash"}, {}, limit=1)
    path = tmp_path / "contracts.jsonl"
    n = write_local_jsonl(records, path)
    assert n == 1
    row = json.loads(path.read_text().strip())
    assert row["expected"] == "merger_agreement"
    assert row["expected_subclass"] == "all_cash"
    assert row["filename"] == "contract_0_merger_agreement.txt"
    assert "doc_text" in row and len(row["doc_text"]) > 0


def test_fake_zip_loads(tmp_path):
    """The fake zip is loadable through the streamer's zenodo path (no download)."""
    zf = _fake_zip(tmp_path)
    names = [n for n in zf.namelist() if n.endswith(".txt")]
    assert len(names) == 3
    assert "data/contracts/contract_0.txt" in names
