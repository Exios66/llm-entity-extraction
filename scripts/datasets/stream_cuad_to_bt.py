#!/usr/bin/env python3
"""Stream the CUAD v1 contracts (The Atticus Project) into a Braintrust dataset.

CUAD v1 (https://github.com/TheAtticusProject/cuad, CC BY 4.0) is the canonical
contract-understanding corpus: 510 real SEC-exhibit contracts with clause-level
QA annotations. This script streams the official ``CUAD_v1.json`` (SQuAD-style)
straight from the Hugging Face mirror into the Braintrust dataset
``mailroom-cuad-contracts`` — one dataset item per contract, each with the full
contract text as input and ``doc_type: contract`` as the expected value.

Nothing is committed to the repo: the JSON is streamed to a temp file, parsed,
and deleted. Reruns upsert by the deterministic item id ``cuad-<title>``.

Usage:
    python scripts/datasets/stream_cuad_to_bt.py                    # all contracts
    python scripts/datasets/stream_cuad_to_bt.py --limit 10         # first 10
    python scripts/datasets/stream_cuad_to_bt.py --sample 12 --seed 42  # 12 random
    python scripts/datasets/stream_cuad_to_bt.py --min-chars 2000   # skip stubs
    python scripts/datasets/stream_cuad_to_bt.py --dry-run          # preview only
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import upload_text_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402

CUAD_JSON_URL = (
    "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/"
    "CUAD_v1/CUAD_v1.json"
)

_CUAD = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"
DEFAULT_PROJECT_ID = _CUAD.project_id


def download_json(url: str, dest: Path) -> Path:
    """Stream the CUAD JSON into a temp file with progress feedback."""
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


def parse_contracts(json_bytes: bytes, min_chars: int) -> list[dict]:
    """Parse the SQuAD-style CUAD JSON into per-contract records.

    Each document's paragraphs (with QA annotations) are joined into one
    ``doc_text``; duplicate paragraph contexts are dropped.
    """
    data = json.loads(json_bytes)
    documents = data.get("data", [])
    contracts: list[dict] = []
    for doc in documents:
        title = (doc.get("title") or "").strip() or "unknown"
        seen: set[str] = set()
        parts: list[str] = []
        qa_count = 0
        for paragraph in doc.get("paragraphs", []):
            context = (paragraph.get("context") or "").strip()
            if context and context not in seen:
                seen.add(context)
                parts.append(context)
            qa_count += len(paragraph.get("qas", []) or [])
        doc_text = "\n\n".join(parts)
        if len(doc_text) < min_chars:
            continue
        contracts.append({
            "title": title,
            "doc_text": doc_text,
            "chars": len(doc_text),
            "paragraphs": len(parts),
            "qa_count": qa_count,
        })
    return contracts


def build_records(contracts: list[dict]) -> list[dict]:
    """Convert parsed contracts into Braintrust dataset records."""
    records = []
    for c in contracts:
        records.append({
            "input": {
                "doc_text": c["doc_text"],
                "filename": f"{c['title']}.txt",
                "metadata": {
                    "source": "cuad_v1",
                    "contract_title": c["title"],
                    "paragraphs": c["paragraphs"],
                    "qa_count": c["qa_count"],
                },
            },
            "expected": {"doc_type": "contract"},
            "metadata": {"source": "cuad_v1", "license": "CC BY 4.0", "chars": c["chars"]},
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset name")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Braintrust project id")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N contracts (0 = all)")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N contracts")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--min-chars", type=int, default=1500, help="Skip contracts shorter than this")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Braintrust")
    parser.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "cuad_stream",
                        help="Temp dir for the source JSON (deleted after use)")
    args = parser.parse_args()

    (api_key,) = require_env("BRAINTRUST_API_KEY")
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    tmp = args.cache_dir / "CUAD_v1.json"
    try:
        if not tmp.exists():
            download_json(CUAD_JSON_URL, tmp)
        contracts = parse_contracts(tmp.read_bytes(), args.min_chars)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
                args.cache_dir.rmdir()
            except OSError:
                pass

    print(f"Parsed {len(contracts)} contracts from CUAD v1")
    if args.sample:
        contracts = random.Random(args.seed).sample(contracts, min(args.sample, len(contracts)))
        print(f"Sampled {len(contracts)} contracts (seed {args.seed})")
    elif args.limit:
        contracts = contracts[: args.limit]
        print(f"Limited to {len(contracts)} contracts")

    records = build_records(contracts)
    total_chars = sum(r["metadata"]["chars"] for r in records)
    print(f"Records: {len(records)}, total text {total_chars / 1e6:,.1f} MB")

    if args.dry_run:
        for r in records[:10]:
            print(f"  would sync  {r['input']['filename']}")
        if len(records) > 10:
            print(f"  ... and {len(records) - 10} more")
        print(f"\nDry run: {len(records)} records would sync to {args.dataset}")
        return 0

    summary = upload_text_dataset(
        records,
        project_id=args.project_id,
        dataset_name=args.dataset,
        api_key=api_key,
        description=f"CUAD v1 contracts ({len(records)} docs, CC BY 4.0) — doc_type=contract",
        metadata={"source": "cuad_v1", "license": "CC BY 4.0", "total_chars": total_chars},
        on_progress=lambda i, n: print(f"  Inserted {i}/{n}..."),
    )
    print(f"\nDone: {summary['inserted']} inserted, {summary['failed']} failed into {args.dataset}")
    if summary["failures"]:
        print("Failures:", *summary["failures"][:5], sep="\n  ")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
