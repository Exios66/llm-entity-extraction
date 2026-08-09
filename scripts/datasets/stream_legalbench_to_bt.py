#!/usr/bin/env python3
"""Stream the LegalBench MAUD v1 merger agreements into a Braintrust dataset.

MAUD v1 (https://zenodo.org/records/7500064, CC BY 4.0) is the expert-annotated
merger-agreement corpus behind LegalBench's 34 ``maud_*`` tasks. This script
streams the official ``maud_v1.zip`` from Zenodo into the Braintrust dataset
``mailroom-legalbench-contracts`` — one dataset item per contract, with the
full agreement text as input and ``doc_type: contract`` as the expected value.

Each item also carries the contract's MAUD task labels (question -> label,
capped via ``--labels-per-contract``) in ``expected_output`` so later
extraction evals can judge against the clause-level ground truth.

Nothing is committed to the repo: the zip is streamed to a temp file and
deleted. Reruns upsert by the deterministic item id ``maud-<contract>``.

Usage:
    python scripts/datasets/stream_legalbench_to_bt.py                 # all 139
    python scripts/datasets/stream_legalbench_to_bt.py --limit 6       # pilot slice
    python scripts/datasets/stream_legalbench_to_bt.py --dry-run
    python scripts/datasets/stream_legalbench_to_bt.py --dataset mailroom-legalbench-6
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


def load_maud_labels(zf: zipfile.ZipFile, cap: int) -> dict[str, list[dict]]:
    """Parse ``data/MAUD_train.csv`` into per-contract label lists.

    Returns ``{contract_name: [{question, label, answer, category}, ...]}``
    with each list capped at ``cap`` rows.
    """
    try:
        raw = zf.read("data/MAUD_train.csv").decode("utf-8", "replace")
    except KeyError:
        return {}
    by_contract: dict[str, list[dict]] = defaultdict(list)
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
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
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Braintrust project id")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N contracts (0 = all)")
    parser.add_argument("--labels-per-contract", type=int, default=50,
                        help="Max MAUD label rows embedded per contract (0 = none)")
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
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
                args.cache_dir.rmdir()
            except OSError:
                pass

    total_chars = sum(r["metadata"]["chars"] for r in records)
    print(f"Records: {len(records)}, total text {total_chars / 1e6:,.1f} MB")

    if args.dry_run:
        for r in records[:10]:
            print(f"  would sync  {r['input']['filename']}  (labels={r['metadata']['maud_label_count']})")
        if len(records) > 10:
            print(f"  ... and {len(records) - 10} more")
        print(f"\nDry run: {len(records)} records would sync to {args.dataset}")
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
    print(f"\nDone: {summary['inserted']} inserted, {summary['failed']} failed into {args.dataset}")
    if summary["failures"]:
        print("Failures:", *summary["failures"][:5], sep="\n  ")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
