"""Tests for the deterministic Braintrust scorers."""

from src.scorers import (
    ERROR_PREFIX,
    build_scorers,
    exact_match,
    failure,
    macro_accuracy,
    normalize_label,
    per_class_stats,
)


def test_normalize_label_exact():
    assert normalize_label("contract") == "contract"
    assert normalize_label("Contract") == "contract"


def test_normalize_label_from_json():
    assert normalize_label('{"doc_type": "contract", "confidence": 0.9}') == "contract"


def test_normalize_label_snake_variants():
    assert normalize_label("corporate record") == "corporate_record"
    assert normalize_label("court opinion") == "court_opinion"


def test_normalize_label_unrecognized():
    assert normalize_label("banana") == "banana"


def test_exact_match():
    assert exact_match("contract", "contract") == 1.0
    assert exact_match("correspondence", "contract") == 0.0
    assert exact_match("Contract", "contract") == 1.0


def test_failure_sentinel():
    assert failure(f"{ERROR_PREFIX}doc: timeout", "contract") == 1.0
    assert failure("contract", "contract") == 0.0


def test_build_scorers_default_all():
    scorers = build_scorers(None)
    assert {s.__name__ for s in scorers} == {"exact_match", "failure", "cost"}


def test_build_scorers_subset():
    scorers = build_scorers(["exact_match"])
    assert [s.__name__ for s in scorers] == ["exact_match"]


def test_per_class_stats():
    class Row:
        def __init__(self, expected, output):
            self.expected = expected
            self.output = output

    results = [
        Row("contract", "contract"),
        Row("contract", "correspondence"),
        Row("correspondence", "correspondence"),
        Row("correspondence", "contract"),
    ]
    stats = per_class_stats(results)
    assert stats["contract"]["n"] == 2 and stats["contract"]["correct"] == 1
    assert stats["correspondence"]["n"] == 2 and stats["correspondence"]["correct"] == 1
    assert stats["contract"]["accuracy"] == 0.5


def test_macro_accuracy():
    class Row:
        def __init__(self, expected, output):
            self.expected = expected
            self.output = output

    results = [
        Row("contract", "contract"),
        Row("correspondence", "correspondence"),
    ]
    assert macro_accuracy(results) == 1.0
