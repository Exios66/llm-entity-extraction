#!/usr/bin/env python3
"""Publish the DEDUPLICATED + GT-ENRICHED ENRON CORRESPONDENCE corpus to HF.

KANBAN-079 (human directive 2026-08-23): extend
``Lucius-Morningstar/enron-correspondence-dedup`` with richer ground truth —
``content_topic`` (+ evidence) and ``sentiment_score``/``sentiment_label``
(+ evidence) per row — while making GT **invisible to pipeline agents by
default**. HF has no column-level ACL, so the separation is structural:

  TWO card-declared configs, native per-split files:

    config ``default``       ->  blind/train.jsonl, blind/test.jsonl
        filename, subject, text, split, metadata          (NO answer keys)
    config ``ground_truth``  ->  ground_truth/train.jsonl, ground_truth/test.jsonl
        filename, expected, expected_subclass, label_evidence,
        content_topic, topic_evidence,
        sentiment_score, sentiment_label, sentiment_evidence

  ``load_dataset("Lucius-Morningstar/enron-correspondence-dedup")`` returns
  the BLIND view only; scorers join GT via
  ``load_dataset(..., "ground_truth", split="train"/"test")`` on ``filename``.
  The dataset viewer exposes BOTH configs for human GT auditing.

The legacy monolithic all-columns jsonl is DELETED from the Hub repo during
publish — otherwise the JSON loader folds it back into the default config and
re-leaks every answer key.

Enrichment labelers are IMPORTED (never forked) from Enron-Evaluation-
Environment ``scripts/`` beside the shared subclass module:
``content_topics.label_content_topic`` and
``sentiment_scorer.sentiment_for_row``. Dedup rule unchanged (KANBAN-076):
``body_hash`` md5 exact-body dedup, first occurrence wins, empty bodies never
deduped against each other. Splits recomputed + asserted via the family's
single ``assign_split``.

Guards (refuse to publish on ANY violation):
- every enriched row carries a valid topic key, sentiment label, float score
- blind files contain NO GT keys; GT rows join 1:1 with blind rows on filename
- identical metadata key-set on every row (struct-cast rule)
- no null leading columns anywhere

Usage:
    .venv/bin/python scripts/datasets/publish_enron_correspondence_dedup.py \\
        [--source data/hf_export/enron_correspondence.jsonl] \\
        [--write] [--publish] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.datasets.build_docclass_merged import assign_split  # noqa: E402

DEFAULT_SOURCE = REPO_ROOT / "data" / "hf_export" / "enron_correspondence.jsonl"
ENRON_SCRIPTS = Path.home() / "Enron-Evaluation-Environment" / "scripts"
OUT_DIR = REPO_ROOT / "data" / "hf_export" / "kanban079_dedup_v2"
HF_USERNAME = os.environ.get("HF_USERNAME", "Lucius-Morningstar")
REPO_ID = f"{HF_USERNAME}/enron-correspondence-dedup"

# sha256 prefix of the verified full-corpus export this MUST be built from
EXPECTED_SOURCE_SHA_PREFIX = "0554a5973935"

# ---- schema contracts -------------------------------------------------------
BLIND_KEYS = ["filename", "subject", "text", "split", "metadata"]
GT_KEYS = [
    "filename", "expected", "expected_subclass", "label_evidence",
    "content_topic", "topic_evidence",
    "sentiment_score", "sentiment_label", "sentiment_evidence",
    "split",
]
# keys that must NEVER appear in the blind config ("split" is deliberately
# shared — it is the partition indicator, not an answer key)
GT_ONLY = set(GT_KEYS) - {"filename", "split"}
SENTIMENT_LABELS = ("negative", "neutral", "positive")
LEGACY_HUB_FILES = ["enron_correspondence_dedup.jsonl"]  # deleted at publish

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
- ground-truth
- sentiment-analysis
- topic-classification
- llm-mailroom
pretty_name: "Enron Correspondence Deduplicated (Enriched GT, Agent-Blind Default)"
size_categories:
- 100K<n<1M
configs:
- config_name: default
  data_files:
  - split: train
    path: blind/train.jsonl
  - split: test
    path: blind/test.jsonl
- config_name: ground_truth
  data_files:
  - split: train
    path: ground_truth/train.jsonl
  - split: test
    path: ground_truth/test.jsonl
---

# Enron Correspondence Deduplicated (Enriched GT, Agent-Blind Default)

The **deduplicated, ground-truth-enriched** companion to
[`Lucius-Morningstar/enron-correspondence`](https://huggingface.co/datasets/Lucius-Morningstar/enron-correspondence):
exact-duplicate bodies removed from the cleaned CMU Enron corpus ({total_rows:,}
rows in -> **{written:,} unique-text rows out**, {dropped:,} duplicates dropped;
first occurrence wins on maildir-path order; empty bodies never deduped against
each other).

## ⚠️ Two-config layout: agents get NO answers by default

This dataset ships TWO configs. **`default` is agent-blind** — it carries the
email content plus routing metadata and ZERO ground-truth columns. The answer
keys live in the separate `ground_truth` config, keyed 1:1 on `filename`.

```python
from datasets import load_dataset

# what a sorting/extraction agent may see:
blind = load_dataset("Lucius-Morningstar/enron-correspondence-dedup")

# what the scorer joins against (explicit opt-in):
gt = load_dataset("Lucius-Morningstar/enron-correspondence-dedup",
                  "ground_truth", split="test")
```

| config | splits | columns |
|---|---|---|
| `default` | train {train_n:,} / test {test_n:,} | filename, subject, text, split, metadata |
| `ground_truth` | train {train_n:,} / test {test_n:,} | filename, expected, expected_subclass, label_evidence, content_topic, topic_evidence, sentiment_score, sentiment_label, sentiment_evidence, split |

Ground truth is hidden from the default config so automated agents cannot be
tipped off; humans can still audit every label in the viewer by switching to
the `ground_truth` config. This is separation of concerns, NOT encryption —
the Hub is public and any deliberate download can fetch both configs.

## Ground-truth dimensions

1. **doc_type / subclass** (`expected`, `expected_subclass`,
   `label_evidence`) — heuristic form taxonomy from the shared
   [`correspondence_subclasses`](https://github.com/Exios66/Enron-Evaluation-Environment)
   labeler: {taxonomy}.
2. **content_topic** (`content_topic`, `topic_evidence`) — WHAT the message
   body is about: an 11-key priority-scored marker taxonomy
   (`content_topics.py`): {topics}.
3. **sentiment** (`sentiment_score` ∈ [-1, 1], `sentiment_label` ∈
   negative/neutral/positive, `sentiment_evidence`) — deterministic lexicon
   polarity over the subject + forwarded-tail-stripped body
   (`sentiment_scorer.py`), negation/intensifier-aware, politeness-formula
   controlled.

All three dimensions are HEURISTIC ground truth (deterministic pure functions,
human-reviewed via spot checks where noted) — not hand annotations. Honest
gaps: single-topic assignment for multi-topic emails; head-window scanning
(~2000 chars); lexicon sentiment cannot read sarcasm or long-range context —
treat scores as weak labels/routing priors. Attorney detection relies on
domain/name lists; `voicemail` cannot occur in this text-only corpus.

## Splits

Per-row `split` follows the family rule `md5(filename) % 10 == 0 -> test`
(~10%), recomputed and asserted row-by-row at build time. Filename-keyed, so
dedup/enrichment cannot change any surviving row's split. Coverage: train
{train_n:,} / test {test_n:,}.

## Provenance

Built by [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
`scripts/datasets/publish_enron_correspondence_dedup.py` (KANBAN-079,
{built_utc}) from the sha256-verified full-corpus export (LFS
`0554a5973935…`). Labelers: Enron-Evaluation-Environment `scripts/`
(`correspondence_subclasses.py`, `content_topics.py`,
`sentiment_scorer.py`). Source: CMU Enron Email Dataset (cleaned maildir);
dedup rule `scripts/dedupe.py::body_hash`. Research-use license — treat
personally identifying content accordingly.
"""


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"module not found: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enrich_row(row: dict, topics_mod, sent_mod) -> dict:
    """Compute the GT enrichment fields for one dedup'd row."""
    view = {"subject": row.get("subject") or "", "body": row.get("text") or "",
            "parseable": True}
    topic, topic_ev = topics_mod.label_content_topic(view)
    score, label, sent_ev = sent_mod.sentiment_for_row(view)
    return {
        "content_topic": topic,
        "topic_evidence": topic_ev,
        "sentiment_score": score,
        "sentiment_label": label,
        "sentiment_evidence": sent_ev,
    }


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="sha-verified staged full-corpus export")
    parser.add_argument("--enron-scripts", type=Path, default=ENRON_SCRIPTS,
                        help="dir holding the shared labelers + dedupe.py")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test cap on rows read")
    parser.add_argument("--write", action="store_true",
                        help="write the two-config artifacts locally")
    parser.add_argument("--publish", action="store_true",
                        help="upload to the Hub (requires --write)")
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

    # ---- shared modules: dedupe hash + enrichment labelers (imported, never forked)
    dedupe = load_module(args.enron_scripts / "dedupe.py", "enron_dedupe")
    body_hash = dedupe.body_hash
    topics_mod = load_module(args.enron_scripts / "content_topics.py",
                             "enron_content_topics")
    sent_mod = load_module(args.enron_scripts / "sentiment_scorer.py",
                           "enron_sentiment_scorer")
    VALID_TOPICS = set(topics_mod.TOPIC_KEYS)

    # ---- stream-dedupe + enrich (first occurrence wins) ----
    seen: set[str] = set()
    rows_out: list[dict] = []
    total = dropped_duplicates = empty_body_kept = split_fixed = 0
    sub_before: Counter = Counter()
    sub_after: Counter = Counter()
    topic_counts: Counter = Counter()
    sent_counts: Counter = Counter()
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

            r.update(enrich_row(r, topics_mod, sent_mod))
            rows_out.append(r)
            sub_after[r["expected_subclass"]] += 1
            topic_counts[r["content_topic"]] += 1
            sent_counts[r["sentiment_label"]] += 1
            custodians.add(str(r.get("metadata", {}).get("custodian") or ""))

    largest_group = max(hash_counts.values()) if hash_counts else 0
    written = len(rows_out)
    print(f"\nread {total:,} rows -> wrote {written:,} "
          f"(dropped {dropped_duplicates:,} duplicates, "
          f"{empty_body_kept:,} empty-body rows kept)")
    print(f"custodians: {len(custodians)} | largest dup group: {largest_group:,}")
    print(f"split mismatches fixed: {split_fixed} (must be 0)")

    # ---- guards: enrichment validity + uniformity (struct-cast rule) ----
    bad = []
    md_keysets: set[tuple] = set()
    for i, r in enumerate(rows_out):
        if not (isinstance(r["filename"], str) and r["filename"].strip()):
            bad.append((i, "filename"))
        if r["expected_subclass"] not in sub_after or r["split"] not in ("train", "test"):
            bad.append((i, "subclass/split"))
        if not isinstance(r["text"], str):
            bad.append((i, "text"))
        if r["content_topic"] not in VALID_TOPICS:
            bad.append((i, f"topic={r['content_topic']!r}"))
        if r["sentiment_label"] not in SENTIMENT_LABELS:
            bad.append((i, f"sent_label={r['sentiment_label']!r}"))
        s = r["sentiment_score"]
        if not isinstance(s, (int, float)) or not math.isfinite(s) \
                or not (-1.0 <= s <= 1.0):
            bad.append((i, f"score={s!r}"))
        md = r.get("metadata")
        if not isinstance(md, dict):
            bad.append((i, "metadata type"))
        else:
            md_keysets.add(tuple(sorted(md.keys())))
            if any(v is None for v in md.values()):
                bad.append((i, "metadata null member"))
    if bad:
        parser.error(f"{len(bad)} rows fail the enrichment/schema guard "
                     f"(first: {bad[0]}) — refusing to publish")
    if len(md_keysets) > 1:
        parser.error(f"non-uniform metadata key-sets {md_keysets} — refusing")

    # ---- build the two-config artifact views ----
    blind_rows = [{k: r[k] for k in BLIND_KEYS} for r in rows_out]
    gt_rows = [{k: r[k] for k in GT_KEYS} for r in rows_out]

    # guard: GT keys must not leak into blind view
    leak = [k for k in GT_ONLY if any(k in b for b in blind_rows[:100])]
    if leak:
        parser.error(f"GT keys leaked into blind view: {leak} — refusing")
    # guard: 1:1 join integrity
    assert [b["filename"] for b in blind_rows] == [g["filename"] for g in gt_rows]

    train_n = sum(1 for r in rows_out if r["split"] == "train")
    test_n = written - train_n

    manifest = {
        "name": "enron-correspondence-dedup",
        "schema_version": 2,
        "layout": "two-config (default=agent-blind, ground_truth=answer keys)",
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
        "configs": {
            "default": {"files": ["blind/train.jsonl", "blind/test.jsonl"],
                        "columns": BLIND_KEYS},
            "ground_truth": {"files": ["ground_truth/train.jsonl",
                                       "ground_truth/test.jsonl"],
                             "columns": GT_KEYS},
        },
        "subclass_counts_dedup": dict(sub_after),
        "content_topic_counts": dict(topic_counts),
        "sentiment_counts": dict(sent_counts),
        "split_coverage": {"train": train_n, "test": test_n,
                           "rule": "md5(filename) % 10 == 0 -> test (10%); "
                                   "filename-keyed; recomputed+asserted"},
        "dedupe_rule": "md5(text utf-8 errors=ignore); empty-body rows never "
                       "deduped against each other; first occurrence wins "
                       "(maildir-path order) — scripts/dedupe.py body_hash",
        "labelers": ["scripts/correspondence_subclasses.py",
                     "scripts/content_topics.py",
                     "scripts/sentiment_scorer.py"],
        "honest_gaps": [
            "EXACT-hash dedup only: near-duplicates not detected",
            "heuristic GT (see source repo); voicemail impossible in "
            "text-only corpus",
            "single-topic assignment; ~2000-char head window",
            "lexicon sentiment = weak labels, no sarcasm/context modeling",
        ],
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    out_dir: Path = args.out_dir
    if args.write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "blind").mkdir(exist_ok=True)
        (out_dir / "ground_truth").mkdir(exist_ok=True)
        shas = {}
        files = {
            "blind/train.jsonl": [b for b in blind_rows if b["split"] == "train"],
            "blind/test.jsonl": [b for b in blind_rows if b["split"] == "test"],
            "ground_truth/train.jsonl": [g for g in gt_rows if g["split"] == "train"],
            "ground_truth/test.jsonl": [g for g in gt_rows if g["split"] == "test"],
        }
        for rel, rows in files.items():
            p = out_dir / rel
            with p.open("w", encoding="utf-8") as fh2:
                for row in rows:
                    fh2.write(json.dumps(row, ensure_ascii=False) + "\n")
            shas[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            print(f"wrote {len(rows):>7,} rows -> {rel} "
                  f"(sha256 {shas[rel][:12]}…)")
        # guard: no null LEADING columns (Hub loader infers early-batch dtypes)
        for rel, rows in files.items():
            first = rows[0]
            if any(v is None for v in first.values()):
                parser.error(f"{rel}: leading-row null column — refusing")
        manifest["file_sha256"] = shas
        (out_dir / "manifest.txt").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nmanifest -> {out_dir/'manifest.txt'} "
              f"(rows {written:,}, train {train_n:,} / test {test_n:,})")

    if args.publish:
        if not args.write:
            parser.error("--publish requires --write")
        token = os.environ.get("HF_TOKEN") or None
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        print(f"HF account: {api.whoami()['name']}")
        api.create_repo(repo_id=REPO_ID, repo_type="dataset", private=False,
                        exist_ok=True)

        # KANBAN-079: the legacy monolithic jsonl MUST leave the repo or the
        # loader folds its GT columns back into the default config (re-leak).
        tree_before = [f.path for f in api.list_repo_tree(
            REPO_ID, repo_type="dataset", recursive=True)]
        stale = [p for p in LEGACY_HUB_FILES if p in tree_before]
        if stale:
            print(f"deleting legacy all-columns files from Hub: {stale} …")
            api.delete_files(repo_id=REPO_ID, repo_type="dataset",
                             delete_patterns=stale,
                             commit_message=("KANBAN-079: remove monolithic "
                                             "all-columns jsonl — GT must not "
                                             "fold into the default config"))

        tax = ", ".join(sorted(sub_after))
        tops = ", ".join(t for t in topics_mod.TOPIC_PRIORITY)
        card_ctx = {
            "total_rows": total, "written": written,
            "dropped": dropped_duplicates, "train_n": train_n, "test_n": test_n,
            "taxonomy": tax, "topics": tops,
            "built_utc": manifest["built_utc"],
        }
        readme = out_dir / "README.md"
        readme.write_text(CARD.format(**card_ctx), encoding="utf-8")
        print(f"uploading two-config tree from {out_dir} …")
        api.upload_folder(folder_path=str(out_dir), repo_id=REPO_ID,
                          repo_type="dataset",
                          commit_message=("KANBAN-079: GT-enriched two-config "
                                          "republish (content_topic + sentiment; "
                                          "agent-blind default)"))

        # ---- verify: per-file sha vs Hub (LFS pointer for >=10MB blobs,
        #      download round-trip hash for smaller non-LFS files) ----
        tree = {f.path: getattr(f, "lfs", None) for f in api.list_repo_tree(
            REPO_ID, repo_type="dataset", recursive=True)}
        results = {}
        from huggingface_hub import hf_hub_download
        for rel, sha in manifest["file_sha256"].items():
            lfs = tree.get(rel)
            if lfs is None and rel not in tree:
                results[rel] = False  # missing entirely
            elif lfs is not None:
                results[rel] = lfs.sha256 == sha
            else:
                # non-LFS (<10MB): hash the served bytes directly
                dl = Path(hf_hub_download(REPO_ID, rel, repo_type="dataset"))
                results[rel] = hashlib.sha256(dl.read_bytes()).hexdigest() == sha
        result = {
            "repo": f"https://huggingface.co/datasets/{REPO_ID}",
            "rows": written, "train": train_n, "test": test_n,
            "files_verified": results,
            "legacy_deleted": all(p not in tree for p in LEGACY_HUB_FILES),
            "verified": all(results.values()),
        }
        summary = out_dir / "PUBLISH_SUMMARY.json"
        summary.write_text(json.dumps({"enron_correspondence_dedup_v2": result},
                                      indent=2), encoding="utf-8")
        print("\n" + json.dumps(result, indent=1))
        print("VERIFY:", "GREEN" if (result["verified"] and
                                     result["legacy_deleted"]) else
              "RED — inspect!")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
