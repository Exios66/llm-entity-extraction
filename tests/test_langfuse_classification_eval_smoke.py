"""End-to-end smoke test of the LANGFUSE MIRROR doc-type classification eval
(no network, no LLM): one sorter observation per row with the sorter's
designated task scores, and the repo experiment log record tagged
``tracing_backend: langfuse``."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from tests.test_langfuse_tracing import StubLangfuse


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


@pytest.fixture
def fake_langfuse_classification(monkeypatch):
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")

    calls = {"sorter": 0}

    def fake_classify_json(self, doc_text):
        calls["sorter"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "an agreement"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)
    stub.calls = calls
    return stub


def _dataset_row():
    return {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }


def test_langfuse_classification_loop_wiring(fake_langfuse_classification, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "sorter_v6",
        "--experiment-name", "smoke_langfuse_classification",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert fake_langfuse_classification.calls["sorter"] == 1
    names = [s.kwargs["name"] for s in fake_langfuse_classification.spans]
    assert names == ["doc_type_classification", "sorter"]

    # The sorter's designated task scores attach to ITS observation.
    agent_scores = {s["name"]: s["value"] for s in fake_langfuse_classification.scores
                    if s.get("observation_id") == "obs-1"}
    assert set(agent_scores) == {"exact_match", "confidence"}
    assert agent_scores["exact_match"] == 1.0
    assert agent_scores["confidence"] == 0.95

    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "sorter_classification"
        assert record["prompt_version"] == "sorter_v6"
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["parameters"]["input_mode"] == "text"
        assert record["scores"]["exact_match"] == 1.0
        assert record["scores"]["per_class_accuracy"]["contract"] == 1.0


def test_langfuse_classification_dry_run(fake_langfuse_classification, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
    assert rc == 0
    assert fake_langfuse_classification.calls["sorter"] == 0
