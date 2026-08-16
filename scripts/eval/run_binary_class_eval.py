#!/usr/bin/env python3
"""Binary document classification eval: ONE prompt, ONE positive class.

The mailroom's core routing question is often binary: "is this a contract?"
(or any other class) vs "not". This runner tests a single prompt version on
the binary question and records precision/recall/F1 alongside exact match in
Braintrust — the numbers the routing layer will later be tuned against.

The task output is ``positive``/``negative`` (normalized from the sorter's
predicted doc class), so the dataset rows can come from ANY Braintrust
dataset (multi-class labels get folded into the binary label at load time).

Usage:
    python scripts/eval/run_binary_class_eval.py --dataset mailroom-cuad-contracts \\
        --positive contract --prompt-version sorter_v0
    python scripts/eval/run_binary_class_eval.py --positive correspondence \\
        --prompt-version sorter_v1 --scorers precision,recall,f1
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
from src.scorers import ERROR_PREFIX, normalize_label
from scripts.eval.run_classification_eval import default_experiment_name

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"
POSITIVE = "positive"
NEGATIVE = "negative"


def to_binary(expected: str, positive: str) -> str:
    """Fold a doc class into the binary label."""
    return POSITIVE if normalize_label(expected) == positive else NEGATIVE


def binary_dataset(dataset: list[dict], positive: str) -> list[dict]:
    """Return a copy of the dataset with expected folded to binary labels."""
    rows = []
    for row in dataset:
        rows.append({**row, "expected": to_binary(row["expected"], positive)})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name)
    parser.add_argument("--project-id", default=_CONFIG.project_id)
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset to evaluate")
    parser.add_argument("--positive", required=True, choices=DOC_CLASS_KEYS,
                        help="The positive class (e.g. contract)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N rows")
    parser.add_argument("--seed", type=int, default=42)
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
        f"{default_experiment_name(args.model, args.prompt_version)}_binary-{args.positive}"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset)
    total_rows = len(dataset)
    if args.sample:
        dataset = random.Random(args.seed).sample(dataset, min(args.sample, len(dataset)))
    if args.limit:
        dataset = dataset[: args.limit]
    dataset = binary_dataset(dataset, args.positive)
    validate_dataset(dataset, valid={POSITIVE, NEGATIVE})
    counts = Counter(d["expected"] for d in dataset)
    print(f"Binary dataset: {counts[POSITIVE]} positive / {counts[NEGATIVE]} negative")
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
        predicted = str(result.get("doc_type", "")).strip().lower()
        binary_pred = POSITIVE if predicted == args.positive else NEGATIVE
        braintrust.current_span().log(
            metadata={
                "filename": filename,
                "prompt_version": args.prompt_version,
                "predicted_class": predicted,
                "binary_prediction": binary_pred,
                "positive_class": args.positive,
                "reasoning": str(result.get("reasoning", "")),
                "confidence": result.get("confidence"),
            }
        )
        return binary_pred

    def precision(output, expected) -> float:
        """TP / (TP + FP): of rows predicted positive, how many were positive."""
        if output != POSITIVE:
            return 0.0
        return 1.0 if expected == POSITIVE else 0.0

    def recall(output, expected) -> float:
        """TP / (TP + FN): of positive rows, how many predicted positive."""
        if expected != POSITIVE:
            return 0.0
        return 1.0 if output == POSITIVE else 0.0

    def f1(output, expected) -> float:
        p = precision(output, expected)
        r = recall(output, expected)
        return 0.0 if p + r == 0 else 2 * p * r / (p + r)

    result = braintrust.Eval(
        args.project,
        data=lambda: [
            {"input": {"filename": d["filename"], "doc_text": d["doc_text"],
                       "expected": d["expected"]},
             "expected": d["expected"], "filename": d["filename"]}
            for d in dataset
        ],
        task=classify_document,
        scores=[precision, recall, f1],
        max_concurrency=args.max_concurrency,
        project_id=args.project_id,
        experiment_name=experiment_name,
        metadata={
            "prompt": prompt_text,
            "prompt_version": args.prompt_version,
            "model": args.model,
            "positive_class": args.positive,
            "dataset": f"{args.dataset_project}/{args.dataset}",
            "task": "binary_classification",
        },
        description=f"{args.model} | prompt {args.prompt_version} | binary positive={args.positive}",
    )

    print_binary_results(result, args.positive)
    braintrust.flush()
    return 0


def print_binary_results(result, positive: str) -> None:
    tp = fp = tn = fn = 0
    for r in result.results:
        if r.error is not None or str(r.output).startswith(ERROR_PREFIX):
            continue
        pred = str(r.output)
        exp = str(r.expected)
        if exp == POSITIVE and pred == POSITIVE:
            tp += 1
        elif exp == POSITIVE and pred != POSITIVE:
            fn += 1
        elif exp != POSITIVE and pred == POSITIVE:
            fp += 1
        else:
            tn += 1
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    print(f"\n== Binary results (positive={positive}) ==")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision={prec:.3f} recall={rec:.3f} f1={f1:.3f}")


if __name__ == "__main__":
    raise SystemExit(main())
