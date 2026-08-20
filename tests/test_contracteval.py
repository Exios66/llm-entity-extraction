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
    _clean_span,
    build_category_output,
    contracteval_metrics,
    coverage_bands,
    evaluate_record,
    get_jaccard,
    load_master_gt,
    map_span_to_categories,
    normalize_filename,
    run_kpis,
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


def test_clean_span_collapses_whitespace_and_strips_omitted():
    assert _clean_span("MA may not\nassign  any  rights") == "MA may not assign any rights"
    assert _clean_span("For the term,<omitted>distribute the content") == \
        "For the term, distribute the content"
    assert _clean_span("  both\nsides <omitted> and [omitted]  ") == "both sides and"
    assert _clean_span("plain clause text.") == "plain clause text."


def test_load_master_gt_normalizes_artifact_spans(tmp_path):
    csv_path = tmp_path / "master.csv"
    csv_path.write_text(
        'Filename,Anti-Assignment,License Grant\n'
        '"Doc A .PDF","[\'MA may not\\nassign  any rights\']","[\'For the term,<omitted>distribute\']"\n'
    )
    gt = load_master_gt(csv_path)
    doc = gt[normalize_filename("Doc A.pdf")]
    assert doc["Anti-Assignment"] == ["MA may not assign any rights"]
    assert doc["License Grant"] == ["For the term, distribute"]


def test_load_master_gt_literal_newline_cell_degrades_to_empty(tmp_path):
    """18 real cells contain LITERAL newlines (unparseable literals): the
    whole cell degrades to an empty GT (pre-existing behavior, not a crash)."""
    csv_path = tmp_path / "master.csv"
    csv_path.write_text(
        'Filename,Anti-Assignment\n'
        '"Doc A .PDF","[\'MA may not\nassign any rights\']"\n'
    )
    gt = load_master_gt(csv_path)
    assert "Anti-Assignment" not in gt[normalize_filename("Doc A.pdf")]


def test_cleaned_gt_span_matches_model_output_verbatim():
    """KANBAN-058: the whitespace/`<omitted>` GT artifacts must no longer
    break the ContractEval TP predicate for a faithful verbatim quote."""
    from src.contracteval import contracteval_metrics
    gt_label = "For the License Term and within the Licensed Territory,<omitted>Producer grants a right"
    model = "For the License Term and within the Licensed Territory, Producer grants a right to ConvergTV"
    pairs = [([_clean_span(gt_label)], model)]
    metrics = contracteval_metrics(pairs)
    assert metrics["recall"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["f1"] == 1.0


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


def test_run_kpis_block():
    """run_kpis assembles the per-run ContractEval-rubric KPI block
    (KANBAN-054): the pooled confusion F1/F2/Jaccard/false-nr + the semantic
    coverage bands, in the compact shape stored as
    ``scores.contracteval_kpis`` on extraction run records."""
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
        ],
    }
    gt = {normalize_filename("Doc A.pdf"): {
        "Anti-Assignment": ["NEITHER PARTY SHALL ASSIGN THIS AGREEMENT"],
    }}
    k = run_kpis(record, gt, categories=["Anti-Assignment"])
    # Confusion block: 1 positive pair, TP via verbatim containment.
    assert k["task"] == "contracteval_mapping"
    assert k["n_pairs"] == 1
    assert k["n_positive"] == 1
    assert k["n_docs"] == 1
    assert k["n_unjoined"] == 0
    assert k["precision"] == pytest.approx(1.0)
    assert k["recall"] == pytest.approx(1.0)
    assert k["f1"] == pytest.approx(1.0)
    assert k["f2"] == pytest.approx(1.0)
    assert k["jaccard_mean"] > 0.0
    assert k["false_no_related_rate"] == pytest.approx(0.0)
    # Laziness score (ContractEval §III-D): share of ALL pairs answered
    # "no related clause" — the TP pair here answers with a clause, so 0.0.
    assert k["no_related_rate"] == pytest.approx(0.0)
    assert k["laziness"] == pytest.approx(0.0)
    assert k["laziness"] == k["no_related_rate"]
    # Semantic lens companion.
    assert k["semantic"]["n_pos"] == 1
    assert k["semantic"]["verbatim"] == pytest.approx(1.0)
    assert k["semantic"]["ge0_7"] == pytest.approx(1.0)


def test_run_kpis_empty_record_degrades():
    """A record with no joinable rows produces a zero-pair KPI block (the
    runner drops the block when ``n_pairs`` is 0 — the block is best-effort)."""
    record = {"results": [{"filename": "Doc Z.pdf", "predicted": {}}]}
    gt = {normalize_filename("Doc A.pdf"): {"Anti-Assignment": ["x"]}}
    k = run_kpis(record, gt, categories=["Anti-Assignment"])
    assert k["n_pairs"] == 0
    assert k["n_positive"] == 0
    assert k["f1"] == 0.0
    assert k["jaccard_mean"] == 0.0
