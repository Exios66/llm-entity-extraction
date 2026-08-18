#!/usr/bin/env python3
"""Benchmark directly-mirrored ContractEval runs against the paper's Table III.

Reads the repo experiment log for ``task: contracteval`` records (written by
``run_langfuse_contracteval_eval.py`` — the per-(contract, question) mirror of
arXiv 2508.03080) and compares each run's pooled metrics to the paper's full
19-model Table III, plus a per-category breakdown (the paper's Fig-4 analogue)
for the latest run.

Usage:
    python scripts/reporting/run_contracteval_report.py                       # latest record
    python scripts/reporting/run_contracteval_report.py --all                 # every record
    python scripts/reporting/run_contracteval_report.py --runs qwen3.7-flash
    python scripts/reporting/run_contracteval_report.py --output reports/contracteval_benchmark.md
    python scripts/reporting/run_contracteval_report.py --json reports/contracteval_benchmark.json

Offline and free — reads the committed experiment log only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracteval import CONTRACTEVAL_TABLE_III  # noqa: E402

DEFAULT_LOG = "reports/experiment_log.jsonl"


def load_records(path: str) -> list[dict]:
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def contracteval_records(records: list[dict], runs: list[str] | None,
                         all_runs: bool) -> list[dict]:
    """Select ``task: contracteval`` records (newest first)."""
    selected = [r for r in records if r.get("task") == "contracteval"]
    selected.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    if all_runs:
        return selected
    if runs:
        picked = [r for r in selected if any(name in (r.get("experiment_name") or "")
                                             for name in runs)]
        return picked
    return selected[:1]  # latest by default


def display_name(record: dict) -> str:
    model = (record.get("model") or "").split("/")[-1]
    exp = record.get("experiment_name") or ""
    version = "?"
    for token in exp.split("_"):
        if token.startswith("contracteval_v") or (token.startswith("v") and token[1:2].isdigit()):
            version = token
            break
    return f"{model} {version}"


def format_report(records: list[dict], include_reference: bool = True) -> str:
    lines = [
        "# Directly-mirrored ContractEval benchmark",
        "",
        "Pooled over the CUAD test split (one (contract, question) call per row; "
        "faithful full-context, temp 0, max_tokens 5000) using ContractEval's EXACT "
        "rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the "
        "output; token-set Jaccard over positive pairs; false-'no related clause' rate.",
        "",
        "| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr (own) | false-nr (paper/1244) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        s = r["scores"]
        lines.append(
            f"| {display_name(r)} | {s['n_pairs']} | {s['n_positive']} | "
            f"{s['accuracy']:.3f} | {s['precision']:.3f} | {s['recall']:.3f} | "
            f"{s['f1']:.3f} | {s['f2']:.3f} | {s['jaccard_mean']:.3f} | "
            f"{s['false_no_related_rate']:.3f} | {s['false_no_related_rate_paper']:.3f} |"
        )
    if include_reference:
        lines += [
            "",
            "ContractEval Table III reference (F1/F2/Jaccard/false-nr, paper's own 1,244-"
            "positive denominator):",
            "",
            "| Model | F1 | F2 | Jacc | false-nr |",
            "|---|---|---|---|---|",
        ]
        for model, ref in CONTRACTEVAL_TABLE_III.items():
            lines.append(
                f"| {model} | {ref['f1']:.3f} | {ref['f2']:.3f} | "
                f"{ref['jaccard']:.3f} | {ref['false_no_related']:.3f} |"
            )
        lines += [
            "",
            "**Caveat:** our runs use this repo's OpenRouter models (not the paper's exact "
            "model set) — the comparison is same-shape/same-metric, not same-model. The "
            "false-nr column 'own' divides by the run's own positive count; 'paper/1244' "
            "divides by the paper's hardcoded 1,244 positives (identical on the full test "
            "set).",
        ]

    # Per-category breakdown for the LATEST record (paper Fig-4 analogue).
    if records:
        latest = records[0]
        pc = latest["scores"].get("per_category") or {}
        if pc:
            lines += [
                "",
                f"## Per-category breakdown — {display_name(latest)} (Fig-4 analogue)",
                "",
                "| Category | n_pairs | n_pos | P | R | F1 | F2 | Jacc |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for cat, c in sorted(pc.items(), key=lambda kv: -kv[1]["f1"]):
                lines.append(
                    f"| {cat} | {c['n_pairs']} | {c['n_positive']} | "
                    f"{c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} | "
                    f"{c['f2']:.3f} | {c['jaccard_mean']:.3f} |"
                )
    return "\n".join(lines)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-log", default=DEFAULT_LOG)
    parser.add_argument("--runs", help="comma-separated experiment-name substrings")
    parser.add_argument("--all", action="store_true",
                        help="score every stored contracteval record")
    parser.add_argument("--output", help="write the markdown report to this path")
    parser.add_argument("--json", dest="json_out", help="write machine-readable metrics to this path")
    parser.add_argument("--no-reference", action="store_true",
                        help="omit the Table III reference table")
    args = parser.parse_args(argv)

    records = contracteval_records(
        load_records(args.experiment_log),
        [r.strip() for r in args.runs.split(",")] if args.runs else None,
        args.all,
    )
    if not records:
        print("No contracteval records in the experiment log.", file=sys.stderr)
        return 2

    report = format_report(records, include_reference=not args.no_reference)
    print(report)

    if args.output:
        Path(args.output).write_text(report)
        print(f"\n[written] {args.output}")
    if args.json_out:
        payload = {
            "reference_table_iii": CONTRACTEVAL_TABLE_III,
            "runs": [{k: v for k, v in {
                "experiment_name": r.get("experiment_name"),
                "model": r.get("model"),
                "prompt_version": r.get("prompt_version"),
                "scores": r.get("scores"),
                "tokens": r.get("tokens"),
            }.items() if k != "results"} for r in records],
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2))
        print(f"[written] {args.json_out}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
