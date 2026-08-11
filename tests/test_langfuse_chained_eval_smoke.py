"""End-to-end smoke test of the LANGFUSE MIRROR chained eval loop
(no network, no LLM): sorter -> contracts_specialist per row, per-agent
observations with per-agent task scores, the subtype-scoped handoff cue, and
the repo experiment log record tagged ``tracing_backend: langfuse``."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from tests.test_langfuse_tracing import StubLangfuse


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


@pytest.fixture
def fake_langfuse_chained(monkeypatch):
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")

    calls = {"sorter": 0, "extractor": 0, "handoff": []}

    def fake_classify_json(self, doc_text, subtype_focus=False):
        assert subtype_focus is True
        calls["sorter"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "license agreement"}

    def fake_extract(self, doc_text):
        calls["extractor"] += 1
        calls["handoff"].append(self.handoff_context)
        return {
            "document_name": "Content License Agreement",
            "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
            "effective_date": "2024-01-15",
            "term_length": "two (2) years",
            "termination_clauses": ["Either party may terminate for convenience upon sixty days notice."],
            "governing_law": "State of Delaware",
            "key_obligations": [
                "Acme shall pay Beta the sum of one hundred dollars per month.",
                "The Distributor shall not assign this Agreement without prior written consent.",
            ],
            "contract_value": "$100.00 per month",
            "renewal_terms": "auto-renew for successive one (1) year periods",
            "confidence": 0.8,
        }

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)
    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.extract", fake_extract)
    stub.calls = calls
    return stub


CUAD_LABELS = [
    {"question": '...related to "Document Name" that...', "answer": "Content License Agreement", "answer_start": 0},
    {"question": '...related to "Parties" that...', "answer": "Acme Technologies, Inc.", "answer_start": 0},
    {"question": '...related to "Parties" that...', "answer": "Beta Holdings Corp.", "answer_start": 0},
    {"question": '...related to "Effective Date" that...', "answer": "January 15, 2024", "answer_start": 0},
    {"question": '...related to "Renewal Term" that...', "answer": "successive one (1) year periods", "answer_start": 0},
    {"question": '...related to "Anti-Assignment" that...', "answer": "shall not assign", "answer_start": 0},
    {"question": '...related to "Governing Law" that...', "answer": "State of Delaware", "answer_start": 0},
]


def _dataset_row():
    return {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "expected_fields": {}, "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }


def test_langfuse_chained_loop_wiring(fake_langfuse_chained, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_chained_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_chained_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    manifest = tmp_path / "manifest.jsonl"
    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--sorter-prompt-version", "sorter_v1",
        "--extractor-prompt-version", "contracts_specialist_v4",
        "--experiment-name", "smoke_langfuse_chained",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(manifest),
    ])
    assert rc == 0

    # Both agents ran exactly once, each with its OWN traced observation.
    assert fake_langfuse_chained.calls["sorter"] == 1
    assert fake_langfuse_chained.calls["extractor"] == 1
    names = [s.kwargs["name"] for s in fake_langfuse_chained.spans]
    assert names == ["chained_sorter_extractor", "sorter", "contracts_specialist"]

    # The subtype-scoped handoff cue reached the specialist by default.
    handoff = fake_langfuse_chained.calls["handoff"][0]
    assert "Sorter classification: doc_type=contract contract_subtype=license" in handoff
    assert "Expected field groups for this license agreement family" in handoff
    assert "License Grant" in handoff

    # Per-agent task scores attached to the AGENTS' observations.
    sorter_scores = {s["name"]: s for s in fake_langfuse_chained.scores
                     if s.get("observation_id") == "obs-1"}
    specialist_scores = {s["name"]: s for s in fake_langfuse_chained.scores
                         if s.get("observation_id") == "obs-2"}
    assert set(sorter_scores) == {"exact_match", "subtype_accuracy", "confidence"}
    assert sorter_scores["subtype_accuracy"]["value"] == 1.0
    assert set(specialist_scores) == {"overall_extraction_score", "field_presence",
                                      "overall_verified_precision", "category_presence"}
    assert specialist_scores["overall_extraction_score"]["value"] >= 0.0

    # Truncation auditability: the specialist span output carries the flag.
    specialist_span_output = fake_langfuse_chained.spans[2].updates[-1]["output"]
    assert specialist_span_output["truncated"] is False

    # Manifest header carries backend + handoff scope.
    assert json.loads(manifest.read_text().splitlines()[0])["metadata"]["tracing_backend"] == "langfuse"
    assert json.loads(manifest.read_text().splitlines()[0])["metadata"]["handoff_scope"] == "subtype"

    # Repo experiment log record mirrors the Braintrust format + backend.
    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "chained_sorter_extractor"
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["parameters"]["handoff_scope"] == "subtype"
        assert record["scores"]["sorter"]["subtype_accuracy"] == 1.0
        assert record["scores"]["extractor"]["overall_extraction_score"] >= 0.0


def test_langfuse_chained_handoff_none_scope(fake_langfuse_chained, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_chained_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_chained_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(name, f"fake-{name}")

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--sorter-prompt-version", "sorter_v1",
        "--extractor-prompt-version", "contracts_specialist_v4",
        "--experiment-name", "smoke_langfuse_chained_none",
        "--handoff-scope", "none",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0
    handoff = fake_langfuse_chained.calls["handoff"][0]
    assert "Expected field groups" not in handoff
    record = json.loads(open(tmp_path / "exp.jsonl").read().splitlines()[-1])
    assert record["parameters"]["handoff_scope"] == "none"


def test_langfuse_chained_dry_run(fake_langfuse_chained, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_chained_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_chained_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
    assert rc == 0
    assert fake_langfuse_chained.calls["sorter"] == 0
    assert fake_langfuse_chained.spans == []
