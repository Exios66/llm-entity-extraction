"""Shared eval-result shims + a local runner for the no-Braintrust path.

When ``BRAINTRUST_LOGGING=disabled`` the ``run_*_eval.py`` runners skip
``braintrust.Eval`` and execute the SAME task function over the same input
rows locally (``ThreadPoolExecutor``), producing an ``EvalRunShim`` that feeds
the shared ``log_experiment_to_repo`` unchanged. This keeps every eval surface
(including vision classification and chunked extraction) runnable with zero
Braintrust quota consumption — results sink to the repo experiment log (+
LangSmith spans, + the Langfuse mirror runners).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


class EvalResultShim:
    """Minimal ``braintrust.EvalResult``-compatible row."""

    def __init__(self, input: dict, output: Any, error: str | None = None):
        self.input = input
        self.output = output
        self.error = error


class EvalRunShim:
    """Minimal ``braintrust.Eval``-result-compatible container."""

    def __init__(self, results: list[EvalResultShim]):
        self.results = results


def run_local_eval(
    task: Callable[[dict], Any],
    rows: list[dict],
    max_concurrency: int = 8,
) -> EvalRunShim:
    """Run ``task`` over ``rows`` with a thread pool, tolerating per-row errors.

    ``rows`` are the exact ``{"input": ..., "expected": ..., "filename": ...}``
    dicts the Braintrust ``data=lambda`` would produce; ``task`` is the same
    function the Braintrust path hands to ``braintrust.Eval``.
    """
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = {pool.submit(task, row["input"]): i for i, row in enumerate(rows)}
        for future, i in futures.items():
            try:
                results[i] = EvalResultShim(rows[i], future.result(), None)
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], None, str(exc))
    return EvalRunShim(results)
