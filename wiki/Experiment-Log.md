# Experiment Log

## The JSONL — source of truth

`reports/experiment_log.jsonl` is the **append-only** record: one JSON line
per run, never rewritten (the one documented exception: a changelog-noted
one-time backfill). Every record carries:

- `git` snapshot (commit + dirty flag), `model`, `prompt_version` /
  `prompt_versions`
- `data_source`: project, ground truth, **dataset_fingerprint**, n_samples,
  sample_requested, **seed** — the same-surface identity
- `parameters`: temperature, max_tokens, reasoning_effort, max_input_chars,
  max_concurrency, bt_scores, handoff_scope, tracing backend
- `tokens`: prompt/completion/total per stage, `cost_usd`, **`cost_estimated_usd`**
  (deterministic token × price — OpenRouter usage carries no cost), rows_with_usage
- `scores`: task-specific, including **bootstrap CIs** (`*_ci`),
  `judge_calibration`, `ablation` (chained ground-truth handoff)
- `results[]`: per-document rows with the model's predicted outputs

## The markdown — derived

`reports/experiment_log.md` is regenerated whole from the JSONL:

```bash
python scripts/reporting/render_experiment_log.py
```

Each run renders as a fully expanded section: metadata, data source,
parameters, tokens, every score with breakdowns, per-document results,
scoring matrices, confusion matrices, model outputs, and (subtype) failed-
classification insights with full reasoning.

## The site — GitHub Pages

> ### [https://exios66.github.io/llm-entity-extraction/](https://exios66.github.io/llm-entity-extraction/)

A dependency-free single-page viewer served from `docs/` on `main` (no
Actions runners). Rebuild after every run:

```bash
python scripts/site/build_site.py          # docs/data/* (index, meta, runs/, trends.json, prompts.json)
python scripts/site/build_site.py --check  # verify freshness
node tests/assets/site_render_audit.js     # headless render audit of EVERY view
```

See [Site](Site) for what the viewer offers. **Cost scoring:** every run
shows a deterministic estimate (tokens × verified per-model prices) and the
billed OpenRouter total when the activity-log CSV is ingested
(`build_site.py --openrouter-csv openrouter_activity.csv`).

## Mirror into llm-mailroom

llm-mailroom holds a synced copy at
`docs/reports/experiments/experiment_log.md` (SYNCED-DOCUMENT header carrying
the upstream commit + the site link). Re-sync after every upstream push:

```bash
cd ../llm-mailroom
PYTHONPATH=src python -c "from legalbench.experiment_log import regenerate, default_log_path; regenerate(default_log_path())"
```
