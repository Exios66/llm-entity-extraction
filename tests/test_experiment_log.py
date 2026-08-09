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
