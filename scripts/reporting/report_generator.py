#!/usr/bin/env python3
"""Generate a markdown experiment report from a Braintrust experiment.

Fetches the scored task rows of an experiment and writes
``reports/report_<experiment>.md`` containing:

- run metadata (prompt version, model, dataset, experiment id)
- aggregate exact-match + failure counts
- per-class accuracy table
- confusion matrix table (expected x predicted)
- the misclassification ledger: every wrong row with filename, expected,
  predicted, confidence, and reasoning (capped via ``--max-misses``)

Usage:
    python scripts/reporting/report_generator.py --experiment qwen3.7-flash_sorter_v0
    python scripts/reporting/report_generator.py --experiment qwen3.7-flash_sorter_v0 \
        --output-dir reports --max-misses 50
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import fetch_experiment_rows, find_experiment_by_name, resolve_prompt_version
from src.env_utils import require_env
from src.scorers import ERROR_PREFIX, normalize_label
from src.taxonomy import doc_class_keys

_CONFIG = load_braintrust_config()


def _task_rows(rows: list[dict]) -> list[dict]:
    span_meta: dict[str, dict] = {}
    for row in rows:
        root = row.get("root_span_id") or row.get("span_id") or ""
        metadata = row.get("metadata") or {}
        if isinstance(metadata, dict) and (metadata.get("reasoning") or metadata.get("filename")):
            span_meta.setdefault(root, {}).update(metadata)

    tasks = []
    for row in rows:
        if row.get("expected") is None or row.get("output") is None:
            continue
        root = row.get("root_span_id") or row.get("span_id") or ""
        meta = dict(row.get("metadata") or {})
        meta.update(span_meta.get(root, {}))
        tasks.append({
            "expected": str(row["expected"]).lower(),
            "output": str(row["output"]),
            "input": row.get("input") or {},
            "metadata": meta,
            "metrics": row.get("metrics") or {},
        })
    return tasks


def _filename(input_data) -> str:
    if isinstance(input_data, dict):
        return str(input_data.get("filename") or "")
    return ""


def render_report(experiment_meta: dict, rows: list[dict]) -> str:
    tasks = _task_rows(rows)
    prompt_version = resolve_prompt_version(experiment_meta)
    experiment_id = experiment_meta.get("id", "?")
    classes = doc_class_keys()

    valid = [t for t in tasks if not t["output"].startswith(ERROR_PREFIX)]
    failed = [t for t in tasks if t["output"].startswith(ERROR_PREFIX)]
    correct = sum(1 for t in valid if normalize_label(t["output"]) == t["expected"])
    accuracy = correct / len(valid) if valid else 0.0

    # Per-class
    by_class: dict[str, dict] = defaultdict(lambda: {"n": 0, "correct": 0})
    for t in valid:
        b = by_class[t["expected"]]
        b["n"] += 1
        b["correct"] += int(normalize_label(t["output"]) == t["expected"])

    # Confusion matrix
    matrix: dict[str, Counter] = {c: Counter() for c in classes}
    for t in valid:
        expected = t["expected"] if t["expected"] in matrix else "unknown"
        matrix[expected][normalize_label(t["output"])] += 1

    # Misclassification ledger
    misses = [
        t for t in valid if normalize_label(t["output"]) != t["expected"]
    ]
    misses.sort(key=lambda t: t["expected"])

    lines = [
        f"# Experiment report — {experiment_meta.get('name', '?')}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Run metadata",
        "",
        f"- experiment id: `{experiment_id}`",
        f"- prompt version: `{prompt_version}`",
        f"- model: `{experiment_meta.get('metadata', {}).get('model', '?')}`",
        f"- dataset: `{experiment_meta.get('metadata', {}).get('dataset', '?')}`",
        f"- dataset size: `{experiment_meta.get('metadata', {}).get('dataset_size', len(tasks))}`",
        "",
        "## Aggregate",
        "",
        f"- rows: **{len(tasks)}**",
        f"- exact_match: **{accuracy:.4f}** ({correct}/{len(valid)})",
        f"- failed rows: **{len(failed)}**",
        "",
        "## Per-class accuracy",
        "",
        "| class | correct | total | accuracy |",
        "|-------|---------|-------|----------|",
    ]
    for cls in classes:
        b = by_class.get(cls, {"n": 0, "correct": 0})
        acc = b["correct"] / b["n"] if b["n"] else "-"
        acc_str = f"{acc:.4f}" if isinstance(acc, float) else "-"
        lines.append(f"| {cls} | {b['correct']} | {b['n']} | {acc_str} |")

    lines += ["", "## Confusion matrix (expected \\ predicted)", "",
              "| expected \\ predicted | " + " | ".join(classes) + " |", "|" + "---|" * (len(classes) + 1)]
    for cls in classes:
        row = matrix[cls]
        lines.append("| " + cls + " | " + " | ".join(str(row.get(c, 0)) for c in classes) + " |")

    lines += ["", "## Misclassification ledger", ""]
    if not misses:
        lines.append("_No misclassifications._")
    else:
        lines.append(f"_{len(misses)} rows; showing up to 100._")
        lines.append("")
        lines.append("| expected | predicted | filename | confidence | reasoning |")
        lines.append("|----------|-----------|----------|------------|-----------|")
        for t in misses[:100]:
            meta = t["metadata"]
            conf = meta.get("confidence")
            conf_str = f"{conf:.3f}" if isinstance(conf, (int, float)) else "-"
            reasoning = str(meta.get("reasoning") or "")[:120].replace("|", "\\|")
            lines.append(f"| {t['expected']} | {normalize_label(t['output'])} | {_filename(t['input'])} | "
                         f"{conf_str} | {reasoning} |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Braintrust experiment name")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"), help="Output directory")
    parser.add_argument("--max-misses", type=int, default=100, help="Max ledger rows in the report")
    args = parser.parse_args()

    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")
    exp = find_experiment_by_name(braintrust_key, _CONFIG.project_id, args.experiment, _CONFIG.api_base)
    if not exp:
        parser.error(f"Experiment not found: {args.experiment!r}")

    rows = fetch_experiment_rows(braintrust_key, exp["id"], _CONFIG.api_base)
    if not rows:
        parser.error(f"No events in experiment {args.experiment!r}.")

    markdown = render_report(exp, rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.experiment.replace("/", "_")
    out = args.output_dir / f"report_{slug}.md"
    out.write_text(markdown, encoding="utf-8")
    print(f"Report written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
