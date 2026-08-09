"""Tests for the post-hoc extraction scorer (manifest-based, no Braintrust)."""

import json

from scripts.reporting.score_extraction_manifest import (
    load_manifest,
    render_markdown,
    score_row,
    summarize,
)


def _write_manifest(tmp_path, records):
    path = tmp_path / "run.jsonl"
    lines = [json.dumps({"type": "header", "metadata": {"experiment_name": "x"}})]
    for record in records:
        lines.append(json.dumps(record))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_manifest_skips_header(tmp_path):
    path = _write_manifest(tmp_path, [
        {"filename": "a.txt", "status": "completed", "predicted": {}, "expected_fields": {}},
    ])
    rows = load_manifest(path)
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.txt"


def test_score_row_content_scores():
    record = {
        "filename": "doc1.txt",
        "status": "completed",
        "predicted": {
            "parties": ["Acme Technologies, Inc.", "Sovereign State Bank of Ohio"],
            "governing_law": "State of Delaware",
            "effective_date": "2024-01-15",
            "confidence": 0.8,
        },
        "expected_fields": {
            "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
            "governing_law": "State of Delaware",
            "effective_date": "January 15, 2024",
        },
    }
    row = score_row(record)
    assert row["field_scores"]["governing_law"] == 1.0
    assert row["field_scores"]["effective_date"] == 1.0
    assert row["entity_list_f1"]["parties"] == 0.5
    assert row["field_presence"] == 1.0
    assert row["schema_valid"] == 1.0


def test_score_row_missing_prediction_scores_zero():
    row = score_row({
        "filename": "doc2.txt", "status": "completed",
        "predicted": {}, "expected_fields": {"governing_law": "State of Delaware"},
    })
    assert row["field_scores"]["governing_law"] == 0.0
    assert row["field_presence"] == 0.0


def test_summarize_aggregates(tmp_path):
    path = _write_manifest(tmp_path, [
        {"filename": "a.txt", "status": "completed",
         "predicted": {"governing_law": "Delaware law governs"},
         "expected_fields": {"governing_law": "State of Delaware"}},
        {"filename": "b.txt", "status": "completed",
         "predicted": {"governing_law": "State of Delaware"},
         "expected_fields": {"governing_law": "State of Delaware"}},
        {"filename": "c.txt", "status": "error", "predicted": {}, "expected_fields": {}},
    ])
    rows = [score_row(r) for r in load_manifest(path)]
    summary = summarize(rows)
    assert summary["governing_law"]["n"] == 2
    assert 0.5 < summary["governing_law"]["mean"] < 1.0
    assert summary["field_presence"]["mean"] == 1.0  # both rows populated the field
    assert "overall" in summary


def test_render_markdown_contains_table(tmp_path):
    path = _write_manifest(tmp_path, [
        {"filename": "a.txt", "status": "completed",
         "predicted": {"governing_law": "State of Delaware"},
         "expected_fields": {"governing_law": "State of Delaware"}},
    ])
    rows = [score_row(r) for r in load_manifest(path)]
    md = render_markdown(rows, summarize(rows), path)
    assert "Per-field content scores" in md
    assert "| governing_law |" in md
    assert "| a.txt |" in md
