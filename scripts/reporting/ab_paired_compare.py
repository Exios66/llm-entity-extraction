#!/usr/bin/env python3
"""Paired same-surface A/B comparator for extraction run records.

Compares TWO experiment-log records (same model, same prompt surface — same
seed/sample ⇒ identical filenames) per document, on the identical-document
intersection: per-document deltas of the chosen metric, resampled with
replacement (paired bootstrap, seed 42) → mean Δ, 95% CI, ``P(A beats B)``,
and the GEPA verdict (the noise-floor contract from ``monte_carlo_gepa.py``):
a version BEATS its peer when the CI excludes zero AND ``P(win) >= 0.9``;
inside the band it is a LOGIC REPAIR (no champion change). Per-field deltas
(mean score delta + the same bootstrap verdict) are reported for every
scored field, so recall/miss patterns on specific fields surface directly.

Usage:
    python scripts/reporting/ab_paired_compare.py \
        --experiment-a qwen3.7-flash_contracts_specialist_v34_extraction_chunked_half \
        --experiment-b qwen3.7-flash_contracts_specialist_v35_extraction_chunked_half
    python scripts/reporting/ab_paired_compare.py ... --metric field_presence
    python scripts/reporting/ab_paired_compare.py ... --n-boot 2000
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.experiment_log import default_jsonl_path  # noqa: E402
from src.monte_carlo import paired_delta_bootstrap  # noqa: E402

WIN_P_THRESHOLD = 0.9  # GEPA noise-floor contract: P(A beats B) to call a pair
DEFAULT_N_BOOT = 2_000
DEFAULT_SEED = 42
DEFAULT_METRIC = "overall_score"


def load_record(log_path: Path, experiment_name: str) -> dict:
    """Return the LAST experiment-log record with the given name."""
    matches = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("experiment_name") == experiment_name:
                matches.append(record)
    if not matches:
        raise SystemExit(f"no record named {experiment_name!r} in {log_path}")
    return matches[-1]


def per_doc_metric(record: dict, metric: str) -> dict[str, float]:
    """Map filename -> per-document metric value (rows only; errors excluded)."""
    out: dict[str, float] = {}
    for row in record.get("results") or []:
        if row.get("error") or row.get("status") == "error":
            continue
        value = row.get(metric)
        if value is None:
            continue
        out[row["filename"]] = float(value)
    return out


def per_doc_field_scores(record: dict) -> dict[str, dict[str, float]]:
    """Map field -> {filename -> field score} across the record's rows."""
    fields: dict[str, dict[str, float]] = defaultdict(dict)
    for row in record.get("results") or []:
        if row.get("error") or row.get("status") == "error":
            continue
        for field, value in (row.get("field_scores") or {}).items():
            if value is not None:
                fields[field][row["filename"]] = float(value)
    return dict(fields)


def verdict(ab: dict) -> str:
    """GEPA noise-floor verdict from a paired-bootstrap result.

    A symmetric 95% CI excluding zero already implies P(win) >= 0.95, so the
    noise-floor contract reduces to: CI excludes zero => BEATS/LOSES;
    CI touches zero => INSIDE the band => LOGIC REPAIR (no champion change).
    """
    ci_lo, ci_hi, mean = ab["ci_lo"], ab["ci_hi"], ab["mean"]
    if ci_lo > 0.0 or ci_hi < 0.0:
        return "BEATS" if mean > 0 else "LOSES"
    return "INSIDE the noise band -> LOGIC REPAIR (no champion change)"


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-a", required=True, help="challenger record name")
    parser.add_argument("--experiment-b", required=True, help="champion/control record name")
    parser.add_argument("--log", type=Path, default=None,
                        help="experiment-log jsonl (default: repo default)")
    parser.add_argument("--metric", default=DEFAULT_METRIC,
                        choices=("overall_score", "field_presence", "schema_valid",
                                 "overall_verified_precision", "category_presence"),
                        help="per-document metric to compare (default: overall_score)")
    parser.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    log_path = args.log or default_jsonl_path()
    if not log_path.exists():
        raise SystemExit(f"no experiment log at {log_path}")
    record_a = load_record(log_path, args.experiment_a)
    record_b = load_record(log_path, args.experiment_b)
    if record_a.get("parameters", {}).get("manifest") == record_b.get("parameters", {}).get("manifest"):
        raise SystemExit("ERROR: both records share the same manifest — not an A/B pair")

    scores_a = per_doc_metric(record_a, args.metric)
    scores_b = per_doc_metric(record_b, args.metric)
    shared = sorted(scores_a.keys() & scores_b.keys())
    if len(shared) < 20:
        raise SystemExit(f"shared-document surface too small for a paired verdict: {len(shared)}")
    deltas = [scores_a[f] - scores_b[f] for f in shared]
    ab = paired_delta_bootstrap(deltas, n_boot=args.n_boot, seed=args.seed)

    mean_a = sum(scores_a[f] for f in shared) / len(shared)
    mean_b = sum(scores_b[f] for f in shared) / len(shared)

    print(f"Paired same-surface A/B  {args.experiment_a}  vs  {args.experiment_b}")
    print(f"  metric={args.metric}  shared docs={len(shared)}  n_boot={args.n_boot} seed={args.seed}")
    print(f"  A mean {mean_a:.4f}   B mean {mean_b:.4f}   delta {mean_a - mean_b:+.4f}")
    print(f"  paired bootstrap: mean {ab['mean']:+.4f}  CI [{ab['ci_lo']:+.4f}, {ab['ci_hi']:+.4f}]  "
          f"P(A beats B) {ab['p_win']:.4f}")
    print(f"  VERDICT: {verdict(ab)}")

    fields_a = per_doc_field_scores(record_a)
    fields_b = per_doc_field_scores(record_b)
    print("\n  per-field deltas (A - B, same shared docs):")
    for field in sorted(fields_a.keys() & fields_b.keys()):
        shared_f = sorted(fields_a[field].keys() & fields_b[field].keys())
        if len(shared_f) < 10:
            continue
        delta_f = [fields_a[field][f] - fields_b[field][f] for f in shared_f]
        fb = paired_delta_bootstrap(delta_f, n_boot=args.n_boot, seed=args.seed)
        fa = sum(fields_a[field][f] for f in shared_f) / len(shared_f)
        fbb = sum(fields_b[field][f] for f in shared_f) / len(shared_f)
        print(f"    {field:24s} n={len(shared_f):3d}  A {fa:.4f}  B {fbb:.4f}  "
              f"delta {fb['mean']:+.4f}  CI [{fb['ci_lo']:+.4f}, {fb['ci_hi']:+.4f}]  "
              f"P(win) {fb['p_win']:.3f}  {verdict(fb)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_with_args(sys.argv[1:]))