#!/usr/bin/env python3
"""Sync LegalBench task train/test records into Langfuse datasets.

Mirrors the exact records the streamer builds
(``scripts/datasets/stream_legalbench_tasks_to_bt.py``) into Langfuse
**datasets** (default: the llm-dojo project, keys in ``langfuse.env``) so
prompt iterations have the task data as versioned, queryable dataset items in
the SAME environment their traces land — the Langfuse-side twin of the
Braintrust ``mailroom-lb-<task>`` datasets (and of the ``--local-dump`` JSONL
when Braintrust writes are unavailable).

Each record becomes one dataset item:

    dataset_name:    mailroom-lb-<task> (train) / mailroom-lb-<task>-test (test)
    input:           the record's input (filled few-shot prompt, doc_text, metadata)
    expected_output: the task label (e.g. "Yes" / "No")
    id:              deterministic content-addressed id (same as the Braintrust
                     row id) so reruns UPSERT in place — never duplicate items

The dataset names match the Braintrust dataset names, so the eval runners
(``--dataset mailroom-lb-hearsay``) map 1:1 between environments.

Usage:
    python scripts/eval/sync_langfuse_datasets.py --tasks hearsay --dry-run
    python scripts/eval/sync_langfuse_datasets.py --tasks hearsay           # train only
    python scripts/eval/sync_langfuse_datasets.py --tasks hearsay --test    # train + 94-row test
    python scripts/eval/sync_langfuse_datasets.py --tasks hearsay --env-file langfuse.env \\
        --env-file langfuse-llm-mailroom.env                                # multiple projects
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langfuse import Langfuse  # noqa: E402

from scripts.datasets.stream_legalbench_tasks_to_bt import (  # noqa: E402
    build_records,
    fetch_hf_split,
    load_task,
    normalize_hf_rows,
    valid_classes_for,
)
from src.braintrust_utils import _deterministic_record_id  # noqa: E402

DATASET_PREFIX = "mailroom-lb"
DEFAULT_ENV_FILE = "langfuse.env"
DEFAULT_BASE_URL = "https://us.cloud.langfuse.com"


def _sync_records(client: Langfuse, dataset_name: str, records: list[dict],
                  dry_run: bool) -> tuple[int, int]:
    """Create/upsert dataset items for one record set.

    Returns ``(upserted, skipped)`` — ``upserted`` counts items that would be
    (or were) written; deterministic content-addressed ids mean reruns land on
    the SAME items instead of appending duplicates.
    """
    upserted = 0
    skipped = 0
    for record in records:
        item_id = _deterministic_record_id(record)
        input_data = record.get("input") or {}
        expected = (record.get("expected") or {}).get("doc_type")
        if dry_run:
            upserted += 1
            continue
        client.create_dataset(name=dataset_name)
        client.create_dataset_item(
            dataset_name=dataset_name,
            input=input_data,
            expected_output=expected,
            metadata={
                **(record.get("metadata") or {}),
                "dataset_item_id": item_id,
            },
            id=item_id,
        )
        upserted += 1
    return upserted, skipped


def _sync_project(env_file: Path, tasks: list[str], with_test: bool,
                  dry_run: bool) -> dict:
    """Mirror each task's train (+ test) records into one Langfuse project."""
    public_key = None
    secret_key = None
    project = "unknown-project"
    base_url = DEFAULT_BASE_URL
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key == "LANGFUSE_PUBLIC_KEY":
                public_key = value
            elif key == "LANGFUSE_SECRET_KEY":
                secret_key = value
            elif key == "LANGFUSE_PROJECT":
                project = value
            elif key in ("LANGFUSE_BASE_URL", "LANGFUSE_HOST"):
                base_url = value or DEFAULT_BASE_URL

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY") or public_key
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY") or secret_key
    project = os.environ.get("LANGFUSE_PROJECT") or project
    base_url = (os.environ.get("LANGFUSE_BASE_URL")
                or os.environ.get("LANGFUSE_HOST") or base_url).rstrip("/")
    if not public_key or not secret_key:
        return {"project": project, "skipped_env": True, "items": 0, "datasets": 0, "total": 0}

    client = Langfuse(public_key=public_key, secret_key=secret_key, host=base_url)
    total_items = 0
    datasets = []
    for task in tasks:
        meta = load_task(task, include_prompt=True)
        records = build_records(meta)
        if not records:
            print(f"  {task}: no train records; skipping")
            continue
        train_name = f"{DATASET_PREFIX}-{task}"
        n_train, _ = _sync_records(client, train_name, records, dry_run)
        total_items += n_train
        datasets.append(train_name)
        print(f"  {task}: {n_train} train items -> {train_name}"
              + (" (would)" if dry_run else ""))

        if with_test:
            test_raw = fetch_hf_split(task, "test")
            test_rows = normalize_hf_rows(test_raw)
            if test_rows:
                test_meta = {
                    **meta,
                    "rows": test_rows,
                    "valid_classes": valid_classes_for(test_rows, meta["task_type"]),
                }
                test_records = build_records(test_meta)
                test_name = f"{DATASET_PREFIX}-{task}-test"
                n_test, _ = _sync_records(client, test_name, test_records, dry_run)
                total_items += n_test
                datasets.append(test_name)
                print(f"    {task}: {n_test} test items -> {test_name}"
                      + (" (would)" if dry_run else ""))
            else:
                print(f"    {task}: no test rows on HF; skipping")

    if not dry_run:
        client.flush()
        client.shutdown()
    return {"project": project, "items": total_items, "datasets": len(datasets),
            "total": sum(1 for _ in tasks), "skipped_env": False}


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="hearsay",
                        help="Comma-separated LegalBench task names (default: hearsay)")
    parser.add_argument("--test", action="store_true",
                        help="Also mirror each task's TEST split (nguha/legalbench HF) "
                             "into a <task>-test dataset")
    parser.add_argument("--env-file", action="append", default=[],
                        help="Langfuse env file with keys + project label (repeatable). "
                             f"Defaults to {DEFAULT_ENV_FILE}")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would sync without writing")
    args = parser.parse_args(argv)

    env_files = [Path(p) for p in (args.env_file or [DEFAULT_ENV_FILE])]
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    if not tasks:
        parser.error("--tasks requires at least one task name")
    print(f"Syncing {len(tasks)} tasks"
          + (" + test splits" if args.test else "")
          + " into Langfuse datasets")
    for env_file in env_files:
        if not env_file.exists():
            print(f"  [warn] {env_file} not found — skipped (add it with --env-file to sync that project)")
            continue
        report = _sync_project(env_file, tasks, args.test, args.dry_run)
        if report.get("skipped_env"):
            print(f"  [warn] {env_file}: no Langfuse keys found — skipped")
            continue
        mode = "would upsert" if args.dry_run else "upserted"
        print(f"  {report['project']}: {mode} {report['items']} items across "
              f"{report['datasets']} datasets (of {report['total']} tasks)")
    return 0


def main() -> None:
    sys.exit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
