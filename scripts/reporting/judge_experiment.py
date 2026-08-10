#!/usr/bin/env python3
"""Run the JUDGE AGENT post hoc over an experiment's failed classifications.

After any classification run (subtype or chained), this script replays the
failed rows through the offline ``JudgeAgent.judge_classification`` — the
model that audits whether the sorter's assigned class was the best fit for
the document — using the row's FULL document text and the sorter's own
reasoning. The judgments are appended to ``data/judgments/<experiment>.jsonl``
(one line per judged row) and the markdown experiment log renders a
**Judge agent review** section for every record that has a judgments file.

The experiment log jsonl stays append-only: judgments live in their own file,
keyed by experiment name.

Usage:
    python scripts/reporting/judge_experiment.py --dry-run
    python scripts/reporting/judge_experiment.py                      # latest run
    python scripts/reporting/judge_experiment.py --experiment <name>  # specific run
    python scripts/reporting/judge_experiment.py --limit 10           # judge only N failures
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.judge_agent import JudgeAgent  # noqa: E402
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.experiment_log import default_jsonl_path  # noqa: E402

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts-full"
JUDGMENTS_DIR = Path("data/judgments")


def load_record(experiment: str | None, log_path: Path) -> dict:
    """Load the named record from the log, or the most recent one."""
    records = [json.loads(l) for l in open(log_path)]
    if experiment:
        matches = [r for r in records if r["experiment_name"] == experiment]
        if not matches:
            raise SystemExit(f"No record named {experiment!r} in {log_path}")
        return matches[-1]
    return records[-1]


def failed_rows(record: dict) -> list[dict]:
    """The record's rows whose classification missed (subtype or chained)."""
    failed = []
    for row in record.get("results", []):
        sorter = row.get("sorter") or {}
        if sorter and sorter.get("subtype_ok") is False:
            failed.append(row)
    return failed


def doc_text_by_filename(dataset_name: str) -> dict[str, str]:
    dataset = load_braintrust_dataset(_CONFIG.dataset_project, dataset_name,
                                      project_id=_CONFIG.project_id)
    return {d["filename"]: d["doc_text"] for d in dataset if d.get("doc_text")}


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default=None,
                        help="Experiment record name (default: the most recent run)")
    parser.add_argument("--log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dataset", default=DEFAULT_DATASET,
                        help="Dataset holding the source document texts")
    parser.add_argument("--judge-model", default=None,
                        help="Judge model override (default: taxonomy judge mapping)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Judge at most N failed rows (0 = all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan without calling the judge")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    log_path = args.log or default_jsonl_path()
    record = load_record(args.experiment, log_path)
    name = record["experiment_name"]
    failures = failed_rows(record)
    if not failures:
        print(f"No failed classifications in {name} — nothing to judge.")
        return 0
    if args.limit:
        failures = failures[: args.limit]
    print(f"{name}: {len(failures)} failed rows to judge "
          f"(task={record.get('task')})")

    if args.dry_run:
        for row in failures:
            sorter = row.get("sorter") or {}
            print(f"  would judge {row['filename'][:60]} "
                  f"({sorter.get('expected_subtype')} vs "
                  f"{sorter.get('contract_subtype')})")
        return 0

    JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    judgments_path = JUDGMENTS_DIR / f"{name}.jsonl"

    docs = doc_text_by_filename(args.dataset)
    judge = JudgeAgent(model=args.judge_model, api_key=openrouter_key)
    print(f"Loading documents from {args.dataset} ({len(docs)} texts)...")

    judged = 0
    with judgments_path.open("a") as fh:
        for i, row in enumerate(failures, start=1):
            filename = row["filename"]
            sorter = row.get("sorter") or {}
            doc_text = docs.get(filename, "")
            if not doc_text:
                print(f"  ! no source text for {filename} — skipping")
                continue
            try:
                judgment = judge.judge_classification(
                    sorter.get("doc_type", "contract"), doc_text,
                    reasoning=sorter.get("reasoning") or "",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  ! judge failed on {filename}: {exc}")
                continue
            entry = {
                "filename": filename,
                "expected_subtype": sorter.get("expected_subtype"),
                "predicted_subtype": sorter.get("contract_subtype"),
                "sorter_confidence": sorter.get("confidence"),
                "sorter_reasoning": (sorter.get("reasoning") or "")[:2000],
                "judgment": judgment,
            }
            fh.write(json.dumps(entry) + "\n")
            judged += 1
            print(f"  [{i}/{len(failures)}] {filename[:60]} -> "
                  f"{judgment['classification_correct']} "
                  f"({judgment['classification_quality']})")

    print(f"\n{judged} judgments appended to {judgments_path}")
    if judged:
        subprocess_render()
    return 0


def subprocess_render() -> None:
    import subprocess

    subprocess.run([sys.executable, "scripts/reporting/render_experiment_log.py"],
                   check=True)
    print("Markdown log regenerated with judge sections.")


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
