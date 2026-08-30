"""Network-free smoke of the Enron correspondence eval scaffold (KANBAN-103).

Covers: GT/blind join (no answer-key leak into sorter text), subclass
stratification, sentiment scoring against the Hub GT assortment, predicted-
field alignment, and ``main_with_args --dry-run`` / a mocked live loop.
"""

from __future__ import annotations

import json

import pytest

from agents.sorter_agent import (
    CORRESPONDENCE_EVAL_SCHEMA,
    SENTIMENT_LABELS,
    normalize_sentiment_label,
    normalize_sentiment_score,
    sentiment_label_from_score,
)
from src.correspondence_eval import (
    CORRESPONDENCE_DOC_TYPE,
    GT_FIELDS,
    PREDICTED_FIELDS,
    compose_doc_text,
    filter_correspondence,
    join_blind_and_gt,
    predicted_aligns_with_gt,
    score_sentiment,
    stratified_by_subclass,
)
from src.prompts import get_prompt, list_prompts


# --- schema / prompt / field alignment --------------------------------------


def test_correspondence_eval_schema_carries_sentiment_and_docclass():
    props = CORRESPONDENCE_EVAL_SCHEMA["properties"]
    assert "doc_type" in props
    assert "doc_subclass" in props
    assert "sentiment_score" in props
    assert "sentiment_label" in props
    assert set(props["sentiment_label"]["enum"]) == set(SENTIMENT_LABELS)
    assert props["sentiment_score"]["minimum"] == -1.0
    assert props["sentiment_score"]["maximum"] == 1.0


def test_correspondence_prompt_registered_and_derives_from_v7():
    assert "sorter_docclass_correspondence_v0" in list_prompts()
    prompt = get_prompt("sorter_docclass_correspondence_v0")
    v7 = get_prompt("sorter_docclass_v7")
    assert prompt.startswith(v7[:300])
    assert "44. CORRESPONDENCE SENTIMENT" in prompt
    assert "sentiment_score" in prompt
    assert "sentiment_label" in prompt
    assert "44. CORRESPONDENCE SENTIMENT" not in v7


def test_predicted_fields_align_with_gt_assortment():
    assert PREDICTED_FIELDS == (
        "doc_type", "doc_subclass", "sentiment_label", "sentiment_score")
    assert GT_FIELDS == (
        "expected", "expected_subclass", "sentiment_label", "sentiment_score")
    aligned = predicted_aligns_with_gt(
        {"doc_type": "correspondence", "doc_subclass": "memo",
         "sentiment_label": "positive", "sentiment_score": 0.4},
        {"expected": "correspondence", "expected_subclass": "memo",
         "sentiment_label": "positive", "sentiment_score": 0.4},
    )
    assert aligned["doc_type"]["ok"] is True
    assert aligned["doc_subclass"]["ok"] is True
    assert aligned["sentiment_label"]["ok"] is True


def test_join_does_not_put_gt_in_doc_text():
    blind = [{
        "filename": "a/1.",
        "subject": "Lunch",
        "text": "See you at noon.",
        "metadata": {"custodian": "allen-p"},
    }]
    gt = [{
        "filename": "a/1.",
        "expected": "correspondence",
        "expected_subclass": "email",
        "sentiment_score": 0.2,
        "sentiment_label": "positive",
        "content_topic": "general_business",
        "label_evidence": "ordinary email",
        "sentiment_evidence": "lunch",
        "split": "train",
    }]
    rows = join_blind_and_gt(blind, gt)
    assert len(rows) == 1
    row = rows[0]
    assert row["expected"] == CORRESPONDENCE_DOC_TYPE
    assert row["expected_subclass"] == "email"
    assert row["sentiment_label"] == "positive"
    assert "positive" not in row["doc_text"]
    assert "ordinary email" not in row["doc_text"]
    assert "Subject: Lunch" in row["doc_text"]
    assert "See you at noon." in row["doc_text"]


def test_join_drops_non_correspondence_and_empty_bodies():
    blind = [
        {"filename": "c/1.", "subject": "", "text": ""},
        {"filename": "c/2.", "subject": "Hi", "text": "Hello"},
        {"filename": "k/1.", "subject": "K", "text": "contract text"},
    ]
    gt = [
        {"filename": "c/1.", "expected": "correspondence", "expected_subclass": "email",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
        {"filename": "c/2.", "expected": "correspondence", "expected_subclass": "letter",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
        {"filename": "k/1.", "expected": "contract", "expected_subclass": "license",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
    ]
    rows = join_blind_and_gt(blind, gt)
    assert [r["filename"] for r in rows] == ["c/2."]
    assert filter_correspondence(rows) == rows


def test_stratified_by_subclass_covers_every_class():
    rows = []
    for sub, n in (("email", 40), ("memo", 10), ("demand", 5),
                   ("attorney_demand", 3)):
        for i in range(n):
            rows.append({
                "filename": f"{sub}_{i}",
                "expected": "correspondence",
                "expected_subclass": sub,
                "doc_text": f"{sub} body {i}",
            })
    sample = stratified_by_subclass(rows, 16, seed=42)
    assert len(sample) == 16
    classes = {r["expected_subclass"] for r in sample}
    assert classes == {"email", "memo", "demand", "attorney_demand"}
    # Tiny class contributes every available row, not more.
    assert sum(1 for r in sample if r["expected_subclass"] == "attorney_demand") == 3
    # Deterministic.
    assert [r["filename"] for r in sample] == [
        r["filename"] for r in stratified_by_subclass(rows, 16, seed=42)
    ]


def test_sentiment_scoring_band_and_label():
    hit = score_sentiment(0.10, "neutral", 0.0, "neutral")
    assert hit["sentiment_label_ok"] is True
    assert hit["sentiment_score_ok"] is True
    assert hit["sentiment_score_mae"] == pytest.approx(0.10)

    miss = score_sentiment(-0.9, "negative", 0.8, "positive")
    assert miss["sentiment_label_ok"] is False
    assert miss["sentiment_score_ok"] is False
    assert miss["sentiment_score_mae"] == pytest.approx(1.7)

    derived = score_sentiment(-0.4, None, -0.5, "negative")
    assert derived["sentiment_label"] == "negative"
    assert derived["sentiment_label_ok"] is True


def test_sentiment_normalizers():
    assert normalize_sentiment_label("Positive") == "positive"
    assert normalize_sentiment_label("meh") is None
    assert normalize_sentiment_score(1.5) == 1.0
    assert normalize_sentiment_score(-2) == -1.0
    assert sentiment_label_from_score(-0.2) == "negative"
    assert sentiment_label_from_score(0.0) == "neutral"
    assert sentiment_label_from_score(0.2) == "positive"


def test_compose_doc_text():
    assert compose_doc_text("Re: Q3", "Please send the report.") == (
        "Subject: Re: Q3\n\nPlease send the report."
    )
    assert compose_doc_text("", "body only") == "body only"


# --- runner smoke -----------------------------------------------------------


@pytest.fixture
def dump_path(tmp_path):
    rows = [
        {"filename": "e1", "subject": "Hi", "doc_text": "Subject: Hi\n\nSee you.",
         "expected": "correspondence", "expected_subclass": "email",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
        {"filename": "m1", "subject": "Memo", "doc_text": "TO: all\nFROM: legal\nRE: policy",
         "expected": "correspondence", "expected_subclass": "memo",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
        {"filename": "d1", "subject": "Demand", "doc_text": "We demand payment of $5000.",
         "expected": "correspondence", "expected_subclass": "demand",
         "sentiment_label": "negative", "sentiment_score": -0.6},
        {"filename": "skip_contract", "doc_text": "THIS AGREEMENT",
         "expected": "contract", "expected_subclass": "license",
         "sentiment_label": "neutral", "sentiment_score": 0.0},
    ]
    path = tmp_path / "enron.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return path


def test_local_dump_filters_to_correspondence(dump_path):
    from scripts.datasets.load_enron_correspondence import load_local_jsonl

    rows = load_local_jsonl(dump_path)
    assert {r["filename"] for r in rows} == {"e1", "m1", "d1"}
    assert all(r["expected"] == "correspondence" for r in rows)


def test_correspondence_eval_dry_run(dump_path, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-bt-test")
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("EXPERIMENT_LOG_MD_PATH", str(tmp_path / "log.md"))

    from scripts.eval.run_correspondence_eval import main_with_args

    code = main_with_args([
        "--local-dumps", str(dump_path),
        "--stratified", "3",
        "--seed", "42",
        "--dry-run",
        "--no-braintrust-logging",
        "--experiment-name", "correspondence_smoke_dry",
    ])
    assert code == 0
    assert not (tmp_path / "log.jsonl").exists()


def test_correspondence_eval_mocked_run(dump_path, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("BRAINTRUST_API_KEY", "sk-bt-test")
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("EXPERIMENT_LOG_MD_PATH", str(tmp_path / "log.md"))
    monkeypatch.setenv("PHOENIX_TRACING", "disabled")
    monkeypatch.setenv("BRAINTRUST_LOGGING", "disabled")

    def fake_classify_json(self, doc_text, subtype_focus=False,
                           correspondence_focus=False):
        text = doc_text.upper()
        if "DEMAND" in text:
            subclass, label, score = "demand", "negative", -0.6
        elif "TO:" in text and "FROM:" in text:
            subclass, label, score = "memo", "neutral", 0.0
        else:
            subclass, label, score = "email", "neutral", 0.0
        return {
            "doc_type": "correspondence",
            "contract_subtype": None,
            "doc_subclass": subclass,
            "sentiment_label": label,
            "sentiment_score": score,
            "confidence": 0.9,
            "reasoning": f"{subclass} {label}",
        }

    monkeypatch.setattr(
        "agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)

    from scripts.eval.run_correspondence_eval import main_with_args

    code = main_with_args([
        "--local-dumps", str(dump_path),
        "--stratified", "3",
        "--seed", "42",
        "--no-braintrust-logging",
        "--experiment-name", "correspondence_smoke_run",
        "--manifest", str(tmp_path / "manifest.jsonl"),
        "--max-concurrency", "2",
    ])
    assert code == 0
    records = [json.loads(line) for line in
               (tmp_path / "log.jsonl").read_text().strip().splitlines()]
    assert len(records) == 1
    rec = records[0]
    assert rec["task"] == "correspondence_classification"
    assert rec["experiment_name"] == "correspondence_smoke_run"
    assert rec["prompt_versions"]["sorter"] == "sorter_docclass_correspondence_v0"
    assert rec["scores"]["doc_type_accuracy"] == 1.0
    assert rec["scores"]["subclass_accuracy"] == 1.0
    assert rec["scores"]["sentiment_label_accuracy"] == 1.0
    assert rec["scores"]["correspondence_exact"] == 1.0
    assert rec["scores"]["n_rows"] == 3
    assert rec["scores"]["sorter"]["failure_insights"]["n_failed"] == 0
    md = (tmp_path / "log.md").read_text()
    assert "correspondence_smoke_run" in md
    assert "Per-sentiment-label accuracy" in md
    assert "expected sent." in md
