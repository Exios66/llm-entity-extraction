#!/usr/bin/env python3
"""A/B test two prompt versions on the SAME dataset and compare in Braintrust.

Runs experiment A then experiment B — identical model, temperature, dataset,
and scorers; only the prompt version differs — then fetches both experiments
and prints a side-by-side comparison (exact match, per-class accuracy, cost,
latency). Re-running with the same names overwrites the same experiments, so
an A/B pair is always a clean comparison.

To compare two already-run experiments without re-running the models, pass
``--experiment-a`` and ``--experiment-b`` (their names) with ``--compare-only``.

Usage:
    python scripts/eval/evaluate_prompt_version.py \\
        --dataset mailroom-cuad-contracts \\
        --prompt-a sorter_v0 --prompt-b sorter_v1 \\
        --experiment-a qwen3.7-flash_sorter_v0 --experiment-b qwen3.7-flash_sorter_v1

    python scripts/eval/evaluate_prompt_version.py --compare-only \\
        --experiment-a qwen3.7-flash_sorter_v0 --experiment-b qwen3.7-flash_sorter_v1
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import fetch_experiment_rows, find_experiment_by_name, list_experiments
from src.env_utils import require_env
from src.prompts import list_prompts
from src.scorers import ERROR_PREFIX, normalize_label
from scripts.eval.run_classification_eval import default_experiment_name

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


def _experiment_id(cfg, api_key: str, name: str) -> str:
    """Resolve an experiment name to its id (creating nothing)."""
    exp = find_experiment_by_name(api_key, cfg.project_id, name, cfg.api_base)
    if not exp:
        raise SystemExit(f"Experiment not found: {name!r} — run it first or fix --experiment-a/--experiment-b.")
    return exp["id"]


def _task_results(api_key: str, experiment_id: str, api_base: str) -> list[dict]:
    """Fetch an experiment and return scored task rows."""
    rows = fetch_experiment_rows(api_key, experiment_id, api_base)
    tasks = []
    for row in rows:
        if row.get("expected") is None:
            continue
        output = row.get("output")
        if output is None:
            continue
        tasks.append({
            "expected": str(row["expected"]).lower(),
            "output": str(output),
            "input": row.get("input"),
            "metadata": row.get("metadata") or {},
            "metrics": row.get("metrics") or {},
        })
    return tasks


def _summarize(tasks: list[dict]) -> dict:
    valid = [t for t in tasks if not t["output"].startswith(ERROR_PREFIX)]
    failed = len(tasks) - len(valid)
    total = len(valid)
    correct = sum(1 for t in valid if normalize_label(t["output"]) == t["expected"])
    by_class: dict[str, dict] = defaultdict(lambda: {"n": 0, "correct": 0})
    for t in valid:
        bucket = by_class[t["expected"]]
        bucket["n"] += 1
        bucket["correct"] += int(normalize_label(t["output"]) == t["expected"])
    per_class = {cls: (round(v["correct"] / v["n"], 4) if v["n"] else 0.0)
                 for cls, v in sorted(by_class.items())}
    total_cost = round(sum(float(t["metrics"].get("cost") or 0.0) for t in tasks), 6)
    return {
        "rows": total,
        "failed": failed,
        "correct": correct,
        "exact_match": round(correct / total, 4) if total else 0.0,
        "per_class": per_class,
        "total_cost": total_cost,
    }


def _prompt_version(tasks: list[dict]) -> str:
    for t in tasks:
        if t["metadata"].get("prompt_version"):
            return str(t["metadata"]["prompt_version"])
    return "?"


def print_comparison(summary_a: dict, summary_b: dict, name_a: str, name_b: str) -> None:
    def cell(s: dict, key: str) -> str:
        return f"{s[key]:.4f}" if isinstance(s[key], float) else str(s[key])

    print(f"\n== A/B: {name_a}  vs  {name_b} ==")
    print(f"{'metric':<16}{name_a:<24}{name_b:<24}")
    print(f"{'rows':<16}{summary_a['rows']:<24}{summary_b['rows']:<24}")
    print(f"{'exact_match':<16}{cell(summary_a, 'exact_match'):<24}{cell(summary_b, 'exact_match'):<24}")
    print(f"{'failed':<16}{summary_a['failed']:<24}{summary_b['failed']:<24}")
    print(f"{'total_cost_usd':<16}{summary_a['total_cost']:<24}{summary_b['total_cost']:<24}")

    classes = sorted(set(summary_a["per_class"]) | set(summary_b["per_class"]))
    print("\nPer-class accuracy:")
    print(f"{'class':<24}{name_a:<24}{name_b:<24}")
    for cls in classes:
        print(f"{cls:<24}{cell(summary_a['per_class'], cls) if cls in summary_a['per_class'] else '-':<24}"
              f"{cell(summary_b['per_class'], cls) if cls in summary_b['per_class'] else '-':<24}")

    delta = summary_b["exact_match"] - summary_a["exact_match"]
    verdict = "B wins" if delta > 0.001 else ("A wins" if delta < -0.001 else "tie")
    print(f"\ndelta exact_match (B - A): {delta:+.4f}  ->  {verdict}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name)
    parser.add_argument("--project-id", default=_CONFIG.project_id)
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--prompt-a", default="sorter_v0", help="Prompt version for experiment A")
    parser.add_argument("--prompt-b", default="sorter_v1", help="Prompt version for experiment B")
    parser.add_argument("--experiment-a", default=None, help="Experiment name for A (default: {model}_p{prompt-a})")
    parser.add_argument("--experiment-b", default=None, help="Experiment name for B (default: {model}_p{prompt-b})")
    parser.add_argument("--model", default=_CONFIG.model)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--compare-only", action="store_true",
                        help="Skip running; compare the two existing experiments")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")

    available = list_prompts()
    if not args.compare_only:
        for pv in (args.prompt_a, args.prompt_b):
            if pv not in available:
                parser.error(f"Unknown prompt version {pv!r}. Available: {available}")

    exp_a = args.experiment_a or default_experiment_name(args.model, args.prompt_a)
    exp_b = args.experiment_b or default_experiment_name(args.model, args.prompt_b)

    if not args.compare_only:
        if args.prompt_a == args.prompt_b and exp_a == exp_b:
            parser.error("prompt-a and prompt-b must differ (or use different experiment names).")

        from scripts.eval import run_classification_eval

        def run(prompt_version: str, experiment_name: str) -> int:
            argv = [
                "--dataset", args.dataset,
                "--prompt-version", prompt_version,
                "--model", args.model,
                "--experiment-name", experiment_name,
            ]
            if args.limit:
                argv += ["--limit", str(args.limit)]
            print(f"\n>>> Running experiment {experiment_name} (prompt {prompt_version})")
            return run_classification_eval.main_with_args(argv)

        if args.dry_run:
            print(f"Dry run: would run {exp_a} (prompt {args.prompt_a}) and {exp_b} (prompt {args.prompt_b})")
            return 0
        rc_a = run(args.prompt_a, exp_a)
        if rc_a != 0:
            return rc_a
        rc_b = run(args.prompt_b, exp_b)
        if rc_b != 0:
            return rc_b

    id_a = _experiment_id(_CONFIG, braintrust_key, exp_a)
    id_b = _experiment_id(_CONFIG, braintrust_key, exp_b)
    tasks_a = _task_results(braintrust_key, id_a, _CONFIG.api_base)
    tasks_b = _task_results(braintrust_key, id_b, _CONFIG.api_base)

    if not tasks_a or not tasks_b:
        print("WARNING: one of the experiments has no scored task rows; comparison is incomplete.",
              file=sys.stderr)

    print_comparison(_summarize(tasks_a), _summarize(tasks_b), exp_a, exp_b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
