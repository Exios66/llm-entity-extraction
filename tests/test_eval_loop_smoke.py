"""End-to-end smoke test of the eval loop wiring (no network, no LLM).

Mocks ``braintrust.Eval`` and ``setup_langchain`` so the full runner executes:
dataset loading -> task invocation (with the SorterAgent mocked) -> scorer
registration -> reporter -> experiment metadata. This proves the loop wiring
end to end without touching Braintrust or OpenRouter.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class FakeEvalResult:
    def __init__(self, input, expected, output, error=None):
        self.input = input
        self.expected = expected
        self.output = output
        self.error = error


class FakeEvalRun:
    """Records the arguments handed to braintrust.Eval and runs the task."""

    def __init__(self):
        self.kwargs = None
        self.results = []

    def _run(self):
        data_rows = self.kwargs["data"]()
        task = self.kwargs["task"]
        for row in data_rows:
            try:
                output = task(row["input"])
            except Exception as exc:  # noqa: BLE001
                self.results.append(FakeEvalResult(row["input"], row["expected"], None, str(exc)))
                continue
            self.results.append(FakeEvalResult(row["input"], row["expected"], output))
        # Run the scorers over the results, mirroring braintrust.Eval behavior
        # (1-arg scorers receive the input; 2-arg scorers receive output+expected).
        self.scores = {}
        for scorer in self.kwargs.get("scores", []):
            import inspect

            arity = len(inspect.signature(scorer).parameters)
            values = []
            for result in self.results:
                if result.error is not None:
                    continue
                if arity == 1:
                    values.append(scorer(result.input))
                else:
                    values.append(scorer(result.output, result.expected))
            self.scores[scorer.__name__] = values
        return self


@pytest.fixture
def fake_eval(monkeypatch, tmp_path):
    run = FakeEvalRun()

    def fake_eval_call(project, *args, **kwargs):
        run.kwargs = kwargs
        run.kwargs["project"] = project
        return run._run()

    import braintrust

    monkeypatch.setattr(braintrust, "Eval", fake_eval_call)
    monkeypatch.setattr(braintrust, "flush", lambda *a, **k: None)
    monkeypatch.setattr("braintrust.integrations.langchain.setup_langchain",
                        lambda *a, **k: True)
    monkeypatch.setattr("scripts.eval.run_classification_eval.setup_langchain",
                        lambda *a, **k: True)

    def fake_classify_json(self, doc_text):
        # Deterministic fake sorter: documents mentioning the class win.
        lowered = doc_text.lower()
        for cls in ("contract", "correspondence", "court_opinion", "corporate_record",
                    "due_diligence", "compliance_filing"):
            if cls.replace("_", " ") in lowered or cls in lowered:
                return {"doc_type": cls, "confidence": 0.9, "reasoning": "fake sorter"}
        return {"doc_type": "correspondence", "confidence": 0.5, "reasoning": "fake default"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)
    return run


def test_full_loop_wiring(fake_eval, monkeypatch, tmp_path):
    import scripts.eval.run_classification_eval as runner

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a_contract.txt").write_text("This is a formal contract agreement between parties. " * 10)
    (docs / "b_letter.txt").write_text("Dear Counsel, please find our correspondence. " * 10)

    monkeypatch.setattr(runner, "require_env",
                        lambda *names: tuple("fake-key" for _ in names))

    rc = runner.main_with_args([
        "--documents-dir", str(docs),
        "--expected", "contract",
        "--prompt-version", "sorter_v0",
        "--model", "qwen/qwen3.7-flash",
        "--experiment-name", "smoke_test_run",
        "--project-id", "proj-test-0000",
        "--max-concurrency", "2",
    ])
    assert rc == 0

    # The eval was handed the expected wiring.
    assert fake_eval.kwargs["experiment_name"] == "smoke_test_run"
    assert fake_eval.kwargs["project_id"] == "proj-test-0000"
    assert fake_eval.kwargs["metadata"]["prompt_version"] == "sorter_v0"
    assert "prompt" in fake_eval.kwargs["metadata"]
    assert fake_eval.kwargs["description"] == "qwen/qwen3.7-flash | prompt sorter_v0 | temperature 0.1"

    # Data rows carry input/expected/filename.
    rows = fake_eval.kwargs["data"]()
    assert len(rows) == 2
    filenames = {r["input"]["filename"] for r in rows}
    assert filenames == {"a_contract.txt", "b_letter.txt"}
    assert all(r["expected"] == "contract" for r in rows)

    # The task produced normalized doc classes.
    outputs = [r.output for r in fake_eval.results]
    assert "contract" in outputs

    # Scorers registered and computed.
    assert set(fake_eval.scores) == {"exact_match", "failure", "cost"}
    assert all(v in (0.0, 1.0) for v in fake_eval.scores["exact_match"])


def test_manifest_checkpoint_skips_cached_rows(fake_eval, monkeypatch, tmp_path):
    """Cached rows replay from the manifest without calling the LLM again."""
    import scripts.eval.run_classification_eval as runner

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a_contract.txt").write_text("contract agreement. " * 10)
    (docs / "b_letter.txt").write_text("correspondence letter. " * 10)

    manifest_path = tmp_path / "run.jsonl"
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))

    # First run writes the manifest.
    rc = runner.main_with_args([
        "--documents-dir", str(docs), "--expected", "contract",
        "--prompt-version", "sorter_v0",
        "--manifest", str(manifest_path),
        "--experiment-name", "smoke_checkpoint",
        "--max-concurrency", "2",
    ])
    assert rc == 0

    # Second run with the same metadata reuses it.
    calls_before = 0
    orig_classify = runner.SorterAgent
    calls = {"n": 0}

    def counting_classify_json(self, doc_text):
        calls["n"] += 1
        return orig_classify(prompt_version="sorter_v0").classify_json(doc_text)

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", counting_classify_json)
    rc = runner.main_with_args([
        "--documents-dir", str(docs), "--expected", "contract",
        "--prompt-version", "sorter_v0",
        "--manifest", str(manifest_path),
        "--experiment-name", "smoke_checkpoint",
        "--max-concurrency", "2",
    ])
    assert rc == 0
    # Both rows were cached -> the fake LLM was never invoked again.
    assert calls["n"] == 0
