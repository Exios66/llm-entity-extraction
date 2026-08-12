#!/usr/bin/env python3
"""Cross-model cost/quality matrix (GitHub issue #1).

Runs the SAME fixed sample (same dataset, seed, size — one surface) across a
small model x prompt-version grid and appends one experiment-log record per
cell (reusing the existing eval runners), then prints a matrix summary: score
+ bootstrap CI + cost per cell.

This turns "models are swappable via OpenRouter" into a measured fact — the
per-cell records carry the same dataset fingerprint, so the site's same-surface
guardrail and trend charts pick them up automatically.

Usage:
    python scripts/eval/run_model_matrix.py --task subtype \\
        --models qwen/qwen3.7-flash,deepseek/deepseek-v4-flash \\
        --prompts sorter_v5,sorter_v6 --sample 10 --seed 42
    python scripts/eval/run_model_matrix.py --task classification --models a,b \\
        --prompts sorter_v4 --sample 20 --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _cell_name(task: str, model: str, prompt: str) -> str:
    slug = model.split("/")[-1]
    return f"matrix_{task}_{slug}_{prompt}"


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=("subtype", "classification"), default="subtype",
                        help="which runner to loop (default subtype)")
    parser.add_argument("--models", required=True,
                        help="comma-separated OpenRouter model ids (2-3 recommended)")
    parser.add_argument("--prompts", required=True,
                        help="comma-separated prompt versions (top 2 recommended)")
    parser.add_argument("--sample", type=int, default=10,
                        help="fixed sample size per cell (default 10)")
    parser.add_argument("--seed", type=int, default=42,
                        help="fixed sample seed (default 42)")
    parser.add_argument("--dataset", default="mailroom-cuad-contracts-full",
                        help="Braintrust dataset to sample from")
    parser.add_argument("--dataset-project", default="mailroom-eval",
                        help="Braintrust project (default mailroom-eval)")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="override the experiment log path")
    parser.add_argument("--bt-scores", choices=("none", "overall", "full"),
                        default="none", help="Braintrust scorer registration per cell")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the grid plan without running anything")
    args = parser.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    prompts = [p.strip() for p in args.prompts.split(",") if p.strip()]
    if not models or not prompts:
        parser.error("--models and --prompts must each list at least one value")

    print(f"MODEL MATRIX PLAN — {args.task} — {len(models)} models x {len(prompts)} prompts "
          f"= {len(models) * len(prompts)} cells")
    print(f"  surface: dataset={args.dataset_project}/{args.dataset} "
          f"sample={args.sample} seed={args.seed} (identical across cells)")
    print(f"  bt_scores={args.bt_scores}")
    if args.dry_run:
        return 0

    for model in models:
        for prompt in prompts:
            experiment = _cell_name(args.task, model, prompt)
            print(f"\n=== cell {experiment} ===")
            if args.task == "subtype":
                from scripts.eval import run_subtype_eval

                cell_args = [
                    "--dataset", args.dataset,
                    "--dataset-project", args.dataset_project,
                    "--sample", str(args.sample),
                    "--seed", str(args.seed),
                    "--model", model,
                    "--sorter-prompt-version", prompt,
                    "--experiment-name", experiment,
                    "--bt-scores", args.bt_scores,
                    "--reasoning-effort", "medium",
                ]
                if args.experiment_log:
                    cell_args += ["--experiment-log", str(args.experiment_log)]
                rc = run_subtype_eval.main_with_args(cell_args)
            else:
                from scripts.eval import run_classification_eval

                cell_args = [
                    "--dataset", args.dataset,
                    "--dataset-project", args.dataset_project,
                    "--limit", str(args.sample),
                    "--sample-seed", str(args.seed),
                    "--model", model,
                    "--prompt-version", prompt,
                    "--experiment-name", experiment,
                    "--bt-scores", args.bt_scores,
                ]
                if args.experiment_log:
                    cell_args += ["--experiment-log", str(args.experiment_log)]
                rc = run_classification_eval.main_with_args(cell_args)
            if rc != 0:
                print(f"cell {experiment} failed (rc={rc})", file=sys.stderr)

    print_matrix(_load_records(args.experiment_log), task=args.task,
                 models=models, prompts=prompts)
    return 0


def _load_records(log_path: Path | None) -> list[dict]:
    path = Path(log_path) if log_path else Path("reports/experiment_log.jsonl")
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def print_matrix(records: list[dict], *, task: str, models: list[str], prompts: list[str]) -> None:
    """Score (+bootstrap CI) and cost per cell, prompts x models."""
    cells = {
        (r["experiment_name"], r.get("model", ""), r.get("prompt_version") or
         " + ".join((r.get("prompt_versions") or {}).values()))
        for r in records if r.get("experiment_name", "").startswith("matrix_")
    }
    if not cells:
        print("\nNo matrix cells found in the log.")
        return

    def _cell_value(record: dict) -> tuple:
        scores = record.get("scores") or {}
        sorter = scores.get("sorter") or {}
        if "subtype_accuracy" in sorter:
            value = sorter.get("subtype_accuracy")
            ci = sorter.get("subtype_accuracy_ci") or {}
        else:
            value = scores.get("exact_match")
            ci = scores.get("exact_match_ci") or {}
        tokens = record.get("tokens") or {}
        cost = (tokens.get("total") or tokens).get("cost_total_usd")
        return value, ci, cost

    print("\nMODEL MATRIX RESULTS — score (95% CI) | cost $")
    header = "prompt\\model".ljust(24) + "".join(m.split("/")[-1].ljust(30) for m in models)
    print(header)
    for prompt in prompts:
        row = prompt.ljust(24)
        for model in models:
            for r in records:
                pv = r.get("prompt_version") or " + ".join((r.get("prompt_versions") or {}).values())
                if r.get("experiment_name", "").startswith("matrix_") and r.get("model") == model \
                        and pv == prompt:
                    value, ci, cost = _cell_value(r)
                    if value is None:
                        cell = "—"
                    else:
                        ci_txt = f"[{ci['lo']:.2f}-{ci['hi']:.2f}]" if ci else "no CI"
                        cost_txt = f"{cost:.4f}" if isinstance(cost, (int, float)) else "?"
                        cell = f"{value:.3f} {ci_txt} ${cost_txt}"
                    row += cell.ljust(30)
                    break
            else:
                row += "—".ljust(30)
        print(row)
    print("\nCompare cells ONLY within this matrix (same sample surface); "
          "deltas whose bootstrap CIs overlap are not significant.")


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
