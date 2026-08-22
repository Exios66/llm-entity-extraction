# `data/` — corpora, ground truth, and run artifacts

Repo-root dataset layout. **Tracked** paths are committed; **gitignored** paths
are regenerated locally (see each subdirectory's README). Nothing under
`data/` holds secrets — credentials live in `config/environments/` dotenv files.

## Layout

| Path | Status | What it holds |
|---|---|---|
| [`cuad/`](cuad/README.md) | **tracked** | Curated CUAD master ground-truth CSV (`master_clauses.csv`) |
| [`eda/`](eda/README.md) | **tracked** | Full-corpus CUAD exploratory analysis (report, findings, figures) |
| [`legalbench_classes.jsonl`](legalbench_classes.jsonl) | **tracked** | Per-task answer spaces + questions (written by `stream_legalbench_tasks_to_bt.py`) |
| [`cuad_pdfs/`](cuad_pdfs/README.md) | gitignored | Local mirror of all 510 CUAD contract PDFs + `CUAD_v1.json` |
| [`maud/`](maud/README.md) | gitignored | MAUD v1 merger-agreement local JSONL dumps (KANBAN-033) |
| [`s1_corporate_records/`](s1_corporate_records/README.md) | gitignored | EDGAR S-1 corporate-record exhibit local JSONL dumps (KANBAN-033) |
| [`legalbench_local/`](legalbench_local/README.md) | gitignored | LegalBench task train/test JSONL mirrors (`--local-dump`) |
| [`contracteval/`](contracteval/README.md) | mixed | ContractEval CUAD test split (KANBAN-052): pairs + full contracts gitignored, `questions.json`/`testset_summary.json` tracked |
| [`manifests/`](manifests/README.md) | gitignored | Resumable eval-run checkpoints (JSONL) |
| [`hf_export/`](hf_export/README.md) | gitignored (README tracked) | KANBAN-069 Braintrust → Hugging Face staging; KANBAN-071 upstream-source pack staging (`legalbench_full/`, `docclass_merged.jsonl`); the Hub is the distribution point |
| [`judgments/`](judgments/README.md) | gitignored | Post-hoc LLM-judge calibration records |
| [`samples/`](samples/README.md) | gitignored | Ad-hoc pilot slices and one-off fixtures |

## Quick populate

```bash
# CUAD PDF corpus (local-only; ~510 contracts)
python scripts/datasets/download_cuad_pdfs.py --out-dir data/cuad_pdfs

# MAUD merger agreements + per-question suite (~168 MB)
python scripts/datasets/stream_maud_to_bt.py --local-dump data/maud/

# EDGAR S-1 corporate-record exhibits
python scripts/datasets/stream_s1_exhibits.py --max-filings 40 --local-dump data/s1_corporate_records/

# LegalBench tasks (e.g. hearsay) without Braintrust upload
python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks hearsay --local-dump data/legalbench_local/

# Full LegalBench pack + CUAD enrichment (KANBAN-071; needs data/cuad_pdfs/CUAD_v1.json)
python scripts/datasets/build_legalbench_full_pack.py

# Merged docclass corpus (CUAD 509 + MAUD 152 + S-1 39 = 700 rows)
python scripts/datasets/build_docclass_merged.py

# Hierarchical doc-class eval (MAUD + S-1 local dumps)
python scripts/eval/run_langfuse_docclass_eval.py \
    --local-dumps data/maud/contracts.jsonl,data/s1_corporate_records/corporate-records.jsonl \
    --stratified 120 --seed 42
```

## Related docs

- Root [`README.md`](../README.md) — sync commands and eval loop
- [`scripts/README.md`](../scripts/README.md) — streamers and eval runners
- [`reports/README.md`](../reports/README.md) — experiment log vs runtime artifacts

## Hugging Face mirror (universal dataset access, KANBAN-069)

The Braintrust-hosted eval ground truth is mirrored to the Hub for
platform-independent agent/eval-runner access. Braintrust stays READ-ONLY
(`BRAINTRUST_LOGGING=disabled` preserved); the mirror is export-only.

```bash
# refresh staging from Braintrust (read-only BTQL reads)
python scripts/datasets/export_bt_to_hf.py

# publish to https://huggingface.co/datasets/Lucius-Morningstar/<dataset>
python scripts/datasets/publish_hf_mirror.py

# consume from anywhere — no Braintrust seat required
hf download Lucius-Morningstar/mailroom-cuad-contracts-full --repo-type dataset --local-dir data/cuad_mirror
```

Both live repos carry a full provenance card (source corpus + license + BT ids
+ export sha256); `mailroom-cuad-contracts-full` was verified byte-identical
post-upload via LFS sha256. See [`hf_export/README.md`](hf_export/README.md)
for the current mirror table incl. known-empty upstream datasets.

## Upstream-source Hub datasets (KANBAN-071)

Two further datasets are published straight from upstream sources (no
Braintrust involvement):

- [legalbench-full](https://huggingface.co/datasets/Lucius-Morningstar/legalbench-full) —
  the complete LegalBench task pack (verbatim upstream TSVs/prompts/READMEs
  for all 162 task dirs) plus CUAD expert-annotation enrichment for the 38
  `cuad_*` tasks (`*.enriched.jsonl`: char offsets, clause questions, expert
  spans, per-row `category_audit`). Built by
  `scripts/datasets/build_legalbench_full_pack.py`; published +
  byte-verified (git-blob OID vs the Hub tree, every file) by
  `scripts/datasets/publish_kanban071.py`.
- [docclass-merged](https://huggingface.co/datasets/Lucius-Morningstar/docclass-merged) —
  the merged docclass surface: 700 rows = CUAD 509 + MAUD 152 + S-1 39,
  with `expected_subclass` ground truth for MAUD consideration types and
  S-1 record subclasses. Built by `scripts/datasets/build_docclass_merged.py`
  (local-first; `--bt-cuad` falls back to read-only Braintrust).

```bash
# rebuild staging for both
python scripts/datasets/build_legalbench_full_pack.py
python scripts/datasets/build_docclass_merged.py

# publish + verify (cards, upload, OID/LFS-sha verification)
python scripts/datasets/publish_kanban071.py            # both
python scripts/datasets/publish_kanban071.py --only pack
python scripts/datasets/publish_kanban071.py --only docclass

# consume from anywhere
hf download Lucius-Morningstar/legalbench-full --repo-type dataset --local-dir data/legalbench_full_mirror
hf download Lucius-Morningstar/docclass-merged --repo-type dataset --local-dir data/docclass_mirror
```
