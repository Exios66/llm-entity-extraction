# `scripts/` — ops, evals, reporting, site, releases

| Script | Purpose |
|---|---|
| `release.py` | semver release automation: `--bump <patch|minor|major> --note "<summary>"` converts `[Unreleased]` -> `[vX.Y.Z]`, bumps `pyproject.toml`, prints commit/tag/sync commands; `--check` validates state; `--dry-run` previews |
| `backfill_cost_estimates.py` | documented one-time backfill: stamp `cost_estimated_usd` on historical records (`--dry-run` first) |

## `scripts/datasets/`

| Script | Purpose |
|---|---|
| `stream_cuad_to_bt.py` | CUAD corpus -> Braintrust dataset (`--text-only`, `--dry-run`, `--limit`) |
| `download_cuad_pdfs.py` | keep the CUAD PDF corpus locally |
| `stream_legalbench_to_bt.py` | LegalBench MAUD agreements -> Braintrust |
| `stream_legalbench_tasks_to_bt.py` | LegalBench multi-class task suites -> Braintrust (one `mailroom-lb-<task>` dataset per task, e.g. `--tasks hearsay`; deterministic row ids => reruns upsert) |

## `scripts/eval/` — the runners (see wiki: Eval-Runners)

`run_classification_eval.py`, `run_subtype_eval.py`, `run_extraction_eval.py`,
`run_chained_eval.py` (incl. `--handoff-scope ground_truth` ablation),
`evaluate_prompt_version.py` (A/B with bootstrap delta CI),
`run_model_matrix.py` (model x prompt grid on one surface), and the
`run_langfuse_*_eval.py` mirrors. Every runner: `main_with_args(argv)`,
`--dry-run`, resumable `--manifest`, experiment-log append.

## `scripts/reporting/`

`render_experiment_log.py` (JSONL -> markdown log), `report_generator.py` +
`confusion_matrix.py` (Braintrust-fetching reports), `score_extraction_manifest.py`
(offline manifest scoring).

## `scripts/site/`

`build_site.py` — rebuild `docs/data/` (index.json, meta.json, runs/,
trends.json, prompts.json) for the GH Pages site; `--check` verifies
freshness; `--openrouter-csv` attaches real billed costs.
