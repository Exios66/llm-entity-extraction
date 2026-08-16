#!/usr/bin/env python3
"""Paired-bootstrap prompt ablation over the joint corpus.

For every pair of prompt versions run on the SAME model, compares exact-match
outcomes on the SHARED document set using a paired bootstrap: per-document
deltas ``correct(A) - correct(B)`` are resampled with replacement, giving a
mean delta, a 95% confidence interval, and ``P(A beats B)`` (the fraction of
resamples with a positive mean delta). Per-class and per-confusion-pair deltas
are reported the same way so a prompt change is understood *where* it
wins/loses, not just that it moved overall.

This is the statistical gate for prompt iteration: a candidate version should
beat the incumbent on shared documents with a comfortably-high ``P(win)`` and a
CI that excludes zero before it is promoted (the same contract the repo's
same-surface A/B runs enforce, now evaluated corpus-wide over every recorded
run).

Usage:
    python scripts/reporting/monte_carlo_prompt_ablation.py
    python scripts/reporting/monte_carlo_prompt_ablation.py --min-shared 20
    python scripts/reporting/monte_carlo_prompt_ablation.py --task docclass_classification
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monte_carlo import load_corpus, paired_delta_bootstrap, task_label_vocabulary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"


def run_outcomes(corpus: list[dict], task: str,
                 valid_classes: set[str]) -> dict[tuple[str, str], dict[str, bool]]:
    """{(model, prompt_version): {filename: correct}} for completed label rows."""
    outcomes: dict[tuple[str, str], dict[str, bool]] = defaultdict(dict)
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        if (record.get("predicted") or "") not in valid_classes:
            continue
        key = (record.get("model") or "?", record.get("prompt_version") or "?")
        outcomes[key][record["filename"]] = bool(record.get("correct"))
    return dict(outcomes)


def pairs_with_shared_docs(outcomes: dict[tuple[str, str], dict[str, bool]],
                           min_shared: int) -> list[dict]:
    """All (A, B) prompt pairs on the same model with >= min_shared shared docs."""
    pairs = []
    for (model_a, prompt_a), docs_a in outcomes.items():
        for (model_b, prompt_b), docs_b in outcomes.items():
            if model_a != model_b or prompt_a == prompt_b:
                continue
            shared = sorted(set(docs_a) & set(docs_b))
            if len(shared) < min_shared:
                continue
            deltas = [float(docs_a[f]) - float(docs_b[f]) for f in shared]
            pairs.append({
                "model": model_a, "prompt_a": prompt_a, "prompt_b": prompt_b,
                "n_shared": len(shared), "deltas": deltas,
                "correct_a": sum(1 for f in shared if docs_a[f]),
                "correct_b": sum(1 for f in shared if docs_b[f]),
            })
    return pairs


def per_class_deltas(corpus: list[dict], task: str, prompt_a: str, prompt_b: str,
                     model: str, valid_classes: set[str]) -> dict[str, dict]:
    """Per-class paired deltas for the (A, B) pair (documents whose expected
    label is the class, present in both runs)."""
    by_class: dict[str, list[float]] = defaultdict(list)
    outcomes_a: dict[str, bool] = {}
    outcomes_b: dict[str, bool] = {}
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        if record.get("model") != model:
            continue
        if (record.get("predicted") or "") not in valid_classes:
            continue
        target = outcomes_a if record.get("prompt_version") == prompt_a else (
            outcomes_b if record.get("prompt_version") == prompt_b else None)
        if target is not None:
            target[record["filename"]] = bool(record.get("correct"))
    shared = sorted(set(outcomes_a) & set(outcomes_b))
    for filename in shared:
        expected = next(
            (r["expected"] for r in corpus
             if r["task"] == task and r["filename"] == filename and r["status"] == "completed"),
            "?")
        by_class[expected].append(float(outcomes_a[filename]) - float(outcomes_b[filename]))
    result = {}
    for cls, deltas in by_class.items():
        if len(deltas) < 5:
            continue
        stat = paired_delta_bootstrap(deltas, n_boot=2_000)
        stat["n_docs"] = len(deltas)
        result[cls] = stat
    return result


def render_report(pairs: list[dict], task: str) -> str:
    L = ["# Paired-bootstrap prompt ablation (Monte Carlo gate)", ""]
    L.append(f"_Task: `{task}` · corpus-wide paired bootstrap over shared documents_")
    L.append("")
    L.append("| model | prompt A | prompt B | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    ranked = sorted(pairs, key=lambda p: abs(p["deltas"] and (sum(p["deltas"]) / len(p["deltas"])) or 0.0),
                    reverse=True)
    for p in ranked[:40]:
        stat = paired_delta_bootstrap(p["deltas"], n_boot=2_000)
        acc_a = p["correct_a"] / p["n_shared"]
        acc_b = p["correct_b"] / p["n_shared"]
        L.append(f"| {p['model']} | {p['prompt_a']} | {p['prompt_b']} | {p['n_shared']} | "
                 f"{acc_a:.4f} | {acc_b:.4f} | {stat['mean']:+.4f} | "
                 f"[{stat['ci_lo']:+.4f}, {stat['ci_hi']:+.4f}] | {stat['p_win']:.3f} |")
    L.append("")
    L.append("Reading: `mean Δ > 0` favors A; a CI excluding zero with high "
             "`P(A beats B)` is the promotion signal (same contract as the "
             "repo's same-surface A/B runs).")
    L.append("")
    return "\n".join(L)


def render_class_report(corpus: list[dict], pairs: list[dict], task: str,
                        valid_classes: set[str]) -> str:
    L = ["# Prompt ablation — per-class deltas (worst/strongest movers)", ""]
    L.append(f"_Task: `{task}` — per-class paired deltas for the top pairs_")
    L.append("")
    for p in sorted(pairs, key=lambda p: -abs(sum(p["deltas"]) / len(p["deltas"])))[:6]:
        by_class = per_class_deltas(corpus, task, p["prompt_a"], p["prompt_b"],
                                    p["model"], valid_classes)
        L.append(f"## {p['prompt_a']} vs {p['prompt_b']} ({p['model']})")
        L.append("")
        L.append("| class | mean Δ | P(A beats B) | n docs |")
        L.append("|---|---|---|---|")
        for cls, stat in sorted(by_class.items(), key=lambda kv: kv[1]["mean"]):
            L.append(f"| {cls} | {stat['mean']:+.4f} | {stat['p_win']:.3f} | "
                     f"{stat.get('n_docs', len(stat.get('samples', [])))} |")
        L.append("")
    return "\n".join(L)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="Corpus JSONL path")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    parser.add_argument("--task", default="subtype_classification")
    parser.add_argument("--min-shared", type=int, default=20,
                        help="Minimum shared documents for a pair to be reported")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    valid = set(task_label_vocabulary(args.task))
    if not valid:
        return 1
    outcomes = run_outcomes(corpus, args.task, valid)
    pairs = pairs_with_shared_docs(outcomes, args.min_shared)
    if not pairs:
        print(f"no prompt pairs with >= {args.min_shared} shared docs (task {args.task})")
        return 0

    (out_dir / f"prompt-ablation-{args.task}.md").write_text(
        render_report(pairs, args.task), encoding="utf-8")
    (out_dir / f"prompt-ablation-classes-{args.task}.md").write_text(
        render_class_report(corpus, pairs, args.task, valid), encoding="utf-8")
    top = max(pairs, key=lambda p: sum(p["deltas"]) / len(p["deltas"]))
    stat = paired_delta_bootstrap(top["deltas"], n_boot=2_000)
    print(f"prompt ablation: {len(pairs)} pairs; strongest: {top['prompt_a']} vs "
          f"{top['prompt_b']} ({top['model']}, n={top['n_shared']}) mean Δ {stat['mean']:+.4f} "
          f"P(win) {stat['p_win']:.3f}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()