"""End-to-end smoke test of the extraction eval loop (no network, no LLM).

Mocks ``braintrust.Eval`` and the specialist so the full runner executes:
dataset loading -> CUAD clause labels -> expected_fields derivation ->
specialist extraction -> deterministic content scoring -> Braintrust scorer
registration -> summary.
"""

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
            for result in self.results:
                if result.error is not None:
                    continue
                values.append(scorer(result.output, result.expected))
            self.scores[scorer.__name__] = values
        return self


CUAD_LABELS = [
    {"question": 'Highlight the parts of this contract related to "Governing Law" that should be reviewed...',
     "answer": "State of Delaware", "answer_start": 0},
    {"question": 'Highlight the parts of this contract related to "Effective Date" that should be reviewed...',
     "answer": "January 15, 2024", "answer_start": 0},
    {"question": 'Highlight the parts of this contract related to "Parties" that should be reviewed...',
     "answer": "Acme Technologies, Inc.", "answer_start": 0},
    {"question": 'Highlight the parts of this contract related to "Parties" that should be reviewed...',
     "answer": "Beta Holdings Corp.", "answer_start": 0},
    {"question": 'Highlight the parts of this contract related to "Termination For Convenience" that should be reviewed...',
     "answer": "Either party may terminate this Agreement for convenience upon sixty (60) days written notice.",
     "answer_start": 0},
]


@pytest.fixture
def fake_extraction_eval(monkeypatch):
    run = FakeEvalRun()

    def fake_eval_call(project, *args, **kwargs):
        run.kwargs = kwargs
        run.kwargs["project"] = project
        return run._run()

    import braintrust

    monkeypatch.setattr(braintrust, "Eval", fake_eval_call)
    monkeypatch.setattr(braintrust, "flush", lambda *a, **k: None)
    monkeypatch.setattr("braintrust.integrations.langchain.setup_langchain", lambda *a, **k: True)
    monkeypatch.setattr("scripts.eval.run_extraction_eval.setup_langchain", lambda *a, **k: True)

    def fake_extract(self, doc_text):
        # A realistic-but-imperfect extraction: governing law exact, parties
        # one right + one wrong, effective date right, termination paraphrase.
        return {
            "parties": ["Acme Technologies, Inc.", "Sovereign State Bank of Ohio"],
            "effective_date": "2024-01-15",
            "term_length": None,
            "termination_clauses": [
                "Either party may terminate this Agreement for convenience upon sixty (60) days written notice."
            ],
            "governing_law": "State of Delaware",
            "key_obligations": [],
            "contract_value": None,
            "renewal_terms": None,
            "confidence": 0.8,
        }

    monkeypatch.setattr("agents.specialist_agents.ContractsSpecialist.extract", fake_extract)
    return run


def test_extraction_loop_wiring(fake_extraction_eval, monkeypatch, tmp_path):
    import scripts.eval.run_extraction_eval as runner

    dataset = {
        "input": {
            "doc_text": "This Agreement is governed by the laws of the State of Delaware.",
            "filename": "cuad_doc_01.txt",
            "expected": "contract",
            "expected_fields": {},
        },
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {
            "doc_type": "contract",
            "clause_labels": CUAD_LABELS,
        },
        "doc_text": "This Agreement is governed by the laws of the State of Delaware.",
        "metadata": {},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))

    def fake_load_dataset(*args, **kwargs):
        return [dict(dataset)]

    monkeypatch.setattr("scripts.eval.run_extraction_eval.load_braintrust_dataset", fake_load_dataset)

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "contracts_specialist_v2",
        "--experiment-name", "smoke_extraction",
        "--project-id", "proj-test-0000",
    ])
    assert rc == 0

    # Wiring: experiment metadata records ground-truth source and scoring mode.
    assert fake_extraction_eval.kwargs["experiment_name"] == "smoke_extraction"
    assert fake_extraction_eval.kwargs["metadata"]["ground_truth"] == "cuad_v1_clause_labels"
    assert fake_extraction_eval.kwargs["metadata"]["scoring"] == "field_type_aware_content_scoring"
    assert fake_extraction_eval.kwargs["metadata"]["prompt_version"] == "contracts_specialist_v2"
    # Scorer economy: ZERO Braintrust scorers registered by default.
    assert fake_extraction_eval.kwargs["metadata"]["bt_scores"] == "none"
    assert fake_extraction_eval.kwargs["scores"] == []

    # Expected fields were derived from the CUAD clause labels.
    row_input = fake_extraction_eval.kwargs["data"]()[0]["input"]
    assert row_input["expected_fields"]["governing_law"] == "State of Delaware"
    assert row_input["expected_fields"]["parties"] == ["Acme Technologies, Inc.", "Beta Holdings Corp."]
    assert row_input["expected_fields"]["effective_date"] == "January 15, 2024"
    assert "termination_clauses" in row_input["expected_fields"]

    # The local content scoring (identical to what the manifest records) is
    # the real signal: governing law exact -> 1.0; parties 1/2 matched
    # (the disjoint-name guard correctly rejects the wrong party).
    from src.field_scoring import score_extraction, get_field_types

    local = score_extraction("contract", get_field_types("contract"),
                             fake_extraction_eval.results[0].output,
                             row_input["expected_fields"])
    assert local.field_scores["governing_law"] == 1.0
    assert local.field_scores["effective_date"] == 1.0
    assert local.entity_list_scores["parties"].f1 == pytest.approx(0.5)
    assert 0.0 < local.overall_score < 1.0
    # Binary conformance: all 4 expected fields populated, schema valid.
    assert fake_extraction_eval.results[0].output.get("confidence") is not None  # normalized


def test_extraction_eval_bt_scores_full(fake_extraction_eval, monkeypatch, tmp_path):
    """--bt-scores full registers the whole per-field set (opt-in burn)."""
    import scripts.eval.run_extraction_eval as runner

    dataset = {
        "input": {"doc_text": "text", "filename": "cuad_doc_01.txt", "expected": "contract",
                  "expected_fields": {}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "text",
        "metadata": {},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "contracts_specialist_v2",
        "--bt-scores", "full",
        "--experiment-name", "smoke_extraction_full",
        "--project-id", "proj-test-0000",
    ])
    assert rc == 0
    names = set(fake_extraction_eval.scores)
    assert "overall_extraction_score" in names
    assert "field_presence" in names
    assert "schema_valid" in names
    assert "governing_law_score" in names
    assert "parties_f1" in names  # entity-list field gets an F1 scorer
    assert "effective_date_score" in names


def test_extraction_eval_rejects_rows_without_truth(monkeypatch, tmp_path):
    import scripts.eval.run_extraction_eval as runner

    dataset = {
        "input": {"doc_text": "text", "filename": "noclause.txt", "expected": "contract",
                  "expected_fields": {}},
        "expected": "contract",
        "filename": "noclause.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": []},
        "doc_text": "text",
        "metadata": {},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])
    with pytest.raises(SystemExit):
        runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
