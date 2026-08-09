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

from src.field_scoring import (
    get_field_types,
    score_category_presence,
    score_extraction,
)

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


def score_row(record: dict, doc_text: str | None = None,
              doc_category: str | None = None, clause_labels: list[dict] | None = None) -> dict:
    """Recompute the deterministic content scores for one manifest row.

    ``doc_text`` enables the factuality guard: every predicted list item must
    match a ground-truth label or be grounded in the source document text
    (verified_precision / hallucination_rate in the returned audit).
    ``doc_category`` (CUAD contract type) + ``clause_labels`` rebuild the
    TYPE-AWARE expected fields (per the dataset card, the document's group
    decides what fields to expect) and the YES/NO presence expectations.
    """
    from src.cuad_ground_truth import build_expected_fields, build_presence_expectations

    if doc_category is not None and clause_labels is not None:
        expected = build_expected_fields(clause_labels, doc_category=doc_category)
        presence = build_presence_expectations(clause_labels, doc_category=doc_category)
    else:
        expected = record.get("expected_fields") or {}
        presence = None
    predicted = record.get("predicted") or {}
    result = score_extraction("contract", FIELD_TYPES, predicted, expected,
                              doc_text=doc_text)
    populated = sum(
        1 for key, value in expected.items() if predicted.get(key) not in (None, "", [])
    )
    field_presence = populated / len(expected) if expected else 0.0
    schema_valid = 0.0 if predicted.get("_parse_error") else 1.0
    category_presence, presence_detail = (None, None)
    if presence is not None:
        category_presence, presence_detail = score_category_presence(
            predicted, presence, FIELD_TYPES
        )
    return {
        "filename": record.get("filename", "?"),
        "status": record.get("status", "?"),
        "expected_fields": expected,
        "field_scores": result.field_scores,
        "overall_score": result.overall_score,
        "ambiguous_fields": result.ambiguous_fields,
        # The list score that feeds the per-field score (GT coverage for
        # partial-GT fields, F1 otherwise); raw precision/recall/f1 stay in
        # ``entity_list_scores`` for audit.
        "entity_list_f1": {k: v.score for k, v in result.entity_list_scores.items()},
        "entity_list_scores": {
            k: {"precision": v.precision, "recall": v.recall, "f1": v.f1}
            for k, v in result.entity_list_scores.items()
        },
        "entity_list_audit": result.entity_list_audit,
        "overall_verified_precision": result.overall_verified_precision,
        "category_presence": category_presence,
        "presence_detail": presence_detail,
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
        if row.get("overall_verified_precision") is not None:
            totals["overall_verified_precision"].append(row["overall_verified_precision"])
        if row.get("category_presence") is not None:
            totals["category_presence"].append(row["category_presence"])
        for key, value in row["field_scores"].items():
            totals[key].append(value)
        for key, audit in (row.get("entity_list_audit") or {}).items():
            totals[f"{key}_verified_precision"].append(audit["verified_precision"])
            totals[f"{key}_hallucination_rate"].append(audit["hallucination_rate"])
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
              "| document | overall | verified_prec | ambiguous | field scores |",
              "|----------|---------|---------------|-----------|--------------|"]
    for row in rows:
        if row["status"] != "completed":
            continue
        amb = ",".join(row["ambiguous_fields"]) or "-"
        fields = "; ".join(f"{k}={v:.3f}" for k, v in sorted(row["field_scores"].items()))
        overall = f"{row['overall_score']:.4f}" if row["overall_score"] is not None else "-"
        vprec = (f"{row['overall_verified_precision']:.4f}"
                 if row.get("overall_verified_precision") is not None else "-")
        lines.append(f"| {row['filename']} | {overall} | {vprec} | {amb} | {fields} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSONL run manifest from run_extraction_eval.py")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write a markdown report here (default: stdout)")
    parser.add_argument("--dataset", default=None,
                        help="Braintrust dataset name: enable the FACTUALITY guard — every "
                             "predicted list item is verified against the row's source document "
                             "text (verified_precision / hallucination_rate)")
    parser.add_argument("--dataset-project", default=None,
                        help="Project holding the dataset (default: braintrust.env config)")
    args = parser.parse_args()

    if not args.manifest.exists():
        parser.error(f"Manifest not found: {args.manifest} (run run_extraction_eval.py --manifest first)")
    records = load_manifest(args.manifest)
    if not records:
        parser.error(f"Manifest {args.manifest} has no row records.")

    doc_text_by_filename: dict[str, str] = {}
    category_by_filename: dict[str, str] = {}
    labels_by_filename: dict[str, list[dict]] = {}
    if args.dataset:
        from src.braintrust_config import load_braintrust_config
        from src.braintrust_utils import load_braintrust_dataset

        cfg = load_braintrust_config()
        dataset_rows = load_braintrust_dataset(
            args.dataset_project or cfg.dataset_project, args.dataset,
            project_id=cfg.project_id,
        )
        for r in dataset_rows:
            doc_text_by_filename[r["filename"]] = r["doc_text"]
            category_by_filename[r["filename"]] = (r.get("metadata") or {}).get("category") or None
            labels_by_filename[r["filename"]] = r.get("clause_labels") or []
        print(f"Factuality guard ON: {len(doc_text_by_filename)} documents loaded "
              f"from {args.dataset} for source verification")

    rows = [
        score_row(
            r,
            doc_text_by_filename.get(r.get("filename")),
            category_by_filename.get(r.get("filename")),
            labels_by_filename.get(r.get("filename")),
        )
        for r in records
    ]
    summary = summarize(rows)

    print("\n== Post-hoc extraction scoring (local, deterministic) ==")
    print(f"rows: {len(rows)}")
    for key in ["overall", "field_presence", "schema_valid", "overall_verified_precision",
                "category_presence"] + sorted(
        k for k in summary if k not in ("overall", "field_presence", "schema_valid",
                                        "overall_verified_precision", "category_presence")
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
