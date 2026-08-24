#!/usr/bin/env python3
"""Backfill: add ContractEval-rubric KPIs (``scores.contracteval_kpis``) to
historical contract-extraction records in the experiment log.

The extraction runners only started computing the KPI block (F1 / F2 /
Jaccard / false-"no related clause" + the semantic coverage bands, see
``src/contracteval.py::run_kpis``) with the KANBAN-054 change; older records
carry the raw-list ``diagnostics`` but not the rubric KPIs. This script
recomputes the block offline (deterministic — it reads each record's own
rows + the committed master GT; no LLM spend) and rewrites the jsonl once.

Usage:
    python scripts/reporting/backfill_extraction_kpis.py --dry-run
    python scripts/reporting/backfill_extraction_kpis.py
    python scripts/reporting/backfill_extraction_kpis.py --log <path> --gt <master.csv>

This is a DOCUMENTED one-time backfill exception to the append-only log rule
(the same precedent as the failure-reasoning backfill) — record it in the
changelog when used. The markdown log must be regenerated afterwards with
``scripts/reporting/render_experiment_log.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# KANBAN-088: shared JSONL line-boundary safety (Hub worker splits rows on
# U+2028/U+2029/NEL; see scripts/datasets/_jsonl_safety.py).
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from scripts.datasets._jsonl_safety import safe_jsonl_line

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracteval import load_master_gt, run_kpis  # noqa: E402
from src.experiment_log import default_jsonl_path  # noqa: E402


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=None,
                        help="experiment-log jsonl (default: repo default)")
    parser.add_argument("--gt", type=Path, default=None,
                        help="master GT CSV (default: data/cuad/master_clauses.csv)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    parser.add_argument("--refresh", action="store_true",
                        help="recompute the KPI block even when present "
                             "(KANBAN-058 scorer/GT fix re-scoring pass)")
    args = parser.parse_args(argv)

    log_path = args.log or default_jsonl_path()
    gt_path = args.gt or Path("data/cuad/master_clauses.csv")
    if not log_path.exists():
        print(f"no experiment log at {log_path} — nothing to backfill")
        return 0
    if not gt_path.exists():
        print(f"master GT missing at {gt_path} — cannot compute KPIs")
        return 1

    master_gt = load_master_gt(gt_path)
    if not master_gt:
        print(f"master GT unreadable at {gt_path}")
        return 1

    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    updated = skipped = already = 0
    new_lines: list[str] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        if record.get("task") != "contract_entity_extraction":
            new_lines.append(line)
            continue
        existing_kpis = (record.get("scores") or {}).get("contracteval_kpis")
        if existing_kpis and "laziness" in existing_kpis and not args.refresh:
            already += 1
            new_lines.append(line)
            continue
        results = [
            {"filename": row.get("filename"), "predicted": row.get("predicted") or {}}
            for row in (record.get("results") or [])
            if not row.get("status") == "error" and not row.get("error")
            and (row.get("predicted") or {}).get("_parse_error") is not True
            and row.get("predicted") is not None
        ]
        kpis = run_kpis({"results": results}, master_gt) if results else None
        if not kpis or not kpis.get("n_pairs"):
            print(f"  SKIP {record.get('experiment_name', '?')} — no joinable rows")
            skipped += 1
            new_lines.append(line)
            continue
        record.setdefault("scores", {})["contracteval_kpis"] = kpis
        new_lines.append(safe_jsonl_line(record))
        updated += 1
        print(f"  {record['experiment_name']}: n_pairs {kpis['n_pairs']} / "
              f"n_pos {kpis['n_positive']} / F1 {kpis['f1']} / F2 {kpis['f2']} / "
              f"Jacc {kpis['jaccard_mean']} / false-nr {kpis['false_no_related_rate']}")

    print(f"\n{updated} record(s) updated, {already} already carried KPIs, "
          f"{skipped} skipped (no joinable rows)")
    if args.dry_run:
        print("dry run — no writes")
        return 0
    if not updated:
        return 0
    log_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"wrote {log_path}")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())