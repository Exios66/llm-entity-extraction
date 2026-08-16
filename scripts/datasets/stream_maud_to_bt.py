#!/usr/bin/env python3
"""Stream the MAUD v1 merger-agreement corpus into the utilized datasets.

MAUD (Merger Agreement Understanding Dataset, Wang et al. 2023 — CC BY 4.0,
The Atticus Project) is the expert-annotated merger-agreement corpus behind
LegalBench's 34 ``maud_*`` tasks: 152 agreements and plans of merger with
25,827 per-(contract, question) training annotations across 22 question
families (MAE definition, no-shop, fiduciary outs, knowledge definitions,
...) and 7 expert categories.

This is the MAUD wiring for the hierarchical sorter evaluation (KANBAN-033):
the corpus becomes TWO utilized datasets plus a local JSONL mirror:

1. ``mailroom-maud-contracts`` — one item per merger agreement with the FULL
   agreement text. Ground truth: ``doc_type: merger_agreement`` (the NEW
   primary sorter class) and ``doc_subclass`` = the agreement's consideration
   type, read from MAUD's own expert GT ("Type of Consideration" question:
   All Cash / All Stock / Mixed Cash/Stock / Mixed Cash/Stock: Election).
   The MAUD category distribution (which deal-protection topics the
   agreement's annotations concentrate on) stays in metadata — the tertiary
   level was dropped by design (human directive: only where the data
   necessitates it; category is provenance, not a classification axis).

2. ``mailroom-maud-classification`` — one item per (contract, question):
   excerpt + question as input, the gold answer TEXT as expected, the
   question's answer space in ``metadata.valid_classes``, and the question's
   family + category as metadata. This is the multi-class M&A diligence
   surface (mirrors ``mailroom-legalbench-maud-classification`` from
   ``stream_legalbench_to_bt.py`` but reads train/dev/test and runs through
   the modern local-dump + Langfuse mirror path).

Sources (identical data, CC BY 4.0):
- Zenodo: https://zenodo.org/records/7500064/files/maud_v1.zip (train CSV)
- HuggingFace mirror: ``theatticusproject/maud`` (adds dev/test CSVs)

Braintrust dataset-row uploads are capped on the org plan; the ``--local-dump``
JSONL is the RELIABLE eval path (same record shape the eval runners consume).
Reruns upsert by deterministic content-addressed ids.

Usage:
    python scripts/datasets/stream_maud_to_bt.py --dry-run
    python scripts/datasets/stream_maud_to_bt.py --local-dump data/maud/
    python scripts/datasets/stream_maud_to_bt.py --source huggingface --split all
    python scripts/datasets/stream_maud_to_bt.py --limit 10 --labels-per-contract 20
    python scripts/datasets/stream_maud_to_bt.py --skip-classification
    python scripts/datasets/stream_maud_to_bt.py --limit-classification 5000
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import upload_text_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402

MAUD_ZIP_URL = "https://zenodo.org/records/7500064/files/maud_v1.zip?download=1"
HF_REPO = "theatticusproject/maud"
HF_CSV_PREFIX = "MAUD_v1/MAUD_"

# ---------------------------------------------------------------------------
# MAUD subclass dimension — consideration type (expert GT, "Type of
# Consideration" question). This is the data-necessitated second level for
# merger agreements: MAUD ships it as an expert answer per agreement, and the
# sorter can classify it from the agreement's consideration sections.
# ---------------------------------------------------------------------------
CONSIDERATION_SUBCLASSES = [
    {"key": "all_cash", "label": "All Cash Consideration",
     "description": "Consideration payable entirely in cash"},
    {"key": "all_stock", "label": "All Stock Consideration",
     "description": "Consideration payable entirely in stock/equity"},
    {"key": "mixed_cash_stock", "label": "Mixed Cash/Stock Consideration",
     "description": "Consideration payable in a mix of cash and stock"},
    {"key": "mixed_cash_stock_election", "label": "Mixed Cash/Stock Consideration with Election",
     "description": "Mixed consideration with a per-shareholder election"},
]
CONSIDERATION_UNKNOWN = "other"

_CONSIDERATION_ALIASES = {
    "all cash": "all_cash",
    "all stock": "all_stock",
    "mixed cash/stock": "mixed_cash_stock",
    "mixed cash/stock: election": "mixed_cash_stock_election",
}


def normalize_consideration(answer: str | None) -> str:
    """Normalize a MAUD 'Type of Consideration' answer to a subclass key."""
    if not answer:
        return CONSIDERATION_UNKNOWN
    key = re.sub(r"\s+", " ", str(answer).strip().lower())
    return _CONSIDERATION_ALIASES.get(key, CONSIDERATION_UNKNOWN)


# ---------------------------------------------------------------------------
# MAUD tertiary metadata (NOT a classification dimension — see module docstring)
# ---------------------------------------------------------------------------
MAUD_CATEGORIES = [
    "General Information",
    "Conditions to Closing",
    "Material Adverse Effect",
    "Knowledge",
    "Deal Protection and Related Provisions",
    "Operating and Efforts Covenant",
    "Remedies",
]


def _download_zip(url: str, dest: Path) -> Path:
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
                    print(f"\r  {written / 1e6:,.1f} / {total / 1e6:,.1f} MB "
                          f"({written / total * 100:.0f}%)", end="", flush=True)
    print()
    os.replace(part, dest)
    print(f"Downloaded {dest.stat().st_size / 1e6:,.1f} MB to {dest}")
    return dest


def _fetch_hf_csv(split: str) -> list[dict]:
    """Load one MAUD CSV split from the HuggingFace mirror (dev/test only exist there)."""
    import requests

    url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/{HF_CSV_PREFIX}{split}.csv"
    print(f"Fetching HF {split} split from {url}")
    resp = requests.get(url, timeout=600)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))


def _acquire_zenodo_zip(cache_dir: Path) -> Path:
    """Return the local path of the maud_v1.zip (downloading once if needed).

    The caller owns cleanup (the zip is deleted when the run finishes, so a
    contracts + classification pass downloads it exactly once).
    """
    tmp = cache_dir / "maud_v1.zip"
    if not tmp.exists():
        _download_zip(MAUD_ZIP_URL, tmp)
    return tmp


def load_maud_rows(source: str, split: str, cache_dir: Path) -> list[dict]:
    """Load MAUD annotation rows for the requested split.

    ``source='zenodo'`` serves the ``maud_v1.zip`` train CSV (the canonical
    corpus behind LegalBench's maud tasks); ``source='huggingface'`` serves
    train/dev/test from the HF mirror. ``split`` is one of train/dev/test/all.
    """
    rows: list[dict] = []
    if source == "zenodo":
        tmp = _acquire_zenodo_zip(cache_dir)
        with zipfile.ZipFile(tmp) as zf:
            raw = zf.read("data/MAUD_train.csv").decode("utf-8", "replace")
        rows = list(csv.DictReader(io.StringIO(raw)))
        if split in ("dev", "test"):
            print(f"WARNING: the Zenodo zip carries only the train split "
                  f"(dev/test live on HuggingFace) — falling back to train.")
    else:
        for want in ("train", "dev", "test"):
            if split in ("all", want):
                rows.extend(_fetch_hf_csv(want))
    return rows


def load_contract_texts(source: str, cache_dir: Path) -> dict[str, str]:
    """Return ``{contract_name: full_text}`` from the source archive."""
    texts: dict[str, str] = {}
    if source == "zenodo":
        tmp = _acquire_zenodo_zip(cache_dir)
        with zipfile.ZipFile(tmp) as zf:
            for n in zf.namelist():
                if n.startswith("data/contracts/") and n.endswith(".txt"):
                    texts[Path(n).stem] = zf.read(n).decode("utf-8", "replace")
    else:
        import requests

        idx = requests.get(
            f"https://huggingface.co/api/datasets/{HF_REPO}/tree/main/MAUD_v1/contracts",
            timeout=60,
        ).json()
        for entry in idx:
            name = entry.get("path", "")
            if not name.endswith(".txt"):
                continue
            stem = Path(name).stem
            url = (f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/"
                   f"MAUD_v1/contracts/{name.split('/')[-1]}")
            resp = requests.get(url, timeout=600)
            resp.raise_for_status()
            texts[stem] = resp.text
    return texts


def per_contract_consideration(rows: list[dict]) -> dict[str, str]:
    """MAUD expert GT: each contract's dominant 'Type of Consideration' answer."""
    by_contract: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if (row.get("text_type") or "") != "Type of Consideration":
            continue
        answer = (row.get("answer") or "").strip()
        if answer:
            by_contract[row.get("contract_name") or ""].append(answer)
    result: dict[str, str] = {}
    for contract, answers in by_contract.items():
        if not answers:
            result[contract] = CONSIDERATION_UNKNOWN
            continue
        counts = Counter(answers)
        best = counts.most_common(1)[0][0]
        result[contract] = normalize_consideration(best)
    return result


def per_contract_categories(rows: list[dict]) -> dict[str, dict[str, int]]:
    """MAUD category distribution per contract (metadata only)."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        cat = (row.get("category") or "").strip()
        if cat:
            counts[row.get("contract_name") or ""][cat] += 1
    return {c: dict(counts[c]) for c in counts}


def build_contract_records(
    texts: dict[str, str],
    consideration: dict[str, str],
    categories: dict[str, dict[str, int]],
    limit: int,
) -> list[dict]:
    """Build Braintrust records for the merger-agreement dataset."""
    records = []
    for i, contract in enumerate(sorted(texts, key=lambda c: int(re.sub(r"\D", "", c) or 0))):
        if limit and i >= limit:
            break
        doc_text = texts[contract]
        subclass = consideration.get(contract, CONSIDERATION_UNKNOWN)
        records.append({
            "input": {
                "doc_text": doc_text,
                "filename": f"{contract}_merger_agreement.txt",
                "metadata": {
                    "source": "maud_v1",
                    "contract": contract,
                    "expected_doc_type": "merger_agreement",
                    "expected_subclass": subclass,
                    "maud_categories": categories.get(contract, {}),
                    "maud_label_count": sum((categories.get(contract) or {}).values()),
                },
            },
            "expected": {"doc_type": "merger_agreement", "doc_subclass": subclass},
            "expected_output": {
                "doc_type": "merger_agreement",
                "doc_subclass": subclass,
            },
            "metadata": {
                "source": "maud_v1",
                "license": "CC BY 4.0",
                "contract": contract,
                "chars": len(doc_text),
                "expected_doc_type": "merger_agreement",
                "expected_subclass": subclass,
            },
        })
    return records


def build_classification_records(rows: list[dict], split: str) -> list[dict]:
    """Build per-question multi-class classification records from MAUD rows.

    Each row is one (contract, question) classification instance: the model
    must pick the gold answer TEXT from the question's answer space. The
    question's valid classes (distinct answers across the set) are embedded
    in metadata so eval runners can validate with ``--valid-classes``.
    """
    spaces: dict[tuple, list[str]] = defaultdict(list)
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
                "filename": f"maud_{contract}_{row.get('id', 'q')}_{split}.txt",
                "metadata": {
                    "task": task,
                    "subquestion": subquestion,
                    "category": row.get("category") or "",
                    "valid_classes": spaces[q_key],
                    "contract": contract,
                    "maud_id": row.get("id", ""),
                    "split": split,
                },
            },
            "expected": {"doc_type": answer},
            "expected_output": {"doc_type": answer, "task": task, "subquestion": subquestion},
            "metadata": {
                "source": "maud_v1",
                "license": "CC BY 4.0",
                "task": task,
                "subquestion": subquestion,
                "category": row.get("category") or "",
                "answer": answer,
                "label_idx": row.get("label", ""),
                "contract": contract,
                "split": split,
            },
        })
    return records


def write_local_jsonl(records: list[dict], path: Path) -> int:
    """Write Braintrust record dicts to the local JSONL eval shape.

    Each line: ``{filename, doc_text, prompt, expected, metadata}`` — the
    record shape ``load_task_dataset``/the eval runners consume. ``expected``
    is the doc_type label; the subclass rides in ``metadata.expected_subclass``
    (the docclass eval runner reads it from there).
    """
    import json as _json

    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            input_data = record.get("input") or {}
            expected = record.get("expected") or {}
            label = expected.get("doc_type") if isinstance(expected, dict) else expected
            metadata = dict(record.get("metadata") or {})
            metadata.update(input_data.get("metadata") or {})
            row = {
                "filename": input_data.get("filename", ""),
                "doc_text": input_data.get("doc_text", ""),
                "prompt": input_data.get("prompt", ""),
                "expected": label,
                "expected_subclass": expected.get("doc_subclass") if isinstance(expected, dict) else None,
                "metadata": metadata,
            }
            fh.write(_json.dumps(row) + "\n")
            written += 1
    return written


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="zenodo", choices=("zenodo", "huggingface"),
                        help="MAUD source archive (HF adds dev/test splits)")
    parser.add_argument("--split", default="train", choices=("train", "dev", "test", "all"),
                        help="Annotation split for the classification dataset")
    parser.add_argument("--dataset", default="mailroom-maud-contracts",
                        help="Braintrust dataset name for the contracts")
    parser.add_argument("--classification-dataset", default="mailroom-maud-classification",
                        help="Braintrust dataset name for the per-question rows")
    parser.add_argument("--project-id", default=load_braintrust_config().project_id,
                        help="Braintrust project id")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N contracts (0 = all)")
    parser.add_argument("--limit-classification", type=int, default=0,
                        help="Cap the classification rows (0 = all)")
    parser.add_argument("--skip-contracts", action="store_true",
                        help="Skip the contracts dataset (classification only)")
    parser.add_argument("--skip-classification", action="store_true",
                        help="Skip the per-question dataset (contracts only)")
    parser.add_argument("--local-dump", type=Path, default=None,
                        help="Write local JSONL to <dir>/contracts.jsonl + <dir>/classification.jsonl "
                             "(the reliable eval path while Braintrust row uploads are capped)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(tempfile.gettempdir()) / "maud_stream",
                        help="Temp dir for the source archive (deleted after use)")
    args = parser.parse_args(argv)

    args.cache_dir.mkdir(parents=True, exist_ok=True)

    rows = load_maud_rows(args.source, args.split, args.cache_dir)
    print(f"Loaded {len(rows)} MAUD annotation rows ({args.split} split, {args.source} source)")
    if not args.skip_contracts:
        texts = load_contract_texts(args.source, args.cache_dir)
        print(f"Loaded {len(texts)} merger agreements")
    else:
        texts = {}
    if args.source == "zenodo":
        _zip = _acquire_zenodo_zip(args.cache_dir)
        try:
            _zip.unlink()
            args.cache_dir.rmdir()
        except OSError:
            pass

    consideration = per_contract_consideration(rows)
    categories = per_contract_categories(rows)
    subclass_counts = Counter(consideration.values())
    print(f"Consideration-type subclass GT: {dict(subclass_counts)}")

    contract_records = [] if args.skip_contracts else build_contract_records(
        texts, consideration, categories, args.limit)
    classification_records = [] if args.skip_classification else build_classification_records(
        rows, args.split)
    if args.limit_classification:
        classification_records = classification_records[: args.limit_classification]

    if contract_records:
        print(f"Contracts: {len(contract_records)} "
              f"({sum(r['metadata']['chars'] for r in contract_records) / 1e6:,.1f} MB text)")
    if classification_records:
        tasks = len({r["metadata"]["task"] for r in classification_records})
        print(f"Classification rows: {len(classification_records)} across {tasks} question families")

    if args.local_dump:
        n_contracts = write_local_jsonl(contract_records, args.local_dump / "contracts.jsonl") if contract_records else 0
        n_class = write_local_jsonl(classification_records, args.local_dump / "classification.jsonl") if classification_records else 0
        print(f"Local dump: {n_contracts} contract rows -> {args.local_dump / 'contracts.jsonl'}, "
              f"{n_class} classification rows -> {args.local_dump / 'classification.jsonl'}")

    if args.dry_run:
        if contract_records:
            for r in contract_records[:5]:
                print(f"  would sync  {r['input']['filename']}  "
                      f"(doc_type={r['expected']['doc_type']}, subclass={r['expected']['doc_subclass']})")
            if len(contract_records) > 5:
                print(f"  ... and {len(contract_records) - 5} more contracts")
        if classification_records:
            for r in classification_records[:3]:
                print(f"  would sync  {r['input']['filename']}  "
                      f"(task={r['metadata']['task']!r} -> {r['expected']['doc_type']!r})")
            if len(classification_records) > 3:
                print(f"  ... and {len(classification_records) - 3} more classification rows")
        print(f"\nDry run: {len(contract_records)} contract records + "
              f"{len(classification_records)} classification rows")
        return 0

    if contract_records and not args.local_dump:
        (api_key,) = require_env("BRAINTRUST_API_KEY")
        summary = upload_text_dataset(
            contract_records,
            project_id=args.project_id,
            dataset_name=args.dataset,
            api_key=api_key,
            description=f"MAUD v1 merger agreements ({len(contract_records)} docs, CC BY 4.0)",
            metadata={"source": "maud_v1", "license": "CC BY 4.0",
                      "subclass_dimension": "consideration_type"},
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
                description=f"MAUD per-question multi-class classification "
                            f"({len(classification_records)} rows, CC BY 4.0, split={args.split})",
                metadata={"source": "maud_v1", "license": "CC BY 4.0", "split": args.split},
                on_progress=lambda i, n: print(f"  Inserted {i}/{n} classification rows..."),
            )
            print(f"Classification: {class_summary['inserted']} inserted, "
                  f"{class_summary['failed']} failed into {args.classification_dataset}")
            return 0 if class_summary["failed"] == 0 else 1
        return 0 if summary["failed"] == 0 else 1

    if args.local_dump:
        print("Local dump written; Braintrust upload skipped (use --local-dump only "
              "when the org plan caps dataset rows).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
