#!/usr/bin/env python3
"""Rebuild the human-readable experiment log from the JSONL source of truth.

The eval runners append one JSON line per experiment to
``reports/experiment_log.jsonl`` and one markdown section to
``reports/experiment_log.md``. The JSONL is the durable, complete record;
this script regenerates the ENTIRE markdown document from it (title, index
table, and one fully expanded section per experiment — scores, per-field
scoring matrices, confusion matrices, factuality audits, and model outputs),
so the markdown always reflects every record, in order, with no stale or
hand-edited sections.

Usage:
    python scripts/reporting/render_experiment_log.py                     # regenerate reports/experiment_log.md
    python scripts/reporting/render_experiment_log.py \
        --jsonl data/manifests/other.jsonl --markdown /tmp/log.md          # custom paths
    python scripts/reporting/render_experiment_log.py --dry-run            # just print the render
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.experiment_log import (
    DEFAULT_JSONL,
    DEFAULT_MD,
    default_jsonl_path,
    default_md_path,
    render_full_log,
)


def load_records(path: Path) -> list[dict]:
    """Read every experiment record from the JSONL log (append-only source)."""
    records = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover
            print(f"Skipping malformed line in {path}: {exc}", file=sys.stderr)
    return records


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=None,
                        help="JSONL experiment log (default: $EXPERIMENT_LOG_PATH or "
                             f"reports/experiment_log.jsonl)")
    parser.add_argument("--markdown", type=Path, default=None,
                        help="Output markdown path (default: $EXPERIMENT_LOG_MD_PATH or "
                             f"reports/experiment_log.md)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the rendered markdown to stdout instead of writing it")
    args = parser.parse_args(argv)

    jsonl_path = args.jsonl or default_jsonl_path()
    md_path = args.markdown or default_md_path()

    records = load_records(jsonl_path)
    if not records:
        parser.error(f"No experiment records found in {jsonl_path}.")

    markdown = render_full_log(records)
    if args.dry_run:
        print(markdown)
        return 0

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    print(f"Experiment log rendered: {len(records)} records -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
