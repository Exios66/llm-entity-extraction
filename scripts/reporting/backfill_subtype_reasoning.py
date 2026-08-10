#!/usr/bin/env python3
"""One-time backfill: enrich historical subtype-classification records with
FULL failure reasoning and derived failure insights.

The subtype eval runner only started storing full reasoning on failed rows
(4000-char span) and per-row ``failure_mode`` + ``failure_insights`` after the
05:15 runs; the earlier records capped the model's reasoning at 500 chars,
truncating the insight-bearing text on exactly the failed rows that matter.

This script:
  1. Reads ``reports/experiment_log.jsonl``.
  2. For every ``subtype_classification`` record, maps it to its Braintrust
     experiment (by dataset_size + sorter prompt, disambiguated by created
     order) and fetches the experiment's LLM spans.
  3. Rebuilds each failed row with the model's FULL reasoning (from the raw
     structured-output span), its derived ``failure_mode``, and the
     ``scores.sorter.failure_insights`` aggregate (mode counts + per-failed-row
     entries).
  4. Rewrites the jsonl once (a DOCUMENTED exception to the append-only rule —
     record it in the changelog), then regenerates the markdown log.

Usage:
    python scripts/reporting/backfill_subtype_reasoning.py --dry-run
    python scripts/reporting/backfill_subtype_reasoning.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_utils import fetch_experiment_rows  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.experiment_log import default_jsonl_path  # noqa: E402
from scripts.eval.run_subtype_eval import classify_failure  # noqa: E402

REASONING_FULL_CAP = 4000
REASONING_EXCERPT_CAP = 500


def find_experiments(api_key: str, project_id: str) -> list[dict]:
    """List every subtype experiment, oldest first (see braintrust_utils)."""
    import requests

    resp = requests.get(
        "https://api.braintrust.dev/v1/experiment",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"project_id": project_id, "limit": 200},
        timeout=60,
    )
    resp.raise_for_status()
    exps = [e for e in resp.json().get("objects", [])
            if "subtype" in (e.get("name") or "") and not (e.get("name") or "").startswith("sh_")]
    return sorted(exps, key=lambda e: e.get("created", ""))


def span_reasoning_by_filename(events: list[dict]) -> dict[str, str]:
    """Map filename -> full classification reasoning from the LLM spans.

    Each LLM span is a descendant of the row's task span, whose input carries
    the filename; the LLM output is the structured classification JSON with
    the model's full ``reasoning`` text.
    """
    by_id = {s.get("span_id"): s for s in events}
    filename_of_root: dict[str, str] = {}
    for s in events:
        inp = s.get("input") or {}
        if isinstance(inp, dict) and inp.get("filename"):
            for parent in s.get("span_parents") or []:
                if parent in by_id and (by_id[parent].get("span_attributes") or {}).get("type") == "eval":
                    filename_of_root[s["span_id"]] = str(inp["filename"])
                    break
            else:
                # Fall back: any span carrying the filename maps to its root.
                filename_of_root.setdefault(s["span_id"], str(inp["filename"]))

    out: dict[str, str] = {}
    for s in events:
        if (s.get("span_attributes") or {}).get("type") != "llm":
            continue
        gens = (s.get("output") or {}).get("generations") or [[{}]]
        content = gens[0][0].get("message", {}).get("content", "")
        if not content:
            continue
        try:
            parsed = json.loads(content)
        except Exception:
            continue
        reasoning = str(parsed.get("reasoning") or "").strip()
        if not reasoning:
            continue
        # The LLM span's ancestor chain leads to the row's filename.
        seen = set()
        current = s.get("span_id")
        while current and current not in seen:
            seen.add(current)
            node = by_id.get(current)
            if node is None:
                break
            inp = node.get("input") or {}
            if isinstance(inp, dict) and inp.get("filename"):
                filename = str(inp["filename"])
                existing = out.get(filename)
                if existing is None or len(reasoning) > len(existing):
                    out[filename] = reasoning
                break
            current = (node.get("span_parents") or [None])[0]
    return out


def backfill_record(record: dict, reasoning_by_filename: dict[str, str]) -> dict:
    """Derive failure modes + full reasoning for one record's failed rows."""
    from collections import Counter

    failures = []
    for row in record.get("results", []):
        sorter = row.get("sorter") or {}
        if sorter.get("subtype_ok"):
            continue
        full = reasoning_by_filename.get(row.get("filename", ""))
        if full:
            sorter["reasoning"] = full[:REASONING_FULL_CAP]
        mode = classify_failure(sorter)
        sorter["failure_mode"] = mode
        failures.append({
            "filename": row.get("filename", ""),
            "expected": sorter.get("expected_subtype"),
            "predicted": sorter.get("contract_subtype"),
            "doc_type": sorter.get("doc_type"),
            "confidence": sorter.get("confidence"),
            "mode": mode,
            "equiv_recovered": bool(sorter.get("subtype_ok_equiv")),
            "reasoning": sorter.get("reasoning") or "",
        })
    if not failures:
        return record
    sorter_scores = record.setdefault("scores", {}).setdefault("sorter", {})
    sorter_scores["failure_insights"] = {
        "mode_counts": dict(sorted(Counter(f["mode"] for f in failures).items())),
        "n_failed": len(failures),
        "failures": failures,
    }
    return record


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing")
    args = parser.parse_args(argv)

    (api_key,) = require_env("BRAINTRUST_API_KEY")
    from src.braintrust_config import load_braintrust_config

    project_id = load_braintrust_config().project_id
    log_path = args.log or default_jsonl_path()

    experiments = find_experiments(api_key, project_id)
    print(f"Found {len(experiments)} subtype experiments in Braintrust")

    lines = [json.loads(l) for l in open(log_path)]
    changed = 0
    for record in lines:
        if record.get("task") != "subtype_classification":
            continue
        # Match by (dataset_size, sorter prompt); among the candidates pick the
        # experiment whose `created` is CLOSEST to the record's timestamp
        # (reruns of the same name create new experiments minutes apart).
        size = record["data_source"]["n_samples"]
        prompt = record.get("prompt_versions", {}).get("sorter")
        record_time = record.get("timestamp", "")
        candidates = [e for e in experiments
                      if (e.get("metadata") or {}).get("dataset_size") == size
                      and (e.get("metadata") or {}).get("sorter_prompt") == prompt]
        if not candidates:
            print(f"  ! no experiment match for {record['experiment_name']} "
                  f"({record['timestamp'][:16]}, {size} docs)")
            continue

        def _dist(exp: dict) -> float:
            try:
                from datetime import datetime, timezone
                t0 = datetime.fromisoformat(record_time.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat((exp.get("created") or "").replace("Z", "+00:00"))
                return abs((t1 - t0).total_seconds())
            except Exception:
                return float("inf")

        experiment = min(candidates, key=_dist)
        print(f"  {record['experiment_name']} {record['timestamp'][:16]} "
              f"({size} docs) -> {experiment['id'][:12]} "
              f"({experiment.get('created', '')[:16]})")

        events = fetch_experiment_rows(api_key, experiment["id"])
        reasoning = span_reasoning_by_filename(events)
        print(f"    fetched {len(events)} events, "
              f"full reasoning for {len(reasoning)} documents")
        updated = backfill_record(record, reasoning)
        changed += 1

    if args.dry_run:
        print(f"\nDry run: {changed} records would be enriched.")
        return 0

    with open(log_path, "w") as fh:
        for record in lines:
            fh.write(json.dumps(record) + "\n")
    print(f"\nBackfilled {changed} records in {log_path} "
          f"(documented append-only exception).")

    import subprocess

    subprocess.run([sys.executable, "scripts/reporting/render_experiment_log.py"],
                   check=True)
    print("Markdown log regenerated.")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
