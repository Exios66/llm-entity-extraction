"""Network-free tests for the ContractEval mapping scorer (src/contracteval.py).

Covers the master-GT loader, the span->category mapper (routing / verbatim /
best-match), the exact ContractEval metric math, and the per-record evaluation
over synthetic rows.
"""

from __future__ import annotations

import json

import pytest

from src.contracteval import (
    BEST_MATCH_FLOOR,
    build_category_output,
    contracteval_metrics,
    coverage_bands,
    evaluate_record,
    get_jaccard,
    load_master_gt,
    map_span_to_categories,
    normalize_filename,
)


def test_normalize_filename():
    assert normalize_filename("Monsanto Company - SECOND A_R EXCLUSIVE AGENCY AND MARKETING AGREEMENT") == \
        normalize_filename("Monsanto Company - SECOND A&R EXCLUSIVE AGENCY AND MARKETING AGREEMENT .PDF")
    assert normalize_filename("CybergyHoldingsInc_20140520_10-Q_EX-10.27_8605784_EX-10.27_Affiliate Agreement.pdf") == \
        normalize_filename("CybergyHoldingsInc_20140520_10-Q_EX-10.27_8605784_EX-10.27_Affiliate Agreement")
    assert normalize_filename(None) == ""


def test_load_master_gt(tmp_path):
    csv_path = tmp_path / "master.csv"
    csv_path.write_text(
        'Filename,Anti-Assignment,Anti-Assignment-Answer,Volume Restriction\n'
        '"Doc A .PDF","[\'MA may not assign any rights\']","Yes","[]"\n'
        '"Doc B.pdf","[]","No","[\'no volume restrictions apply\']"\n'
    )
    gt = load_master_gt(csv_path)
    assert normalize_filename("Doc A.pdf") in gt
    doc = gt[normalize_filename("Doc A.pdf")]
    assert doc["Anti-Assignment"] == ["MA may not assign any rights"]
    assert "Volume Restriction" not in doc  # empty cells dropped
    assert normalize_filename("Doc B.pdf") in gt
    assert gt[normalize_filename("Doc B.pdf")]["Volume Restriction"] == ["no volume restrictions apply"]


def test_load_master_gt_real_csv_is_joinable():
    import csv
    rows = list(csv.DictReader(open("data/cuad/master_clauses.csv")))
    assert len(rows) == 510
    gt = load_master_gt("data/cuad/master_clauses.csv")
    assert len(gt) == 510
    some = rows[0]["Filename"]
    assert normalize_filename(some) in gt


def test_get_jaccard_mirrors_contracteval():
    gt = "NEITHER PARTY SHALL, WITHOUT THE PRIOR WRITTEN CONSENT OF THE OTHER PARTY, ASSIGN THIS AGREEMENT."
    pred = "neither party shall without the prior written consent of the other party assign this agreement."
    assert get_jaccard(gt, pred) == pytest.approx(1.0)
    assert get_jaccard("a b c", "a b") == pytest.approx(2 / 3)
    # Faithful ContractEval quirk: split(" ") on empty -> {""}, so empty-vs-
    # empty is 1.0 while empty-vs-nonempty is 0.0.
    assert get_jaccard("", "") == pytest.approx(1.0)
    assert get_jaccard("", "x") == pytest.approx(0.0)


ANTI = "NEITHER PARTY SHALL, WITHOUT THE PRIOR WRITTEN CONSENT OF THE OTHER PARTY, ASSIGN THIS AGREEMENT"


def test_map_span_to_categories_verbatim():
    gt_spans = {"Anti-Assignment": [ANTI], "Non-Compete": []}
    assert map_span_to_categories(ANTI, gt_spans, {}) == ["Anti-Assignment"]


def test_map_span_to_categories_best_match():
    gt_spans = {
        "Anti-Assignment": ["party shall not assign without consent"],
        "Insurance": ["company shall maintain comprehensive insurance coverage"],
    }
    span = "the party shall not assign this agreement without the prior consent"
    mapped = map_span_to_categories(span, gt_spans, {})
    assert mapped == ["Anti-Assignment"]


def test_map_span_to_categories_routing():
    gt_spans = {"Anti-Assignment": [ANTI], "Audit Rights": []}
    routed = {"Audit Rights": ["company shall maintain accurate records of sales"]}
    span = "company shall maintain accurate records of the sales of the products"
    mapped = map_span_to_categories(span, gt_spans, routed)
    assert "Audit Rights" in mapped


def test_contracteval_metrics_confusion():
    pairs = [
        ([ANTI], ANTI),            # TP: label verbatim-contained
        ([ANTI], "no related clause"),  # FN + false-no-related
        ([], "no related clause"),      # TN
        ([], "a fabricated clause"),    # FP
        ([ANTI, "second label"], ANTI),  # FN: not ALL labels contained
    ]
    m = contracteval_metrics(pairs)
    assert m["tp"] == 1
    assert m["fn"] == 2
    assert m["tn"] == 1
    assert m["fp"] == 1
    assert m["n_positive"] == 3
    assert m["precision"] == pytest.approx(0.5)
    assert m["recall"] == pytest.approx(1 / 3, abs=1e-3)
    assert m["false_no_related_rate"] == pytest.approx(1 / 3, abs=1e-3)
    # Jaccard only over positive pairs (3 of them, two are "no related clause").
    assert m["jaccard_mean"] > 0.0


def test_evaluate_record_synthetic(tmp_path):
    csv_path = tmp_path / "master.csv"
    csv_path.write_text(
        'Filename,Anti-Assignment,Anti-Assignment-Answer,Volume Restriction,Volume Restriction-Answer\n'
        '"Doc A.pdf","[\'NEITHER PARTY SHALL ASSIGN THIS AGREEMENT\']","Yes","[]","No"\n'
    )
    gt = load_master_gt(csv_path)
    record = {
        "experiment_name": "synthetic_run",
        "results": [
            {
                "filename": "Doc A.pdf",
                "error": None,
                "predicted": {
                    "key_obligations": [
                        "NEITHER PARTY SHALL ASSIGN THIS AGREEMENT; "
                        "the Company shall keep accurate records of sales."
                    ],
                    "termination_clauses": [],
                    "reasoning": {"entries": []},
                },
            },
            {"filename": "Doc B.pdf", "error": None, "predicted": {}},  # unjoined
        ],
    }
    m = evaluate_record(record, gt)
    # 1 joined doc x 32 obligation categories; Anti-Assignment TP, the rest TN.
    assert m["n_docs"] == 1
    assert m["n_unjoined"] == 1
    assert m["n_pairs"] == 32
    assert m["tp"] >= 1
    assert m["precision"] == pytest.approx(1.0)
    assert m["n_positive"] >= 1


def test_coverage_bands():
    record = {
        "results": [
            {
                "filename": "Doc A.pdf",
                "error": None,
                "predicted": {
                    "key_obligations": ["NEITHER PARTY SHALL ASSIGN THIS AGREEMENT"],
                    "termination_clauses": [],
                    "reasoning": {"entries": []},
                },
            }
        ]
    }
    gt = {normalize_filename("Doc A.pdf"): {
        "Anti-Assignment": ["NEITHER PARTY SHALL ASSIGN THIS AGREEMENT"],
    }}
    bands = coverage_bands(record, gt, categories=["Anti-Assignment"])
    assert bands["n_pos"] == 1
    assert bands["verbatim"] == pytest.approx(1.0)
    assert bands["ge0_7"] == pytest.approx(1.0)
