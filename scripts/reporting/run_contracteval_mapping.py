#!/usr/bin/env python3
"""Benchmark stored extraction runs against ContractEval (arXiv 2508.03080).

Maps every disaggregated predicted obligation span to its CUAD category
against ``data/cuad/master_clauses.csv`` and scores the stored runs with
ContractEval's EXACT rubric (verbatim-containment TP, pooled correctness
F1/F2, token-set Jaccard over positive pairs, false-"no related clause" rate),
then compares to ContractEval Table III.

Usage:
    python scripts/reporting/run_contracteval_mapping.py                      # champion + llama set
    python scripts/reporting/run_contracteval_mapping.py --runs v32,llama-4-scout
    python scripts/reporting/run_contracteval_mapping.py --all                # every extraction record
    python scripts/reporting/run_contracteval_mapping.py --output reports/contracteval_benchmark.md
    python scripts/reporting/run_contracteval_mapping.py --json reports/contracteval_benchmark.json

Offline and free — reads the committed master GT + the experiment log only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.contracteval import (  # noqa: E402
    CONTRACTEVAL_TABLE_III,
    coverage_bands,
    evaluate_record,
    format_report,
    load_master_gt,
)

DEFAULT_GT = "data/cuad/master_clauses.csv"
DEFAULT_LOG = "reports/experiment_log.jsonl"

# The default comparison set: the champion (qwen3.7-flash v32 clean full
# corpus) + its v31 predecessor + the llama-4-scout v31 full-corpus run.
DEFAULT_RUNS = [
    "qwen3.7-flash_contracts_specialist_v32_extraction_langfuse_510_full_clean",
    "qwen3.7-flash_contracts_specialist_v31_extraction_langfuse_510_full",
    "llama-4-scout_contracts_specialist_v31_extraction_langfuse",
]


def load_records(path: str) -> list[dict]:
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_records(records: list[dict], runs: list[str] | None,
                   all_runs: bool) -> list[dict]:
    if all_runs:
        return [r for r in records if r.get("task") == "contract_entity_extraction"]
    if runs:
        picked = []
        for name in runs:
            matches = [r for r in records
                       if r.get("task") == "contract_entity_extraction"
                       and (name in (r.get("experiment_name") or ""))]
            if not matches:
                print(f"WARNING: no extraction record matches {name!r}", file=sys.stderr)
            picked.extend(matches)
        return picked
    picked = []
    for name in DEFAULT_RUNS:
        matches = [r for r in records
                   if r.get("task") == "contract_entity_extraction"
                   and (r.get("experiment_name") or "") == name]
        if not matches:
            print(f"WARNING: default run not found: {name}", file=sys.stderr)
        picked.extend(matches)
    return picked


def display_name(record: dict) -> str:
    model = (record.get("model") or "").split("/")[-1]
    exp = record.get("experiment_name") or ""
    version = "?"
    for token in exp.split("_"):
        if token.startswith("v") and token[1:2].isdigit():
            version = token
            break
    return f"{model} {version}"


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-gt", default=DEFAULT_GT)
    parser.add_argument("--experiment-log", default=DEFAULT_LOG)
    parser.add_argument("--runs", help="comma-separated experiment-name substrings")
    parser.add_argument("--all", action="store_true",
                        help="score every stored extraction record")
    parser.add_argument("--output", help="write the markdown report to this path")
    parser.add_argument("--json", dest="json_out", help="write machine-readable metrics to this path")
    args = parser.parse_args(argv)

    master_gt = load_master_gt(args.master_gt)
    records = load_records(args.experiment_log)
    runs = [r.strip() for r in args.runs.split(",")] if args.runs else None
    selected = select_records(records, runs, args.all)
    if not selected:
        print("No extraction records selected.", file=sys.stderr)
        return 2

    results: dict[str, dict] = {}
    for record in selected:
        name = display_name(record)
        metrics = evaluate_record(record, master_gt)
        bands = coverage_bands(record, master_gt)
        metrics["coverage_bands"] = bands
        results[name] = metrics

    report = format_report(results, include_reference=True)
    report += (
        "\n\n## Semantic-coverage companion (contained-label lens)\n\n"
        "Share of positive-label (doc, category) pairs whose best predicted-span "
        "containment against the GT label reaches each band. Verbatim = "
        "ContractEval's exact-substring TP; the wider bands quantify the "
        "paraphrase penalty this repo's field-type-aware scorer is designed to "
        "absorb.\n\n"
        "| Run | n_pos | verbatim | >=0.7 | >=0.5 | >=0.3 |\n"
        "|---|---|---|---|---|---|\n"
    )
    for name, m in results.items():
        b = m["coverage_bands"]
        report += (
            f"| {name} | {b['n_pos']} | {b['verbatim']:.3f} | {b['ge0_7']:.3f} | "
            f"{b['ge0_5']:.3f} | {b['ge0_3']:.3f} |\n"
        )
    report += (
        "\n## Scope notes\n\n"
        "- Task unit: ContractEval asks one (contract, question) per category; "
        "this pipeline extracts the obligation lists in one pass, so each "
        "predicted span is mapped to the CUAD category whose label it covers "
        "(verbatim, else best containment >= 0.5). Only the 32 YES/NO "
        "obligation categories are scored (the pipeline has no per-question "
        "surface for the string-answer categories).\n"
        "- Precision is structurally 1.0 (a one-pass extractor never claims a "
        "category the GT marks absent), so F1 tracks recall and is NOT directly "
        "comparable to ContractEval's precision-constrained F1.\n"
        "- GT = `data/cuad/master_clauses.csv` (full clause spans per "
        "category); rows joined by aggressive filename normalization.\n"
    )
    print(report)

    if args.output:
        Path(args.output).write_text(report)
        print(f"\n[written] {args.output}")
    if args.json_out:
        payload = {
            "reference_table_iii": CONTRACTEVAL_TABLE_III,
            "runs": {name: {k: v for k, v in m.items() if k != "rows"}
                     for name, m in results.items()},
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2))
        print(f"[written] {args.json_out}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
