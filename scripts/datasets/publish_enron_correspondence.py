#!/usr/bin/env python3
"""Publish the CLEANED ENRON CORRESPONDENCE corpus to the Hugging Face Hub.

KANBAN-074 (human directive 2026-08-22): the Lucius-Morningstar dataset
family must carry metadata, labels, ground truth, and train/test splits —
including the cleaned Enron email data. This publisher consumes the
full-corpus index built by Enron-Evaluation-Environment's
``scripts/build_corpus_index.py`` (CMU maildir → one JSONL row per parsed
message, 517,390 rows, deterministic order) and publishes:

    Lucius-Morningstar/enron-correspondence

Every row carries:
- ``filename``     maildir path relative to the root (deterministic id)
- ``text``         the cleaned email body (text/plain or HTML-stripped)
- ``subject``      decoded subject header
- ``expected``     ``correspondence`` (family doc_type)
- ``expected_subclass``  ground truth from the SHARED labeler
                   (``correspondence_subclasses.label_correspondence`` —
                   10-key taxonomy, first-match-wins; the exact module every
                   downstream mailroom tool imports)
- ``label_evidence``     why the labeler fired (audit trail, on-row)
- ``split``        deterministic train/test — SAME rule as the whole family
                   (md5(filename) % 10 == 0 -> test, ~10%)
- ``metadata``     provenance: custodian, folder, date, sender/message ids,
                   recipient/attachment facts, source + license notes

Schema guard (KANBAN-073 lesson): rows lacking filename/subclass/split/text
refuse to publish — all-null leading batches crash the Hub viewer's JSON→
parquet conversion (string→null cast). Rows with an EMPTY body AND empty
subject are dropped (counted honestly in the manifest).

Usage:
    .venv/bin/python scripts/datasets/publish_enron_correspondence.py \
        [--index ~/Enron-Evaluation-Environment/data/enron/index.jsonl] [--dry-run]
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

DEFAULT_INDEX = Path.home() / "Enron-Evaluation-Environment" / "data" / \
    "enron" / "index.jsonl"
ENRON_SCRIPTS = Path.home() / "Enron-Evaluation-Environment" / "scripts"
OUT_DIR = REPO_ROOT / "data" / "hf_export"
STAGED_NAME = "enron_correspondence.jsonl"
HF_USERNAME = os.environ.get("HF_USERNAME", "Lucius-Morningstar")
REPO_ID = f"{HF_USERNAME}/enron-correspondence"

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
- llm-mailroom
pretty_name: "Enron Correspondence (Cleaned, Subclass-Labeled)"
size_categories:
- 100K<n<1M
---

# Enron Correspondence (Cleaned, Subclass-Labeled)

The **full cleaned CMU Enron corpus** ({rows} parsed messages from the classic
maildir, {custodians} custodians) prepared for the llm-mailroom
document-classification pipeline: one row per message, every row carrying a
heuristic ground-truth subclass label from the shared
[`correspondence_subclasses`](https://github.com/Exios66/Enron-Evaluation-Environment)
labeler (10-key taxonomy: {taxonomy}) plus a deterministic train/test split.

## Row shape

One JSON object per line:

| Field | Meaning |
|---|---|
| `filename` | maildir path relative to the root (stable row id) |
| `text` | cleaned email body (text/plain, else HTML-stripped) |
| `subject` | decoded subject header |
| `expected` | gold doc_type — always `correspondence` |
| `expected_subclass` | heuristic ground truth: `{taxonomy}` |
| `label_evidence` | which marker/rule fired (on-row audit trail) |
| `split` | `train` / `test` — md5(filename) mod 10 == 0 → test (~10%) |
| `metadata` | custodian, folder, date, sender, message/thread ids, recipient + attachment facts, source/license |

Labels are HEURISTIC ground truth (regex/marker rules, human-reviewed via
spot checks in the source repo) — not hand annotations. They are exactly the
labels the production pipeline scores against; `other` means no specific
marker matched. Known honest gaps (from the source repo's AGENTS.md):
attorney detection relies on domain/name lists and is not exhaustive;
`voicemail` cannot occur in this text-only corpus (0% by construction);
cross-custodian duplicate copies of the same message are NOT merged — use
`metadata.message_id` to group or dedupe.

## Splits

Per-row `split`: `train` / `test` assigned by `md5(filename) mod 10 == 0`
(~10% test). Deterministic and order-independent — rebuilds and consumers
recompute identical splits without shipping separate files.

## Provenance

Built by [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
`scripts/datasets/publish_enron_correspondence.py` (KANBAN-074,
{built_utc}) from Enron-Evaluation-Environment's full-corpus index
(`build_corpus_index.py`, {parseable}/{total} messages parseable, sorted
maildir walk — rebuilds byte-identical). Source: CMU Enron Email Dataset
(cleaned maildir). Distribution restrictions: the Enron corpus is released
for RESEARCH use — treat personally identifying content accordingly.
Subclass labels: heuristic ruleset documented + regression-tested in the
source repo ({labeler_tests} labeler tests).
"""


def load_labeler(enron_scripts: Path):
    spec = importlib.util.spec_from_file_location(
        "correspondence_subclasses", enron_scripts / "correspondence_subclasses.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"labeler not found under {enron_scripts} — clone "
                         f"Enron-Evaluation-Environment or pass --enron-scripts")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--enron-scripts", type=Path, default=ENRON_SCRIPTS,
                        help="dir holding correspondence_subclasses.py")
    parser.add_argument("--out", type=Path, default=OUT_DIR / STAGED_NAME)
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test cap on rows processed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    labeler = load_labeler(args.enron_scripts)
    taxonomy = ", ".join(labeler.SUBCLASS_KEYS)

    if not args.index.exists():
        parser.error(f"index not found: {args.index} — run "
                     f"build_corpus_index.py in Enron-Evaluation-Environment first")

    rows: list[dict] = []
    total = dropped_empty = unparseable = 0
    sub_counts: Counter = Counter()
    custodians: set[str] = set()
    with args.index.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            if args.limit and len(rows) >= args.limit:
                break
            r = json.loads(line)
            if not r.get("parseable"):
                unparseable += 1
                continue
            body = str(r.get("body") or "")
            subject = str(r.get("subject") or "")
            if not body.strip() and not subject.strip():
                dropped_empty += 1
                continue
            key, evidence = labeler.label_correspondence(r)
            fn = str(r.get("filename") or "")
            recips = r.get("recipients") or []
            meta = {
                "source": "cmu_enron_maildir",
                "license": "Enron corpus — released for research use",
                "built_by": "llm-entity-extraction scripts/datasets/"
                            "publish_enron_correspondence.py (KANBAN-074)",
                "custodian": str(r.get("custodian") or ""),
                "folder": str(r.get("folder") or ""),
                "date": str(r.get("date") or ""),
                "sender_addr": str(r.get("sender_addr") or ""),
                "message_id": str(r.get("message_id") or ""),
                "in_reply_to": str(r.get("in_reply_to") or ""),
                "n_recipients": len(recips),
                "has_attachments": bool(r.get("attachments")),
                "body_content_type": str(r.get("body_content_type") or ""),
            }
            rows.append({
                "filename": fn,
                "text": body,
                "subject": subject,
                "expected": "correspondence",
                "expected_subclass": key,
                "label_evidence": str(evidence or ""),
                "split": assign_split(fn),
                "metadata": meta,
            })
            sub_counts[key] += 1
            custodians.add(str(r.get("custodian") or ""))

    print(f"index rows read: {total} (unparseable skipped: {unparseable}, "
          f"empty body+subject dropped: {dropped_empty})")
    print(f"published rows: {len(rows)} | custodians: {len(custodians)}")
    print(f"subclass GT: {dict(sub_counts.most_common())}")

    # schema guard — same discipline as docclass (KANBAN-073/074): never
    # ship a partial-null schema to the Hub viewer.
    bad = [i for i, r in enumerate(rows)
           if not (isinstance(r["filename"], str) and r["filename"].strip())
           or not (isinstance(r["expected_subclass"], str) and r["expected_subclass"].strip())
           or r["expected_subclass"] not in labeler.SUBCLASS_KEYS
           or r["split"] not in ("train", "test")
           or not isinstance(r["text"], str)]
    if bad:
        parser.error(f"{len(bad)} rows fail the schema guard "
                     f"(first: {bad[0]}) — refusing to publish")
    train_n = sum(1 for r in rows if r["split"] == "train")
    test_n = len(rows) - train_n

    if args.dry_run:
        print(f"\nDry run: would write {len(rows)} rows -> {args.out}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    local_sha = hashlib.sha256(args.out.read_bytes()).hexdigest()

    manifest = {
        "name": "enron-correspondence",
        "schema_version": 1,
        "rows": len(rows),
        "index_rows_read": total,
        "unparseable_skipped": unparseable,
        "empty_dropped": dropped_empty,
        "custodians": len(custodians),
        "subclass_counts": dict(sub_counts),
        "split_coverage": {"train": train_n, "test": test_n,
                           "rule": "md5(filename) % 10 == 0 -> test (10%); "
                                   "same family rule as docclass-merged"},
        "local_sha256": local_sha,
        "labeler": "Enron-Evaluation-Environment scripts/correspondence_subclasses.py "
                   "(shared 10-key taxonomy, first-match-wins)",
        "sources": {
            "corpus": "CMU Enron Email Dataset — cleaned maildir via "
                      "Enron-Evaluation-Environment build_corpus_index.py",
            "license": "research-use distribution; treat PII accordingly",
        },
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (args.out.parent / "enron_correspondence.manifest.json").write_text(
        json.dumps(manifest, indent=2))
    print(f"\nWrote {len(rows)} rows -> {args.out}\nsha256: {local_sha[:12]}…")

    # ---- publish ----
    token = os.environ.get("HF_TOKEN") or None
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    print(f"HF account: {api.whoami()['name']}")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", private=False,
                    exist_ok=True)

    import tempfile
    card_ctx = {
        "rows": len(rows),
        "custodians": len(custodians),
        "taxonomy": taxonomy,
        "built_utc": manifest["built_utc"],
        "parseable": total - unparseable,
        "total": total,
        "labeler_tests": "40",
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "README.md").write_text(CARD.format(**card_ctx),
                                          encoding="utf-8")
        # KANBAN-074 hotfix lesson, CORRECTED by KANBAN-076 canaries: ANY
        # filename containing ".json" (.json, .json.txt, any subdir) gets
        # ingested as data rows by the Hub's JSON loader (CastError,
        # "column names don't match") — only manifest.txt is invisible.
        (tmpdir / "manifest.txt").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        (tmpdir / STAGED_NAME).write_bytes(args.out.read_bytes())
        print(f"uploading enron-correspondence "
              f"({args.out.stat().st_size >> 20} MB, {len(rows)} rows) ...")
        api.upload_folder(folder_path=str(tmpdir), repo_id=REPO_ID,
                          repo_type="dataset",
                          commit_message=(f"Cleaned Enron correspondence corpus — "
                                          f"subclass GT + deterministic splits "
                                          f"(KANBAN-074, {len(rows)} rows)"))

    # ---- verify: LFS sha256 vs local ----
    tree = list(api.list_repo_tree(REPO_ID, repo_type="dataset", recursive=True))
    entry = next((f for f in tree if f.path == STAGED_NAME), None)
    lfs = getattr(entry, "lfs", None)
    hub_sha = lfs.sha256 if lfs else None
    result = {
        "repo": f"https://huggingface.co/datasets/{REPO_ID}",
        "rows": len(rows),
        "train": train_n,
        "test": test_n,
        "custodians": len(custodians),
        "subclass_counts": dict(sub_counts),
        "local_sha256": local_sha[:12],
        "hub_lfs_sha256": (hub_sha or "")[:12],
        "verified": bool(hub_sha and hub_sha == local_sha),
    }
    out = OUT_DIR / "KANBAN074_PUBLISH_SUMMARY.json"
    out.write_text(json.dumps({"enron_correspondence": result}, indent=2))
    print("\n" + json.dumps(result, indent=1))
    print("VERIFY:", "GREEN" if result["verified"] else "RED — inspect!")
    return 0


def main() -> int:
    return main_with_args(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
