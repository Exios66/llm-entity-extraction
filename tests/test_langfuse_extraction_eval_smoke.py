"""End-to-end smoke test of the LANGFUSE MIRROR extraction eval loop
(no network, no LLM): one contracts_specialist observation per row with the
specialist's designated task scores, and the repo experiment log record
tagged ``tracing_backend: langfuse``."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from tests.test_langfuse_chained_eval_smoke import CUAD_LABELS
from tests.test_langfuse_tracing import StubLangfuse


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


@pytest.fixture
def fake_langfuse_extraction(monkeypatch):
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")

    calls = {"extractor": 0}

    def fake_extract(self, doc_text):
        calls["extractor"] += 1
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

    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.extract", fake_extract)
    stub.calls = calls
    return stub


def _dataset_row():
    return {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "expected_fields": {"key_obligations": ["GT-SENTINEL-secret-obligation"]}, "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }


def test_langfuse_extraction_loop_wiring(fake_langfuse_extraction, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_extraction_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "contracts_specialist_v4",
        "--experiment-name", "smoke_langfuse_extraction",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert fake_langfuse_extraction.calls["extractor"] == 1
    names = [s.kwargs["name"] for s in fake_langfuse_extraction.spans]
    assert names == ["contract_entity_extraction", "contracts_specialist"]

    # The specialist's designated task scores attach to ITS observation.
    agent_scores = {s["name"]: s["value"] for s in fake_langfuse_extraction.scores
                    if s.get("observation_id") == "obs-1"}
    assert set(agent_scores) == {"overall_extraction_score", "field_presence",
                                 "overall_verified_precision", "category_presence",
                                 "schema_valid"}
    assert agent_scores["schema_valid"] == 1.0
    assert agent_scores["field_presence"] == 1.0

    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "contract_entity_extraction"
        assert record["prompt_version"] == "contracts_specialist_v4"
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["parameters"]["tracing"]["project"] == "fake-LANGFUSE_PROJECT"
        assert record["scores"]["overall_extraction_score"] >= 0.0
        assert record["scores"]["per_field"]


def test_langfuse_extraction_audit_pass_wiring(fake_langfuse_extraction, monkeypatch, tmp_path):
    """The --audit flag runs the runner-level missed-category audit pass after
    the extraction (KANBAN-060): audit_extraction receives the doc text, the
    predicted extraction, and the chunk window params; the merged output
    flows into the composite; the record's parameters carry audit=True."""
    import scripts.eval.run_langfuse_extraction_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")
    audit_calls = []

    def fake_audit(self, doc_text, extraction, chunk_chars, overlap_chars):
        audit_calls.append((doc_text, extraction, chunk_chars, overlap_chars))
        merged = dict(extraction)
        merged["key_obligations"] = list(extraction.get("key_obligations") or []) + [
            "Neither party shall sue the other under this Agreement.",
        ]
        merged["reasoning"] = {"summary": "audited",
                               "entries": [{"field": "Covenant Not To Sue",
                                            "evidence": "Neither party shall sue the other under this Agreement.",
                                            "section_ref": "audit-pass"}]}
        return merged

    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.audit_extraction",
                        fake_audit)
    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "contracts_specialist_v4",
        "--audit",
        "--chunked",
        "--chunk-chars", "90000",
        "--chunk-overlap", "8000",
        "--experiment-name", "smoke_langfuse_audit",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0
    assert len(audit_calls) == 1
    doc_text, extraction, chunk_chars, overlap_chars = audit_calls[0]
    assert "This Agreement between Acme and Beta" in doc_text
    assert extraction["parties"] == ["Acme Technologies, Inc.", "Beta Holdings Corp."]
    assert chunk_chars == 90000 and overlap_chars == 8000

    record = json.loads(open(tmp_path / "exp.jsonl").read().splitlines()[-1])
    assert record["parameters"]["audit"] is True
    obligations = record["results"][0]["predicted"]["key_obligations"]
    assert any("shall sue the other" in o for o in obligations)


def test_langfuse_extraction_no_audit_by_default(fake_langfuse_extraction, monkeypatch, tmp_path):
    """Without --audit the audit pass never runs."""
    import scripts.eval.run_langfuse_extraction_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")
    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.audit_extraction",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("audit ran")))
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts",
                                "--experiment-name", "smoke_langfuse_no_audit",
                                "--experiment-log", str(tmp_path / "exp.jsonl")])
    assert rc == 0
    record = json.loads(open(tmp_path / "exp.jsonl").read().splitlines()[-1])
    assert record["parameters"]["audit"] is False


def test_langfuse_extraction_dry_run(fake_langfuse_extraction, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_extraction_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
    assert rc == 0
    assert fake_langfuse_extraction.calls["extractor"] == 0


def test_langfuse_extraction_gt_never_leaks_to_model(fake_langfuse_extraction, monkeypatch, tmp_path):
    """Ground truth must never reach the model: expected_fields feeds the
    post-hoc scorer ONLY — the specialist receives raw doc_text and nothing
    else, so no GT content can be copied or parroted."""
    import scripts.eval.run_langfuse_extraction_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    received = []

    def spy_extract(self, doc_text):
        received.append(doc_text)
        return {
            "document_name": "Content License Agreement",
            "parties": ["Acme Technologies, Inc.", "Beta Holdings Corp."],
            "effective_date": "2024-01-15",
            "term_length": "two (2) years",
            "termination_clauses": [],
            "governing_law": "State of Delaware",
            "key_obligations": ["Acme shall not assign this Agreement."],
            "contract_value": None,
            "renewal_terms": None,
            "confidence": 0.8,
        }

    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.extract", spy_extract)
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts",
                                "--sample", "1", "--seed", "42",
                                "--manifest", str(tmp_path / "m.jsonl"),
                                "--experiment-log", str(tmp_path / "exp.jsonl")])
    assert rc == 0
    assert received, "specialist was never called"
    for text in received:
        assert "GT-SENTINEL" not in text
        assert "expected_fields" not in text
