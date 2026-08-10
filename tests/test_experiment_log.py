"""Unit tests for the repo experiment log (src/experiment_log.py)."""

from __future__ import annotations

import json

import pytest


def test_append_experiment_writes_one_json_line(tmp_path):
    from src.experiment_log import append_experiment

    path = tmp_path / "logs" / "experiment_log.jsonl"
    record = {
        "type": "experiment",
        "experiment_name": "smoke_exp",
        "model": "qwen/qwen3.7-flash",
        "scores": {"overall_extraction_score": 0.42},
        "results": [{"filename": "a.txt", "status": "completed"}],
    }
    written = append_experiment(record, path)
    assert written == path
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["experiment_name"] == "smoke_exp"
    assert "timestamp" in parsed  # stamped automatically
    assert parsed["results"][0]["filename"] == "a.txt"


def test_append_experiment_is_append_only(tmp_path):
    from src.experiment_log import append_experiment

    path = tmp_path / "experiment_log.jsonl"
    append_experiment({"experiment_name": "first"}, path)
    append_experiment({"experiment_name": "second"}, path)
    names = [json.loads(line)["experiment_name"]
             for line in path.read_text().strip().splitlines()]
    assert names == ["first", "second"]


def test_tokens_summary_aggregates_usage():
    from src.experiment_log import tokens_summary

    usage = [
        {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "cost": 0.01},
        {"prompt_tokens": 200, "completion_tokens": 30, "total_tokens": 230, "cost": 0.02},
        {},  # replayed-from-manifest rows carry no usage
    ]
    summary = tokens_summary(usage)
    assert summary["prompt_tokens"] == 300
    assert summary["completion_tokens"] == 80
    assert summary["total_tokens"] == 380
    assert summary["cost_total_usd"] == pytest.approx(0.03)
    assert summary["rows_with_usage"] == 2


def test_append_markdown_renders_section(tmp_path):
    from src.experiment_log import append_markdown

    md_path = tmp_path / "experiment_log.md"
    record = {
        "experiment_name": "exp_1",
        "task": "contract_entity_extraction",
        "model": "m",
        "scores": {"overall_extraction_score": 0.5},
        "tokens": {"total_tokens": 10},
        "results": [
            {"filename": "a.pdf", "status": "completed", "overall_score": 0.5},
            {"filename": "b.pdf", "status": "error", "error": "boom"},
        ],
    }
    append_markdown(record, md_path)
    text = md_path.read_text()
    assert "## exp_1" in text
    assert "contract_entity_extraction" in text
    assert "a.pdf" in text
    assert "b.pdf" in text
    assert "boom" in text


def test_renderer_includes_judge_review_section(monkeypatch, tmp_path):
    import json as _json

    import src.experiment_log as el

    judgments_dir = tmp_path / "judgments"
    judgments_dir.mkdir()
    monkeypatch.setattr(el, "JUDGMENTS_DIR", judgments_dir)

    record = {
        "experiment_name": "exp_judged",
        "task": "subtype_classification",
        "model": "m",
        "scores": {"sorter": {
            "subtype_accuracy": 0.5,
            "failure_insights": {"mode_counts": {"family_confusion": 1}, "n_failed": 1,
                                 "failures": [{"filename": "a.pdf", "expected": "license",
                                               "predicted": "franchise", "mode": "family_confusion",
                                               "equiv_recovered": False, "reasoning": "title says franchise"}]},
        }},
        "results": [{"filename": "a.pdf", "status": "completed",
                     "sorter": {"doc_type": "contract", "contract_subtype": "franchise",
                                "expected_subtype": "license", "subtype_ok": False,
                                "subtype_ok_equiv": False, "confidence": 0.9,
                                "failure_mode": "family_confusion",
                                "reasoning": "title says franchise"}}],
    }
    (judgments_dir / "exp_judged.jsonl").write_text(_json.dumps({
        "filename": "a.pdf", "expected_subtype": "license", "predicted_subtype": "franchise",
        "judgment": {"classification_correct": "correct", "classification_quality": 0.9,
                     "reasoning": "The document IS a franchise agreement — the folder mislabels it."},
    }) + "\n")

    md = el.experiment_markdown(record)
    assert "### Failed classification insights" in md
    assert "family_confusion" in md
    assert "### Judge agent review (post hoc)" in md
    assert "correct" in md and "quality 0.9" in md
    assert "folder mislabels" in md


def test_default_paths_read_env(monkeypatch, tmp_path):
    from src.experiment_log import default_jsonl_path, default_md_path

    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(tmp_path / "l.jsonl"))
    monkeypatch.setenv("EXPERIMENT_LOG_MD_PATH", str(tmp_path / "l.md"))
    assert default_jsonl_path() == tmp_path / "l.jsonl"
    assert default_md_path() == tmp_path / "l.md"


def test_git_snapshot_runs_in_repo():
    from src.experiment_log import git_snapshot

    snapshot = git_snapshot()
    assert "commit" in snapshot
    assert isinstance(snapshot["commit"], str) and snapshot["commit"]
    assert isinstance(snapshot["dirty"], bool)


def test_experiment_markdown_renders_score_tables():
    from src.experiment_log import experiment_markdown

    record = {
        "experiment_name": "exp_scores",
        "task": "contract_entity_extraction",
        "model": "m",
        "scores": {
            "overall_extraction_score": 0.8123,
            "field_presence": 0.9,
            "per_field": {"parties": 0.5, "governing_law": 1.0},
            "entity_list_f1": {"parties": 0.5},
        },
        "results": [
            {"filename": "a.pdf", "status": "completed", "overall_score": 0.8123,
             "field_presence": 0.9, "schema_valid": 1.0,
             "field_scores": {"parties": 0.5, "governing_law": 1.0},
             "entity_list_f1": {"parties": 0.5}},
            {"filename": "b.pdf", "status": "completed", "overall_score": 0.6,
             "field_presence": 1.0, "schema_valid": 1.0,
             "field_scores": {"parties": 1.0, "governing_law": 1.0},
             "entity_list_f1": {"parties": 1.0}},
        ],
    }
    text = experiment_markdown(record)
    # Headline scores lead, then per-field breakdown tables.
    assert "| overall_extraction_score | 0.8123 |" in text
    assert "**Scores — per_field**" in text
    # Full scoring calculation: document x field matrix with a mean column.
    assert "Per-field content scores (document x field)" in text
    assert "| parties | 0.5 | 1 |" in text
    assert "| mean |" in text


def test_experiment_markdown_renders_confusion_matrix():
    from src.experiment_log import experiment_markdown

    record = {
        "experiment_name": "exp_class",
        "task": "sorter_classification",
        "results": [
            {"filename": "a", "status": "completed", "expected": "contract",
             "predicted": "contract", "correct": True},
            {"filename": "b", "status": "completed", "expected": "contract",
             "predicted": "correspondence", "correct": False},
            {"filename": "c", "status": "completed", "expected": "correspondence",
             "predicted": "correspondence", "correct": True},
        ],
    }
    text = experiment_markdown(record)
    assert "Confusion matrix (expected x predicted)" in text
    assert "| contract | **1** | 1 |" in text
    assert "| correspondence | 0 | **1** |" in text


def test_render_full_log_has_index_and_sections():
    from src.experiment_log import render_full_log

    records = [
        {"experiment_name": "one", "task": "t1", "model": "m",
         "scores": {"exact_match": 0.5}, "n_rows": 2,
         "tokens": {"total_tokens": 100},
         "results": [{"filename": "a", "status": "completed"}]},
        {"experiment_name": "two", "task": "t2", "model": "m",
         "scores": {"overall_extraction_score": 0.75}, "n_rows": 3,
         "tokens": {"total_tokens": 200},
         "results": [{"filename": "b", "status": "completed"}]},
    ]
    text = render_full_log(records)
    assert text.startswith("# Experiment Log")
    assert "## Index" in text
    assert "| 1 | one |" in text
    assert "| 2 | two |" in text
    assert "## one  (t1)" in text
    assert "## two  (t2)" in text
