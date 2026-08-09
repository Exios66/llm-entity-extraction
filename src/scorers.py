"""Shared scorers for Braintrust evaluation loops.

Scorers are plain functions ``(output, expected) -> float`` (or
``(input) -> float`` for cost) registered with ``braintrust.Eval``. They are
deliberately deterministic — every experiment compares on the same metric
definitions, and local scoring (score_manifest) uses the same functions so
Braintrust scores and local manifests never disagree.
"""

from __future__ import annotations

import json
import re

ERROR_PREFIX = "ERROR: "  # task output sentinel for failed rows

_VALID_CLASSES_RE = {
    "contract": re.compile(r"\bcontract\b"),
    "corporate_record": re.compile(r"\bcorporate[_ ]?record\b"),
    "due_diligence": re.compile(r"\bdue[_ ]?diligence\b"),
    "correspondence": re.compile(r"\bcorrespondence\b"),
    "compliance_filing": re.compile(r"\bcompliance[_ ]?filing\b"),
    "court_opinion": re.compile(r"\bcourt[_ ]?opinion\b"),
}


def normalize_label(value) -> str:
    """Coerce an LLM output into a doc class key (best effort)."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    # Prefer a JSON object's doc_type field.
    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            text = str(obj.get("doc_type") or text).lower()
        except json.JSONDecodeError:
            pass
    # Exact match.
    if text in _VALID_CLASSES_RE:
        return text
    for cls, pattern in _VALID_CLASSES_RE.items():
        if pattern.search(text):
            return cls
    return text.strip('"`*_ ')


def exact_match(output, expected) -> float:
    """Score 1.0 if the prediction matches the expected class, else 0.0."""
    return 1.0 if normalize_label(output) == normalize_label(expected) else 0.0


def failure(output, expected) -> float:
    """Score 1.0 for rows the model failed to classify (error sentinel)."""
    return 1.0 if str(output).startswith(ERROR_PREFIX) else 0.0


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
