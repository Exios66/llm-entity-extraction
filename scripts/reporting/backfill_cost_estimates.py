#!/usr/bin/env python3
"""One-time cost backfill (GitHub issue #1): stamp ``cost_estimated_usd``.

Historical records were written before cost scoring existed — their token
counts are complete but ``cost_total_usd`` is $0.00 because OpenRouter usage
payloads carry no cost field. This script rewrites every record in the
experiment log (append-only exception, documented in CHANGELOG) adding the
deterministic token x price estimate (``src/cost_models.py``) to each tokens
bucket; no other field is touched and record order is preserved.

Usage:
    python scripts/reporting/backfill_cost_estimates.py            # reports/experiment_log.jsonl
    python scripts/reporting/backfill_cost_estimates.py --dry-run  # preview the deltas
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.cost_models import estimate_cost  # noqa: E402


def _bucket_cost(bucket: dict, model: str) -> dict:
    if not isinstance(bucket, dict):
        return bucket
    prompt = bucket.get("prompt_tokens")
    completion = bucket.get("completion_tokens")
    estimated = estimate_cost(prompt, completion, model)
    if estimated is None:
        return bucket
    out = dict(bucket)
    out["cost_estimated_usd"] = estimated
    return out


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=Path("reports/experiment_log.jsonl"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.jsonl.exists():
        parser.error(f"log not found: {args.jsonl}")

    lines = args.jsonl.read_text(encoding="utf-8").splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    changed = 0
    total = 0.0
    for record in records:
        tokens = record.get("tokens") or {}
        model = record.get("model")
        bucket_keys = list(tokens.keys()) if "total" in tokens else [None]
        for key in bucket_keys:
            bucket = tokens[key] if key is not None else tokens
            new_bucket = _bucket_cost(bucket, model)
            if new_bucket is not bucket and new_bucket.get("cost_estimated_usd") is not None:
                if key is not None:
                    tokens[key] = new_bucket
                else:
                    record["tokens"] = new_bucket
                changed += 1
                total += new_bucket["cost_estimated_usd"]

    print(f"backfill plan: {len(records)} records, {changed} token buckets "
          f"gaining cost_estimated_usd (total ${total:.6f})")
    if args.dry_run:
        return 0
    out_lines = []
    for i, record in enumerate(records):
        if i < len(lines) and lines[i].strip():
            out_lines.append(json.dumps(record, default=str))
    args.jsonl.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(f"wrote {args.jsonl}")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
