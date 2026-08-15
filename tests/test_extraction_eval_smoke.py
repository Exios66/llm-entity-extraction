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
    monkeypatch.setenv("BRAINTRUST_LOGGING", "enabled")


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
            "reasoning": {
                "summary": "Scanned 4 sections; two conflicts resolved via definitions.",
                "entries": [
                    {"field": "governing_law", "evidence": "State of Delaware",
                     "section_ref": "Section 12"},
                    {"field": "effective_date", "evidence": "2024-01-15",
                     "section_ref": "Section 1"},
                    {"field": "parties", "evidence": "Acme Technologies, Inc.",
                     "section_ref": "Recitals"},
                ],
            },
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
    # Cross-experiment trackers: the default registers the complex content
    # accuracy + binary conformance + factuality-guard + CUAD YES/NO category
    # conformance lookups (no recompute on Braintrust side).
    assert fake_extraction_eval.kwargs["metadata"]["bt_scores"] == "overall"
    names = set(fake_extraction_eval.scores)
    assert "overall_extraction_score" in names
    assert "field_presence" in names
    assert "overall_verified_precision" in names
    assert "category_presence" in names
    assert len(fake_extraction_eval.kwargs["scores"]) == 4  # the tracker quartet

    # Expected fields were derived from the CUAD clause labels.
    row_input = fake_extraction_eval.kwargs["data"]()[0]["input"]
    assert row_input["expected_fields"]["governing_law"] == "State of Delaware"
    assert row_input["expected_fields"]["parties"] == ["Acme Technologies, Inc.", "Beta Holdings Corp."]
    assert row_input["expected_fields"]["effective_date"] == "January 15, 2024"
    assert "termination_clauses" in row_input["expected_fields"]

    # The composite output carries the locally computed content scores —
    # governing law exact -> 1.0; parties 1/2 matched (the disjoint-name
    # guard correctly rejects the wrong party).
    output = fake_extraction_eval.results[0].output
    assert output["field_scores"]["governing_law"] == 1.0
    assert output["field_scores"]["effective_date"] == 1.0
    assert output["entity_list_f1"]["parties"] == pytest.approx(0.5)
    # Raw precision/recall/F1 audit detail rides alongside the tracker values.
    audit = output["entity_list_scores"]["parties"]
    assert audit["precision"] == pytest.approx(0.5)
    assert audit["recall"] == pytest.approx(0.5)
    assert audit["f1"] == pytest.approx(0.5)
    assert audit["n_predicted"] == 2
    # Factuality guard runs against the document text (present in the row).
    fact = output["entity_list_audit"]["parties"]
    assert fact["n_predicted"] == 2
    assert fact["matched_gt"] == 1
    assert fact["verified_precision"] > 0.0
    assert 0.0 < output["overall_score"] < 1.0
    assert output["field_presence"] == 1.0  # all 4 expected fields populated
    assert output["schema_valid"] == 1.0
    assert output["predicted"].get("confidence") is not None  # normalized + backfilled
    # The reasoning trace rides along inside the predicted output (and thus
    # into the experiment record + Langfuse observation outputs).
    assert output["predicted"]["reasoning"]["summary"].startswith("Scanned 4 sections")
    assert output["predicted"]["reasoning"]["entries"][0]["field"] == "governing_law"
    # The registered tracker scorers are trivial lookups on the composite.
    assert fake_extraction_eval.scores["overall_extraction_score"] == [output["overall_score"]]
    assert fake_extraction_eval.scores["field_presence"] == [1.0]

    # Run-level diagnostics ride on the logged record: field-level error
    # decomposition + date MAE/R² (effective_date expected "January 15, 2024"
    # vs predicted "2024-01-15" — a perfect date -> 0 days MAE).
    import json as _json
    from pathlib import Path

    log_path = Path(runner.default_jsonl_path())
    record = _json.loads(log_path.read_text().splitlines()[-1])
    diag = record["scores"]["diagnostics"]
    assert diag["n_fields_scored"] > 0
    assert diag["field_exact_rate"] > 0.0
    assert diag["error_decomposition"]["effective_date"]["exact_rate"] == 1.0
    assert diag["date_mae_days"] == 0.0
    assert diag["date_r2"] is None  # a single parseable date pair — R² undefined
    assert diag["field_presence_per_field"]["effective_date"] == 1.0
    # The reasoning trace lands in the logged record's per-document output.
    assert record["results"][0]["predicted"]["reasoning"]["entries"][0]["field"] == "governing_law"
    # Master labels load best-effort: absent here, or the sibling CSV path on
    # dev machines — the record names whatever was used.
    assert "master_labels" in record["data_source"]


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


def test_judge_calibration_tracker(fake_extraction_eval, monkeypatch, tmp_path):
    """Issue #1: --judge rows are persisted to data/judgments/<exp>.jsonl and
    aggregated into scores.judge_calibration (judge-vs-deterministic lean)."""
    import json as _json
    import os
    from pathlib import Path

    import scripts.eval.run_extraction_eval as runner

    # Redirect the judgments dir so the test never writes into the repo.
    import src.experiment_log as experiment_log_mod
    monkeypatch.setattr(experiment_log_mod, "JUDGMENTS_DIR", tmp_path / "judgments")

    calls = {"correctness": 0, "completeness": 0}

    def fake_correctness(self, doc_type, extracted, doc_text):
        calls["correctness"] += 1
        return {"extraction_correctness_label": "accurate",
                "extraction_correctness": 1.0, "reasoning": "matches the source"}

    def fake_completeness(self, doc_type, extracted, doc_text):
        calls["completeness"] += 1
        return {"completeness_label": "complete", "completeness": 1.0}

    monkeypatch.setattr("agents.judge_agent.JudgeAgent.judge_extraction_correctness",
                        fake_correctness)
    monkeypatch.setattr("agents.judge_agent.JudgeAgent.judge_completeness",
                        fake_completeness)

    dataset = {
        "input": {
            "doc_text": "This Agreement is governed by the laws of the State of Delaware.",
            "filename": "cuad_doc_01.txt",
            "expected": "contract",
            "expected_fields": {},
        },
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "expected_output": {"doc_type": "contract", "clause_labels": CUAD_LABELS},
        "doc_text": "This Agreement is governed by the laws of the State of Delaware.",
        "metadata": {},
    }
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_extraction_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(dataset)])

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "contracts_specialist_v2",
        "--experiment-name", "smoke_extraction_judge",
        "--judge",
        "--project-id", "proj-test-0000",
    ])
    assert rc == 0

    # The judge ran on the ambiguous row (parties entity-list F1 = 0.5 lands
    # in the [0.5, 0.85] band -> needs_judge_review).
    assert calls["correctness"] == 1
    assert calls["completeness"] == 1

    # Persisted calibration row.
    jpath = tmp_path / "judgments" / "smoke_extraction_judge.jsonl"
    assert jpath.exists()
    row = _json.loads(jpath.read_text().splitlines()[0])
    assert row["kind"] == "calibration"
    assert row["correctness_label"] == "accurate"
    assert row["deterministic_overall_score"] is not None

    # Record aggregate.
    log = Path(os.environ.get("EXPERIMENT_LOG_PATH", tmp_path / "log.jsonl"))
    record = _json.loads(log.read_text().splitlines()[-1])
    jc = record["scores"]["judge_calibration"]
    assert jc["n_judged"] == 1
    assert jc["agree_rate"] is not None
    assert record["parameters"]["judge"] is True
