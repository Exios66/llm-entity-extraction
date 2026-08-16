#!/usr/bin/env python3
"""Monte Carlo ensemble voting + confidence-gated escalation simulation.

Reads the joint corpus (``reports/monte_carlo/corpus.jsonl``) and treats every
completed row as a sample from a per-document label distribution. Zero-spend
answers (mirroring the RVL-CDIP-classifier's ``monte_carlo_ensemble.py``):

1. **Ensemble voting** — if each document were re-run ``K`` times and the
   labels majority-voted, what accuracy would we get? ``accuracy(K)`` overall
   and per class, with bootstrap confidence bands (the committee ceiling and
   its cost multiplier are known up front).

2. **Confidence heuristic** — per-document confidence in ``[0, 1]`` from vote
   dominance, label entropy, a near-miss signal (some observation's reasoning
   named the expected class), uncertainty phrasing, and the stored per-row
   confidence when present.

3. **Abstention/escalation** — route the lowest-confidence ``alpha`` fraction
   to a stronger model (parameterized ``--escalated-acc`` with a +/- sensitivity
   band) and sweep the accuracy-vs-cost Pareto frontier. The concrete filenames
   to escalate are written to ``escalation_candidates.txt`` for a spend-minimal
   verification eval.

Usage:
    python scripts/reporting/monte_carlo_ensemble.py
    python scripts/reporting/monte_carlo_ensemble.py --k-list 1,3,5,7,10
    python scripts/reporting/monte_carlo_ensemble.py --escalated-acc 0.90 --escalated-cost 3.0
    python scripts/reporting/monte_carlo_ensemble.py --task subtype_classification
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from src.monte_carlo import (  # noqa: E402
    bootstrap,
    confidence_score,
    draw_committee,
    load_corpus,
    majority_margin,
    normalize_dist,
    reasoning_mentions_label,
    save_figure,
    shannon_entropy,
    style_axis,
    task_label_vocabulary,
    uncertainty_phrases,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"


def load_observations(corpus: list[dict], task: str, valid_classes: set[str]) -> dict[str, dict]:
    """Group completed corpus rows into per-document observations.

    Returns ``{filename: {expected, observations, reasoning, confidences,
    near_miss, uncertainty}}`` for one task.
    """
    docs: dict[str, dict] = defaultdict(lambda: {
        "expected": "", "observations": [], "reasoning": [],
        "confidences": [], "near_miss": False, "uncertainty": False,
    })
    for record in corpus:
        if record.get("task") != task:
            continue
        if record.get("status") != "completed":
            continue
        predicted = (record.get("predicted") or "").strip()
        if predicted not in valid_classes:
            continue
        doc = docs[record["filename"]]
        doc["expected"] = record["expected"]
        doc["observations"].append(predicted)
        reasoning = record.get("reasoning") or ""
        if reasoning:
            doc["reasoning"].append(reasoning)
        if record.get("confidence") is not None:
            doc["confidences"].append(float(record["confidence"]))
        if reasoning and record["expected"]:
            doc["near_miss"] = doc["near_miss"] or reasoning_mentions_label(
                reasoning, record["expected"])
        if reasoning and uncertainty_phrases(reasoning):
            doc["uncertainty"] = True
    return dict(docs)


def accuracy_at_k(docs: dict[str, dict], k: int, n_sim: int,
                  rng: random.Random) -> dict[str, float]:
    """Per-doc committee accuracy at K (fraction of draws whose majority is
    the expected label), plus the K=1 empirical baseline."""
    per_doc: dict[str, float] = {}
    for filename, doc in docs.items():
        dist = normalize_dist(Counter(doc["observations"]))
        expected = doc["expected"]
        if not dist or expected not in dist:
            per_doc[filename] = 0.0
            continue
        if k == 1:
            per_doc[filename] = dist[expected]
        else:
            correct = sum(1 for _ in range(n_sim)
                          if draw_committee(dist, k, rng) == expected)
            per_doc[filename] = correct / n_sim
    return per_doc


def simulate_committees(docs: dict[str, dict], k_list: list[int],
                        n_sim: int, seed: int) -> tuple[dict, dict]:
    """Return (accuracy_by_k, per_class_by_k) with bootstrap CIs over docs."""
    rng = random.Random(seed)
    accuracy_by_k: dict[int, dict] = {}
    per_class_by_k: dict[int, dict[str, dict]] = {}
    for k in k_list:
        per_doc = accuracy_at_k(docs, k, n_sim, rng)
        values = list(per_doc.values())
        stat = bootstrap(values, lambda v: float(np.mean(v)), n_boot=2_000, seed=seed)
        accuracy_by_k[k] = {
            "estimate": stat["estimate"], "ci_lo": stat["ci_lo"], "ci_hi": stat["ci_hi"],
        }
        by_class: dict[str, list[float]] = defaultdict(list)
        for filename, p in per_doc.items():
            by_class[docs[filename]["expected"]].append(p)
        per_class_by_k[k] = {
            cls: {"estimate": float(np.mean(v)), "n": len(v)} for cls, v in by_class.items()
        }
    return accuracy_by_k, per_class_by_k


def build_confidence(docs: dict[str, dict]) -> dict[str, float]:
    """Per-document confidence in [0, 1] (heuristic + stored-confidence blend)."""
    confidence: dict[str, float] = {}
    for filename, doc in docs.items():
        dist = normalize_dist(Counter(doc["observations"]))
        heuristic = confidence_score(dist, doc["near_miss"], doc["uncertainty"])
        stored = doc["confidences"]
        blended = (heuristic * 0.6 + float(np.mean(stored)) * 0.4) if stored else heuristic
        confidence[filename] = float(max(0.0, min(1.0, blended)))
    return confidence


def escalation_curve(docs: dict[str, dict], confidence: dict[str, float],
                     alpha_list: list[float], escalated_acc: float,
                     base_cost: float, escalated_cost: float,
                     sensitivity: float = 0.05) -> list[dict]:
    """Accuracy-vs-cost Pareto for routing the alpha lowest-confidence docs.

    Simulated accuracy = (1-alpha)*p_base + alpha*p_escalated where p_base is
    the doc's own empirical correct probability and p_escalated is the
    parameterized stronger-model accuracy (with a +/- sensitivity band).
    Cost = (1-alpha)*base_cost + alpha*escalated_cost per doc.
    """
    rows = []
    order = sorted(confidence, key=confidence.get)
    for alpha in alpha_list:
        n_esc = int(round(alpha * len(order)))
        escalated = set(order[:n_esc])
        p_base_total = 0.0
        for filename, doc in docs.items():
            dist = normalize_dist(Counter(doc["observations"]))
            p_base_total += dist.get(doc["expected"], 0.0)
        p_base = p_base_total / max(1, len(docs))
        acc = (1 - alpha) * p_base + alpha * escalated_acc
        rows.append({
            "alpha": alpha,
            "accuracy": acc,
            "accuracy_low": (1 - alpha) * p_base + alpha * (escalated_acc - sensitivity),
            "accuracy_high": (1 - alpha) * p_base + alpha * (escalated_acc + sensitivity),
            "cost_multiplier": (1 - alpha) * 1.0 + alpha * (escalated_cost / base_cost),
            "n_escalated": n_esc,
        })
    return rows


def render_ensemble_report(docs: dict[str, dict], accuracy_by_k: dict, per_class_by_k: dict,
                           confidence: dict[str, float], task: str) -> str:
    L = ["# Ensemble voting + confidence-gated escalation (Monte Carlo)", ""]
    L.append(f"_Task: `{task}` · corpus: `reports/monte_carlo/corpus.jsonl`_")
    L.append("")
    L.append(f"**{len(docs)} documents** with observations (multi-run docs: "
             f"{sum(1 for d in docs.values() if len(d['observations']) > 1)}).")
    L.append("")
    L.append("## Accuracy(K) — committee majority voting")
    L.append("")
    L.append("| K | accuracy | 95% CI |")
    L.append("|---|---|---|")
    for k in sorted(accuracy_by_k):
        a = accuracy_by_k[k]
        L.append(f"| {k} | {a['estimate']:.4f} | [{a['ci_lo']:.4f}, {a['ci_hi']:.4f}] |")
    L.append("")
    L.append("## Per-class accuracy at K (worst 10)")
    L.append("")
    L.append("| class | K=1 | K=3 | K=10 | n docs |")
    L.append("|---|---|---|---|---|")
    k1 = per_class_by_k.get(1, {})
    k3 = per_class_by_k.get(3, {})
    k10 = per_class_by_k.get(10, {})
    worst = sorted(k1.items(), key=lambda kv: kv[1]["estimate"])[:10]
    for cls, _ in worst:
        L.append(f"| {cls} | {k1[cls]['estimate']:.3f} | "
                 f"{k3.get(cls, {}).get('estimate', 0.0):.3f} | "
                 f"{k10.get(cls, {}).get('estimate', 0.0):.3f} | {k1[cls]['n']} |")
    L.append("")
    confs = list(confidence.values())
    L.append(f"## Confidence heuristic (n={len(confs)})")
    L.append("")
    L.append(f"- median {sorted(confs)[len(confs)//2]:.3f} · "
             f"mean {np.mean(confs):.3f} · below 0.5: "
             f"{sum(1 for c in confs if c < 0.5)} docs")
    L.append("")
    return "\n".join(L)


def render_escalation_report(curve: list[dict], task: str) -> str:
    L = ["# Confidence-gated escalation — accuracy vs cost (Monte Carlo)", ""]
    L.append(f"_Task: `{task}` · escalated model accuracy parameterized (sensitivity ±5 pp)_")
    L.append("")
    L.append("| alpha | accuracy | band (low/high) | cost multiplier | n escalated |")
    L.append("|---|---|---|---|---|")
    for row in curve:
        L.append(f"| {row['alpha']:.2f} | {row['accuracy']:.4f} | "
                 f"[{row['accuracy_low']:.4f}, {row['accuracy_high']:.4f}] | "
                 f"{row['cost_multiplier']:.2f}x | {row['n_escalated']} |")
    L.append("")
    L.append("The Pareto point should be chosen from this table, not extrapolated — "
             "the low-confidence tail is heterogeneous (near-miss/uncertainty-flagged "
             "single-observation docs).")
    L.append("")
    return "\n".join(L)


def make_figures(accuracy_by_k: dict, curve: list[dict], task: str, out_dir: Path) -> None:
    ks = sorted(accuracy_by_k)
    est = [accuracy_by_k[k]["estimate"] for k in ks]
    lo = [accuracy_by_k[k]["ci_lo"] for k in ks]
    hi = [accuracy_by_k[k]["ci_hi"] for k in ks]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(ks, est, marker="o", color="#1d4ed8", lw=2)
    ax.fill_between(ks, lo, hi, alpha=0.2, color="#1d4ed8", label="95% CI")
    ax.set_xticks(ks)
    style_axis(ax, f"Committee accuracy vs K ({task})", "committee size K", "accuracy")
    ax.legend()
    save_figure(fig, out_dir / f"ensemble-accuracy-{task}.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    alphas = [row["alpha"] for row in curve]
    accs = [row["accuracy"] for row in curve]
    lo_a = [row["accuracy_low"] for row in curve]
    hi_a = [row["accuracy_high"] for row in curve]
    costs = [row["cost_multiplier"] for row in curve]
    ax.plot(costs, accs, marker="o", color="#059669", lw=2)
    ax.fill_between(costs, lo_a, hi_a, alpha=0.2, color="#059669", label="±5 pp band")
    style_axis(ax, f"Escalation Pareto ({task})", "cost multiplier", "accuracy")
    ax.legend()
    save_figure(fig, out_dir / f"escalation-pareto-{task}.png")


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="Corpus JSONL path")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    parser.add_argument("--task", default="subtype_classification",
                        help="Task to simulate (subtype/docclass/sorter)")
    parser.add_argument("--k-list", default="1,2,3,5,7,10,15,25",
                        help="Committee sizes to evaluate")
    parser.add_argument("--n-sim", type=int, default=400, help="Draws per (doc, K)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--escalated-acc", type=float, default=0.95,
                        help="Assumed accuracy of the escalated (stronger) model "
                             "(default 0.95 — the measured deepseek-v4-pro level "
                             "on the sorter surface; the baseline K=1 accuracy "
                             "on this corpus is ~0.92)")
    parser.add_argument("--escalated-cost", type=float, default=3.0,
                        help="Cost multiplier of the escalated model over base")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    valid = set(task_label_vocabulary(args.task))
    if not valid:
        print(f"WARNING: no label vocabulary for task {args.task!r} — nothing to do")
        return 1
    docs = load_observations(corpus, args.task, valid)
    if not docs:
        print(f"WARNING: no completed observations for task {args.task!r}")
        return 1

    k_list = [int(k) for k in args.k_list.split(",") if k.strip()]
    accuracy_by_k, per_class_by_k = simulate_committees(docs, k_list, args.n_sim, args.seed)
    confidence = build_confidence(docs)

    alpha_list = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    curve = escalation_curve(docs, confidence, alpha_list, args.escalated_acc,
                             base_cost=1.0, escalated_cost=args.escalated_cost)

    (out_dir / f"ensemble-voting-{args.task}.md").write_text(
        render_ensemble_report(docs, accuracy_by_k, per_class_by_k, confidence, args.task),
        encoding="utf-8")
    (out_dir / f"escalation-{args.task}.md").write_text(
        render_escalation_report(curve, args.task), encoding="utf-8")
    if not args.no_figures:
        make_figures(accuracy_by_k, curve, args.task, out_dir)

    order = sorted(confidence, key=confidence.get)
    n_candidates = max(1, int(round(0.15 * len(order))))
    candidates_path = out_dir / f"escalation_candidates-{args.task}.txt"
    candidates_path.write_text(
        "\n".join(f"{confidence[f]:.3f}\t{f}" for f in order[:n_candidates]) + "\n",
        encoding="utf-8")
    print(f"ensemble: accuracy(K=1) {accuracy_by_k[1]['estimate']:.4f} -> "
          f"K={k_list[-1]} {accuracy_by_k[k_list[-1]]['estimate']:.4f} "
          f"({len(docs)} docs, task {args.task})")
    print(f"candidates -> {candidates_path}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()