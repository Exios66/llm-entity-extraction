"""End-to-end smoke test of the CHAINED sorter->extractor eval loop
(no network, no LLM): both agents run per row, the sorter hands off to the
extractor, and both agent trackers are registered/scored."""

from __future__ import annotations

import pytest


class FakeEvalResult:
    def __init__(self, input, expected, output, error=None):
        self.input = input
        self.expected = expected
        self.output = output
        self.error = error


class FakeEvalRun:
    def __init__(self):
        self.kwargs = None
        self.results = []

    def _run(self):
        import inspect

        data_rows = self.kwargs["data"]()
        task = self.kwargs["task"]
        for row in data_rows:
            try:
                output = task(row["input"])
            except Exception as exc:  # noqa: BLE001
                self.results.append(FakeEvalResult(row["input"], row["expected"], None, str(exc)))
                continue
            self.results.append(FakeEvalResult(row["input"], row["expected"], output))
        self.scores = {}
        for scorer in self.kwargs.get("scores", []):
            arity = len(inspect.signature(scorer).parameters)
            values = []
            for r in self.results:
                if r.error is not None:
                    continue
                values.append(scorer(r.output, r.expected))
            self.scores[scorer.__name__] = values
        return self


@pytest.fixture
def fake_chained_eval(monkeypatch):
    run = FakeEvalRun()

    def fake_eval_call(project, *args, **kwargs):
        run.kwargs = kwargs
        run.kwargs["project"] = project
        return run._run()

    import braintrust

    monkeypatch.setattr(braintrust, "Eval", fake_eval_call)
    monkeypatch.setattr(braintrust, "flush", lambda *a, **k: None)
    monkeypatch.setattr("braintrust.integrations.langchain.setup_langchain", lambda *a, **k: True)
    monkeypatch.setattr("scripts.eval.run_chained_eval.setup_langchain", lambda *a, **k: True)

    calls = {"sorter": 0, "extractor": 0}

    def fake_classify_json(self, doc_text, subtype_focus=False):
        assert subtype_focus is True  # the chained task sorts contracts by subtype
        calls["sorter"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "license agreement"}

    def fake_extract(self, doc_text):
        calls["extractor"] += 1
        assert self.handoff_context  # the sorter hands off its classification
        # Default --handoff-scope subtype: the PREDICTED subtype's CUAD
        # field-group cue is part of the handoff (sorter predicts "license").
        assert "Expected field groups for this license agreement family" in self.handoff_context
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
    run.calls = calls
    return run


CUAD_LABELS = [
    {"question": '...related to "Document Name" that...', "answer": "Content License Agreement", "answer_start": 0},
    {"question": '...related to "Parties" that...', "answer": "Acme Technologies, Inc.", "answer_start": 0},
    {"question": '...related to "Parties" that...', "answer": "Beta Holdings Corp.", "answer_start": 0},
    {"question": '...related to "Effective Date" that...', "answer": "January 15, 2024", "answer_start": 0},
    {"question": '...related to "Renewal Term" that...', "answer": "successive one (1) year periods", "answer_start": 0},
    {"question": '...related to "Anti-Assignment" that...', "answer": "shall not assign", "answer_start": 0},
    {"question": '...related to "Governing Law" that...', "answer": "State of Delaware", "answer_start": 0},
]


def test_chained_loop_wiring(fake_chained_eval, monkeypatch, tmp_path):
    import scripts.eval.run_chained_eval as runner

    dataset = {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "expected_fields": {}, "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_chained_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--sorter-prompt-version", "sorter_v1",
        "--extractor-prompt-version", "contracts_specialist_v4",
        "--experiment-name", "smoke_chained",
        "--project-id", "proj-test-0000",
    ])
    assert rc == 0

    # Both agents ran exactly once per row.
    assert fake_chained_eval.calls["sorter"] == 1
    assert fake_chained_eval.calls["extractor"] == 1

    # Wiring: both prompt versions + chained task stamped in metadata.
    assert fake_chained_eval.kwargs["metadata"]["task"] == "chained_sorter_extractor"
    assert fake_chained_eval.kwargs["metadata"]["sorter_prompt"] == "sorter_v1"
    assert fake_chained_eval.kwargs["metadata"]["extractor_prompt"] == "contracts_specialist_v4"

    # Both agents' trackers registered (default overall set).
    names = set(fake_chained_eval.scores)
    for tracker in ("sorter_exact_match", "sorter_subtype_accuracy", "sorter_confidence",
                    "extractor_overall", "extractor_field_presence",
                    "extractor_verified_precision", "extractor_category_presence"):
        assert tracker in names

    # The sorter classified the CUAD folder correctly; the extractor scored.
    row = fake_chained_eval.results[0].output
    assert row["sorter"]["doc_type_ok"] is True
    assert row["sorter"]["subtype_ok"] is True  # License_Agreements -> license
    assert row["extractor"]["overall_score"] > 0.0
    assert row["extractor"]["category_presence"] == 1.0  # anti-assignment clause covered
    assert row["extractor"]["field_presence"] == 1.0
    # The handoff context was asserted inside fake_extract.


def test_chained_ground_truth_ablation(fake_chained_eval, monkeypatch, tmp_path):
    """Issue #1: --handoff-scope ground_truth runs the specialist TWICE per
    doc (predicted-subtype cue + ground-truth-subtype cue) and records the
    sorter-vs-specialist loss split under scores.ablation."""
    import json as _json

    import scripts.eval.run_chained_eval as runner

    dataset = {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "expected_fields": {}, "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_chained_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--sorter-prompt-version", "sorter_v1",
        "--extractor-prompt-version", "contracts_specialist_v4",
        "--handoff-scope", "ground_truth",
        "--experiment-name", "smoke_chained_gt",
        "--project-id", "proj-test-0000",
    ])
    assert rc == 0

    # Both handoff passes ran on the single document.
    assert fake_chained_eval.calls["extractor"] == 2

    # The log record carries the ablation split.
    from pathlib import Path
    import os
    log = Path(os.environ.get("EXPERIMENT_LOG_PATH", tmp_path / "log.jsonl"))
    records = [_json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    record = records[-1]
    assert record["experiment_name"] == "smoke_chained_gt"
    assert record["scores"]["ablation"]["n_docs"] == 1
    assert record["scores"]["ablation"]["sorter_loss_pp"] is not None
    assert "extractor_gt_scores" in record["results"][0]
    assert record["parameters"]["handoff_scope"] == "ground_truth"
