#!/usr/bin/env python3
"""Post-hoc extraction scoring from a run manifest — NO Braintrust scorers.

The extraction eval (``scripts/eval/run_extraction_eval.py``) scores every
field LOCALLY (deterministic field-type-aware content scoring) and appends
each row's predicted extraction, expected fields, and per-field scores to a
JSONL manifest. This script reads that manifest and produces the full report:

- per-field mean content scores (date/money/name/free-text, entity-list F1)
- overall extraction score
- binary conformance (field_presence, schema_valid)
- per-document table: every field score + ambiguous-band flags
- judge-eligible rows (fields in the ambiguous band)

It never touches Braintrust scoring — the manifest is the durable record, so
re-running this costs nothing and re-scoring after a scorer change is just a
re-run of this script.

Usage:
    python scripts/reporting/score_extraction_manifest.py data/manifests/extract_v2.jsonl
    python scripts/reporting/score_extraction_manifest.py data/manifests/extract_v2.jsonl \\
        --output reports/extraction_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.field_scoring import get_field_types, score_extraction

FIELD_TYPES = get_field_types("contract")


def load_manifest(path: Path) -> list[dict]:
    """Read a run manifest, skipping the header line."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("type") == "header":
            continue
        rows.append(record)
    return rows


def score_row(record: dict) -> dict:
    """Recompute the deterministic content scores for one manifest row."""
    predicted = record.get("predicted") or {}
    expected = record.get("expected_fields") or {}
    result = score_extraction("contract", FIELD_TYPES, predicted, expected)
    populated = sum(
        1 for key, value in expected.items() if predicted.get(key) not in (None, "", [])
    )
    field_presence = populated / len(expected) if expected else 0.0
    schema_valid = 0.0 if predicted.get("_parse_error") else 1.0
    return {
        "filename": record.get("filename", "?"),
        "status": record.get("status", "?"),
        "expected_fields": expected,
        "field_scores": result.field_scores,
        "overall_score": result.overall_score,
        "ambiguous_fields": result.ambiguous_fields,
        "entity_list_f1": {k: v.f1 for k, v in result.entity_list_scores.items()},
        "field_presence": field_presence,
        "schema_valid": schema_valid,
        "predicted": predicted,
    }


def summarize(rows: list[dict]) -> dict:
    """Aggregate per-field means + overall + presence across rows."""
    totals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["status"] != "completed":
            continue
        if row["overall_score"] is not None:
            totals["overall"].append(row["overall_score"])
        totals["field_presence"].append(row["field_presence"])
        totals["schema_valid"].append(row["schema_valid"])
        for key, value in row["field_scores"].items():
            totals[key].append(value)
    return {
        key: {"n": len(values), "mean": round(sum(values) / len(values), 4)}
        for key, values in totals.items() if values
    }


def render_markdown(rows: list[dict], summary: dict, manifest_path: Path) -> str:
    lines = [
        f"# Extraction scoring report — {manifest_path.name}",
        "",
        f"Rows: {len([r for r in rows if r['status'] == 'completed'])} completed",
        "",
        "## Per-field content scores (mean over scored rows)",
        "",
        "| field | n | mean |",
        "|-------|---|------|",
    ]
    for key in ["overall", "field_presence", "schema_valid"] + sorted(
        k for k in summary if k not in ("overall", "field_presence", "schema_valid")
    ):
        stat = summary.get(key)
        if stat:
            lines.append(f"| {key} | {stat['n']} | {stat['mean']} |")

    lines += ["", "## Per-document scores", "",
              "| document | overall | ambiguous | field scores |", "|----------|---------|-----------|--------------|"]
    for row in rows:
        if row["status"] != "completed":
            continue
        amb = ",".join(row["ambiguous_fields"]) or "-"
        fields = "; ".join(f"{k}={v:.3f}" for k, v in sorted(row["field_scores"].items()))
        overall = f"{row['overall_score']:.4f}" if row["overall_score"] is not None else "-"
        lines.append(f"| {row['filename']} | {overall} | {amb} | {fields} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSONL run manifest from run_extraction_eval.py")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write a markdown report here (default: stdout)")
    args = parser.parse_args()

    if not args.manifest.exists():
        parser.error(f"Manifest not found: {args.manifest} (run run_extraction_eval.py --manifest first)")
    records = load_manifest(args.manifest)
    if not records:
        parser.error(f"Manifest {args.manifest} has no row records.")

    rows = [score_row(r) for r in records]
    summary = summarize(rows)

    print("\n== Post-hoc extraction scoring (local, deterministic) ==")
    print(f"rows: {len(rows)}")
    for key in ["overall", "field_presence", "schema_valid"] + sorted(
        k for k in summary if k not in ("overall", "field_presence", "schema_valid")
    ):
        stat = summary.get(key)
        if stat:
            print(f"{key:<28} n={stat['n']:<4} mean={stat['mean']:.4f}")

    judge_rows = [r for r in rows if r["status"] == "completed" and r["ambiguous_fields"]]
    if judge_rows:
        print(f"\n{len(judge_rows)} row(s) have ambiguous-band fields (judge-eligible):")
        for r in judge_rows:
            print(f"  {r['filename']}: {','.join(r['ambiguous_fields'])}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(rows, summary, args.manifest), encoding="utf-8")
        print(f"\nMarkdown report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
