#!/usr/bin/env python3
"""Build the MERGED docclass corpus: one dataset with every docclass document.

Combines the three docclass corpora into a single flat JSONL dump
(``data/datasets/docclass_merged.jsonl``, gitignored) — the ONE dataset that
the hierarchical sorter eval (``run_langfuse_docclass_eval.py --local-dumps``)
and the Langfuse mirror (``sync_langfuse_datasets.py --docclass``) consume:

    mailroom-cuad-contracts-full  -> 509 contract rows            (Braintrust)
    data/maud/contracts.jsonl     -> 152 merger_agreement rows    (local dump)
    data/s1_corporate_records/    ->  39 corporate_record rows    (local dump)
                                   = 700 rows total

Every row carries the flat streamer-dump shape the docclass eval runner reads:
``{filename, doc_text, prompt, expected, expected_subclass, metadata}`` where
``expected`` is the doc_type key and ``expected_subclass`` the second-level
key (KANBAN-073 schema v2: every row carries a non-empty string for both —
contracts use CUAD's own contract grouping, ``metadata.category``). The
builder REFUSES to write if any row lacks either field: a partial-null
schema is what crashed the Hub viewer (JSON loader infers null-typed columns
from all-null batches, then fails casting later string batches).

The merged dump is deterministically ordered (by corpus, then filename) so
its dataset fingerprint is reproducible across rebuilds. Use it as the single
docclass A/B surface:

    python scripts/datasets/build_docclass_merged.py                 # rebuild
    python scripts/eval/run_langfuse_docclass_eval.py \\
        --local-dumps data/datasets/docclass_merged.jsonl \\
        --stratified 30 --seed 42 --prompt-version sorter_docclass_v3
    python scripts/eval/sync_langfuse_datasets.py --docclass          # -> Langfuse

Usage:
    python scripts/datasets/build_docclass_merged.py --dry-run
    python scripts/datasets/build_docclass_merged.py
    python scripts/datasets/build_docclass_merged.py --out data/datasets/docclass_merged.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path("data/datasets/docclass_merged.jsonl")
MAUD_DUMP = Path("data/maud/contracts.jsonl")
S1_DUMP = Path("data/s1_corporate_records/corporate-records.jsonl")
CUAD_DATASET = "mailroom-cuad-contracts-full"
CUAD_SUBCLASS_NOTE = (
    "Contract rows carry expected_subclass = CUAD's own contract grouping "
    "(metadata.category, 28 groups) and filename = the source PDF basename "
    "(KANBAN-073 schema v2). Schema v3 adds a deterministic per-row "
    "`split` (md5-of-filename 90/10 train/test — rebuild-stable, "
    "KANBAN-074)."
)


def assign_split(filename: str) -> str:
    """Deterministic 90/10 train/test split keyed on the row's filename.

    md5 hex digest mod 10 == 0 -> test (10%), else train (90%). Stable
    across rebuilds and machines, independent of row order — the same
    document always lands in the same split, and the SAME rule is used by
    every dataset in the Lucius-Morningstar family (KANBAN-074).
    """
    digest = int(hashlib.md5(filename.strip().encode("utf-8")).hexdigest(), 16)
    return "test" if digest % 10 == 0 else "train"


def load_cuad_rows_local(staging_jsonl: Path | None = None) -> list[dict]:
    """Load CUAD contract rows from the local staging export (BT-free path).

    The staging JSONL is the sha-verified KANBAN-069 export of
    ``mailroom-cuad-contracts-full`` (byte-identical to the Hub copy). With
    BT write quota exhausted, this keeps the docclass build reproducible
    without touching Braintrust at all.
    """
    path = staging_jsonl or (REPO_ROOT / "data" / "hf_export"
                             / f"{CUAD_DATASET}.jsonl")
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            bt_row = json.loads(line)
            inp = bt_row.get("input") or {}
            exp = bt_row.get("expected") or {}
            metadata = dict(bt_row.get("metadata") or {})
            metadata["source_dataset"] = CUAD_DATASET
            metadata["source_provenance"] = "local-staging-export"
            # KANBAN-073 schema v2: contracts carry their subclass (CUAD's own
            # grouping, metadata.category) and the source file name (pdf_path
            # basename). Both are 100% covered in the staging export — rows
            # missing either are refused below, never silently nulled.
            pdf_path = str(metadata.get("pdf_path") or "")
            fn = pdf_path.rsplit("/", 1)[-1] if pdf_path \
                else str(inp.get("filename") or "")
            rows.append({
                "filename": fn,
                "doc_text": str(inp.get("doc_text") or inp.get("text") or ""),
                "prompt": str(inp.get("prompt") or ""),
                "expected": str(exp.get("doc_type") if isinstance(exp, dict)
                                else exp or "").strip(),
                "expected_subclass": str(metadata.get("category") or "").strip() or None,
                "split": assign_split(fn),
                "metadata": metadata,
            })
    return [r for r in rows if r["doc_text"].strip() and r["expected"]]


def load_cuad_rows(project: str, project_id: str) -> list[dict]:
    """Load the CUAD contract rows from Braintrust (the reliable CUAD source)."""
    from src.braintrust_config import load_braintrust_config
    from src.braintrust_utils import load_braintrust_dataset

    cfg = load_braintrust_config()
    dataset = load_braintrust_dataset(project or cfg.project_name, CUAD_DATASET,
                                      valid=None, project_id=project_id or cfg.project_id)
    rows = []
    for d in dataset:
        metadata = dict(d.get("metadata") or {})
        metadata["source_dataset"] = CUAD_DATASET
        # KANBAN-073 schema v2 (same contract-subclass/filename fill as the
        # local-staging path above).
        pdf_path = str(metadata.get("pdf_path") or "")
        fn = pdf_path.rsplit("/", 1)[-1] if pdf_path else str(d.get("filename") or "")
        rows.append({
            "filename": fn,
            "doc_text": str(d.get("doc_text") or ""),
            "prompt": str(d.get("prompt") or ""),
            "expected": str(d.get("expected") or "").strip(),
            "expected_subclass": str(metadata.get("category") or "").strip() or None,
            "split": assign_split(fn),
            "metadata": metadata,
        })
    return [r for r in rows if r["doc_text"].strip() and r["expected"]]


def load_dump_rows(path: Path) -> list[dict]:
    """Load one streamer ``--local-dump`` JSONL (MAUD / S-1) as flat rows."""
    rows = []
    if not path.exists():
        print(f"WARNING: local dump not found: {path}", file=sys.stderr)
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            metadata = dict(row.get("metadata") or {})
            metadata["source_dataset"] = str(path)
            fn = str(row.get("filename") or "")
            rows.append({
                "filename": fn,
                "doc_text": str(row.get("doc_text") or ""),
                "prompt": str(row.get("prompt") or ""),
                "expected": str(row.get("expected") or "").strip(),
                "expected_subclass": row.get("expected_subclass")
                                     or metadata.get("expected_subclass"),
                "split": assign_split(fn),
                "metadata": metadata,
            })
    return [r for r in rows if r["doc_text"].strip() and r["expected"]]


def normalize_metadata_rows(rows: list[dict]) -> list[dict]:
    """KANBAN-076: make the ``metadata`` column cast-safe for the Hub loader.

    The datasets-server JSON loader infers ONE arrow struct schema for the
    metadata column from the first row-group, then casts every later group
    to it. A key present only in later rows — e.g. MAUD's nested
    ``maud_categories`` dict, absent from the leading CUAD block — crashes
    the conversion (``TypeError: Couldn't cast array of type struct<…>``):
    the KANBAN-073 partial-schema failure, one level deeper. Normalize so
    every row carries the SAME key set with uniform scalar types:

    - union of all metadata keys on EVERY row (missing -> empty string,
      never null — null-typed columns are the 073 crash)
    - nested dicts AND lists -> compact sorted-key JSON strings (a key that
      is list-typed on some rows MUST be string-typed on all rows: the
      loader casts later row-groups against the first group's inferred
      schema, and string != list<string> is a hard cast error)
    - scalars -> strings
    """
    if not rows:
        return rows
    union = sorted({k for r in rows for k in (r.get("metadata") or {})})
    for r in rows:
        md = r.get("metadata") or {}
        flat = {}
        for k in union:
            v = md.get(k, "")
            if isinstance(v, (dict, list)):
                v = json.dumps(v, sort_keys=True, ensure_ascii=False)
            else:
                v = "" if v is None else str(v)
            flat[k] = v
        r["metadata"] = flat
    return rows


def build_merged(cuad: list[dict], maud: list[dict], s1: list[dict]) -> list[dict]:
    """Merge the three corpora into one deterministic row list.

    Corpus order: contract (CUAD), merger_agreement (MAUD), corporate_record
    (S-1); within each corpus rows are filename-sorted so rebuilds produce a
    byte-identical dump and therefore the same dataset fingerprint.
    Metadata is normalized cast-safe (see ``normalize_metadata_rows``).
    """
    merged = []
    for corpus in (cuad, maud, s1):
        merged.extend(sorted(corpus, key=lambda r: r["filename"]))
    return normalize_metadata_rows(merged)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Output JSONL path (default: {DEFAULT_OUT})")
    parser.add_argument("--project", default=None,
                        help="Braintrust project holding the CUAD dataset (default: config)")
    parser.add_argument("--project-id", default=None, help="Braintrust project id")
    parser.add_argument("--maud-dump", type=Path, default=MAUD_DUMP,
                        help=f"MAUD contracts dump (default: {MAUD_DUMP})")
    parser.add_argument("--s1-dump", type=Path, default=S1_DUMP,
                        help=f"S-1 corporate-record dump (default: {S1_DUMP})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load + count the sources and print the plan without writing")
    parser.add_argument("--bt-cuad", action="store_true",
                        help="Load CUAD rows from Braintrust instead of the local "
                             "staging export (fallback path; BT reads only)")
    args = parser.parse_args(argv)

    staging = REPO_ROOT / "data" / "hf_export" / f"{CUAD_DATASET}.jsonl"
    if args.bt_cuad or not staging.exists():
        print(f"Loading CUAD rows from Braintrust dataset {CUAD_DATASET} ...")
        cuad = load_cuad_rows(args.project, args.project_id)
    else:
        print(f"Loading CUAD rows from local staging export ({staging.name}) ...")
        cuad = load_cuad_rows_local(staging)
    maud = load_dump_rows(args.maud_dump)
    s1 = load_dump_rows(args.s1_dump)
    print(f"  CUAD contract rows: {len(cuad)}")
    print(f"  MAUD merger_agreement rows: {len(maud)}")
    print(f"  S-1 corporate_record rows: {len(s1)}")

    merged = build_merged(cuad, maud, s1)
    if not merged:
        parser.error("No rows loaded — check the Braintrust keys and local dumps.")
    # KANBAN-073/074 schema guard: every row must carry non-empty string
    # filename, expected_subclass AND a train/test split. A single null
    # would poison the Hub viewer's schema inference (string→null cast
    # crash) — refuse to write, loudly.
    bad = [r["metadata"].get("source_dataset", "?") for r in merged
           if not (isinstance(r.get("filename"), str) and r["filename"].strip())
           or not (isinstance(r.get("expected_subclass"), str)
                   and r["expected_subclass"].strip())
           or r.get("split") not in ("train", "test")]
    if bad:
        parser.error(
            f"{len(bad)} rows lack filename/expected_subclass — refusing to "
            f"write a partial-null schema (Hub viewer crashes on it). "
            f"Offending source_datasets: {sorted(set(bad))[:5]}")
    if len(merged) < 600:
        print(f"WARNING: expected ~700 rows (509 CUAD + 152 MAUD + 39 S-1), got "
              f"{len(merged)} — a source corpus may be missing or empty.",
              file=sys.stderr)

    from collections import Counter

    from src.evaluation import dataset_fingerprint

    counts = Counter(r["expected"] for r in merged)
    sub_counts = Counter(r["expected_subclass"] for r in merged if r["expected_subclass"])
    print(f"\nMerged docclass corpus: {len(merged)} rows "
          f"(doc_type {dict(counts)}; subclass GT {dict(sub_counts)})")
    print(f"CUAD subclass note: {CUAD_SUBCLASS_NOTE}")
    print(f"dataset_fingerprint: {dataset_fingerprint(merged)}")

    if args.dry_run:
        print(f"\nDry run: would write {len(merged)} rows -> {args.out}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in merged:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(merged)} rows -> {args.out}")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
