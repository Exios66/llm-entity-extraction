#!/usr/bin/env python3
"""Publish the DEDUPLICATED ENRON CORRESPONDENCE corpus to the Hugging Face Hub.

KANBAN-076 (human directive 2026-08-23): finish the HF family sync — including
the deduplicated + cleaned Enron dataset. Full-corpus EDA (Enron-Evaluation-
Environment ``reports/eda/report.md`` §14) showed over half of the non-empty
message bodies in the corpus are byte-exact copies (cross-custodian cc'ing,
blast mails, saved sent-folder copies), so the full-corpus release
(``enron-correspondence``, 517,390 rows) repeatedly draws the same underlying
text under different filenames.

This publisher consumes the sha256-VERIFIED staged export of the full corpus
(``data/hf_export/enron_correspondence.jsonl``, LFS sha ``0554a5973935…``) and
publishes:

    Lucius-Morningstar/enron-correspondence-dedup

Deduplication rule — SINGLE SOURCE OF TRUTH: imports ``body_hash`` from
Enron-Evaluation-Environment's ``scripts/dedupe.py`` (the exact module the EDA
§14 duplicate counting uses):

- md5 over UTF-8 (errors="ignore") of the row's ``text`` (== the indexed body)
- rows with EMPTY text are NEVER treated as duplicates of each other (they
  carry distinct headers/paths)
- FIRST occurrence wins; the staged export preserves the corpus index's
  sorted-maildir-path order, so output is deterministic and byte-comparable
  to ``scripts/dedupe.py`` applied upstream

Everything else passes through untouched: labels, evidence, metadata, splits.
Splits are RECOMPUTED and asserted (never trusted): the family rule
``md5(filename) % 10 == 0 -> test`` is filename-keyed, so removing duplicate
rows cannot change any surviving row's split — the assert proves it.

Schema guard (KANBAN-073/074 lesson): rows lacking non-null
filename/subclass/split or a string text refuse to publish. The manifest is
shipped ONLY as ``manifest.json.txt`` — a bare root ``manifest.json`` gets
ingested by the Hub's JSON loader as a 1-row data table (CastError,
"column names don't match").

Usage:
    .venv/bin/python scripts/datasets/publish_enron_correspondence_dedup.py \
        [--source data/hf_export/enron_correspondence.jsonl] [--write] [--publish]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.datasets.build_docclass_merged import assign_split  # noqa: E402  (single split-rule source)

DEFAULT_SOURCE = REPO_ROOT / "data" / "hf_export" / "enron_correspondence.jsonl"
ENRON_SCRIPTS = Path.home() / "Enron-Evaluation-Environment" / "scripts"
OUT_DIR = REPO_ROOT / "data" / "hf_export"
STAGED_NAME = "enron_correspondence_dedup.jsonl"
HF_USERNAME = os.environ.get("HF_USERNAME", "Lucius-Morningstar")
REPO_ID = f"{HF_USERNAME}/enron-correspondence-dedup"

# sha256 prefix of the verified full-corpus export this MUST be built from
EXPECTED_SOURCE_SHA_PREFIX = "0554a5973935"

CARD = """---
license: other
task_categories:
- text-classification
language:
- en
tags:
- legal
- enron
- email
- correspondence
- document-classification
- evaluation
- deduplicated
- llm-mailroom
pretty_name: "Enron Correspondence Deduplicated (Cleaned, Subclass-Labeled)"
size_categories:
- 100K<n<1M
---

# Enron Correspondence Deduplicated (Cleaned, Subclass-Labeled)

The **deduplicated** companion to
[`Lucius-Morningstar/enron-correspondence`](https://huggingface.co/datasets/Lucius-Morningstar/enron-correspondence):
exact-duplicate bodies removed from the full cleaned CMU Enron corpus so that
sampling draws each distinct message text at most once. Every surviving row
keeps its ground-truth subclass label from the shared
[`correspondence_subclasses`](https://github.com/Exios66/Enron-Evaluation-Environment)
labeler (10-key taxonomy), on-row audit evidence, rich metadata, and the
family's deterministic train/test split.

## Deduplication rule

Byte-exact duplicate removal keyed on **md5 of the UTF-8 message body**
(``body_hash`` from Enron-Evaluation-Environment ``scripts/dedupe.py`` — the
same hash the source repo's EDA §14 uses, so counts are directly comparable):

- {total_rows:,} full-corpus rows in → **{written:,} unique-text rows out**
  ({dropped:,} duplicate copies dropped; largest duplicate group:
  {largest_group:,} copies of one text)
- FIRST occurrence wins (rows ordered by maildir path — deterministic;
  rebuilding reproduces this file byte-for-byte given the same source)
- Rows with an **empty body are never deduped against each other** — they
  carry distinct headers/paths and are all retained ({empty_kept:,} kept)

Honest gap: this is EXACT-hash deduplication only. Near-duplicates
(quote-stripped replies, minor edits, same attachment re-sent) are NOT
detected — use ``metadata.message_id`` / ``metadata.in_reply_to`` for
thread-level grouping.

## Row shape

Identical schema to the full-corpus dataset — one JSON object per line:

| Field | Meaning |
|---|---|
| `filename` | maildir path relative to the root (stable row id; the KEPT copy's path) |
| `text` | cleaned email body (text/plain, else HTML-stripped) |
| `subject` | decoded subject header |
| `expected` | gold doc_type — always `correspondence` |
| `expected_subclass` | heuristic ground truth: `{taxonomy}` |
| `label_evidence` | which marker/rule fired (on-row audit trail) |
| `split` | `train` / `test` — md5(filename) mod 10 == 0 → test (~10%) |
| `metadata` | custodian, folder, date, sender, message/thread ids, recipient + attachment facts, source/license |

Labels are HEURISTIC ground truth (regex/marker rules, human-reviewed via
spot checks in the source repo) — not hand annotations. Known honest gaps
(source repo AGENTS.md): attorney detection relies on domain/name lists and
is not exhaustive; `voicemail` cannot occur in this text-only corpus.

## Splits

Per-row `split` unchanged from the full corpus for every surviving row: the
rule keys on `filename`, which dedup never alters — recomputed and asserted
row-by-row at build time (`assign_split()` from the family's single split
implementation). Split coverage: train {train_n:,} / test {test_n:,}.

## Subclass ground truth (post-dedup)

{subclass_table}

## Provenance

Built by [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
`scripts/datasets/publish_enron_correspondence_dedup.py` (KANBAN-076,
{built_utc}) from the sha256-verified full-corpus export (LFS
`0554a5973935…`, byte-identical local == Hub). Source: CMU Enron Email
Dataset (cleaned maildir) via Enron-Evaluation-Environment
`build_corpus_index.py`; dedup rule `scripts/dedupe.py`. Research-use
license — treat personally identifying content accordingly.
"""


def load_dedupe_module(enron_scripts: Path):
    spec = importlib.util.spec_from_file_location(
        "enron_dedupe", enron_scripts / "dedupe.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"dedupe.py not found under {enron_scripts}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="sha-verified staged full-corpus export")
    parser.add_argument("--enron-scripts", type=Path, default=ENRON_SCRIPTS,
                        help="dir holding dedupe.py (single-source hash)")
    parser.add_argument("--out", type=Path, default=OUT_DIR / STAGED_NAME)
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test cap on rows read")
    parser.add_argument("--write", action="store_true",
                        help="write the dedup'd JSONL + manifest locally")
    parser.add_argument("--publish", action="store_true",
                        help="upload to the Hub (requires --write artifacts)")
    args = parser.parse_args(argv)

    if not args.source.exists():
        parser.error(f"source not found: {args.source}")

    # ---- integrity gate: only build from the VERIFIED export ----
    print(f"verifying source sha256: {args.source} ...")
    src_sha = hashlib.sha256(args.source.read_bytes()).hexdigest()
    print(f"  sha256 {src_sha[:16]}…")
    if not src_sha.startswith(EXPECTED_SOURCE_SHA_PREFIX):
        parser.error(f"source sha {src_sha[:12]} != expected "
                     f"{EXPECTED_SOURCE_SHA_PREFIX}… — refusing to build from "
                     f"unverified bytes")

    dedupe = load_dedupe_module(args.enron_scripts)
    body_hash = dedupe.body_hash

    # ---- stream-dedupe (first occurrence wins) ----
    seen: set[str] = set()
    rows_out: list[dict] = []
    total = dropped_duplicates = empty_body_kept = split_fixed = 0
    sub_before: Counter = Counter()
    sub_after: Counter = Counter()
    custodians: set[str] = set()
    hash_counts: Counter = Counter()

    with args.source.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if args.limit and total >= args.limit:
                break
            total += 1
            r = json.loads(line)
            sub_before[r["expected_subclass"]] += 1
            h = body_hash(r["text"])
            if h is not None:
                hash_counts[h] += 1
                if h in seen:
                    dropped_duplicates += 1
                    continue
                seen.add(h)
            else:
                empty_body_kept += 1

            # splits: recompute from filename, assert equal to shipped value
            fn = r["filename"]
            want = assign_split(fn)
            if want != r["split"]:
                r["split"] = want
                split_fixed += 1

            rows_out.append(r)
            sub_after[r["expected_subclass"]] += 1
            custodians.add(str(r.get("metadata", {}).get("custodian") or ""))

    largest_group = max(hash_counts.values()) if hash_counts else 0
    written = len(rows_out)
    print(f"\nread {total:,} rows -> wrote {written:,} "
          f"(dropped {dropped_duplicates:,} duplicates, "
          f"{empty_body_kept:,} empty-body rows kept)")
    print(f"custodians: {len(custodians)} | largest dup group: {largest_group:,}")
    print(f"split mismatches fixed: {split_fixed} (must be 0)")

    # ---- schema guard ----
    bad = [i for i, r in enumerate(rows_out)
           if not (isinstance(r["filename"], str) and r["filename"].strip())
           or not (isinstance(r["expected_subclass"], str)
                   and r["expected_subclass"] in sub_after)
           or r["split"] not in ("train", "test")
           or not isinstance(r["text"], str)]
    if bad:
        parser.error(f"{len(bad)} rows fail the schema guard "
                     f"(first: {bad[0]}) — refusing to publish")
    train_n = sum(1 for r in rows_out if r["split"] == "train")
    test_n = written - train_n

    manifest = {
        "name": "enron-correspondence-dedup",
        "schema_version": 1,
        "derived_from": {
            "dataset": "Lucius-Morningstar/enron-correspondence",
            "source_lfs_sha256_prefix": EXPECTED_SOURCE_SHA_PREFIX,
            "verified_local_sha256": src_sha,
        },
        "rows": written,
        "source_rows": total,
        "dropped_duplicates": dropped_duplicates,
        "empty_body_rows_kept": empty_body_kept,
        "largest_duplicate_group_copies": largest_group,
        "unique_texts": len(seen),
        "custodians": len(custodians),
        "subclass_counts_source": dict(sub_before),
        "subclass_counts_dedup": dict(sub_after),
        "split_coverage": {"train": train_n, "test": test_n,
                           "rule": "md5(filename) % 10 == 0 -> test (10%); "
                                   "filename-keyed so dedup cannot change any "
                                   "surviving row's split; recomputed+asserted"},
        "dedupe_rule": "md5(text utf-8 errors=ignore); empty-body rows never "
                       "deduped against each other; first occurrence wins "
                       "(maildir-path order) — scripts/dedupe.py body_hash",
        "honest_gaps": [
            "EXACT-hash dedup only: near-duplicates (quote-stripped replies, "
            "minor edits) not detected",
            "heuristic GT labels (see source repo); voicemail impossible in "
            "text-only corpus",
        ],
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            for row in rows_out:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        out_sha = hashlib.sha256(args.out.read_bytes()).hexdigest()
        manifest["local_sha256"] = out_sha
        (OUT_DIR / "enron_correspondence_dedup.manifest.json").write_text(
            json.dumps(manifest, indent=2))
        (OUT_DIR / "KANBAN076_DEDUP_STATS.json").write_text(
            json.dumps(manifest, indent=2))
        print(f"\nwrote {written:,} rows -> {args.out}")
        print(f"sha256: {out_sha[:12]}… "
              f"({args.out.stat().st_size >> 20} MB)")

    if args.publish:
        token = os.environ.get("HF_TOKEN") or None
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        print(f"HF account: {api.whoami()['name']}")
        api.create_repo(repo_id=REPO_ID, repo_type="dataset", private=False,
                        exist_ok=True)

        import tempfile
        tax = ", ".join(sorted(sub_after))
        sub_rows = "\n".join(
            f"| {k} | {v:,} |" for k, v in sub_after.most_common())
        card_ctx = {
            "total_rows": total,
            "written": written,
            "dropped": dropped_duplicates,
            "empty_kept": empty_body_kept,
            "largest_group": largest_group,
            "taxonomy": tax,
            "train_n": train_n,
            "test_n": test_n,
            "subclass_table": "| subclass | rows |\n|---|---|\n" + sub_rows,
            "built_utc": manifest["built_utc"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "README.md").write_text(CARD.format(**card_ctx),
                                              encoding="utf-8")
            # KANBAN-076 canary-proven (kanban076-canary{2,3,4}): the Hub's
            # dataset loader ingests ANY path whose name contains ".json" —
            # bare .json, .json.txt, any subdir — as data rows (CastError,
            # "column names don't match"). Only an extension with NO json
            # substring is loader-invisible: ship manifests as manifest.txt.
            (tmpdir / "manifest.txt").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8")
            (tmpdir / STAGED_NAME).write_bytes(args.out.read_bytes())
            print(f"uploading {REPO_ID} "
                  f"({args.out.stat().st_size >> 20} MB, {written:,} rows) …")
            api.upload_folder(folder_path=str(tmpdir), repo_id=REPO_ID,
                              repo_type="dataset",
                              commit_message=(f"Deduplicated Enron correspondence — "
                                              f"exact-body-hash dedup "
                                              f"({total:,}->{written:,} rows, KANBAN-076)"))

        # ---- verify: LFS sha256 vs local ----
        tree = list(api.list_repo_tree(REPO_ID, repo_type="dataset",
                                       recursive=True))
        entry = next((f for f in tree if f.path == STAGED_NAME), None)
        lfs = getattr(entry, "lfs", None)
        hub_sha = lfs.sha256 if lfs else None
        result = {
            "repo": f"https://huggingface.co/datasets/{REPO_ID}",
            "rows": written,
            "source_rows": total,
            "dropped_duplicates": dropped_duplicates,
            "train": train_n,
            "test": test_n,
            "local_sha256": (manifest.get("local_sha256") or "")[:12],
            "hub_lfs_sha256": (hub_sha or "")[:12],
            "verified": bool(hub_sha and hub_sha ==
                             manifest.get("local_sha256")),
        }
        (OUT_DIR / "KANBAN076_PUBLISH_SUMMARY.json").write_text(
            json.dumps({"enron_correspondence_dedup": result}, indent=2))
        print("\n" + json.dumps(result, indent=1))
        print("VERIFY:", "GREEN" if result["verified"] else "RED — inspect!")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
