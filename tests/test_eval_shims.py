"""Unit tests for the no-Braintrust local eval loop (``src/eval_shims.py``).

Pins the shim contract the shared loggers rely on: ``input`` is the task's
INNER input dict (so ``index``-keyed usage/cost accounting resolves) and
``expected`` mirrors the Braintrust ``EvalResult`` attribute.
"""

from __future__ import annotations

from src.eval_shims import EvalResultShim, run_local_eval


def _rows():
    return [
        {"input": {"index": 0, "filename": "h_0.txt", "expected": "No",
                   "doc_text": "James came first in his class."},
         "expected": "No", "filename": "h_0.txt"},
        {"input": {"index": 1, "filename": "h_1.txt", "expected": "Yes",
                   "doc_text": "Ava screamed at the officer."},
         "expected": "Yes", "filename": "h_1.txt"},
    ]


def test_run_local_eval_contract():
    seen = []

    def task(input_data):
        seen.append(input_data["filename"])
        return input_data["expected"]

    run = run_local_eval(task, _rows(), max_concurrency=2)
    assert len(run.results) == 2
    for i, r in enumerate(run.results):
        assert isinstance(r, EvalResultShim)
        # input is the INNER dict the task received (index/filename resolve).
        assert r.input == _rows()[i]["input"]
        assert r.input.get("index") == i
        assert r.input.get("filename") == _rows()[i]["filename"]
        assert r.expected == _rows()[i]["expected"]  # r.expected works, like EvalResult
        assert r.output == r.expected
        assert r.error is None
    assert seen == ["h_0.txt", "h_1.txt"]


def test_run_local_eval_tolerates_row_errors():
    def task(input_data):
        raise ValueError("boom")

    run = run_local_eval(task, _rows(), max_concurrency=2)
    for r in run.results:
        assert r.output is None
        assert r.error == "boom"
        assert r.input.get("index") in (0, 1)
        assert r.expected in ("No", "Yes")
