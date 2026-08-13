#!/usr/bin/env python3
"""Re-score historical extraction manifests with the CURRENT scorer.

The experiment log is append-only: records keep the scores computed at run
time, so scorer changes (e.g. the v21-era date fixes) drift across history.
This script re-scores every row of a set of manifests with the scorer as it
exists TODAY (embedding rescue disabled — the local sentence-transformers
model is optional and the remote route costs money; a consistent no-
embedding pass treats every arm identically) and emits a same-scorer
comparison: per prompt version, per-field means + overall.

Usage:
    python scripts/reporting/rescore_manifests.py \
        --manifest data/manifests/extraction_ab_v18_50.jsonl \
        --manifest data/manifests/extraction_ab_v19_50.jsonl ...
    python scripts/reporting/rescore_manifests.py --auto-50   # the 50-doc seed-42 series

The report is written to ``reports/same_scorer_scores.json`` (machine
readable) and printed as a table. Factuality-audit fields (verified
precision) are NOT recomputed — the manifests do not carry the source
document text; field scores and overall are the drift-sensitive numbers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import src.field_scoring as fs  # noqa: E402
from src.taxonomy import load_taxonomy  # noqa: E402

# The 50-doc seed-42 same-surface extraction series (dataset fingerprint
# 0a37dd25…): short label -> manifest.
SERIES_50 = [
    ("v13", "data/manifests/extraction_ab_v13_50.jsonl"),
    ("v14", "data/manifests/extraction_ab_v14_50.jsonl"),
    ("v15", "data/manifests/extraction_ab_v15_50.jsonl"),
    ("v16", "data/manifests/extraction_ab_v16_50.jsonl"),
    ("v17", "data/manifests/extraction_ab_v17_50.jsonl"),
    ("v18", "data/manifests/extraction_ab_v18_50.jsonl"),
    ("v19", "data/manifests/extraction_ab_v19_50.jsonl"),
    ("v21", "data/manifests/extraction_ab_v21_50.jsonl"),
    ("v22", "data/manifests/extraction_ab_v22_50.jsonl"),
    ("v22max", "data/manifests/extraction_ab_v22_max_50.jsonl"),
    ("v23", "data/manifests/extraction_ab_v23_50.jsonl"),
]

FIELD_ORDER = ["document_name", "parties", "effective_date", "term_length",
               "governing_law", "renewal_terms", "termination_clauses",
               "key_obligations"]


def _version_from_stem(stem: str) -> str:
    """extraction_ab_v18_50 -> v18; extraction_ab_v22_max_50 -> v22max."""
    name = stem.replace("extraction_ab_", "")
    name = name.replace("_max_50", "max").replace("_50", "").replace("_50b", "")
    return name


def _load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("type") == "header":
            continue
        rows.append(row)
    return rows


def rescore_manifest(path: Path, field_types: dict) -> dict:
    """Re-score every completed row; return per-field means + overall."""
    per_field: dict[str, list[float]] = defaultdict(list)
    overall: list[float] = []
    n_ok = n_skip = 0
    for row in _load_rows(path):
        if row.get("status") != "completed" or not row.get("predicted"):
            n_skip += 1
            continue
        result = fs.score_extraction(
            "contract", field_types,
            row.get("predicted") or {},
            row.get("expected_fields") or {},
            doc_text=None,
        )
        n_ok += 1
        if result.overall_score is not None:
            overall.append(result.overall_score)
        for key, score in result.field_scores.items():
            per_field[key].append(score)
    return {
        "rows": n_ok,
        "skipped": n_skip,
        "overall": round(sum(overall) / len(overall), 4) if overall else None,
        "fields": {k: round(sum(v) / len(v), 4) for k, v in per_field.items()},
    }


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", default=[],
                        help="Manifest(s) to re-score (repeatable)")
    parser.add_argument("--auto-50", action="store_true",
                        help="Re-score the 50-doc seed-42 series (SERIES_50)")
    parser.add_argument("--out", default="reports/same_scorer_scores.json",
                        help="Report output path")
    args = parser.parse_args(argv)

    fs._get_embedding = lambda: None  # consistent no-embedding pass
    ct = next(dc["field_types"] for dc in load_taxonomy()["doc_classes"]
              if dc["key"] == "contract")

    pairs = []
    if args.auto_50:
        pairs = SERIES_50
    for m in args.manifest:
        pv = _version_from_stem(Path(m).stem)
        pairs.append((pv, m))

    report: dict[str, dict] = {}
    print(f"{'prompt':14s} {'rows':>4s} {'overall':>8s} " +
          " ".join(f"{f[:8]:>9s}" for f in FIELD_ORDER))
    for pv, manifest in pairs:
        path = Path(manifest)
        if not path.exists():
            print(f"[warn] {manifest} not found")
            continue
        stats = rescore_manifest(path, ct)
        report[pv] = stats
        row = (f"{pv[:14]:14s} {stats['rows']:4d} "
               f"{(stats['overall'] or 0):8.4f} ")
        row += " ".join(f"{(stats['fields'].get(f) or 0):9.4f}" for f in FIELD_ORDER)
        print(row)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nreport written to {args.out}")
    return 0


def main() -> None:
    sys.exit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
