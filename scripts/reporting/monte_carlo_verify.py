#!/usr/bin/env python3
"""Spend-minimal verification of the Monte Carlo simulator's predictions.

Prints (or, with ``--run-eval``, executes) the eval commands that test the
simulator against reality, mirroring the RVL-CDIP-classifier's
``monte_carlo_verify.py``:

1. **Escalation verification** — the ``--alpha`` fraction of lowest-confidence
   documents (from the ensemble/confidence study) run at the base config; the
   *simulated* accuracy of that tail (per-document empirical ``p_correct``) is
   printed next to the command so measured-vs-simulated is readable after the
   run. The concrete filenames live in
   ``escalation_candidates-<task>.txt`` (written by ``monte_carlo_ensemble.py``).

2. **Exemplar verification** — documents whose expected label is in the top
   confusion pairs targeted by the exemplar miner, so a base prompt vs
   exemplar-appended prompt eval on the same slice can confirm the simulated
   error-flip gain.

No model credits are spent unless ``--run-eval`` is passed; the default is a
dry-run that prints the exact commands (the repo's funding gate is NOT
triggered — these use the default key and small samples).

Usage:
    python scripts/reporting/monte_carlo_verify.py --task subtype_classification
    python scripts/reporting/monte_carlo_verify.py --alpha 0.03
    python scripts/reporting/monte_carlo_verify.py --run-eval
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monte_carlo import (  # noqa: E402
    load_corpus,
    normalize_dist,
    task_label_vocabulary,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"

SUB_RUNNER = "python scripts/eval/run_langfuse_subtype_eval.py"
DOCCLASS_RUNNER = "python scripts/eval/run_langfuse_docclass_eval.py"


def tail_slice(corpus: list[dict], task: str, valid: set[str], alpha: float,
               seed: int) -> tuple[list[dict], float]:
    """The alpha fraction of lowest-confidence documents + their simulated
    per-document p_correct (mean of the empirical label distribution mass on
    the expected class)."""
    from scripts.reporting.monte_carlo_ensemble import build_confidence, load_observations

    docs = load_observations(corpus, task, valid)
    confidence = build_confidence(docs)
    order = sorted(confidence, key=confidence.get)
    n = max(1, int(round(alpha * len(order))))
    tail = order[:n]
    p_correct = []
    for filename in tail:
        doc = docs[filename]
        dist = normalize_dist(Counter(doc["observations"]))
        p_correct.append(dist.get(doc["expected"], 0.0))
    return [{"filename": f, "confidence": confidence[f]} for f in tail], \
        (sum(p_correct) / len(p_correct) if p_correct else 0.0)


def confusion_slice(corpus: list[dict], task: str, n_pairs: int = 2) -> list[str]:
    """Filenames whose expected label is in the top confusion pairs."""
    from scripts.reporting.monte_carlo_exemplars import confusion_pairs

    pairs = confusion_pairs(corpus, task)
    top_expected = {expected for (expected, _), _ in pairs.most_common(n_pairs * 2)}
    return sorted({r["filename"] for r in corpus
                   if r["task"] == task and r["expected"] in top_expected})


def render_plan(task: str, tail: list[dict], simulated_tail_acc: float,
                confusion: list[str], alpha: float, dry_run: bool) -> str:
    L = ["# Monte Carlo verification recipe (spend-minimal)", ""]
    L.append(f"_Task: `{task}` · dry-run: {dry_run} (no credits spent unless "
             "`--run-eval`)_")
    L.append("")
    L.append(f"## 1. Escalation tail ({len(tail)} lowest-confidence docs, "
             f"alpha {alpha:.0%})")
    L.append("")
    L.append(f"- **Simulated tail accuracy: {simulated_tail_acc:.4f}** (mean of "
             "the per-doc empirical p_correct) — compare with the measured "
             "accuracy of the command below.")
    L.append(f"- Filenames: `reports/monte_carlo/escalation_candidates-{task}.txt`")
    L.append("")
    runner = DOCCLASS_RUNNER if task == "docclass_classification" else SUB_RUNNER
    dataset = ("--local-dumps data/datasets/docclass_merged.jsonl"
               if task == "docclass_classification"
               else "--dataset mailroom-cuad-contracts-full")
    manifest = f"data/manifests/verify_{task}_tail.jsonl"
    dry = " --dry-run" if dry_run else ""
    L.append("```bash")
    L.append(f"{runner} {dataset} --sample {len(tail)} --seed 42 "
             f"--sorter-prompt-version sorter_v13 --manifest {manifest}{dry}")
    L.append("```")
    L.append("")
    L.append(f"## 2. Top-confusion-pair slice ({len(confusion)} docs)")
    L.append("")
    L.append("```bash")
    L.append(f"{runner} {dataset} --sample {min(len(confusion), 60)} --seed 42 "
             f"--sorter-prompt-version sorter_v13 "
             f"--manifest data/manifests/verify_{task}_confusion.jsonl{dry}")
    L.append("```")
    L.append("")
    L.append("Compare the measured accuracy on the slice against the simulator's "
             "K=1 expectation (the empirical distribution of the same docs); "
             "`--run-eval` executes only the first command (base config).")
    L.append("")
    return "\n".join(L)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--task", default="subtype_classification")
    parser.add_argument("--alpha", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-eval", action="store_true",
                        help="Execute the base-config tail eval (the only spend)")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    valid = set(task_label_vocabulary(args.task))
    tail, simulated_acc = tail_slice(corpus, args.task, valid, args.alpha, args.seed)
    confusion = confusion_slice(corpus, args.task)

    plan = render_plan(args.task, tail, simulated_acc, confusion,
                       args.alpha, dry_run=not args.run_eval)
    (out_dir / f"verify-{args.task}.md").write_text(plan, encoding="utf-8")
    print(plan)

    if args.run_eval and tail:
        import subprocess

        runner = (DOCCLASS_RUNNER if args.task == "docclass_classification"
                  else SUB_RUNNER)
        dataset = ("--local-dumps data/datasets/docclass_merged.jsonl"
                   if args.task == "docclass_classification"
                   else "--dataset mailroom-cuad-contracts-full")
        cmd = [sys.executable, *runner.split()[1:], dataset,
               "--sample", str(len(tail)), "--seed", "42",
               "--sorter-prompt-version", "sorter_v13",
               "--manifest", f"data/manifests/verify_{args.task}_tail.jsonl"]
        print(f"[verify] executing: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=ROOT).returncode
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()