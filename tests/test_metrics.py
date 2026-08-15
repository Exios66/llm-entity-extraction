"""Unit tests for the run-level extraction diagnostics (``src/metrics.py``)
and the master-labels loader (``src/master_labels.py``). Network-free: all
inputs are hand-built rows, no LLM calls.
"""

from __future__ import annotations

import pytest

from src.field_scoring import get_field_types
from src.master_labels import load_master_labels, master_answer, resolve_expected_value
from src.metrics import (
    _r2,
    extraction_diagnostics,
    parse_duration_days,
)


@pytest.fixture(scope="module")
def contract_field_types():
    return get_field_types("contract")


# ---------------------------------------------------------------------------
# parse_duration_days
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("two (2) years", 730),            # parenthesized digit wins over the spelled number
    ("thirty (30) days", 30),
    ("three (3) years", 1095),
    ("24 months", 720),
    ("one (1) year", 365),
    ("twelve (12) months", 360),
    ("annual", 365),
    ("annually", 365),
    ("ninety (90) days", 90),
    ("up to another two (2) years", 730),   # leading qualifier ignored, last pair wins
    ("", None),
    (None, None),
    ("until the Closing Date", None),       # no duration unit
    ("perpetual", None),
    (123, None),                            # non-string
])
def test_parse_duration_days(text, expected):
    assert parse_duration_days(text) == expected


# ---------------------------------------------------------------------------
# _r2 (coefficient of determination)
# ---------------------------------------------------------------------------

def test_r2_perfect_fit_is_one():
    assert _r2([(5.0, 5.0), (7.0, 7.0), (9.0, 9.0)]) == pytest.approx(1.0)


def test_r2_mean_predictor_is_zero():
    # Predictions all equal the mean of the expected values -> SS_res == SS_tot.
    pairs = [(5.0, 4.0), (5.0, 6.0), (5.0, 5.0)]
    assert _r2(pairs) == pytest.approx(0.0)


def test_r2_worse_than_mean_is_negative():
    # Off by a constant 100x the spread: worse than predicting the mean.
    pairs = [(104.0, 4.0), (106.0, 6.0), (105.0, 5.0)]
    assert _r2(pairs) < 0.0


def test_r2_partial_explanation():
    # Errors halved vs the mean predictor: SS_res = 0.5, SS_tot = 2 -> R² = 0.75.
    pairs = [(4.5, 4.0), (5.5, 6.0), (5.0, 5.0)]
    r2 = _r2(pairs)
    assert r2 == pytest.approx(0.75)


def test_r2_requires_two_pairs():
    assert _r2([(5.0, 5.0)]) is None
    assert _r2([]) is None


def test_r2_zero_expected_variance_is_undefined():
    # All expected values identical -> SS_tot == 0 -> undefined, not 1.0.
    assert _r2([(5.0, 7.0), (9.0, 7.0)]) is None


# ---------------------------------------------------------------------------
# extraction_diagnostics end-to-end
# ---------------------------------------------------------------------------

def _row(filename, predicted, expected, field_scores=None,
         entity_list_scores=None):
    return {
        "filename": filename,
        "predicted": predicted,
        "expected_fields": expected,
        "field_scores": field_scores or {},
        "entity_list_scores": entity_list_scores or {},
    }


def test_extraction_diagnostics_list_and_field_metrics(contract_field_types):
    rows = [
        _row(
            "doc_a.txt",
            predicted={"parties": ["Acme"], "key_obligations": ["clause 1"]},
            expected={"parties": ["Acme", "Beta"], "key_obligations": ["clause 1"]},
            field_scores={"parties": 0.5, "governing_law": 1.0},
            entity_list_scores={
                "parties": {"precision": 0.5, "recall": 0.5, "f1": 0.5,
                            "n_predicted": 1, "n_expected": 2, "matched": 1},
                "key_obligations": {"precision": 1.0, "recall": 1.0, "f1": 1.0,
                                    "n_predicted": 1, "n_expected": 1, "matched": 1},
            },
        ),
        _row(
            "doc_b.txt",
            predicted={"parties": [], "key_obligations": []},
            expected={"parties": ["Gamma"], "key_obligations": []},
            field_scores={"parties": 0.0, "governing_law": 0.75},
            entity_list_scores={
                "parties": {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                            "n_predicted": 0, "n_expected": 1, "matched": 0},
            },
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types)

    # Field-level error decomposition: exact (governing_law 1.0),
    # partial (governing_law 0.75, parties 0.5), miss (parties 0.0).
    assert metrics["n_fields_scored"] == 4
    assert metrics["field_exact_rate"] == pytest.approx(0.25)
    assert metrics["field_partial_rate"] == pytest.approx(0.5)
    assert metrics["field_miss_rate"] == pytest.approx(0.25)
    assert metrics["error_decomposition"]["parties"] == {
        "exact_rate": 0.0, "partial_rate": 0.5, "miss_rate": 0.5}
    assert metrics["field_presence_per_field"]["parties"] == pytest.approx(0.5)

    # List quality: macro over key_obligations + pooled (micro) over both list fields.
    assert metrics["list_f1"] == pytest.approx(1.0)
    assert metrics["list_micro_f1"] == pytest.approx(2.0 / 3.0, abs=0.0001)  # 2/3 (rounded to 4dp)
    assert metrics["list_micro_n_predicted"] == 2
    assert metrics["list_micro_n_expected"] == 4
    assert metrics["list_micro_matched"] == 2
    assert metrics["entity_list_raw_f1"]["parties"] == pytest.approx(0.25)


def test_extraction_diagnostics_date_mae_and_r2(contract_field_types):
    # Same-surface dates: predicted == expected for doc_a (0 err),
    # doc_b off by exactly 2 years (730 days). MAE = 365, R² < 1.
    rows = [
        _row(
            "doc_a.txt",
            predicted={"effective_date": "2024-01-15"},
            expected={"effective_date": "January 15, 2024"},
        ),
        _row(
            "doc_b.txt",
            predicted={"effective_date": "2024-01-15"},
            expected={"effective_date": "January 15, 2022"},
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types, master=None)
    assert metrics["date_mae_days"] == pytest.approx(365.0)
    assert metrics["date_median_ae_days"] == pytest.approx(365.0)
    assert metrics["date_mae_per_field"]["effective_date"] == pytest.approx(365.0)
    assert metrics["date_r2"] is not None
    assert metrics["date_r2"] < 1.0  # 1 of 2 docs missed


def test_extraction_diagnostics_duration_mae_and_r2(contract_field_types):
    # term_length pairs: (730, 730) err 0, (365, 730) err 365, (1095, 365)
    # err 730 -> MAE 365; expected values vary (730/730/365) so R² is defined.
    rows = [
        _row(
            "doc_a.txt",
            predicted={"term_length": "two (2) years", "renewal_terms": "one (1) year"},
            expected={"term_length": "2 years", "renewal_terms": "one (1) year"},
        ),
        _row(
            "doc_b.txt",
            predicted={"term_length": "one (1) year", "renewal_terms": None},
            expected={"term_length": "2 years", "renewal_terms": None},
        ),
        _row(
            "doc_c.txt",
            predicted={"term_length": "three (3) years", "renewal_terms": None},
            expected={"term_length": "1 year", "renewal_terms": None},
        ),
        # Unparseable prediction: neither MAE nor R² counts it.
        _row(
            "doc_d.txt",
            predicted={"term_length": "until the Closing Date", "renewal_terms": None},
            expected={"term_length": "2 years", "renewal_terms": None},
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types, master=None)
    # term_length errors (0, 365, 730) + renewal_terms error (0) pooled -> 273.75.
    assert metrics["duration_mae_days"] == pytest.approx(273.75)
    assert metrics["duration_mae_per_field"]["term_length"] == pytest.approx(365.0)
    assert metrics["duration_r2"] is not None
    assert metrics["duration_r2"] < 1.0
    # renewal_terms has ONE parseable pair (doc_a) -> per-field R² is None
    # (explicitly present, undefined), MAE still reported.
    assert metrics["duration_mae_per_field"]["renewal_terms"] == pytest.approx(0.0)
    assert metrics["duration_r2_per_field"]["renewal_terms"] is None


def test_extraction_diagnostics_date_duration_crossover(contract_field_types):
    # term_length expected text is sometimes an expiration DATE: it feeds the
    # date MAE/R² buckets, not the duration buckets. Dates vary across docs
    # so the date R² is defined (both docs exact -> 1.0).
    rows = [
        _row(
            "doc_a.txt",
            predicted={"term_length": "shall terminate on June 30, 2010",
                       "effective_date": "2010-06-30"},
            expected={"term_length": "shall terminate on June 30, 2010",
                      "effective_date": "June 30, 2010"},
        ),
        _row(
            "doc_b.txt",
            predicted={"term_length": "shall terminate on June 30, 2012",
                       "effective_date": "2012-06-30"},
            expected={"term_length": "shall terminate on June 30, 2012",
                      "effective_date": "June 30, 2012"},
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types, master=None)
    assert "duration_mae_days" not in metrics
    assert "duration_r2" not in metrics
    assert metrics["date_mae_days"] == 0.0
    assert metrics["date_r2"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# money MAE + span-count drift
# ---------------------------------------------------------------------------

def test_extraction_diagnostics_money_mae(contract_field_types):
    rows = [
        _row(
            "doc_a.txt",
            predicted={"contract_value": "$10,000,000"},
            expected={"contract_value": "$10,000,000"},
        ),
        _row(
            "doc_b.txt",
            predicted={"contract_value": "$10,000,001"},
            expected={"contract_value": "$10,000,000"},
        ),
        # Unparseable prediction: excluded from the MAE pairs.
        _row(
            "doc_c.txt",
            predicted={"contract_value": "TBD at signing"},
            expected={"contract_value": "$10,000,000"},
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types, master=None)
    assert metrics["money_mae_usd"] == pytest.approx(0.5)
    assert metrics["money_median_ae_usd"] == pytest.approx(0.5)
    assert metrics["money_mae_per_field"]["contract_value"] == pytest.approx(0.5)
    assert metrics["money_n_pairs"] == 2


def test_extraction_diagnostics_span_count_drift(contract_field_types):
    rows = [
        _row(
            "doc_a.txt",
            predicted={"key_obligations": ["a", "b", "c"]},
            expected={"key_obligations": ["a", "b"]},
            entity_list_scores={
                "key_obligations": {"precision": 2 / 3, "recall": 1.0, "f1": 0.8,
                                    "n_predicted": 3, "n_expected": 2, "matched": 2},
            },
        ),
        _row(
            "doc_b.txt",
            predicted={"key_obligations": ["a"]},
            expected={"key_obligations": ["a", "b", "c"]},
            entity_list_scores={
                "key_obligations": {"precision": 1.0, "recall": 1 / 3, "f1": 0.5,
                                    "n_predicted": 1, "n_expected": 3, "matched": 1},
            },
        ),
    ]
    metrics = extraction_diagnostics(rows, contract_field_types, master=None)
    # Drift: +1 and -2 -> symmetric MAE = 1.5, signed mean = -0.5 (net
    # under-extraction on this surface).
    assert metrics["span_count_mae"] == pytest.approx(1.5)
    assert metrics["span_count_signed_mean"] == pytest.approx(-0.5)
    assert metrics["span_count_mae_per_field"]["key_obligations"] == pytest.approx(1.5)
    assert metrics["span_count_signed_mean_per_field"]["key_obligations"] == \
        pytest.approx(-0.5)
    assert metrics["span_count_n_docs"] == 2


def test_extraction_diagnostics_support_sizes(contract_field_types):
    # Support sizes are always present (0 when no pairs) so the experiment
    # log can show how much evidence each MAE/R² row rests on.
    metrics = extraction_diagnostics([], contract_field_types, master=None)
    assert metrics["date_n_pairs"] == 0
    assert metrics["duration_n_pairs"] == 0
    assert metrics["money_n_pairs"] == 0
    assert "span_count_n_docs" not in metrics


# ---------------------------------------------------------------------------
# master_labels
# ---------------------------------------------------------------------------

def test_master_labels_load_and_resolve(tmp_path):
    csv_path = tmp_path / "master_clauses.csv"
    csv_path.write_text(
        "Filename,Effective Date-Answer,Renewal Term-Answer,Parties-Answer\n"
        '"AGREEMENT FINAL (1).pdf","5/8/14","2 years","Acme"\n'
        '"OTHER DOC.PDF","","",""\n'
    )
    master = load_master_labels(csv_path)
    # Rows with no non-empty answers still register (existence marker), so
    # both CSVs rows are present.
    assert len(master) == 2
    assert master_answer(master, "AGREEMENT FINAL (1).pdf", "Effective Date") == "5/8/14"
    # Filename join is case/punctuation-insensitive.
    assert master_answer(master, "agreement_final_1.pdf", "Effective Date") == "5/8/14"
    # Empty-answer row: no answers, so every lookup falls back.
    assert master["otherdoc"] == {}
    assert master_answer(master, "OTHER DOC.PDF", "Effective Date") is None
    # Fallback to the raw clause-label text when no master answer exists.
    assert resolve_expected_value(master, "OTHER DOC.PDF", "Effective Date",
                                  "7th day of September, 1999.") == \
        "7th day of September, 1999."
    assert master_answer(master, "UNKNOWN.pdf", "Effective Date") is None


def test_master_labels_missing_file_degrades():
    assert load_master_labels("/nonexistent/master_clauses.csv") == {}
    import os

    from src.master_labels import DEFAULT_MASTER_LABELS
    if not os.path.exists(DEFAULT_MASTER_LABELS):
        assert load_master_labels(None) == {}  # default sibling path absent
