# `scripts/` — ops, evals, reporting, site, releases

Every script is `#!/usr/bin/env python3`, runs from the repo root, exposes
`main_with_args(argv)` (testable), and anything that spends LLM money offers
`--dry-run`.

## `scripts/` root

| Script | Purpose |
|---|---|
| `release.py` | semver release automation: `--bump <patch|minor|major> --note "<summary>"` converts `[Unreleased]` -> `[vX.Y.Z]`, bumps `pyproject.toml`, prints commit/tag/sync commands; `--check` validates state (version == changelog header, site data, tests, render audit); `--dry-run` previews |

## `scripts/datasets/` — sync the corpora into Braintrust datasets

| Script | Purpose |
|---|---|
| `stream_cuad_to_bt.py` | CUAD corpus -> Braintrust dataset (`--text-only`, `--dry-run`, `--limit`) |
| `download_cuad_pdfs.py` | keep the CUAD PDF corpus locally (`--out-dir`, `--category`, resumable) |
| `stream_legalbench_to_bt.py` | LegalBench MAUD agreements -> Braintrust |
| `stream_legalbench_tasks_to_bt.py` | LegalBench multi-class task suites -> Braintrust (one `mailroom-lb-<task>` dataset per task, e.g. `--tasks hearsay`; deterministic row ids => reruns upsert) |

## `scripts/eda/`

`explore_cuad.py` — full-corpus CUAD EDA -> `data/eda/{report.md, findings.md, figures/01–10}` (reproducible from the repo root).

## `scripts/eval/` — the runners (see wiki: Eval-Runners)

Every runner: `main_with_args(argv)`, `--dry-run`, resumable `--manifest`,
experiment-log append. Names are `{model-slug}_{prompt-version}[_suffix]`.

| Script | Purpose |
|---|---|
| `run_classification_eval.py` | one prompt version; `--input-mode auto/text/vision`, `--prompt-mode sorter/task`, `--valid-classes`, local PDFs |
| `run_subtype_eval.py` | sorter-only contract-subtype eval (one call per PDF; strict + equiv accuracy) |
| `run_extraction_eval.py` | contracts specialist vs CUAD ground truth; `--bt-scores`, `--judge`, `--chunked` |
| `run_chained_eval.py` | sorter -> extractor end-to-end; `--handoff-scope none|subtype|ground_truth` ablation |
| `run_binary_class_eval.py` | binary question precision/recall/F1 |
| `run_multiclass_eval.py` | all-class eval with per-class accuracy |
| `run_model_matrix.py` | model x prompt grid on one surface |
| `evaluate_prompt_version.py` | A/B two prompt versions on the same dataset (bootstrap delta CI) |
| `run_annotation_queue.py` | HITL annotation queues (llm-dojo mirror): `build`/`status` on low-performing extraction traces + failed sorter classifications |
| `run_langfuse_subtype_eval.py` | **primary-sink mirror** of `run_subtype_eval` (per-doc Langfuse traces + scores, LangSmith spans) |
| `run_langfuse_chained_eval.py` | **primary-sink mirror** of the chained eval (per-agent spans + task scores) |
| `run_langfuse_extraction_eval.py` | **primary-sink mirror** of the extraction eval (`--chunked` supported) |
| `run_langfuse_classification_eval.py` | **Langfuse mirror** of the classification eval (`--prompt-mode task` for LegalBench tasks) |
| `sync_langfuse_prompts.py` | mirror versioned prompts into Langfuse (idempotent; `--env-file` adds projects) |
| `sync_langfuse_datasets.py` | mirror Braintrust datasets into Langfuse datasets (deterministic item ids => upsert) |

## `scripts/reporting/`

| Script | Purpose |
|---|---|
| `render_experiment_log.py` | JSONL -> markdown log (rebuilds `reports/experiment_log.md`) |
| `report_generator.py` | markdown experiment report from Braintrust (needs `BRAINTRUST_API_KEY`) |
| `confusion_matrix.py` | PNG + CSV confusion matrix from Braintrust |
| `score_extraction_manifest.py` | post-hoc extraction scoring from a manifest (offline) |
| `rescore_manifests.py` | re-score extraction manifests with the CURRENT scorer (scorer-drift immune; `--auto-50`) |
| `judge_experiment.py` | post-hoc JudgeAgent review of failed classifications |
| `backfill_subtype_reasoning.py` | one-time enrichment: full failure reasoning from Braintrust spans |
| `backfill_cost_estimates.py` | documented one-time backfill: stamp `cost_estimated_usd` on historical records (`--dry-run` first) |
| `export_experiment_results.py` | regenerate the per-task performance workbooks + codebooks (Google-Sheets-friendly): `Sorter_Experiment_Results.xlsx` (114 cols, Eval Results + Codebook sheets) + `Sorter_Experiment_Codebook.csv` from `subtype_classification` runs, `Entity_Extraction_Results.xlsx` (141 cols) + `Entity_Extraction_Codebook.csv` from `contract_entity_extraction` runs. `--task {sorter,extraction,all}`, `--outdir`, `--log`. Mirrors the reference format byte-for-byte (headers/order, percent/date formats, freeze panes, autofilter, per-subtype ordering). |

## `scripts/site/`

`build_site.py` — rebuild `docs/data/` (index.json, meta.json, runs/,
trends.json, prompts.json, board.json, memos.json) for the GH Pages site;
`--check` verifies freshness; `--openrouter-csv`/`--benchmarks-key` attach
real billed costs / live OpenRouter benchmark data.
