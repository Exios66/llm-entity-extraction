#!/usr/bin/env python3
"""Publish docclass-merged **v6** to the Hub — the KANBAN-105 rebalance:
v5 parent + 240 new Enron correspondence rows + 200 new CMS DE-SynPUF
insurance_claim rows (contracts fall from 54.6% to 40.1% of the corpus).

Evolution discipline (family law, mirror of ``publish_docclass_v5.py``):

* sharded parquet under ``parquet/<config>/<split>/`` OVERWRITES the v5
  shards in place (same names, so the card YAML globs stay valid);
* the legacy combined ``docclass_merged.jsonl`` STAYS in-tree untouched
  (pinned consumers keep working; it still describes v4 rows);
* ``manifest.txt`` is replaced with the v6 lineage record;
* the README card evolves surgically: regex-anchored edits with count==1
  assertions — never positional slicing;
* the ground_truth config gains the ``intent`` / ``subject_matter`` /
  ``keywords`` columns on BOTH splits (the llm-mailroom purpose-GT push of
  2026-08-30 filled them on train only; new append rows carry them EMPTY
  until the incremental labeler pass fills them in a follow-up revision —
  every purpose-class row is gradable after that pass).

Usage:
    python scripts/datasets/publish_docclass_v6.py --v6 data/datasets/docclass_merged_v6.jsonl --stage /tmp/v6_stage
    python scripts/datasets/publish_docclass_v6.py --v6 ... --stage ... --publish
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.datasets.build_docclass_merged import normalize_metadata_rows  # noqa: E402
from scripts.datasets.build_docclass_pilot import GT_SCALAR_KEYS  # noqa: E402
from scripts.datasets.build_docclass_v5 import CLAIM_GT_KEYS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ID = "Lucius-Morningstar/docclass-merged"
LEGACY_JSONL = "docclass_merged.jsonl"
V5_BASE_REVISION = "1d4753578d91aae09033b359bc32dc1b431e4c20"
EXPECTED_V6_ROWS = 1650
EXPECTED_CLAIM_GT_KEYS = len(CLAIM_GT_KEYS)

# the purpose/gist trio rides the GT config (the llm-mailroom labeler pushes
# it; new append rows are empty until the incremental pass)
PURPOSE_GT_KEYS: tuple[str, ...] = ("intent", "subject_matter", "keywords")

GT_COLUMNS: list[str] = (
    ["filename", "expected", "expected_subclass"]          # keys (split added below)
    + [k for k in GT_SCALAR_KEYS if k not in ("cuad_clause_labels",
                                              "maud_clause_labels")]
    + ["cuad_clause_labels", "maud_clause_labels"]
    + list(PURPOSE_GT_KEYS)
)


def load_v6(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    # blind-surface GT leak guard FIRST (fail fast regardless of row count):
    # no answer keys may ride in metadata
    leak_keys = {"ground_truth", "intent", "subject_matter", "keywords",
                 "expected", "expected_subclass"}
    for r in rows:
        leaked = leak_keys & set(r.get("metadata") or {})
        assert not leaked, f"{r['filename']}: GT keys leaked into metadata: {leaked}"
    assert len(rows) == EXPECTED_V6_ROWS, \
        f"expected {EXPECTED_V6_ROWS} v6 rows, got {len(rows)}"
    return rows


def _blind_row(r: dict) -> dict:
    return {"filename": r["filename"], "doc_text": r["doc_text"],
            "prompt": r.get("prompt") or "",
            "metadata": dict(r.get("metadata") or {})}


def _gt_row(r: dict) -> dict:
    out = {"filename": r["filename"], "expected": r["expected"],
           "expected_subclass": r["expected_subclass"],
           "split": r["split"]}
    gf = r.get("gt_fields") or {}
    for k in GT_COLUMNS[3:]:
        v = gf.get(k)
        # explicit-schema coercion: every string-typed column receives
        # strings-or-None only (sentiment_score keeps its dedicated float
        # column in the local dump; the Hub GT config rides strings-or-null,
        # matching the v5 storage convention)
        out[k] = None if v is None else str(v)
    return out


def stage_parquet(stage: Path, rows: list[dict]) -> dict[tuple[str, str], int]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    blind = [_blind_row(r) for r in rows]
    normalize_metadata_rows(blind)

    gt_names = GT_COLUMNS + ["split"]
    gt_schema = pa.schema([(k, pa.string()) for k in gt_names])

    counts = {}
    for split in ("train", "test"):
        subset_b = [r for r, src in zip(blind, rows) if src["split"] == split]
        subset_g = [_gt_row(r) for r in rows if r["split"] == split]
        bdir = stage / "parquet" / "default" / split
        gdir = stage / "parquet" / "ground_truth" / split
        bdir.mkdir(parents=True, exist_ok=True)
        gdir.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(subset_b),
                       bdir / f"{split}-00000-of-00001.parquet")
        pq.write_table(pa.Table.from_pylist(subset_g, schema=gt_schema),
                       gdir / f"{split}-00000-of-00001.parquet")
        counts[("default", split)] = len(subset_b)
        counts[("ground_truth", split)] = len(subset_g)
    return counts


MANIFEST = """docclass-merged manifest — schema v6 (KANBAN-105)
=================================================
built_utc        : {built}
schema_version   : 6
rows_total       : {rows} ({types})
rows_by_config   : default train={bt} test={btest}; ground_truth train={gt} test={gtest}
strata           : {strata} (expected x expected_subclass)
v5_base_revision : {v5_base}
v6_additions     : +{corr_n} correspondence rows (stratified sha256-filename draw
                   of {corr_n} from {pool_n:,} dedup GT rows after excluding the 110
                   existing; 3-labeler verification pass GREEN — subclass/topic/
                   sentiment reproduce the Hub GT on every row; KANBAN-103 overrides
                   honored, {corr_overrides} override hits) from
                   Lucius-Morningstar/enron-correspondence-dedup;
                   +{ins_n} insurance_claim rows (DE-SynPUF Sample-1 re-render via
                   Exios66/claims-data-eda, verbatim GT contract, existing 400
                   record_ids excluded) — subtypes {ins_types}.
purpose_gt       : intent/subject_matter/keywords on {purpose_n} rows (the
                   llm-mailroom purpose-GT push of 2026-08-30 covers the v5 train
                   purpose-class rows); new append rows are EMPTY until the
                   incremental labeler pass fills them in a follow-up revision.
family_split     : md5(filename) % 10 == 0 -> test; recomputed and asserted for
                   every append row at fusion.
legacy_files     : {legacy_jsonl} retained UNTOUCHED (describes v4; kept for
                   pinned consumers). Parquet shards supersede it.
builder          : scripts/datasets/build_docclass_v6.py @ Exios66/llm-entity-extraction
"""


def stage_sidecars(stage: Path, rows: list[dict],
                   counts: dict[tuple[str, str], int],
                   append_stats: dict) -> None:
    types = Counter(r["expected"] for r in rows)
    strata = Counter((r["expected"], r["expected_subclass"]) for r in rows)
    purpose_n = sum(1 for r in rows if (r.get("gt_fields") or {}).get("intent"))
    text = MANIFEST.format(
        built=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        rows=len(rows), types=dict(sorted(types.items())),
        bt=counts[("default", "train")], btest=counts[("default", "test")],
        gt=counts[("ground_truth", "train")],
        gtest=counts[("ground_truth", "test")],
        strata=len(strata), v5_base=V5_BASE_REVISION,
        corr_n=append_stats["corr_n"], pool_n=append_stats["pool_n"],
        corr_overrides=append_stats["corr_overrides"],
        ins_n=append_stats["ins_n"], ins_types=append_stats["ins_types"],
        purpose_n=purpose_n, legacy_jsonl=LEGACY_JSONL)
    (stage / "manifest.txt").write_text(text, encoding="utf-8")


def render_card(rows: list[dict], append_stats: dict) -> str:
    """Surgical evolution of the live v5 card (fetched fresh at build time)."""
    corr_n = append_stats["corr_n"]
    ins_n = append_stats["ins_n"]
    r = __import__("subprocess").run(
        ["curl", "-sL", "--max-time", "60",
         f"https://huggingface.co/datasets/{REPO_ID}/raw/main/README.md"],
        capture_output=True, text=True, timeout=90)
    card = r.stdout
    assert card.startswith("---"), "could not fetch the live parent card"

    # 1) pretty_name -> v6
    card, n = re.subn(r'pretty_name: "Docclass Merged Corpus v5 \(([^)]+)\)"',
                      'pretty_name: "Docclass Merged Corpus v6 (\\1)"',
                      card, count=1)
    assert n == 1, "pretty_name anchor"
    # 2) headline counts
    card, n = re.subn(
        r"Single flat document-classification surface: \*\*1,210 legal documents\*\* across\nfive corpora, one row per document \(schema v5\):",
        f"Single flat document-classification surface: **{len(rows):,} legal documents** across\nfive corpora, one row per document (schema v6):",
        card, count=1)
    assert n == 1, "headline anchor"
    # 3) corpus table rows: Enron 110 -> 350, claims 400 -> 600
    card, n = re.subn(
        r"\| \*\*Enron correspondence sample\*\* \| \*\*110\*\* \|",
        f"| **Enron correspondence sample** | **{110 + corr_n}** |",
        card, count=1)
    assert n == 1, "enron row anchor"
    card, n = re.subn(
        r"\| \*\*CMS DE-SynPUF rendered EOBs\*\* \| \*\*400\*\* \|",
        f"| **CMS DE-SynPUF rendered EOBs** | **{400 + ins_n}** |",
        card, count=1)
    assert n == 1, "claims row anchor"
    # 4) correspondence deep-dive heading count
    card, n = re.subn(
        r"### Enron correspondence sample — 110 rows \(`correspondence`\)",
        f"### Enron correspondence sample — {110 + corr_n} rows (`correspondence`)",
        card, count=1)
    assert n == 1, "correspondence heading anchor"
    # 5) v6 provenance section before the Two-config section
    marker = "## ⚠️ Two-config layout"
    assert marker in card, "two-config anchor"
    v6_section = f"""## Schema v6 additions (KANBAN-105, 2026-08-30)

* **Correspondence rebalance**: +{corr_n} rows (110 → {110 + corr_n}) — deterministic `sha256(filename)` stratified draw from [`enron-correspondence-dedup`](https://huggingface.co/datasets/Lucius-Morningstar/enron-correspondence-dedup) after excluding every existing filename; the shared Enron labelers (subclass / content-topic / sentiment) were RE-RUN on every drawn row as a verification pass and reproduce the Hub ground truth exactly; the KANBAN-103 phrase-lexicon GT overrides are honored. The dedup corpus carries no `attorney_demand` rows beyond the 3 already present (all in the v4 sample) — honest gap, not an omission.
* **Insurance boost**: +{ins_n} rows (400 → {400 + ins_n}) — newly rendered EOBs from CMS DE-SynPUF Sample 1 via [Exios66/claims-data-eda](https://github.com/Exios66/claims-data-eda) with the verbatim GT contract asserted at render time; every existing record_id was excluded, so the original 400 claims are untouched. Subtypes: {append_stats['ins_types']}. Same synthetic-data caveats as v5 (PAID claims only, `adjuster` null, health LOB).
* **Purpose/gist GT**: the ground_truth config now carries `intent` / `subject_matter` / `keywords` columns on BOTH splits (train rows labeled by the llm-mailroom purpose-GT push of 2026-08-30; new append rows are empty until the incremental labeler pass fills them in a follow-up revision — then every corporate_record / correspondence / insurance_claim row is gradable against the controlled `INTENT_LABELS` vocabularies).
* **Class balance after v6**: contract {sum(1 for r in rows if r['expected'] == 'contract')} ({sum(1 for r in rows if r['expected'] == 'contract') / len(rows):.1%}), insurance_claim {sum(1 for r in rows if r['expected'] == 'insurance_claim')} ({sum(1 for r in rows if r['expected'] == 'insurance_claim') / len(rows):.1%}), correspondence {sum(1 for r in rows if r['expected'] == 'correspondence')} ({sum(1 for r in rows if r['expected'] == 'correspondence') / len(rows):.1%}), merger_agreement {sum(1 for r in rows if r['expected'] == 'merger_agreement')}, corporate_record {sum(1 for r in rows if r['expected'] == 'corporate_record')}.

"""
    card = card.replace(marker, v6_section + marker, 1)
    return card


def publish(stage: Path) -> None:
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)
    api.upload_folder(folder_path=str(stage), repo_id=REPO_ID,
                      repo_type="dataset",
                      commit_message="KANBAN-105: schema v6 — correspondence + insurance rebalance (+240 Enron / +200 DE-SynPUF), purpose-gist GT columns")
    print(f"Published -> https://huggingface.co/datasets/{REPO_ID}")


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v6", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--corr-n", type=int, default=240)
    parser.add_argument("--pool-n", type=int, default=247413)
    parser.add_argument("--corr-overrides", type=int, default=0)
    parser.add_argument("--ins-n", type=int, default=200)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)

    rows = load_v6(args.v6)
    print(f"Loaded {len(rows)} v6 rows")
    ins_types = ", ".join(
        sorted(k for k, n in Counter(r["expected_subclass"] for r in rows
                                     if r["expected"] == "insurance_claim").items()))
    append_stats = {"corr_n": args.corr_n, "pool_n": args.pool_n,
                    "corr_overrides": args.corr_overrides,
                    "ins_n": args.ins_n, "ins_types": ins_types}

    if args.stage.exists():
        shutil.rmtree(args.stage)
    args.stage.mkdir(parents=True)
    counts = stage_parquet(args.stage, rows)
    (args.stage / "README.md").write_text(
        render_card(rows, append_stats), encoding="utf-8")
    stage_sidecars(args.stage, rows, counts, append_stats)
    print("Staged:", {f"{a}/{b}": n for (a, b), n in sorted(counts.items())})

    if args.publish:
        publish(args.stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_with_args(sys.argv[1:]))
