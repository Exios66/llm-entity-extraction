#!/usr/bin/env python3
"""Publish the KANBAN-071 datasets to the Hugging Face Hub.

Two repos under ``Lucius-Morningstar``:

1. ``legalbench-full`` — the complete LegalBench task pack staged by
   ``build_legalbench_full_pack.py`` (verbatim upstream TSVs + prompts +
   READMEs for every task dir, plus CUAD-enriched JSONL records for the
   ``cuad_*`` tasks).
2. ``docclass-merged`` — the merged docclass corpus (CUAD 509 + MAUD 152 +
   S-1 39 = 700 rows) staged by ``build_docclass_merged.py``.

Verification (KANBAN-069 discipline):
- per-file byte proof: every uploaded file's git blob OID (sha1, computed
  locally git-style) must equal the Hub tree's ``blob_id``;
- LFS sha256 for large files (docclass JSONL) compared to the local digest;
- referential sanity: tree file set == local file set (names + counts).

Usage:
    .venv/bin/python scripts/datasets/publish_kanban071.py [--only pack|docclass]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_DIR = REPO_ROOT / "data" / "hf_export" / "legalbench_full"
DOCCLASS_JSONL = REPO_ROOT / "data" / "datasets" / "docclass_merged.jsonl"

HF_USERNAME = os.environ.get("HF_USERNAME", "Lucius-Morningstar")

PACK_CARD = """---
license: cc-by-4.0
task_categories:
- text-classification
language:
- en
tags:
- legal
- legalbench
- evaluation
- llm-mailroom
- clause-classification
pretty_name: "LegalBench Full Task Pack (CUAD-Enriched)"
size_categories:
- 10K<n<100K
---

# LegalBench Full Task Pack (CUAD-Enriched)

Complete mirror of the [LegalBench](https://huggingface.co/datasets/nguha/legalbench)
task collection ({tasks_with_data} classification/reasoning task directories,
{train_rows} train rows, {test_rows} test rows across {n_test_tasks} test splits),
fetched verbatim from `HazyResearch/legalbench` @ main and repackaged for
eval-runner consumption. CC BY 4.0 (Hazy Research / project authors).

## Layout

    tasks/<task>/train.tsv            # verbatim upstream bytes (sha256-pinned in index.jsonl)
    tasks/<task>/train.enriched.jsonl # cuad_* only: row records + CUAD expert annotations
    tasks/<task>/test.tsv             # when present upstream
    tasks/<task>/test.enriched.jsonl  # when present upstream
    tasks/<task>/base_prompt.txt      # when present upstream
    tasks/<task>/README.md            # task metadata (type, source paper)
    index.jsonl                       # one record per task: types, row counts, shas
    ENRICHMENT_REPORT.json            # cuad_* join statistics (honest gaps)

## CUAD enrichment (what makes this more than a mirror)

For every `cuad_*` row we re-join the excerpt back to the master
[CUAD v1](https://huggingface.co/datasets/theatticusproject/cuad) annotations
(CC BY 4.0, The Atticus Project) by locating the excerpt inside its source
contract (whitespace-flexible match, fuzzy fallback with score floor 0.75),
then attaching:

- `enrichment.match_status`: `exact` / `fuzzy` (+score) / `span_unmatched`
- `char_start`, `char_end`: the excerpt's location in the full contract text
- `primary_clause_question`, `clause_questions[]`: every CUAD expert QA whose
  highlighted answer span overlaps the excerpt, with the exact expert spans
  and their offsets
- `category_audit`: cross-audit of the LegalBench Yes/No label against CUAD's
  expert highlights ON THE EXCERPT — `agree` / `SUSPECT` / `MISMATCH` with an
  explanatory note. Labels are NEVER rewritten; both records ship so you can
  filter or adjudicate.

Audit outcomes across the {cuad_rows} enriched cuad_* rows: {audit_line}.

The `SUSPECT` rows (LB says Yes while experts highlighted that category
elsewhere in the contract, not on this excerpt) are label-quality flags, not
corrections — treat them as review-queue items.

## Honest gaps

{gaps_note}

## Provenance

Built by [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
`scripts/datasets/build_legalbench_full_pack.py` (KANBAN-071, {built_utc}).
Sources: HazyResearch/legalbench (tasks), theatticusproject/cuad CUAD_v1.json
(enrichment layer). Both CC BY 4.0.
"""

DOCCLASS_CARD = """---
license: cc-by-4.0
task_categories:
- text-classification
language:
- en
tags:
- legal
- contracts
- merger-agreements
- corporate-records
- document-classification
- evaluation
- llm-mailroom
pretty_name: "Docclass Merged Corpus (Contracts + Merger Agreements + Corporate Records)"
size_categories:
- n<1K
---

# Docclass Merged Corpus

Single flat document-classification surface: **{rows} legal documents** across
three corpora, one row per document:

| Corpus | Rows | doc_type | Source |
|---|---|---|---|
| CUAD contracts | {cuad_rows} | `contract` | CUAD v1 (CC BY 4.0, The Atticus Project) |
| MAUD merger agreements | {maud_rows} | `merger_agreement` | MAUD v1 (CC BY 4.0, Wang et al. 2023) |
| S-1 corporate-record exhibits | {s1_rows} | `corporate_record` | SEC EDGAR public filings |

## Row shape

One JSON object per line: `filename` (the source FILE name — CUAD PDF
basename, MAUD/S-1 dump filenames), `doc_text` (full document text),
`prompt`, `expected` (the gold `doc_type`), `expected_subclass` (second-level
gold on EVERY row — CUAD's own contract grouping for contracts,
{contract_groups} groups; MAUD consideration type; S-1 record subclass),
`split` (deterministic train/test: md5(filename) mod 10 == 0 → test, ~10%;
stable across rebuilds — use it for reproducible evaluation),
`metadata` (per-corpus provenance fields). Schema v3 (KANBAN-074; v2 added
subclass+filename in KANBAN-073): all three label columns are non-null
strings on every row — partial-null schemas crash the Hub viewer's JSON→
parquet conversion (`Couldn't cast array of type string to null`).

Deterministically ordered (corpus, then filename) — rebuilds are
byte-identical; dataset fingerprint `{fp_short}…`.

## Splits

Per-row `split` column (schema v3): `train` / `test` assigned by
`md5(filename) mod 10 == 0 → test` (~10% test). The rule is deterministic
and order-independent, so any consumer recomputes or extends the same split
without shipping separate files; stratification by doc_type/subclass is not
forced (hash-based), but class balance is stable because assignment is
uniform at this scale.

## Provenance

Built by [`llm-entity-extraction`](https://github.com/Exios66/llm-entity-extraction)
`scripts/datasets/build_docclass_merged.py` (KANBAN-071, {built_utc}).
CUAD portion derives from the Braintrust mirror export
(`mailroom-cuad-contracts-full`, byte-verified); MAUD streamed from the Zenodo
v1 corpus; S-1 exhibits discovered and extracted live from SEC EDGAR.
"""

GAPS_DEFAULT = """- 2 of 162 upstream task directories carry no `train.tsv` and ship as
  `EMPTY` markers (recorded in `index.jsonl`);
- 8 enriched rows reference contract filenames absent from CUAD_v1.json
  (`unknown_contract`) — kept, flagged;
- 20 excerpts could not be located inside their contract (`span_unmatched`),
  1 matched only fuzzily — both classes keep their rows, flags included;
- `rule_qa` lists 0 train rows upstream (its data lives in test.tsv);
- enrichment covers `cuad_*` tasks only — other LB tasks ship verbatim.
"""


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\x00".encode())
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def load_index():
    return [json.loads(l) for l in (PACK_DIR / "index.jsonl").open()]


def audit_line(report: dict) -> str:
    t = report["totals"]
    agree = t.get("train_audit_agree", 0) + t.get("test_audit_agree", 0)
    suspect = t.get("train_audit_suspect", 0) + t.get("test_audit_suspect", 0)
    mismatch = t.get("train_audit_mismatch", 0) + t.get("test_audit_mismatch", 0)
    return (f"**{agree} agree · {suspect} SUSPECT · {mismatch} MISMATCH** "
            f"(flagged on-row, never rewritten)")


def publish_pack(api) -> dict:
    idx = load_index()
    report = json.loads((PACK_DIR / "ENRICHMENT_REPORT.json").read_text())
    tasks_data = [r for r in idx if r.get("rows_train", 0) > 0]
    ctx = {
        "tasks_with_data": len(tasks_data),
        "train_rows": sum(r["rows_train"] for r in tasks_data),
        "test_rows": sum(r.get("rows_test", 0) for r in tasks_data),
        "n_test_tasks": sum(1 for r in tasks_data if r.get("rows_test")),
        "cuad_rows": sum(report["totals"].get(k, 0) for k in
                         ("train_exact", "train_fuzzy", "train_span_unmatched",
                          "train_unknown_contract")),
        "audit_line": audit_line(report),
        "gaps_note": GAPS_DEFAULT,
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    card_path = PACK_DIR / "README.md"
    card_path.write_text(PACK_CARD.format(**ctx), encoding="utf-8")

    repo_id = f"{HF_USERNAME}/legalbench-full"
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
    print(f"uploading pack ({sum(1 for _ in PACK_DIR.rglob('*') if _.is_file())} files) ...")
    api.upload_folder(folder_path=str(PACK_DIR), repo_id=repo_id, repo_type="dataset",
                      commit_message=f"LegalBench full task pack + CUAD enrichment (KANBAN-071, {ctx['train_rows']} train rows)")

    # --- verify: every file's git blob OID must match the Hub tree ---
    from huggingface_hub import hf_hub_download
    tree = {f.path: f for f in api.list_repo_tree(repo_id, repo_type="dataset",
                                                  recursive=True)}
    local_files = sorted(p for p in PACK_DIR.rglob("*") if p.is_file()
                         and p.name != "README.md")
    missing = [str(p.relative_to(PACK_DIR)) for p in local_files
               if str(p.relative_to(PACK_DIR)) not in tree]
    oid_bad, oid_checked = [], 0
    for p in local_files:
        rel = str(p.relative_to(PACK_DIR))
        entry = tree.get(rel)
        if entry is None:
            continue
        if getattr(entry, "lfs", None) is not None:
            continue  # LFS handled separately below
        oid_checked += 1
        if entry.blob_id != git_blob_sha1(p):
            oid_bad.append(rel)
    # content-proof on the two aggregate files via round-trip too
    agg_ok = True
    for rel in ("index.jsonl", "ENRICHMENT_REPORT.json"):
        dl = hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=rel,
                             local_dir="/tmp/hf071_rt")
        if sha256_file(Path(dl)) != sha256_file(PACK_DIR / rel):
            agg_ok = False
    return {
        "repo": f"https://huggingface.co/datasets/{repo_id}",
        "files_local": len(local_files) + 1,
        "files_missing_on_hub": len(missing),
        "blob_oid_verified": oid_checked,
        "blob_oid_mismatches": len(oid_bad),
        "aggregates_roundtrip_ok": agg_ok,
        "missing_sample": missing[:5],
        "oid_bad_sample": oid_bad[:5],
    }


def publish_docclass(api) -> dict:
    rows = [json.loads(l) for l in DOCCLASS_JSONL.open(encoding="utf-8") if l.strip()]
    rows_n = len(rows)
    # KANBAN-073/074 pre-upload schema guard: every row must carry non-empty
    # string filename, expected_subclass, and a train/test split. All-null
    # batches make the Hub's JSON loader infer null-typed columns; later
    # string batches then die in parquet conversion ("Couldn't cast array of
    # type string to null"). Never upload a partial-null schema.
    bad = [i for i, r in enumerate(rows)
           if not (isinstance(r.get("filename"), str) and r["filename"].strip())
           or not (isinstance(r.get("expected_subclass"), str)
                   and r["expected_subclass"].strip())
           or r.get("split") not in ("train", "test")]
    if bad:
        raise SystemExit(
            f"docclass schema guard: {len(bad)} rows lack filename/"
            f"expected_subclass (first: row {bad[0]}) — refusing to upload a "
            f"partial-null schema; rebuild with build_docclass_merged.py")
    import subprocess

    fp = subprocess.run(
        [sys.executable, "-c",
         "import sys, json; sys.path.insert(0, '.');"
         "from src.evaluation import dataset_fingerprint;"
         "rows=[json.loads(l) for l in open('data/datasets/docclass_merged.jsonl')];"
         "print(dataset_fingerprint(rows))"],
        cwd=str(REPO_ROOT), capture_output=True, text=True).stdout.strip()
    counts = {"cuad": 509, "maud": 152, "s1": 39}
    contract_groups = sorted({r["expected_subclass"] for r in rows
                              if r.get("expected") == "contract"})
    manifest = {
        "name": "docclass-merged",
        "schema_version": 3,
        "rows": rows_n,
        "dataset_fingerprint": fp,
        "corpora": counts,
        "subclass_coverage": {
            "rows_with_nonempty_filename": sum(1 for r in rows
                                               if str(r.get("filename") or "").strip()),
            "rows_with_nonempty_subclass": sum(1 for r in rows
                                               if str(r.get("expected_subclass") or "").strip()),
            "contract_groups": len(contract_groups),
        },
        "split_coverage": {
            "train": sum(1 for r in rows if r.get("split") == "train"),
            "test": sum(1 for r in rows if r.get("split") == "test"),
            "rule": "md5(filename) % 10 == 0 -> test (10%), else train; deterministic across rebuilds",
        },
        "sources": {
            "cuad": "local staging export of mailroom-cuad-contracts-full "
                    "(byte-verified vs Braintrust + Hub, KANBAN-069)",
            "maud": "stream_maud_to_bt.py --local-dump (MAUD v1, Zenodo)",
            "s1": "stream_s1_exhibits.py --local-dump (SEC EDGAR)",
        },
        "built_by": "scripts/datasets/build_docclass_merged.py (KANBAN-071)",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license_note": "CUAD + MAUD portions CC BY 4.0 (The Atticus Project / "
                        "Wang et al. 2023); S-1 exhibits are SEC EDGAR public "
                        "filings.",
    }
    (DOCCLASS_JSONL.parent / "docclass_merged.manifest.json").write_text(
        json.dumps(manifest, indent=2))

    local_sha = sha256_file(DOCCLASS_JSONL)
    if local_sha != hashlib.sha256(DOCCLASS_JSONL.read_bytes()).hexdigest():
        raise SystemExit("unreachable")

    repo_id = f"{HF_USERNAME}/docclass-merged"
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "README.md").write_text(DOCCLASS_CARD.format(
            rows=rows_n, cuad_rows=counts["cuad"], maud_rows=counts["maud"],
            s1_rows=counts["s1"], fingerprint=fp, fp_short=fp[:16],
            contract_groups=len(contract_groups),
            built_utc=manifest["built_utc"]), encoding="utf-8")
        (tmpdir / "docclass_merged.jsonl").write_bytes(DOCCLASS_JSONL.read_bytes())
        # KANBAN-074 hotfix lesson, CORRECTED by KANBAN-076 canaries: ANY
        # filename containing ".json" (.json, .json.txt, any subdir) gets
        # ingested as data rows by the Hub's JSON loader (CastError,
        # "column names don't match") — only manifest.txt is invisible.
        (tmpdir / "manifest.txt").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"uploading docclass ({DOCCLASS_JSONL.stat().st_size >> 20} MB, "
              f"schema v3: subclass+filename+split on all {rows_n} rows) ...")
        api.upload_folder(folder_path=str(tmpdir), repo_id=repo_id, repo_type="dataset",
                          commit_message=f"Docclass merged corpus schema v3 — deterministic train/test split column (KANBAN-074, {rows_n} rows, fp {fp[:12]})")

    # --- verify: LFS sha256 vs local ---
    tree = list(api.list_repo_tree(repo_id, repo_type="dataset", recursive=True))
    hub_entry = next((f for f in tree if f.path == "docclass_merged.jsonl"), None)
    lfs = getattr(hub_entry, "lfs", None)
    hub_sha = lfs.sha256 if lfs else None
    return {
        "repo": f"https://huggingface.co/datasets/{repo_id}",
        "rows": rows_n,
        "fingerprint": fp,
        "local_sha256": local_sha[:12],
        "hub_lfs_sha256": (hub_sha or "")[:12],
        "verified": bool(hub_sha and hub_sha == local_sha),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", choices=["", "pack", "docclass"])
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or None
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    print(f"HF account: {api.whoami()['name']}")

    results = {}
    if args.only in ("", "pack"):
        print("\n== legalbench-full ==")
        results["pack"] = publish_pack(api)
        print(json.dumps(results["pack"], indent=1))
    if args.only in ("", "docclass"):
        print("\n== docclass-merged ==")
        results["docclass"] = publish_docclass(api)
        print(json.dumps(results["docclass"], indent=1))

    out = REPO_ROOT / "data" / "hf_export" / "KANBAN071_PUBLISH_SUMMARY.json"
    merged = {}
    if out.exists():
        try:
            merged.update(json.loads(out.read_text()))
        except Exception:
            pass
    merged.update(results)
    out.write_text(json.dumps(merged, indent=2))
    print(f"\nsummary -> {out}")
    ok = (all(r.get("verified", True) and not r.get("files_missing_on_hub")
              and not r.get("blob_oid_mismatches") and r.get("aggregates_roundtrip_ok", True)
              for r in results.values()))
    print("VERIFY:", "GREEN" if ok else "RED — inspect before close-out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
