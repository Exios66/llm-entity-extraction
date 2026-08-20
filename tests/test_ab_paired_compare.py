"""Smoke tests for the paired same-surface A/B comparator."""

from __future__ import annotations

import json

import pytest

import scripts.reporting.ab_paired_compare as cmp


def _row(filename: str, overall: float, field_scores: dict) -> dict:
    return {"filename": filename, "status": "completed", "error": None,
            "overall_score": overall, "field_scores": field_scores}


def _record(name: str, rows: list[dict], manifest: str) -> dict:
    return {"experiment_name": name, "manifest": manifest,
            "parameters": {"manifest": manifest}, "results": rows}


def test_paired_compare_clear_winner(tmp_path):
    """A deterministic per-document edge produces an excluded-zero CI and the
    BEATS verdict for the challenger."""
    log = tmp_path / "log.jsonl"
    rows_b = [_row(f"doc_{i}.pdf", 0.8, {"key_obligations": 0.7}) for i in range(50)]
    rows_a = [_row(f"doc_{i}.pdf", 0.8 + (0.05 if i < 40 else 0.0),
                   {"key_obligations": 0.7 + (0.1 if i < 40 else 0.0)}) for i in range(50)]
    with log.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(_record("run_a", rows_a, "ma.jsonl")) + "\n")
        fh.write(json.dumps(_record("run_b", rows_b, "mb.jsonl")) + "\n")
    assert cmp.load_record(log, "run_a")["experiment_name"] == "run_a"
    with pytest.raises(SystemExit):
        cmp.load_record(log, "missing")
    # Same manifest on both records must be refused (not an A/B pair).
    same = _record("run_c", rows_a, "ma.jsonl")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(same) + "\n")
    with pytest.raises(SystemExit):
        cmp.main_with_args(["--experiment-a", "run_a", "--experiment-b", "run_c",
                            "--log", str(log)])


def test_paired_compare_verdict_gates(tmp_path, capsys):
    """Inside the noise band the comparator says LOGIC REPAIR, never BEATS."""
    log = tmp_path / "log.jsonl"
    rows_b = [_row(f"doc_{i}.pdf", 0.8, {}) for i in range(50)]
    rows_a = [_row(f"doc_{i}.pdf", 0.8 + (0.004 * ((i % 3) - 1)), {}) for i in range(50)]
    with log.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(_record("run_a", rows_a, "ma.jsonl")) + "\n")
        fh.write(json.dumps(_record("run_b", rows_b, "mb.jsonl")) + "\n")
    rc = cmp.main_with_args(["--experiment-a", "run_a", "--experiment-b", "run_b",
                             "--log", str(log), "--n-boot", "500"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "LOGIC REPAIR" in out
    assert "BEATS" not in out


def test_verdict_helper():
    assert cmp.verdict({"mean": 0.02, "ci_lo": 0.005, "ci_hi": 0.035, "p_win": 0.97}) == "BEATS"
    assert cmp.verdict({"mean": -0.02, "ci_lo": -0.035, "ci_hi": -0.005, "p_win": 0.03}) == "LOSES"
    assert "LOGIC REPAIR" in cmp.verdict({"mean": 0.001, "ci_lo": -0.01, "ci_hi": 0.012, "p_win": 0.55})