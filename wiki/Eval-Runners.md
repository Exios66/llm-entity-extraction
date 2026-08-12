# Eval Runners

Each runner tests **ONE prompt version**; the experiment name is
`{model-slug}_{prompt-version}[_suffix]`. All runners share the
`main() -> main_with_args(argv)` pattern, `--dry-run` on anything that spends
money, and append to `reports/experiment_log.jsonl` on completion.

## Classification (`scripts/eval/run_classification_eval.py`)

The sorter-only task: doc-type classification (or LegalBench multi-class
`--prompt-mode task`). Trackers: `exact_match`, `failure`, `cost_total_usd`,
`cost_mean_usd`, `per_class_accuracy`, plus a bootstrap CI
(`exact_match_ci`).

```bash
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --input-mode text --prompt-version sorter_v0
```

## Subtype (`scripts/eval/run_subtype_eval.py`)

Sorter-only subtype routing: one call per document decides the primary class
AND the contract-subtype family (25 CUAD families + `other`).
`--stratified N` samples evenly across classes. Trackers: `exact_match`,
`subtype_accuracy`, `subtype_accuracy_equiv` (defensible family swaps),
`confidence`, `failure_insights` (mode counts + per-failed-row reasoning),
`per_subtype`, `confusion_matrix`, bootstrap CIs.

```bash
python scripts/eval/run_subtype_eval.py --dataset mailroom-cuad-contracts-full \
    --stratified 200 --seed 42 --sorter-prompt-version sorter_v5
```

## Extraction (`scripts/eval/run_extraction_eval.py`)

The contracts-specialist entity extraction vs CUAD clause-QA ground truth.
Trackers: `overall_extraction_score`, `field_presence`, `schema_valid`,
`overall_verified_precision`, `category_presence`, `per_field`,
`entity_list_f1`, `hallucination_rate`, `overall_extraction_score_ci`.
Optional `--judge` runs the LLM judge on the ambiguous band and records the
**judge-calibration tracker** (`scores.judge_calibration`).

```bash
python scripts/eval/run_extraction_eval.py --dataset mailroom-cuad-contracts \
    --prompt-version contracts_specialist_v11 --judge
```

## Chained (`scripts/eval/run_chained_eval.py`)

Sorter → specialist end-to-end with the subtype handoff:
`--handoff-scope subtype` (default) cues the specialist with the PREDICTED
subtype's field groups; `none` reproduces the legacy handoff;
**`ground_truth`** is the error-propagation ablation — the specialist ALSO
extracts with the ground-truth-subtype cue, and `scores.ablation` splits
sorter routing loss from specialist error.

```bash
python scripts/eval/run_chained_eval.py --dataset mailroom-cuad-contracts-full \
    --sorter-prompt-version sorter_v6 --extractor-prompt-version contracts_specialist_v11
python scripts/eval/run_chained_eval.py ... --handoff-scope ground_truth   # ablation
```

## A/B (`scripts/eval/evaluate_prompt_version.py`)

Runs two prompt versions on the same dataset and reports the delta with a
**two-sample bootstrap CI + significance verdict** (a 5-doc 0.94-vs-0.88 gap
is a CI overlap, not a win).

```bash
python scripts/eval/evaluate_prompt_version.py --prompt-a sorter_v0 --prompt-b sorter_v1
```

## Cross-model matrix (`scripts/eval/run_model_matrix.py`)

Runs the SAME fixed sample (same dataset/seed/size — one surface) across a
model x prompt grid and prints a score (+CI) x cost matrix.

```bash
python scripts/eval/run_model_matrix.py --task subtype \
    --models qwen/qwen3.7-flash,deepseek/deepseek-v4-flash \
    --prompts sorter_v5,sorter_v6 --sample 10 --seed 42
```

## Langfuse mirrors (`scripts/eval/run_langfuse_*_eval.py`)

Same runners traced to the `llm-mailroom-experiments` Langfuse project
(one trace per document, per-agent spans with task scores).

## Datasets (`scripts/datasets/`)

- `stream_cuad_to_bt.py` — the CUAD corpus into Braintrust
  (`--text-only` / vision page images)
- `download_cuad_pdfs.py` — keep the CUAD PDF corpus locally
- `stream_legalbench_to_bt.py` / `stream_legalbench_tasks_to_bt.py` —
  LegalBench MAUD agreements + the multi-class task suites

## Reporting (`scripts/reporting/`)

- `render_experiment_log.py` — rebuild `reports/experiment_log.md` from the
  JSONL (the JSONL is the source of truth; never hand-edit the md)
- `report_generator.py` / `confusion_matrix.py` — Braintrust-fetching reports
- `score_extraction_manifest.py` — offline manifest scoring

## Site (`scripts/site/build_site.py`)

Rebuilds `docs/data/` (index.json, meta.json, runs/, trends.json,
prompts.json) — see [Site](Site).
