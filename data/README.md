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

# Hierarchical doc-class eval (MAUD + S-1 local dumps)
python scripts/eval/run_langfuse_docclass_eval.py \
    --local-dumps data/maud/contracts.jsonl,data/s1_corporate_records/corporate-records.jsonl \
    --stratified 120 --seed 42
```

## Related docs

- Root [`README.md`](../README.md) — sync commands and eval loop
- [`scripts/README.md`](../scripts/README.md) — streamers and eval runners
- [`reports/README.md`](../reports/README.md) — experiment log vs runtime artifacts
