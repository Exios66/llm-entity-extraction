"""KANBAN-061 — network-free tests for the src/score_emitter.py bridge."""

from __future__ import annotations

import json

import pytest

from llm_dojo_scoring.emitter import LangfuseSink, LocalManifestSink

from src.score_emitter import (
    build_emitter,
    dashboard_names,
    emit_run_scores,
    headline_names,
)


def test_build_emitter_local_sink(tmp_path):
    em = build_emitter(tmp_path / "scores.jsonl")
    sinks = em.sinks
    assert len(sinks) == 1
    assert isinstance(sinks[0], LocalManifestSink)
    em.emit_score("sorter", doc_id="d1", metric_name="f1_macro", value=0.9, run_id="r1")
    lines = (tmp_path / "scores.jsonl").read_text().strip().splitlines()
    assert json.loads(lines[0])["metric"] == "f1_macro"


def test_build_emitter_langfuse_inert_without_keys(monkeypatch, tmp_path):
    import os

    for k in list(os.environ):
        if k.startswith("LANGFUSE"):
            monkeypatch.delenv(k)
    em = build_emitter(tmp_path / "s.jsonl", langfuse=True)
    lf = [s for s in em.sinks if isinstance(s, LangfuseSink)]
    assert len(lf) == 1 and lf[0].available is False
    # local sink still fully functional
    em.emit_score("judge", doc_id="d2", metric_name="accuracy", value=1.0, run_id="r1")
    assert (tmp_path / "s.jsonl").exists()


def test_emit_run_scores_known_and_skipped(tmp_path):
    em = build_emitter(tmp_path / "s.jsonl")
    emitted, skipped = emit_run_scores(
        em,
        "contracts_specialist",
        run_id="run_x",
        metrics={
            "recall": 0.36,
            "cost_per_document": 0.0019,
            "not_a_real_metric": 1.0,
            "none_metric": None,
        },
        metadata={"prompt_version": "v39"},
    )
    assert sorted(emitted) == ["cost_per_document", "recall"]
    assert sorted(skipped) == ["none_metric", "not_a_real_metric"]
    card = em.get_scorecard("contracts_specialist", run_id="run_x", min_tier=3)
    assert card["recall"] == pytest.approx(0.36)


def test_dashboard_and_headline_names():
    assert headline_names("sorter") == ["accuracy", "f1_macro"]
    core = dashboard_names("audit_agent")
    assert "audit_disagreement_rate" in core


def test_bridge_uses_registry_tiers_end_to_end(tmp_path):
    """Emit T0-T3 spread, then prune to a dashboard-default scorecard."""
    em = build_emitter(tmp_path / "s.jsonl")
    for i in range(3):
        emit_run_scores(
            em, "sorter", "r9",
            {"f1_macro": 0.8 + i * 0.05, "confusion_matrix": {"a": 1}, "raw_prediction": "x"},
            doc_id=f"d{i}",
        )
    dash = em.get_scorecard("sorter", run_id="r9", min_tier=1)
    assert "f1_macro" in dash
    assert "raw_prediction" not in dash and "confusion_matrix" not in dash
