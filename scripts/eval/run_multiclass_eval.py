#!/usr/bin/env python3
"""Multiclass document classification eval: ONE prompt, all taxonomy classes.

Runs the sorter (LangChain) against a multi-class Braintrust dataset and
records per-class accuracy plus macro accuracy in Braintrust, so a single
experiment surfaces both the aggregate and where the prompt confuses classes.

Identical experiment naming to ``run_classification_eval`` except the task
output is the raw doc class and the scorer set adds ``macro_accuracy``; rows
are additionally tagged with per-class metadata for the confusion-matrix
reports.

Usage:
    python scripts/eval/run_multiclass_eval.py --dataset mailroom-pilot-docs \\
        --prompt-version sorter_v0
    python scripts/eval/run_multiclass_eval.py --samples-per-class 4 --sample-seed 7
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from braintrust.integrations.langchain import setup_langchain

import braintrust

from agents.sorter_agent import DOC_CLASS_KEYS, SorterAgent
from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import load_braintrust_dataset
from src.env_utils import add_research_funding_flag, assert_production_run, require_env, resolve_openrouter_key
from src.evaluation import validate_dataset
from src.prompts import DEFAULT_PROMPT_VERSION, list_prompts
from src.scorers import ERROR_PREFIX, macro_accuracy, normalize_label
from scripts.eval.run_classification_eval import default_experiment_name

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-pilot-docs"


def sample_balanced(dataset: list[dict], samples_per_class: int, seed: int = 42) -> list[dict]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in dataset:
        by_class[row["expected"]].append(row)
    rng = random.Random(seed)
    sampled: list[dict] = []
    for cls in sorted(by_class):
        available = by_class[cls]
        sampled.extend(rng.sample(available, min(samples_per_class, len(available))))
    rng.shuffle(sampled)
    return sampled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name)
    parser.add_argument("--project-id", default=_CONFIG.project_id)
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset to evaluate")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--samples-per-class", type=int, default=None,
                        help="Deterministically subsample N rows per class")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--model", default=_CONFIG.model)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION,
                        help="One prompt version per experiment")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-concurrency", type=int, default=8)
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--dry-run", action="store_true")
    add_research_funding_flag(parser)
    args = parser.parse_args()

    openrouter_key = resolve_openrouter_key(args.research_funding_key)
    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")

    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{default_experiment_name(args.model, args.prompt_version)}_multiclass"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset)
    total_rows = len(dataset)
    if args.samples_per_class:
        dataset = sample_balanced(dataset, args.samples_per_class, args.sample_seed)
    if args.limit:
        dataset = dataset[: args.limit]
    validate_dataset(dataset)
    print(f"Multiclass dataset: {len(dataset)} rows, classes {dict(Counter(d['expected'] for d in dataset))}")
    assert_production_run(args.research_funding_key, dry_run=args.dry_run,
                          selected_rows=len(dataset), total_rows=total_rows)

    if args.dry_run:
        print(f"Dry run: experiment '{experiment_name}' on {len(dataset)} rows")
        return 0

    setup_langchain(api_key=braintrust_key, project_id=args.project_id, project_name=args.project)

    from src.prompts import get_prompt

    prompt_text = get_prompt(args.prompt_version)

    @braintrust.traced
    def classify_document(input_data: dict) -> str:
        filename = input_data["filename"]
        sorter = SorterAgent(model=args.model, api_key=openrouter_key,
                             prompt_version=args.prompt_version)
        sorter._max_input_chars = 12000
        try:
            result = sorter.classify_json(input_data["doc_text"])
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return f"{ERROR_PREFIX}{filename}"
        predicted = normalize_label(result.get("doc_type", ""))
        braintrust.current_span().log(
            metadata={
                "filename": filename,
                "prompt_version": args.prompt_version,
                "predicted_class": predicted,
                "reasoning": str(result.get("reasoning", "")),
                "confidence": result.get("confidence"),
            }
        )
        return predicted if predicted in DOC_CLASS_KEYS else f"{ERROR_PREFIX}invalid-class"

    result = braintrust.Eval(
        args.project,
        data=lambda: [
            {"input": {"filename": d["filename"], "doc_text": d["doc_text"],
                       "expected": d["expected"]},
             "expected": d["expected"], "filename": d["filename"]}
            for d in dataset
        ],
        task=classify_document,
        scores=[macro_accuracy],
        max_concurrency=args.max_concurrency,
        project_id=args.project_id,
        experiment_name=experiment_name,
        metadata={
            "prompt": prompt_text,
            "prompt_version": args.prompt_version,
            "model": args.model,
            "dataset": f"{args.dataset_project}/{args.dataset}",
            "task": "multiclass_classification",
            "classes": DOC_CLASS_KEYS,
        },
        description=f"{args.model} | prompt {args.prompt_version} | multiclass ({len(DOC_CLASS_KEYS)} classes)",
    )

    print_multiclass_results(result)
    braintrust.flush()
    return 0


def print_multiclass_results(result) -> None:
    by_expected: dict[str, list[str]] = defaultdict(list)
    failed = 0
    for r in result.results:
        if r.error is not None:
            failed += 1
            continue
        output = str(r.output)
        if output.startswith(ERROR_PREFIX):
            failed += 1
            continue
        by_expected[normalize_label(r.expected)].append(normalize_label(output))

    print("\n== Per-class accuracy ==")
    accs = []
    for cls in sorted(by_expected):
        rows = by_expected[cls]
        correct = sum(1 for pred in rows if pred == cls)
        acc = correct / len(rows)
        accs.append(acc)
        print(f"{cls:<24} {correct}/{len(rows)} ({acc:.1%})")
    if accs:
        print(f"\nmacro accuracy: {sum(accs) / len(accs):.3f}")
    if failed:
        print(f"{failed} failed rows (tracked as `failure`)")


if __name__ == "__main__":
    raise SystemExit(main())
