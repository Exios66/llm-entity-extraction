#!/usr/bin/env python3
"""Build the static GitHub Pages site that views the experiment log.

The site lives in ``docs/`` (served by GitHub Pages from the ``main`` branch
via Settings -> Pages -> "Deploy from a branch" -> ``main`` -> ``/docs`` —
no Actions runners involved). ``docs/data/`` is DERIVED, exactly like
``reports/experiment_log.md`` is derived from
``reports/experiment_log.jsonl``: this script regenerates the whole data
tree from the JSONL source of truth, so the site always reflects every
record, in order, with no stale or hand-edited data.

Layout produced:

    docs/data/meta.json          build info + dataset-level facts
    docs/data/index.json         one compact summary per run (index table)
    docs/data/runs/{id}.json     the full record per run (detail pages)

Usage:
    python scripts/site/build_site.py                              # rebuild docs/data
    python scripts/site/build_site.py --jsonl /tmp/log.jsonl \
        --out /tmp/site-data                                      # custom paths
    python scripts/site/build_site.py --check                      # verify data is current
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSONL = REPO_ROOT / "reports" / "experiment_log.jsonl"
DEFAULT_OUT = REPO_ROOT / "docs" / "data"
REPO_URL = "https://github.com/Exios66/llm-entity-extraction"


def _fmt(value: float) -> str:
    """Format a score like the markdown log does (4 decimals)."""
    return f"{value:.4f}"


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


def headline_score(record: dict) -> dict:
    """Derive the headline score card for a run, mirroring the md index.

    Returns a dict with the score, its human label, and a 0-1 ratio for
    progress-bar rendering; empty dict when the task has no headline metric.
    """
    scores = record.get("scores") or {}
    task = record.get("task")
    if task == "contract_entity_extraction":
        value = scores.get("overall_extraction_score")
        if isinstance(value, (int, float)):
            return {"label": "extraction", "value": value}
    if task == "chained_sorter_extractor":
        sorter = scores.get("sorter") or {}
        extractor = scores.get("extractor") or {}
        sorter_value = sorter.get("exact_match")
        extractor_value = extractor.get("overall_extraction_score")
        if isinstance(extractor_value, (int, float)):
            value = extractor_value
            if isinstance(sorter_value, (int, float)):
                value = (sorter_value + extractor_value) / 2
            return {
                "label": "sorter / extractor",
                "value": value,
                "detail": (f"sorter {_fmt(sorter_value)} / "
                           f"extractor {_fmt(extractor_value)}"),
            }
    if task == "subtype_classification":
        sorter = scores.get("sorter") or {}
        strict = sorter.get("exact_match")
        equiv = sorter.get("subtype_accuracy")
        if isinstance(strict, (int, float)) and isinstance(equiv, (int, float)):
            return {
                "label": "subtype strict / equiv",
                "value": strict,
                "detail": (f"strict {_fmt(strict)} / equiv {_fmt(equiv)}"),
            }
    return {}


def prompt_string(record: dict) -> str:
    """Human prompt label: record field first, else sorter+extractor pair."""
    prompt = record.get("prompt_version")
    if not prompt and isinstance(record.get("prompt_versions"), dict):
        prompt = " + ".join(str(v) for v in record["prompt_versions"].values())
    return prompt or "—"


def summarize(record: dict, run_id: int) -> dict:
    """Compact index-row summary used by the site's index table."""
    tokens = record.get("tokens") or {}
    if "total" in tokens:
        total_tokens = (tokens["total"] or {}).get("total_tokens")
    else:
        total_tokens = tokens.get("total_tokens")
    data_source = record.get("data_source") or {}
    return {
        "id": run_id,
        "experiment_name": record.get("experiment_name", ""),
        "task": record.get("task", ""),
        "model": record.get("model", ""),
        "prompts": prompt_string(record),
        "headline": headline_score(record),
        "n_rows": record.get("n_rows"),
        "n_ok": record.get("n_ok"),
        "n_error": record.get("n_error"),
        "total_tokens": total_tokens,
        "cost_usd": tokens.get("cost_usd") if tokens else None,
        "timestamp": record.get("timestamp"),
        "git": record.get("git"),
        "data_source_project": data_source.get("project"),
        "data_source_n_samples": data_source.get("n_samples"),
        "seed": data_source.get("seed"),
    }


def build_meta(records: list[dict], jsonl_path: Path, out_dir: Path) -> dict:
    """Dataset-level facts shown in the site header/footer."""
    tasks: dict[str, int] = {}
    models: dict[str, int] = {}
    prompts: dict[str, int] = {}
    n_rows = n_ok = n_error = total_tokens = 0
    for record in records:
        task = record.get("task", "")
        tasks[task] = tasks.get(task, 0) + 1
        model = record.get("model", "")
        models[model] = models.get(model, 0) + 1
        prompt = prompt_string(record)
        prompts[prompt] = prompts.get(prompt, 0) + 1
        n_rows += record.get("n_rows") or 0
        n_ok += record.get("n_ok") or 0
        n_error += record.get("n_error") or 0
        tokens = record.get("tokens") or {}
        if "total" in tokens:
            total_tokens += (tokens["total"] or {}).get("total_tokens") or 0
        else:
            total_tokens += tokens.get("total_tokens") or 0
    best_by_task: dict[str, dict] = {}
    for i, record in enumerate(records, start=1):
        headline = headline_score(record)
        if not headline:
            continue
        task = record.get("task", "")
        current = best_by_task.get(task)
        if current is None or headline["value"] > current["value"]:
            best_by_task[task] = {
                "run_id": i,
                "value": headline["value"],
                "label": headline["label"],
            }
    return {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": str(jsonl_path.relative_to(REPO_ROOT)),
        "repo_url": REPO_URL,
        "run_count": len(records),
        "tasks": tasks,
        "models": models,
        "prompts": prompts,
        "n_rows": n_rows,
        "n_ok": n_ok,
        "n_error": n_error,
        "total_tokens": total_tokens,
        "best_per_task": best_by_task,
    }


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL,
                        help=f"JSONL experiment log (default: {DEFAULT_JSONL})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Site data output dir (default: {DEFAULT_OUT})")
    parser.add_argument("--check", action="store_true",
                        help="Verify docs/data matches the JSONL; exit 1 if stale")
    args = parser.parse_args(argv)

    records = load_records(args.jsonl)
    if not records:
        parser.error(f"No experiment records found in {args.jsonl}.")

    if args.check:
        index_path = args.out / "index.json"
        meta_path = args.out / "meta.json"
        if not index_path.exists() or not meta_path.exists():
            print("Site data is missing; run build_site.py to regenerate.")
            return 1
        current = json.loads(index_path.read_text(encoding="utf-8"))
        if len(current) != len(records):
            print(f"Site data is stale: {len(current)} runs in site, "
                  f"{len(records)} in {args.jsonl}.")
            return 1
        print(f"Site data is current ({len(current)} runs).")
        return 0

    runs_dir = args.out / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, record in enumerate(records, start=1):
        (runs_dir / f"{index:03d}.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")
        summaries.append(summarize(record, index))
    (args.out / "index.json").write_text(
        json.dumps(summaries, indent=1), encoding="utf-8")
    (args.out / "meta.json").write_text(
        json.dumps(build_meta(records, args.jsonl, args.out), indent=1),
        encoding="utf-8")
    print(f"Site data rebuilt: {len(records)} records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
