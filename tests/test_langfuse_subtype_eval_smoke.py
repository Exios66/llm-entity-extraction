"""End-to-end smoke test of the LANGFUSE MIRROR subtype eval loop
(no network, no LLM): the same one-sorter-call-per-PDF task as the Braintrust
runner, the same deterministic logic scorers — but every row traced into a
stubbed Langfuse client, and the repo experiment log record tagged with
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
def fake_langfuse_mirror(monkeypatch, tmp_path):
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")

    calls = {"sorter": 0}

    def fake_classify_json(self, doc_text, **kwargs):
        calls["sorter"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "license agreement"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)
    stub.calls = calls
    return stub


def test_langfuse_subtype_loop_wiring(fake_langfuse_mirror, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_subtype_eval as runner

    dataset = {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_subtype_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    manifest = tmp_path / "manifest.jsonl"
    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--sorter-prompt-version", "sorter_v5",
        "--experiment-name", "smoke_langfuse_subtype",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(manifest),
    ])
    assert rc == 0

    # The sorter ran EXACTLY once per PDF, traced into the stub client.
    assert fake_langfuse_mirror.calls["sorter"] == 1
    assert len(fake_langfuse_mirror.spans) == 1
    span = fake_langfuse_mirror.spans[0]
    assert span.kwargs["name"] == "subtype_classification"
    assert span.kwargs["input"]["filename"] == "cuad_doc_01.txt"
    assert span.kwargs["input"]["expected"] == "license"
    assert span.kwargs["input"]["prompt_version"] == "sorter_v5"
    # Root observation carries the composite output.
    assert span.updates[-1]["output"]["sorter"]["subtype_ok"] is True

    # The SAME deterministic logic scorers as the Braintrust runner, per trace.
    score_names = sorted(s["name"] for s in fake_langfuse_mirror.scores)
    assert score_names == ["confidence", "exact_match",
                           "subtype_accuracy", "subtype_accuracy_equiv"]
    by_name = {s["name"]: s["value"] for s in fake_langfuse_mirror.scores}
    assert by_name["exact_match"] == 1.0
    assert by_name["subtype_accuracy"] == 1.0
    assert by_name["subtype_accuracy_equiv"] == 1.0
    assert by_name["confidence"] == 0.95

    # Manifest checkpoint written (durability: resume is honored).
    lines = manifest.read_text().splitlines()
    assert json.loads(lines[0])["metadata"]["tracing_backend"] == "langfuse"
    assert len(lines) == 2  # header + one completed row

    # The repo experiment log record mirrors the Braintrust format + backend.
    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "subtype_classification"
        assert record["prompt_versions"] == {"sorter": "sorter_v5"}
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["parameters"]["tracing"]["project"] == "fake-LANGFUSE_PROJECT"
        assert record["parameters"]["tracing"]["environment"] == "fake-LANGFUSE_ENVIRONMENT"
        assert record["parameters"]["tracing"]["disabled"] is False
        assert record["scores"]["sorter"]["subtype_accuracy"] == 1.0
        assert record["scores"]["sorter"]["per_subtype"]["license"]["correct"] == 1
        assert record["scores"]["sorter"]["confusion_matrix"]["license"]["license"] == 1


def test_langfuse_runner_dry_run(fake_langfuse_mirror, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_subtype_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_subtype_eval.load_braintrust_dataset",
                        lambda *a, **k: [{
                            "filename": "cuad_doc_01.txt", "expected": "contract",
                            "doc_text": "x", "metadata": {"category": "License_Agreements"},
                        }])
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
    assert rc == 0
    assert fake_langfuse_mirror.calls["sorter"] == 0
    assert fake_langfuse_mirror.spans == []
