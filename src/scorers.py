"""Shared scorers for Braintrust evaluation loops — re-export shim.

The classification scorers live in the **llm-dojo-scoring** package
(``llm_dojo_scoring.classification``); this module re-exports them so every
local call site (and llm-mailroom's ``pip install -e .`` imports) keeps
working unchanged, plus the repo-specific pieces the package deliberately
dropped:

- ``cost`` / ``scorer_names`` / ``build_scorers`` — the package removed the
  ``cost(input)`` scorer and its registry (per its MIGRATION doc, "inline
  it"); the repo's eval loop still registers scorers by name, so the local
  registry stays here.
- ``per_class_stats(results)`` / ``macro_accuracy(results)`` keep their
  EvalResult-object-list form (``run_multiclass_eval.py`` registers
  ``macro_accuracy`` as a Braintrust scorer). The package's versions take
  two parallel lists — the new-style API for new consumers (dojo-analyze).

Scorers are plain functions ``(output, expected) -> float`` (or
``(input) -> float`` for cost) registered with ``braintrust.Eval``. They are
deliberately deterministic — every experiment compares on the same metric
definitions, and local scoring (score_manifest) uses the same functions so
Braintrust scores and local manifests never disagree.
"""

from __future__ import annotations

from llm_dojo_scoring.classification import (  # noqa: F401  (re-export shim)
    ERROR_PREFIX,
    accuracy,
    binary_metrics,
    class_distribution,
    confusion_accuracy,
    confusion_matrix,
    exact_match,
    failure,
    normalize_label,
    top_confusions,
)

from src.dojo_config import apply_taxonomy_settings

apply_taxonomy_settings()


def cost(input) -> float:
    """Actual billed USD cost for this row (captured by the task from
    OpenRouter's usage.cost; 0.0 when the row was replayed from a manifest)."""
    if isinstance(input, dict):
        return float(input.get("cost") or 0.0)
    return 0.0


def scorer_names() -> tuple[str, ...]:
    return ("exact_match", "failure", "cost")


def build_scorers(names: list[str] | None) -> list:
    """Resolve a scorer-name list into functions (all three by default)."""
    registry = {
        "exact_match": exact_match,
        "failure": failure,
        "cost": cost,
    }
    if not names:
        names = list(registry)
    return [registry[name] for name in names if name in registry]


def per_class_stats(results: list) -> dict[str, dict]:
    """Aggregate exact-match accuracy per expected class from eval results.

    Args:
        results: ``braintrust.EvalResult`` list (each has .input/.expected/.output).

    Returns:
        {class: {"n": int, "correct": int, "accuracy": float}}
    """
    by_class: dict[str, dict] = {}
    for r in results:
        expected = normalize_label(r.expected)
        output = str(r.output)
        if str(output).startswith(ERROR_PREFIX):
            continue
        bucket = by_class.setdefault(expected, {"n": 0, "correct": 0})
        bucket["n"] += 1
        bucket["correct"] += int(normalize_label(output) == expected)
    for bucket in by_class.values():
        bucket["accuracy"] = round(bucket["correct"] / bucket["n"], 4) if bucket["n"] else 0.0
    return by_class


def macro_accuracy(results: list) -> float:
    """Unweighted mean of per-class accuracies (ignores empty classes)."""
    stats = per_class_stats(results)
    if not stats:
        return 0.0
    return round(sum(s["accuracy"] for s in stats.values()) / len(stats), 4)
