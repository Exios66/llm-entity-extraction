#!/usr/bin/env python3
"""Sync LegalBench task train/test records into Langfuse datasets.

Mirrors the exact records the streamer builds
(``scripts/datasets/stream_legalbench_tasks_to_bt.py``) into Langfuse
**datasets** (default: the llm-dojo project, keys in
``config/environments/langfuse.env``) so
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
    python scripts/eval/sync_langfuse_datasets.py --cuad --dry-run          # LOCAL CUAD corpus
    python scripts/eval/sync_langfuse_datasets.py --cuad                    # -> mailroom-cuad-contracts
    python scripts/eval/sync_langfuse_datasets.py --cuad --cuad-dir data/cuad_pdfs
    python scripts/eval/sync_langfuse_datasets.py --maud --s1               # MAUD + S-1 local dumps
    python scripts/eval/sync_langfuse_datasets.py --docclass --dry-run      # MERGED docclass corpus
    python scripts/eval/sync_langfuse_datasets.py --docclass                # -> mailroom-docclass
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
from src.env_utils import LANGFUSE_ENV_FILE, resolve_env_file  # noqa: E402

DATASET_PREFIX = "mailroom-lb"
DEFAULT_ENV_FILE = str(LANGFUSE_ENV_FILE)
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


def _sync_cuad(env_file: Path, cuad_dir: Path, dry_run: bool) -> dict:
    """Mirror the LOCAL CUAD corpus into a Langfuse dataset.

    Builds TEXT rows offline — full contract text + clause-QA ground truth +
    category metadata from the local ``CUAD_v1.json`` and the PDF tree under
    ``data/cuad_pdfs/`` (downloaded by ``scripts/datasets/download_cuad_pdfs.py``)
    — and upserts them into the ``mailroom-cuad-contracts`` dataset in the
    project (llm-dojo). This is the Langfuse-side twin of streaming the corpus
    to Braintrust when dataset-row writes are unavailable, so the CUAD data is
    versioned + queryable in the same environment the eval traces land.
    """
    from scripts.datasets.stream_cuad_to_bt import build_records, clause_labels_from_local

    project = "unknown-project"
    public_key = secret_key = None
    base_url = DEFAULT_BASE_URL
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
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
        return {"project": project, "skipped_env": True, "items": 0, "datasets": 0, "total": 1}

    cuad_dir = Path(cuad_dir)
    json_path = cuad_dir / "CUAD_v1.json"
    if not json_path.exists():
        print(f"  [warn] {json_path} not found — download the corpus first with "
              f"scripts/datasets/download_cuad_pdfs.py", file=sys.stderr)
        return {"project": project, "items": 0, "datasets": 0, "total": 1, "skipped_env": False}
    pdf_paths = sorted(str(p.relative_to(cuad_dir)) for p in cuad_dir.rglob("*.pdf"))
    if not pdf_paths:
        print(f"  [warn] no PDFs under {cuad_dir} — download the corpus first", file=sys.stderr)
        return {"project": project, "items": 0, "datasets": 0, "total": 1, "skipped_env": False}

    labels = clause_labels_from_local(json_path)
    records = build_records(
        pdf_paths,
        pages_per_doc="all",
        target_size=(1024, 1024),
        api_key="",  # text-only rows never fetch/render PDFs
        clause_labels=labels,
        text_only=True,
    )
    dataset_name = "mailroom-cuad-contracts"
    client = Langfuse(public_key=public_key, secret_key=secret_key, host=base_url)
    n, _ = _sync_records(client, dataset_name, records, dry_run)
    if not dry_run:
        client.flush()
        client.shutdown()
    print(f"  {dataset_name}: {n} text items -> {dataset_name}"
          + (" (would)" if dry_run else ""))
    return {"project": project, "items": n, "datasets": 1, "total": 1, "skipped_env": False}


def _records_from_local_dump(path: Path) -> list[dict]:
    """Convert a streamer ``--local-dump`` JSONL back into record dicts.

    The flat dump shape is ``{filename, doc_text, prompt, expected,
    expected_subclass, metadata}``; the mirror upsert path consumes
    ``{input, expected, metadata}`` records (deterministic content-addressed
    ids, so reruns upsert in place).
    """
    import json as _json

    records = []
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = _json.loads(line)
            metadata = dict(row.get("metadata") or {})
            expected = row.get("expected") or ""
            records.append({
                "input": {
                    "doc_text": row.get("doc_text", ""),
                    "filename": row.get("filename", ""),
                    "metadata": {
                        **metadata,
                        "expected_doc_type": expected,
                        "expected_subclass": row.get("expected_subclass"),
                    },
                },
                "expected": {"doc_type": expected},
                "expected_output": {"doc_type": expected},
                "metadata": metadata,
            })
    return records


def _sync_local_dumps(env_file: Path, dumps: dict[str, Path], dry_run: bool) -> dict:
    """Mirror streamer local dumps (MAUD / S-1 corporate records) into Langfuse.

    ``dumps`` maps dataset name -> local JSONL path (the streamers' reliable
    data path while Braintrust row uploads are org-capped). Offline: reads the
    dumps only, no archive downloads.
    """
    public_key = secret_key = None
    project = "unknown-project"
    base_url = DEFAULT_BASE_URL
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
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
        return {"project": project, "skipped_env": True, "items": 0, "datasets": 0}

    client = Langfuse(public_key=public_key, secret_key=secret_key, host=base_url)
    total_items = 0
    synced_datasets = []
    for dataset_name, path in dumps.items():
        records = _records_from_local_dump(path)
        if not records:
            print(f"  {dataset_name}: no records in {path}; skipping")
            continue
        n, _ = _sync_records(client, dataset_name, records, dry_run)
        total_items += n
        synced_datasets.append(dataset_name)
        print(f"  {dataset_name}: {n} items -> Langfuse dataset"
              + (" (would)" if dry_run else ""))
    if not dry_run:
        client.flush()
        client.shutdown()
    return {"project": project, "items": total_items, "datasets": len(synced_datasets),
            "skipped_env": False}


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
    parser.add_argument("--cuad", action="store_true",
                        help="Mirror the LOCAL CUAD corpus (data/cuad_pdfs) into a "
                             "Langfuse 'mailroom-cuad-contracts' dataset instead of "
                             "LegalBench tasks (offline text rows from CUAD_v1.json)")
    parser.add_argument("--cuad-dir", type=Path, default=Path("data/cuad_pdfs"),
                        help="Local CUAD mirror root (default: data/cuad_pdfs)")
    parser.add_argument("--maud", action="store_true",
                        help="Mirror the MAUD local dumps (data/maud/contracts.jsonl + "
                             "classification.jsonl) into Langfuse 'mailroom-maud-*' datasets")
    parser.add_argument("--s1", action="store_true",
                        help="Mirror the EDGAR S-1 corporate-record dump "
                             "(data/s1_corporate_records/corporate-records.jsonl) into "
                             "Langfuse 'mailroom-s1-corporate-records'")
    parser.add_argument("--docclass", action="store_true",
                        help="Mirror the MERGED docclass corpus (all three docclass "
                             "corpora in one file — data/datasets/docclass_merged.jsonl, "
                             "built by scripts/datasets/build_docclass_merged.py) into a "
                             "SINGLE Langfuse 'mailroom-docclass' dataset")
    parser.add_argument("--docclass-file", type=Path,
                        default=Path("data/datasets/docclass_merged.jsonl"),
                        help="Merged docclass dump (default: data/datasets/docclass_merged.jsonl)")
    parser.add_argument("--maud-dir", type=Path, default=Path("data/maud"),
                        help="Local MAUD dump dir (default: data/maud)")
    parser.add_argument("--s1-dir", type=Path, default=Path("data/s1_corporate_records"),
                        help="Local S-1 corporate-record dump dir (default: data/s1_corporate_records)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would sync without writing")
    args = parser.parse_args(argv)

    env_files = [resolve_env_file(p, default=LANGFUSE_ENV_FILE)
                 for p in (args.env_file or [DEFAULT_ENV_FILE])]
    if args.docclass:
        print(f"Syncing the MERGED docclass corpus ({args.docclass_file}) into "
              f"Langfuse dataset 'mailroom-docclass'")
        for env_file in env_files:
            if not env_file.exists():
                print(f"  [warn] {env_file} not found — skipped (add it with --env-file to sync that project)")
                continue
            report = _sync_local_dumps(env_file, {"mailroom-docclass": args.docclass_file},
                                       args.dry_run)
            if report.get("skipped_env"):
                print(f"  [warn] {env_file}: no Langfuse keys found — skipped")
                continue
            mode = "would upsert" if args.dry_run else "upserted"
            print(f"  {report['project']}: {mode} {report['items']} items across "
                  f"{report['datasets']} datasets")
        return 0
    if args.maud or args.s1:
        dumps = {}
        if args.maud:
            dumps["mailroom-maud-contracts"] = args.maud_dir / "contracts.jsonl"
            dumps["mailroom-maud-classification"] = args.maud_dir / "classification.jsonl"
        if args.s1:
            dumps["mailroom-s1-corporate-records"] = args.s1_dir / "corporate-records.jsonl"
        print(f"Syncing local dumps into Langfuse datasets: {sorted(dumps)}")
        for env_file in env_files:
            if not env_file.exists():
                print(f"  [warn] {env_file} not found — skipped (add it with --env-file to sync that project)")
                continue
            report = _sync_local_dumps(env_file, dumps, args.dry_run)
            if report.get("skipped_env"):
                print(f"  [warn] {env_file}: no Langfuse keys found — skipped")
                continue
            mode = "would upsert" if args.dry_run else "upserted"
            print(f"  {report['project']}: {mode} {report['items']} items across "
                  f"{report['datasets']} datasets")
        return 0
    if args.cuad:
        print(f"Syncing the LOCAL CUAD corpus ({args.cuad_dir}) into Langfuse datasets")
        for env_file in env_files:
            if not env_file.exists():
                print(f"  [warn] {env_file} not found — skipped (add it with --env-file to sync that project)")
                continue
            report = _sync_cuad(env_file, args.cuad_dir, args.dry_run)
            if report.get("skipped_env"):
                print(f"  [warn] {env_file}: no Langfuse keys found — skipped")
                continue
            mode = "would upsert" if args.dry_run else "upserted"
            print(f"  {report['project']}: {mode} {report['items']} items across "
                  f"{report['datasets']} datasets")
        return 0

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
