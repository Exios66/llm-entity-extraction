#!/usr/bin/env python3
"""Build the ContractEval (arXiv 2508.03080) CUAD test split into local JSONL.

The paper (and github.com/olivialiu121/ContractEval) evaluate LLMs on the CUAD
test set, one (contract, question) call per row. The authoritative source is the
SQuAD-style ``test.json`` inside the Atticus CUAD ``data.zip``
(https://github.com/TheAtticusProject/cuad/raw/main/data.zip) — the exact file
the HuggingFace ``theatticusproject/cuad-qa`` loader downloads for its ``test``
split (this repo does not depend on the ``datasets`` package).

Builds (into ``data/contracteval/`` by default):
  contracteval_test.jsonl       4,182 (contract, question) pairs {id, title,
                                category, question, label_spans, n_labels} —
                                compact (no context duplication) — gitignored
  contracteval_contracts.jsonl  102 contracts {title, context} (FULL text) —
                                gitignored
  questions.json                41 {category: question} — committed curated ref
  testset_summary.json          counts, positive/negative, fingerprint — committed

Fidelity notes (documented in the summary + the card):
  - 102 contracts x 41 categories = 4,182 pairs; positives = 1,244 — EXACTLY the
    hardcoded denominator in ContractEval's ``Evaluation.py`` (false rate is
    reported over the paper's 1,244 positives).
  - The paper reports 4,128 total — a 54-negative-row-smaller snapshot of the
    same ``test.json``; the positive set is identical, so F1/F2/Jaccard/false-nr
    are directly comparable.
  - ``context`` is the FULL contract (min 645 / max 300,768 chars): the paper
    feeds it whole in ONE call (faithful mirror — the eval runner disables the
    repo's input cap for this task).

Usage:
    python scripts/datasets/build_contracteval_testset.py --dry-run
    python scripts/datasets/build_contracteval_testset.py
    python scripts/datasets/build_contracteval_testset.py --out-dir /tmp/contracteval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests  # noqa: E402
import structlog  # noqa: E402

from src.cuad_ground_truth import CUAD_CATEGORIES  # noqa: E402

logger = structlog.get_logger(__name__)

DATA_URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
DEFAULT_OUT_DIR = Path("data/contracteval")
_QUESTION_CATEGORY_RE = re.compile(r'related to "([^"]+)"')
_UA = "llm-entity-extraction-contracteval-builder/1.0 (research sampling)"


def _category_of(question: str) -> str:
    """The CUAD category named in a test.json question string.

    The test set questions use the template "Highlight the parts (if any) of
    this contract related to \"<Category>\" that should be reviewed by a
    lawyer. Details: ..." — the quoted phrase is the canonical CUAD category
    name (1:1 with ``CUAD_CATEGORIES`` keys, verified on all 41 unique
    questions).
    """
    m = _QUESTION_CATEGORY_RE.search(question)
    if m:
        return m.group(1).strip()
    quoted = re.search(r'"([^"]+)"', question)
    return quoted.group(1).strip() if quoted else ""


def download_and_extract(data_dir: Path, force: bool = False) -> Path:
    """Download + extract the Atticus CUAD data.zip (resumable).

    Returns the path to the extracted ``test.json``. Existing non-empty
    downloads are skipped unless ``--force`` (mirrors the other streamers'
    resumable-download discipline).
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = data_dir / "cuad-data.zip"
    if not zip_path.exists() or zip_path.stat().st_size == 0 or force:
        print(f"Downloading {DATA_URL} ...")
        with requests.get(DATA_URL, stream=True, headers={"User-Agent": _UA}) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as handle:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    handle.write(chunk)
        print(f"[written] {zip_path}")
    else:
        print(f"[cached] {zip_path}")
    extracted = data_dir / "cuad-data"
    if not (extracted / "test.json").exists() or force:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extracted)
    test_path = extracted / "test.json"
    if not test_path.exists():
        raise FileNotFoundError(f"test.json not found after extraction in {extracted}")
    return test_path


def parse_test_rows(test_json_path: Path) -> tuple[list[dict], dict[str, str]]:
    """Parse test.json into (pairs, contracts) with deterministic order.

    ``pairs`` are the (contract, question) rows WITHOUT the context (compact);
    ``contracts`` maps title -> full contract text (stored once, like the
    SQuAD source).
    """
    with open(test_json_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    rows: list[dict] = []
    contracts: dict[str, str] = {}
    for doc in payload.get("data", []):
        title = (doc.get("title") or "").strip()
        for paragraph in doc.get("paragraphs", []):
            context = (paragraph.get("context") or "").strip()
            contracts[title] = context
            for qa in paragraph.get("qas", []):
                qid = str(qa.get("id") or "").strip()
                question = (qa.get("question") or "").strip()
                spans = [a.get("text", "").strip()
                         for a in qa.get("answers", []) if a.get("text", "").strip()]
                category = _category_of(question)
                if not qid or not question or not context:
                    logger.warning("row_skipped", id=qid, title=title)
                    continue
                rows.append({
                    "id": qid,
                    "title": title,
                    "category": category,
                    "question": question,
                    "label_spans": spans,
                    "n_labels": len(spans),
                })
    rows.sort(key=lambda r: r["id"])
    return rows, contracts


def _fingerprint(rows: list[dict], contracts: dict[str, str]) -> str:
    """Deterministic identity over pairs + contract texts."""
    pair_payload = "\n".join(
        f"{r['id']}\0{r['category']}\0{len(r['label_spans'])}" for r in rows
    ).encode("utf-8")
    contract_payload = "\n".join(
        f"{title}\0{len(context)}" for title, context in sorted(contracts.items())
    ).encode("utf-8")
    return hashlib.sha256(pair_payload + b"\n" + contract_payload).hexdigest()


def build(out_dir: Path, data_dir: Path, force: bool = False) -> tuple[list[dict], dict[str, str], dict]:
    """Run the full build; returns (rows, contracts, summary)."""
    test_path = download_and_extract(data_dir, force=force)
    rows, contracts = parse_test_rows(test_path)

    n_positive = sum(1 for r in rows if r["label_spans"])
    n_negative = len(rows) - n_positive
    categories = sorted({r["category"] for r in rows})
    missing = sorted(set(categories) - set(CUAD_CATEGORIES))
    if missing:
        raise ValueError(f"categories not in CUAD_CATEGORIES: {missing}")

    summary = {
        "source_url": DATA_URL,
        "n_contracts": len(contracts),
        "n_rows": len(rows),
        "n_positive": n_positive,
        "n_negative": n_negative,
        "positive_rate": round(n_positive / len(rows), 4) if rows else 0.0,
        "n_categories": len(categories),
        "fingerprint": _fingerprint(rows, contracts),
        "context_min_chars": min((len(c) for c in contracts.values()), default=0),
        "context_max_chars": max((len(c) for c in contracts.values()), default=0),
        "fidelity_note": (
            "102 contracts x 41 categories = 4,182 pairs; positives = 1,244 = the "
            "hardcoded denominator in ContractEval's Evaluation.py. The paper "
            "reports 4,128 total (a 54-negative-row-smaller snapshot); the positive "
            "set is identical, so F1/F2/Jaccard/false-nr are directly comparable."
        ),
    }
    return rows, contracts, summary


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="Output directory (default: data/contracteval)")
    parser.add_argument("--data-dir", type=Path, default=Path("data/contracteval/_cache"),
                        help="Where to cache the downloaded data.zip + extraction")
    parser.add_argument("--force", action="store_true",
                        help="Re-download and re-extract even if cached")
    parser.add_argument("--dry-run", action="store_true",
                        help="Download/inspect only; write nothing to out-dir")
    args = parser.parse_args(argv)

    rows, contracts, summary = build(args.out_dir, args.data_dir, force=args.force)
    print(f"Contracts: {summary['n_contracts']} | rows: {summary['n_rows']} "
          f"(positive {summary['n_positive']} / negative {summary['n_negative']}, "
          f"{summary['positive_rate']:.1%}) | categories: {summary['n_categories']} "
          f"| fp {summary['fingerprint'][:12]}")

    if args.dry_run:
        print("Dry run: nothing written to out-dir.")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)

    with (args.out_dir / "contracteval_test.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    print(f"[written] {args.out_dir / 'contracteval_test.jsonl'}")

    with (args.out_dir / "contracteval_contracts.jsonl").open("w", encoding="utf-8") as fh:
        for title, context in sorted(contracts.items()):
            fh.write(json.dumps({"title": title, "context": context}) + "\n")
    print(f"[written] {args.out_dir / 'contracteval_contracts.jsonl'}")

    questions = {cat: next(r["question"] for r in rows if r["category"] == cat)
                 for cat in sorted({r["category"] for r in rows})}
    (args.out_dir / "questions.json").write_text(json.dumps(questions, indent=2) + "\n")
    print(f"[written] {args.out_dir / 'questions.json'}")

    (args.out_dir / "testset_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    print(f"[written] {args.out_dir / 'testset_summary.json'}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
