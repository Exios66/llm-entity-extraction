#!/usr/bin/env python3
"""Mine high-leverage reasoning traces as few-shot exemplars for prompt iteration.

Every reasoning trace that CORRECTLY classified a document while explicitly
navigating a confused pair (the trace body names the *other* label of the pair
— the near-miss decoy) is a candidate exemplar: it demonstrates the
disambiguation the model most often misses. This script (mirroring the
RVL-CDIP-classifier's ``monte_carlo_exemplars.py``):

1. tallies confusion pairs across the corpus (``failure_mode`` rows);
2. finds, per pair, correct traces whose reasoning names the decoy label;
3. runs a Monte Carlo random search over exemplar subsets (bounded by an
   exemplar count and a token budget) with a surrogate: selecting an exemplar
   for pair ``(E -> P)`` is expected to flip ``efficacy x count`` of that
   pair's current errors;
4. writes the winning subset, the full traces, and a ready-to-paste exemplar
   appendix for the next prompt version.

No model spend: everything is derived from the existing corpus. Run this after
each new experiment so the exemplar bank tracks the latest confusion pairs.

Usage:
    python scripts/reporting/monte_carlo_exemplars.py
    python scripts/reporting/monte_carlo_exemplars.py --max-exemplars 8
    python scripts/reporting/monte_carlo_exemplars.py --task docclass_classification
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monte_carlo import (  # noqa: E402
    load_corpus,
    reasoning_mentions_label,
    task_label_vocabulary,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"


def confusion_pairs(corpus: list[dict], task: str) -> Counter:
    """(expected -> predicted) confusion counts from failure rows."""
    pairs: Counter = Counter()
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        if not record.get("correct"):
            pairs[(record.get("expected") or "?", record.get("predicted") or "?")] += 1
    return pairs


def near_miss_traces(corpus: list[dict], task: str, expected: str, decoy: str,
                     valid: set[str]) -> list[dict]:
    """Correct traces that explicitly mention the decoy label of a pair.

    The trace demonstrates the disambiguation the model most often misses: it
    walked to the right answer while naming (and rejecting) the trap label.
    """
    hits = []
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        if record.get("expected") != expected or not record.get("correct"):
            continue
        reasoning = (record.get("reasoning") or "").strip()
        if not reasoning or decoy not in valid:
            continue
        if reasoning_mentions_label(reasoning, decoy):
            hits.append({
                "filename": record.get("filename"),
                "model": record.get("model"),
                "prompt_version": record.get("prompt_version"),
                "reasoning": reasoning,
                "tokens": len(reasoning.split()),
            })
    return hits


_EFFICACY = 0.5
_TOKEN_BUDGET = 12_000
_MAX_EXEMPLARS = 6


def random_search(pairs: list[dict], rng: random.Random, n_iter: int = 800,
                    token_budget: int = _TOKEN_BUDGET,
                    max_exemplars: int = _MAX_EXEMPLARS,
                    efficacy: float = _EFFICACY) -> dict:
    """Monte Carlo search for the exemplar subset with the largest expected
    error-flip gain under the token budget (surrogate: each selected pair's
    exemplar flips ``efficacy x count`` errors)."""
    best = None
    best_score = -1.0
    max_k = min(max_exemplars, len(pairs))
    for _ in range(n_iter):
        k = rng.randint(1, max_k)
        selected = rng.sample(pairs, k)
        tokens = sum(p["tokens"] for p in selected)
        if tokens > token_budget:
            continue
        score = sum(min(p["count"], p["near_misses"]) * efficacy for p in selected)
        if score > best_score:
            best_score = score
            best = selected
    return {"selected": best or [], "score": best_score}


def render_report(pairs: Counter, candidates: dict, selected: list[dict], task: str) -> str:
    L = ["# Near-miss exemplar mining (Monte Carlo selection)", ""]
    L.append(f"_Task: `{task}` · surrogate efficacy {_EFFICACY:.0%} · budget "
             f"{_TOKEN_BUDGET:,} chars · max {_MAX_EXEMPLARS} exemplars_")
    L.append("")
    L.append("## Top confusion pairs")
    L.append("")
    L.append("| expected → predicted | errors | near-miss traces |")
    L.append("|---|---|---|")
    for (expected, predicted), count in pairs.most_common(12):
        candidates_count = candidates.get((expected, predicted), 0)
        L.append(f"| {expected} → {predicted} | {count} | {candidates_count} |")
    L.append("")
    L.append("## Selected exemplar subset (expected error-flip gain "
             f"{selected[0]['expected_gain'] if selected else 0:.1f} errors)")
    L.append("")
    for item in selected:
        L.append(f"### Pair {item['expected']} → {item['decoy']} — "
                 f"{item['near_misses']} near-miss traces, selecting "
                 f"{len(item['traces'])}")
        L.append("")
        for t in item["traces"][:3]:
            L.append(f"- **{t['filename']}** ({t['model']}, {t['prompt_version']}):")
            L.append(f"  `{t['reasoning'][:400]}`")
        L.append("")
    return "\n".join(L)


def render_appendix(selected: list[dict]) -> str:
    L = ["# Ready-to-paste exemplar appendix (next prompt version)", ""]
    L.append("")
    L.append("_Paste the disambiguation examples below into the prompt's few-shot "
             "section (or the rule exemplar list). Each shows a correct "
             "classification that explicitly rejects the decoy label of a "
             "confusion pair._")
    L.append("")
    for item in selected:
        L.append(f"## {item['expected']} (decoy: {item['decoy']})")
        L.append("")
        for t in item["traces"][:2]:
            L.append(f"**Example — {t['filename']}**")
            L.append("")
            L.append("> " + t["reasoning"].replace("\n", "\n> "))
            L.append("")
    return "\n".join(L)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--task", default="subtype_classification")
    parser.add_argument("--max-exemplars", type=int, default=_MAX_EXEMPLARS)
    parser.add_argument("--token-budget", type=int, default=_TOKEN_BUDGET)
    parser.add_argument("--efficacy", type=float, default=_EFFICACY)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    max_exemplars = args.max_exemplars
    token_budget = args.token_budget
    efficacy = args.efficacy

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    valid = set(task_label_vocabulary(args.task))
    pairs = confusion_pairs(corpus, args.task)
    if not pairs:
        print(f"no confusion pairs for task {args.task}")
        return 0

    candidates: dict[tuple[str, str], int] = {}
    pair_items = []
    rng = random.Random(args.seed)
    for (expected, decoy), count in pairs.items():
        traces = near_miss_traces(corpus, args.task, expected, decoy, valid)
        candidates[(expected, decoy)] = len(traces)
        if traces:
            pair_items.append({
                "expected": expected, "decoy": decoy, "count": count,
                "near_misses": len(traces),
                "traces": traces,
                "tokens": min(len(t["reasoning"]) for t in traces),
            })

    # per-pair best token estimate: pick the shortest qualifying trace
    for p in pair_items:
        p["tokens"] = min(len(t["reasoning"]) for t in p["traces"])

    search = random_search(pair_items, rng, token_budget=token_budget,
                            max_exemplars=max_exemplars, efficacy=efficacy)
    selected = []
    for p in search["selected"]:
        item = {
            "expected": p["expected"], "decoy": p["decoy"],
            "near_misses": p["near_misses"],
            "traces": sorted(p["traces"], key=lambda t: len(t["reasoning"]))[:2],
            "expected_gain": min(p["count"], p["near_misses"]) * _EFFICACY,
        }
        selected.append(item)
    selected.sort(key=lambda i: -i["expected_gain"])

    (out_dir / f"exemplars-{args.task}.md").write_text(
        render_report(pairs, candidates, selected, args.task), encoding="utf-8")
    if selected:
        (out_dir / f"exemplar-appendix-{args.task}.md").write_text(
            render_appendix(selected), encoding="utf-8")

    print(f"exemplars: {len(selected)} selected (top: "
          + ", ".join(f"{s['expected']}→{s['decoy']} (+{s['expected_gain']:.1f})"
                      for s in selected[:3]) + ")")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()