"""Tests for the eval runner config/planning (no network, no LLM)."""

import pytest

from scripts.eval.run_classification_eval import sample_balanced, parse_scorers
from scripts.eval.run_multiclass_eval import sample_balanced as sample_balanced_multiclass
from src.evaluation import validate_dataset


def test_parse_scorers():
    assert parse_scorers(None) is None
    assert parse_scorers("exact_match,failure") == ["exact_match", "failure"]
    assert parse_scorers("none") == []
    assert parse_scorers("") == []


def test_sample_balanced(sample_dataset_rows):
    rows = [dict(r) for r in sample_dataset_rows]
    rows += [dict(r, filename=f"dup_{i}.txt") for i, r in enumerate(sample_dataset_rows)]
    sampled = sample_balanced(rows, samples_per_class=2, seed=42)
    validate_dataset(sampled)
    from collections import Counter

    assert Counter(s["expected"] for s in sampled)["contract"] == 2
    assert len(sampled) == 8


def test_sample_balanced_respects_seed(sample_dataset_rows):
    a = sample_balanced(sample_dataset_rows, samples_per_class=1, seed=7)
    b = sample_balanced(sample_dataset_rows, samples_per_class=1, seed=7)
    assert [r["filename"] for r in a] == [r["filename"] for r in b]


def test_multiclass_sample_balanced(sample_dataset_rows):
    sampled = sample_balanced_multiclass(sample_dataset_rows, samples_per_class=1, seed=1)
    assert len(sampled) == 4


def test_dry_run_planning(tmp_path, monkeypatch):
    """The eval runner's dry-run path resolves config and dataset without APIs."""
    import scripts.eval.run_classification_eval as runner

    # Use a local documents dir so no Braintrust dataset call is made.
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("AGREEMENT between parties. " * 20)

    def fake_require_env(*names):
        return tuple("fake-" + n for n in names)

    monkeypatch.setattr(runner, "require_env", fake_require_env)
    rc = runner.main_with_args([
        "--documents-dir", str(docs),
        "--expected", "contract",
        "--prompt-version", "sorter_v0",
        "--dry-run",
    ])
    assert rc == 0


def test_dry_run_rejects_unknown_prompt(tmp_path, monkeypatch, capsys):
    import scripts.eval.run_classification_eval as runner

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("x" * 500)
    monkeypatch.setattr(runner, "require_env", lambda *n: tuple("k" for _ in n))
    with pytest.raises(SystemExit):
        runner.main_with_args([
            "--documents-dir", str(docs),
            "--expected", "contract",
            "--prompt-version", "no_such_version",
            "--dry-run",
        ])
    assert "Unknown prompt version" in capsys.readouterr().err
