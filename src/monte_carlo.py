"""Shared Monte Carlo simulation utilities for the experiment-log reasoning corpus.

Ported from the RVL-CDIP-classifier's ``src/monte_carlo.py`` (Exios66/RVL-CDIP-
Classifier, issue #17) and adapted to this repo's data model. Every completed
eval row in the joint corpus (experiment log + manifests) is treated as one
sample from a per-document (and per prompt/model) label distribution. This
module provides the statistical primitives the ``scripts/reporting/monte_carlo_*``
scripts compose into ensemble/vote simulations, confidence-gated escalation,
paired-bootstrap prompt ablation, retry-pipeline failure simulation, and
few-shot exemplar search:

- ``normalize_dist`` / ``shannon_entropy`` / ``majority_margin`` — label
  distribution statistics for one document.
- ``draw_committee`` — one Monte Carlo majority-vote draw from a distribution.
- ``bootstrap`` / ``paired_delta_bootstrap`` — resampled confidence intervals
  and win probabilities.
- ``confidence_score`` / ``uncertainty_phrases`` — the confidence heuristic
  used by the escalation/router simulator.
- ``task_label_vocabulary`` / ``decoy_mentioned`` — label vocabularies per task
  (from ``agents/sorter_agent.py``) and the near-miss signal for free-form
  reasoning traces (this repo has no structured ``Runner-up:`` lines).
- ``save_figure`` / ``style_axis`` — consistent chart output for ``reports/``.
"""

from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

# Phrases the reasoning traces use when the model is unsure; their presence
# lowers the confidence score for a document.
UNCERTAINTY_PHRASES = (
    "cannot determine",
    "cannot tell",
    "can't determine",
    "can't tell",
    "unable to determine",
    "unable to tell",
    "not sure",
    "uncertain",
    "ambiguous",
    "unclear",
    "difficult to",
    "hard to tell",
    "hard to say",
    "hard to read",
    "guess",
    "unsure",
    "not entirely clear",
    "degraded",
    "noise",
    "low quality",
    "illegible",
    "appears to be",
    "could be",
    "possibly",
    "might be",
)


# ---------------------------------------------------------------------------
# Label vocabularies (per task)
# ---------------------------------------------------------------------------

def task_label_vocabulary(task: str) -> tuple[str, ...]:
    """The valid predicted-label vocabulary for a task.

    Resolution order: the sorter's 7-class doc-class schema for
    ``docclass_classification`` / ``sorter_classification``-with-docclass, the
    25 CUAD subtypes for ``subtype_classification``, and the sorter doc_type
    classes for plain ``sorter_classification``. Unknown tasks return an empty
    tuple (the caller decides how to treat them).
    """
    from agents.sorter_agent import CONTRACT_SUBTYPES, DOCCLASS_SCHEMA, SORTER_SCHEMA

    if task == "docclass_classification":
        classes = DOCCLASS_SCHEMA.get("properties", {}).get("doc_type", {}).get("enum", [])
        return tuple(classes)
    if task == "subtype_classification":
        return tuple(s["key"] for s in CONTRACT_SUBTYPES)
    if task == "sorter_classification":
        classes = SORTER_SCHEMA.get("properties", {}).get("doc_type", {}).get("enum", [])
        return tuple(classes)
    return ()


def _normalize(label: str) -> str:
    """Lowercase alphanumeric normalization used for matching (not display)."""
    return re.sub(r"[^a-z0-9]+", " ", str(label or "").lower()).strip()


def decoy_mentioned(reasoning: str, decoy: str) -> bool:
    """True when a reasoning trace explicitly mentions the decoy label.

    This repo's reasoning traces are free-form (no ``Runner-up:`` lines), so the
    near-miss signal is: a correct trace whose body names the *other* label of
    a confused pair — the model walked to the right answer while explicitly
    considering/rejecting the trap.
    """
    if not reasoning or not decoy:
        return False
    return _normalize(decoy) in _normalize(reasoning)


def decoy_variants(label: str) -> list[str]:
    """Searchable variants of a label (key + human-readable label).

    ``development`` -> ``["development", "development agreement"]``; handles the
    underscore keys and the human-readable labels from the sorter constants.
    """
    from agents.sorter_agent import CONTRACT_SUBTYPES

    variants = [_normalize(label)]
    for s in CONTRACT_SUBTYPES:
        if s["key"] == label:
            variants.append(_normalize(s.get("label") or ""))
    return [v for v in variants if v]


def reasoning_mentions_label(reasoning: str, label: str) -> bool:
    """True when a reasoning trace mentions a label (any key/label variant)."""
    if not reasoning:
        return False
    text = _normalize(reasoning)
    for variant in decoy_variants(label):
        if variant and variant in text:
            return True
    return False


# ---------------------------------------------------------------------------
# Label distributions
# ---------------------------------------------------------------------------

def normalize_dist(counter: dict[str, int | float]) -> dict[str, float]:
    """Turn a {label: weight} counter into a probability distribution."""
    total = float(sum(counter.values()))
    if total <= 0.0:
        return {}
    return {label: count / total for label, count in counter.items()}


def shannon_entropy(dist: dict[str, float], normalized: bool = True) -> float:
    """Shannon entropy of a probability distribution.

    With ``normalized=True`` the result is divided by ``log2(n)`` so it lies in
    ``[0, 1]`` (0 = one-hot, 1 = uniform). A degenerate distribution returns 0.
    """
    if not dist:
        return 0.0
    entropy = -sum(p * math.log2(p) for p in dist.values() if p > 0.0)
    if normalized and len(dist) > 1:
        entropy /= math.log2(len(dist))
    return float(max(0.0, min(1.0, entropy)))


def majority_margin(dist: dict[str, float]) -> float:
    """Top share minus second share, in ``[0, 1]`` (1 = total agreement)."""
    shares = sorted(dist.values(), reverse=True)
    if not shares:
        return 0.0
    first = shares[0]
    second = shares[1] if len(shares) > 1 else 0.0
    return float(first - second)


def draw_committee(dist: dict[str, float], k: int, rng: random.Random) -> str:
    """One Monte Carlo draw of a ``k``-member majority-vote committee.

    Draws ``k`` labels with replacement from ``dist`` and returns the majority
    label, breaking ties with the provided ``rng``. If ``dist`` is empty or ``k``
    < 1 the empty string is returned.
    """
    if not dist or k < 1:
        return ""
    labels = list(dist.keys())
    weights = [dist[label] for label in labels]
    votes = rng.choices(labels, weights=weights, k=k)
    tallies: dict[str, int] = {}
    for label in votes:
        tallies[label] = tallies.get(label, 0) + 1
    best = max(tallies.values())
    winners = [label for label, count in tallies.items() if count == best]
    return rng.choice(winners)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap(
    values: Iterable[float],
    stat_fn: Callable[[list], float],
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict:
    """Bootstrap a statistic over ``values`` with replacement.

    Returns ``{estimate, ci_lo, ci_hi, std, samples}`` where the confidence
    interval is the 2.5/97.5 percentiles of the resampled statistic.
    """
    rng = random.Random(seed)
    arr = list(values)
    n = len(arr)
    if n == 0:
        return {"estimate": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "std": 0.0, "samples": []}
    estimate = float(stat_fn(arr))
    samples = []
    for _ in range(n_boot):
        resampled = [arr[rng.randrange(n)] for _ in range(n)]
        samples.append(float(stat_fn(resampled)))
    samples.sort()
    ci_lo = samples[int(n_boot * 0.025)]
    ci_hi = samples[int(n_boot * 0.975)]
    return {
        "estimate": estimate,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "std": float(np.std(samples)),
        "samples": samples,
    }


def paired_delta_bootstrap(
    deltas: list[float],
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict:
    """Paired bootstrap over per-item deltas (e.g. ``correct(A) - correct(B)``).

    Returns ``{mean, ci_lo, ci_hi, p_win}`` where ``p_win`` is the fraction of
    resamples with a positive mean delta (A beating B).
    """
    result = bootstrap(deltas, lambda items: float(np.mean(items)), n_boot=n_boot, seed=seed)
    result["mean"] = result["estimate"]
    result["p_win"] = float(np.mean([s > 0.0 for s in result["samples"]]))
    return result


# ---------------------------------------------------------------------------
# Confidence heuristic for the escalation/router simulator
# ---------------------------------------------------------------------------

def uncertainty_phrases(text: str) -> bool:
    """True when a reasoning trace contains uncertainty/hesitation language."""
    if not text:
        return False
    lowered = text.lower()
    return any(phrase in lowered for phrase in UNCERTAINTY_PHRASES)


def confidence_score(
    dist: dict[str, float],
    near_miss_signal: bool = False,
    uncertainty: bool = False,
) -> float:
    """A monotone ``[0, 1]`` confidence for one document's label distribution.

    Heuristic blend of vote dominance, label entropy, a near-miss signal (some
    observation's reasoning named the expected class), and uncertainty phrasing
    in the reasoning traces. Higher is more confident.
    """
    margin = majority_margin(dist)
    entropy = shannon_entropy(dist, normalized=True)
    base = 0.5 * margin + 0.3 * (1.0 - entropy)
    base += 0.1 if not near_miss_signal else 0.0
    base += 0.1 if not uncertainty else 0.0
    return float(max(0.0, min(1.0, base)))


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus(path: str | Path) -> list[dict]:
    """Load the joint corpus JSONL built by ``monte_carlo_corpus.py``."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"corpus not found: {path} (run scripts/reporting/monte_carlo_corpus.py first)")
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def save_figure(fig, path: str | Path, dpi: int = 150) -> None:
    """Save a matplotlib figure to ``reports/`` and close it."""
    from matplotlib import pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"Chart saved: {path}")


def style_axis(ax, title: str, xlabel: str, ylabel: str) -> None:
    """Apply the standard label styling used across reports."""
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)


def safe_div(numerator: float, denominator: float) -> float:
    """Division that returns 0.0 instead of raising on a zero denominator."""
    return float(numerator) / float(denominator) if denominator else 0.0