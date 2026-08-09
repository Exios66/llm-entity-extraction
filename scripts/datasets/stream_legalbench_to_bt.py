#!/usr/bin/env python3
"""Stream the LegalBench MAUD v1 merger agreements into Braintrust datasets.

MAUD v1 (https://zenodo.org/records/7500064, CC BY 4.0) is the expert-annotated
merger-agreement corpus behind LegalBench's 34 ``maud_*`` tasks. This script
streams the official ``maud_v1.zip`` from Zenodo into TWO Braintrust datasets:

1. ``mailroom-legalbench-contracts`` — one item per contract (139), with the
   full agreement text as input and ``doc_type: contract`` as expected, plus a
   per-contract MAUD task-label summary in ``expected_output``.
2. ``mailroom-legalbench-maud-classification`` — the per-question multi-class
   classification suite: one item per (contract, question) label, with the
   excerpt + question as input, the gold answer TEXT as expected, and the
   question's answer space embedded in metadata.valid_classes — exactly the
   multi-class set the sorter is evaluated on.

Nothing is committed to the repo: the zip is streamed to a temp file and
deleted. Reruns upsert by deterministic item ids.

Usage:
    python scripts/datasets/stream_legalbench_to_bt.py                 # contracts + main classification rows
    python scripts/datasets/stream_legalbench_to_bt.py --limit 6       # pilot slice
    python scripts/datasets/stream_legalbench_to_bt.py --skip-classification
    python scripts/datasets/stream_legalbench_to_bt.py --maud-data-type all
    python scripts/datasets/stream_legalbench_to_bt.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import upload_text_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402

MAUD_ZIP_URL = "https://zenodo.org/records/7500064/files/maud_v1.zip?download=1"

_CUAD = load_braintrust_config()
DEFAULT_DATASET = "mailroom-legalbench-contracts"
DEFAULT_CLASSIFICATION_DATASET = "mailroom-legalbench-maud-classification"
DEFAULT_PROJECT_ID = _CUAD.project_id


def download_zip(url: str, dest: Path) -> Path:
    """Stream the MAUD zip into a temp file with progress feedback."""
    import requests

    part = Path(str(dest) + ".part")
    if part.exists():
        part.unlink()
    print(f"Streaming {url}")
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        written = 0
        with part.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
                written += len(chunk)
                if total:
                    print(f"\r  {written / 1e6:,.1f} / {total / 1e6:,.1f} MB ({written / total * 100:.0f}%)", end="", flush=True)
    print()
    os.replace(part, dest)
    print(f"Downloaded {dest.stat().st_size / 1e6:,.1f} MB to {dest}")
    return dest


def load_maud_rows(zf: zipfile.ZipFile, data_type: str | None = None) -> list[dict]:
    """Parse ``data/MAUD_train.csv`` into row dicts.

    ``data_type`` filters the CSV's data_type column ('main', 'abridged',
    'rare_answers'); None keeps all. Returns the raw rows.
    """
    try:
        raw = zf.read("data/MAUD_train.csv").decode("utf-8", "replace")
    except KeyError:
        return []
    rows = []
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        if data_type and row.get("data_type") != data_type:
            continue
        rows.append(row)
    return rows


def load_maud_labels(zf: zipfile.ZipFile, cap: int) -> dict[str, list[dict]]:
    """Parse ``data/MAUD_train.csv`` into per-contract label lists.

    Returns ``{contract_name: [{question, label, answer, category}, ...]}``
    with each list capped at ``cap`` rows.
    """
    by_contract: dict[str, list[dict]] = defaultdict(list)
    for row in load_maud_rows(zf):
        contract = row.get("contract_name") or ""
        if not contract:
            continue
        labels = by_contract[contract]
        if len(labels) >= cap:
            continue
        labels.append({
            "question": (row.get("question") or "")[:300],
            "label": (row.get("label") or "")[:200],
            "answer": (row.get("answer") or "")[:300],
            "category": (row.get("category") or ""),
        })
    return dict(by_contract)


def build_maud_classification_records(rows: list[dict]) -> list[dict]:
    """Build per-question multi-class classification records from MAUD rows.

    Each row is one (contract, question) classification instance: the sorter
    must pick the gold answer TEXT from the question's answer space. The
    question's valid classes (distinct answers across the MAUD training set)
    are embedded in metadata so eval runners can validate and score with
    ``--valid-classes``.
    """
    from collections import defaultdict as _defaultdict

    # Per-question answer spaces (classes) across the whole set.
    spaces: dict[tuple, list[str]] = _defaultdict(list)
    for row in rows:
        q = (row.get("text_type") or "", row.get("subquestion") or "")
        answer = (row.get("answer") or "").strip()
        if answer and answer not in spaces[q]:
            spaces[q].append(answer)

    records = []
    for row in rows:
        contract = row.get("contract_name") or "unknown"
        task = row.get("text_type") or ""
        subquestion = row.get("subquestion") or ""
        answer = (row.get("answer") or "").strip()
        question = row.get("question") or ""
        excerpt = (row.get("text") or "").strip()
        if not answer or not excerpt:
            continue
        q_key = (task, subquestion)
        records.append({
            "input": {
                "doc_text": excerpt,
                "question": question or f"{task}: {subquestion}".strip(" :"),
                "filename": f"maud_{contract}_{row.get('id', 'q')}.txt",
                "metadata": {
                    "task": task,
                    "subquestion": subquestion,
                    "category": row.get("category") or "",
                    "valid_classes": spaces[q_key],
                    "contract": contract,
                    "maud_id": row.get("id", ""),
                },
            },
            "expected": {"doc_type": answer},
            "expected_output": {"doc_type": answer, "task": task, "subquestion": subquestion},
            "metadata": {
                "source": "maud_v1",
                "license": "CC BY 4.0",
                "task": task,
                "subquestion": subquestion,
                "answer": answer,
                "label_idx": row.get("label", ""),
                "contract": contract,
            },
        })
    return records


def stream_contracts(zf: zipfile.ZipFile) -> list[str]:
    """Return the ``data/contracts/contract_*.txt`` member names, sorted."""
    members = [n for n in zf.namelist() if n.startswith("data/contracts/") and n.endswith(".txt")]
    return sorted(members, key=lambda n: int("".join(ch for ch in n.split("/")[-1] if ch.isdigit()) or 0))


def build_records(
    zf: zipfile.ZipFile,
    members: list[str],
    labels: dict[str, list[dict]],
    limit: int,
) -> list[dict]:
    """Convert zip members into Braintrust dataset records."""
    records = []
    for i, member in enumerate(members):
        if limit and i >= limit:
            break
        contract = Path(member).stem  # e.g. contract_41
        doc_text = zf.read(member).decode("utf-8", "replace")
        contract_labels = labels.get(contract, [])
        records.append({
            "input": {
                "doc_text": doc_text,
                "filename": f"{contract}_merger_agreement.txt",
                "metadata": {"source": "maud_v1", "contract": contract},
            },
            "expected": {"doc_type": "contract"},
            "expected_output": {
                "doc_type": "contract",
                "maud_labels": contract_labels,
                "maud_label_count": len(contract_labels),
            },
            "metadata": {
                "source": "maud_v1",
                "license": "CC BY 4.0",
                "contract": contract,
                "chars": len(doc_text),
                "maud_label_count": len(contract_labels),
            },
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset name")
    parser.add_argument("--classification-dataset", default=DEFAULT_CLASSIFICATION_DATASET,
                        help="Braintrust dataset for the per-question MAUD multi-class rows")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Braintrust project id")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N contracts (0 = all)")
    parser.add_argument("--labels-per-contract", type=int, default=50,
                        help="Max MAUD label rows embedded per contract (0 = none)")
    parser.add_argument("--maud-data-type", default="main",
                        choices=("main", "abridged", "rare_answers", "all"),
                        help="MAUD CSV data_type for the classification dataset (default: main)")
    parser.add_argument("--skip-classification", action="store_true",
                        help="Skip the per-question multi-class dataset (contracts only)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Braintrust")
    parser.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "maud_stream",
                        help="Temp dir for the source zip (deleted after use)")
    args = parser.parse_args()

    (api_key,) = require_env("BRAINTRUST_API_KEY")
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    tmp = args.cache_dir / "maud_v1.zip"
    try:
        if not tmp.exists():
            download_zip(MAUD_ZIP_URL, tmp)
        with zipfile.ZipFile(tmp) as zf:
            labels = load_maud_labels(zf, args.labels_per_contract)
            members = stream_contracts(zf)
            print(f"Found {len(members)} contracts in MAUD v1 zip, labels for {len(labels)}")
            records = build_records(zf, members, labels, args.limit)
            maud_rows = [] if args.skip_classification else load_maud_rows(
                zf, None if args.maud_data_type == "all" else args.maud_data_type
            )
            classification_records = build_maud_classification_records(maud_rows)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
                args.cache_dir.rmdir()
            except OSError:
                pass

    total_chars = sum(r["metadata"]["chars"] for r in records)
    print(f"Contracts: {len(records)}, total text {total_chars / 1e6:,.1f} MB")
    if classification_records:
        tasks = len({r["metadata"]["task"] for r in classification_records})
        print(f"MAUD classification rows: {len(classification_records)} across {tasks} task families")

    if args.dry_run:
        for r in records[:10]:
            print(f"  would sync  {r['input']['filename']}  (labels={r['metadata']['maud_label_count']})")
        if len(records) > 10:
            print(f"  ... and {len(records) - 10} more")
        if classification_records:
            for r in classification_records[:5]:
                print(f"  would sync  {r['input']['filename']}  (task={r['metadata']['task']!r} -> {r['expected']['doc_type']!r})")
            if len(classification_records) > 5:
                print(f"  ... and {len(classification_records) - 5} more classification rows")
        print(f"\nDry run: {len(records)} contract records + {len(classification_records)} classification "
              f"rows would sync")
        return 0

    summary = upload_text_dataset(
        records,
        project_id=args.project_id,
        dataset_name=args.dataset,
        api_key=api_key,
        description=f"LegalBench MAUD v1 merger agreements ({len(records)} docs, CC BY 4.0)",
        metadata={"source": "maud_v1", "license": "CC BY 4.0", "total_chars": total_chars},
        on_progress=lambda i, n: print(f"  Inserted {i}/{n}..."),
    )
    print(f"\nContracts: {summary['inserted']} inserted, {summary['failed']} failed into {args.dataset}")
    if summary["failures"]:
        print("Failures:", *summary["failures"][:5], sep="\n  ")

    if classification_records:
        class_summary = upload_text_dataset(
            classification_records,
            project_id=args.project_id,
            dataset_name=args.classification_dataset,
            api_key=api_key,
            description=f"LegalBench MAUD per-question multi-class classification "
                        f"({len(classification_records)} rows, CC BY 4.0)",
            metadata={"source": "maud_v1", "license": "CC BY 4.0",
                      "data_type": args.maud_data_type},
            on_progress=lambda i, n: print(f"  Inserted {i}/{n} classification rows..."),
        )
        print(f"Classification: {class_summary['inserted']} inserted, {class_summary['failed']} failed "
              f"into {args.classification_dataset}")
        if class_summary["failures"]:
            print("Failures:", *class_summary["failures"][:5], sep="\n  ")
        return 0 if class_summary["failed"] == 0 else 1

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
