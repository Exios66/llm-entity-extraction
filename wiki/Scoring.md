# Scoring & Metrics Reference

Every metric this repo reports, where it is computed, and how to read it.
Scoring is deliberately **deterministic** — Braintrust scorers are trivial
lookups on locally computed composites, so the Braintrust UI, the run
manifests, and `reports/experiment_log.jsonl` never disagree.

## 1. Label normalization (`src/scorers.py`)

| Function | Purpose |
|---|---|
| `normalize_label(value)` | Coerce an LLM output into a canonical doc-class key: lowercase, strip quoting; prefer a JSON object's `doc_type` field; word-boundary regex fallback (`corporate_record` matches "Corporate Record", "corporate record", ...). |
| `ERROR_PREFIX` | Sentinel `"ERROR: "` prepended to failed-row outputs so failures are never silently counted as predictions. |

## 2. Classification scorers (`src/scorers.py`)

Used by `run_classification_eval.py` (`--scorers exact_match,failure,cost`).

| Scorer | Signature | Definition |
|---|---|---|
| `exact_match` | `(output, expected) -> float` | `1.0` iff `normalize_label(output) == normalize_label(expected)`, else `0.0`. |
| `failure` | `(output, expected) -> float` | `1.0` for rows whose output starts with the `ERROR:` sentinel (model error, invalid class, timeout), else `0.0`. Failed rows are counted as misses in `exact_match` and tracked separately via `failure`. |
| `cost` | `(input) -> float` | Actual billed USD for the row, captured from OpenRouter `usage.cost` by the task; `0.0` for manifest-replayed rows (paid for in the original run). |

**Per-class / macro** (`run_multiclass_eval.py`, plus helpers in `scorers.py`):

| Metric | Definition |
|---|---|
| per-class accuracy | `correct / n` per expected class (failed rows excluded) |
| `macro_accuracy` | unweighted mean of per-class accuracies over non-empty classes |

**Binary question** (`run_binary_class_eval.py`, `--positive <class>`): treats
one class as positive and reports `precision`, `recall`, `f1` over
predicted/expected positives plus exact match.

## 3. Field-type-aware content scoring (`src/field_scoring.py`)

Each extracted field is scored by its declared type
(`config/taxonomy.yaml → doc_classes[].field_types`; unmapped fields fall back
to a name heuristic). `FIELD_SCORERS` dispatch table:

| Type | Scorer | Definition |
|---|---|---|
| `id` | `score_id_field` | Normalize (uppercase, strip punctuation/whitespace, drop corporate suffixes) → exact match. Docket/filing/reference numbers. |
| `date` | `score_date_field` | Parse both sides to a canonical `datetime.date` (ISO, `mm/dd/yyyy`, "March 3, 2024", ordinal prose "10th day of January 2000", OCR artifacts) → exact match. Fallbacks, in order: **containment** — the label's date phrase (month/day-level: 3+ tokens or an explicit month) appears inside the prediction, or vice versa (CUAD maps BOTH "Agreement Date" and "Effective Date" onto `effective_date`, so documents legitimately carry several dates and the labeler may hold any of them) → 1.0; **partial credit** on shared components when both sides parse — year+month → 0.67, within a 45-day cluster (execution vs defined effective date — the same agreement's date pair) → 0.67, year-only → 0.33; unparseable values fall back to `name` fuzzy matching. A bare year ("2024") never earns full credit. |
| `money` | `score_money_field` | Strip `$`, commas, expand `K`/`M`/`B` suffixes and "USD/DOLLARS/EUROS" → float compare within **one cent** (legal amounts are exact: $250,001 ≠ $250,000). Unparseable prose falls back to `name` matching. |
| `name` | `score_name_field` | Normalized fuzzy matching: max(Jaro-Winkler, token-set ratio), but JW is only trusted when the token sets share ≥ 1 token (JW is dangerously lenient on disjoint short-vs-long names). |
| `free_text` | `score_free_text_field` | SQuAD-style token F1 over lowercase token multisets. |
| `containment` | `score_containment_field` | Share of the EXPECTED text's (stopword-filtered) tokens covered by the prediction. For verbatim-clause fields whose label is one sentence of a longer passage — returning the expected sentence plus riders/citations scores 1.0. Applied automatically to `containment_fields` (`governing_law`, `term_length`, `renewal_terms`). |
| `entity_list[:<element>]` | `score_entity_list` | Pairwise similarity matrix over predicted vs expected items, **optimal bipartite matching** (Hungarian algorithm, `scipy`; greedy fallback), threshold `bipartite_match_threshold` (0.6) → `precision = matched/n_predicted`, `recall = matched/n_expected`, `f1 = 2PR/(P+R)`. |

**Embedding rescue** — `name`/`free_text` and list elements of those types
additionally get a second signal when the string score is below
`embedding_rescue_below` (0.7): cosine similarity from
`sentence-transformers/all-MiniLM-L6-v2` (local) with an OpenRouter
`text-embedding-3-small` fallback, lazy-loaded, degrading silently to the
string score when unavailable. `max(string_score, sim)` — never overrides a
confident string-level match.

**Partial ground truth** (`partial_gt_fields`: `parties`,
`key_obligations`, `termination_clauses`) — CUAD clause-QA labels are partial
samples, not exhaustive lists, so the model is usually MORE complete than the
label set. For these fields:

- the reported list score is **ground-truth coverage** = `recall` over matched
  label items (`EntityListScore.score`), NOT F1 — extra correct extractions
  don't cut the score;
- role-word labels ("Shipper.", "Seller", "Sponsor", ...) count as matched
  whenever the prediction names at least one party (the role is instantiated);
- raw precision/recall/F1 are always kept in `entity_list_scores` for audit.

**Ambiguous band** `[0.5, 0.85]` — per-field scores inside the band set
`ambiguous_fields`, which (a) marks the row `needs_judge_review` and (b)
triggers the optional `--judge` LLM pass (correctness/completeness).

## 4. Composite extraction-eval metrics (`run_extraction_eval.py`)

The task returns a composite output computed locally; registered Braintrust
scorers are lookups on it:

| Tracker | Definition |
|---|---|
| `overall_extraction_score` | mean of per-field content scores over expected fields with a non-null expected value (`overall_score` in the composite). |
| `field_presence` | binary conformance: share of expected fields the model populated (non-null/non-empty). |
| `schema_valid` | `1.0` iff the model returned parseable, schema-conformant JSON. |
| `category_presence` | CUAD YES/NO category conformance: share of the document's applicable presence-type categories (labeled clauses that must be covered) whose clause text is present in the extraction. Absent categories are satisfied unless fabricated (the factuality guard catches fabrication). |
| `overall_verified_precision` | factuality guard: mean `verified_precision` over every audited field (list + scalar) the model populated — anchored to exactly the components that make it up. |
| `{field}_score` (`--bt-scores full`) | the field's content score (same number that feeds `overall_extraction_score`). |
| `{field}_f1` (`--bt-scores full`) | the SAME list score that feeds the per-field score (GT coverage for partial-GT fields, F1 otherwise) — tracker consistency rule. |
| `{field}_precision` (`--bt-scores full`) | over-extraction guard: `matched_gt / n_predicted` (raw precision). |
| `{field}_verified_precision` (`--bt-scores full`) | truth guard: share of predicted items that match a GT label OR are grounded in the document text. |

**Factuality audit** — every predicted item/value must be TRUE: it either
matches a ground-truth label (element scorer ≥ 0.6) or its content is present
in the source document (normalized token coverage ≥ `token_coverage` 0.7;
dates grounded by parsing date candidates in ANY format from the document).
Items that are neither are hallucinations:

```
verified_precision = (GT-matched + doc-grounded) / n_predicted
hallucination_rate  = (n_predicted - true_items) / n_predicted
```

**Run-level regression diagnostics** (`scores.diagnostics` in the experiment
log, computed by `src/metrics.py`) — post-hoc aggregates over the stored
rows, NOT Braintrust trackers (run-level, not per-row):

- **Error decomposition** — `field_exact_rate` / `field_partial_rate` /
  `field_miss_rate`: share of scored (doc, field) pairs at 1.0, `0 < s < 1`,
  and 0.0, with `error_decomposition.<field>` per field and
  `field_presence_per_field` (per-field population share).
- **List quality** — raw (not GT-coverage) precision/recall/F1:
  `entity_list_precision/recall/raw_f1` per field, macro `list_*` over
  `key_obligations`, and span-summed micro `list_micro_*` (each contract
  weighted by its number of spans).
- **Regression error (MAE)** — `date_mae_days` / `duration_mae_days` /
  `money_mae_usd` (+ median AE and per-field buckets): mean/median ABSOLUTE
  error between predicted and expected values over rows where BOTH sides
  parse — dates (`effective_date`) and durations (`term_length`,
  `renewal_terms`) in calendar days, money amounts (`contract_value`,
  `demand_amount`) in USD. A day-shifted date or a $1-off amount is a
  near-miss, not a binary wrong answer. Support sizes (`date_n_pairs`,
  `duration_n_pairs`, `money_n_pairs`) state the evidence behind every row.
- **Regression fit (R²)** — `date_r2` / `duration_r2` (+ per-field
  buckets): coefficient of determination over the SAME parseable pairs:

  ```
  R² = 1 − SS_res / SS_tot
  SS_res = Σ (pred − exp)²        SS_tot = Σ (exp − mean(exp))²
  ```

  1.0 = the predictions reproduce the ground truth exactly; 0.0 = as good
  as predicting the mean; **negative = worse than the mean** (kept, not
  clamped — it signals the extraction is anti-correlated with the truth).
  Undefined (`null`) with fewer than 2 parseable pairs or zero expected
  variance (all expected values identical — `SS_tot = 0`). Dates are
  encoded as ordinal days (translation-invariant, so the offset is
  irrelevant).
- **Span-count drift** — `span_count_mae` / `span_count_signed_mean`
  (+ per-field buckets, `span_count_n_docs`): over list fields, the
  model-vs-annotator item-count delta per document. MAE is symmetric
  (over- AND under-extraction both hurt); the signed mean shows the
  DIRECTION — positive = systematic over-extraction (invented/split
  spans), negative = systematic under-extraction (merged/omitted spans).

Parse sources: expected values prefer the curated master-labels CSV
(`src/master_labels.py`, default `../llm-mailroom/data/cuad/master_clauses.csv`
— normalized answers like `"5/8/14"`, `"2 years"`), falling back to the raw
CUAD clause-label text. A `term_length` expected value that is actually an
expiration date ("...shall terminate on June 30, 2010") feeds the date
buckets, not the duration buckets. The optional `--master-labels` flag and
the `MASTER_LABELS_CSV` env var point at the CSV; the diagnostics degrade
gracefully (raw text parsing) when it is absent.

## 5. Chained eval metrics (`run_chained_eval.py`)

Per-stage trackers, registered with `--bt-scores overall|full`:

| Tracker | Definition |
|---|---|
| `sorter_exact_match` | `1.0` iff sorter doc_type == expected (`contract` for CUAD rows). |
| `sorter_subtype_accuracy` | `1.0` iff doc_type AND contract_subtype (normalized against CUAD folder names) match the row's expected subtype. |
| `sorter_confidence` | the sorter's reported confidence. |
| `extractor_overall` / `extractor_field_presence` / `extractor_verified_precision` / `extractor_category_presence` / `extractor_schema_valid` | the same composite lookups as §4, from the specialist stage. |

## 6. A/B evaluation (`evaluate_prompt_version.py`)

Runs prompt A and prompt B on the same dataset, then reports
`delta exact_match (B − A)` with a verdict (`A wins` / `B wins` / `tie` at
±0.001) plus a per-metric side-by-side table. `--compare-only` fetches two
existing experiments without re-running.

## 7. Token & cost accounting

- `tokens_summary()` aggregates per-row `_last_usage` records into
  prompt/completion/total tokens, mean cost and total cost, and
  `rows_with_usage` — rows replayed from a manifest carry no usage and are
  excluded from cost summaries.
- `cost_usd` = mean per-row cost; `cost_total_usd` = sum. Chained runs report
  sorter/extractor/total stage rows separately.

## Bootstrap confidence intervals & delta significance (issue #1)

- Every run's headline carries a **95% bootstrap CI** (percentile method,
  2000 resamples, seed 42) over its per-document scores — computed by the
  runner and stored as `scores.*_ci`; the site falls back to resampling the
  stored `results[]` arrays, then Wilson, for older records.
- **A/B deltas** (same surface only) get a two-sample bootstrap CI on the
  difference (`src/bootstrap.delta_significance`): "significant" means the CI
  excludes zero. A 5-doc 0.94-vs-0.88 gap is a CI overlap, not a win.
- **Same-surface rule enforced end-to-end**: a run's "Δ vs best" is only
  computed/colored against the best run with the same dataset fingerprint +
  seed + sample size; the site refuses to compare across surfaces.


## 8. Subtype metrics (`run_subtype_eval.py`)

| Tracker | Definition |
|---|---|
| `exact_match` | share of rows where doc_type == `contract` |
| `subtype_accuracy` | share of rows whose normalized subtype exactly equals the CUAD ground-truth folder |
| `subtype_accuracy_equiv` | strict OR a defensible equivalent family (`SUBTYPE_EQUIVALENCES`: reseller↔distributor, maintenance↔license, development↔license, affiliate↔joint_venture) |
| `confidence` | mean model-reported confidence |
| `failure_insights` | `mode_counts` + per-failed-row `{expected, predicted, mode, equiv_recovered, reasoning}`; modes: `function_over_form`, `other_fallback`, `equivalent_family`, `family_confusion` |
| `per_subtype` | per-family accuracy / equiv / counts |
| `confusion_matrix` | expected x predicted counts |
| `subtype_accuracy_ci` / `exact_match_ci` | bootstrap 95% CIs over the per-document flags |

## 9. Judge calibration (`--judge`, `run_extraction_eval.py`)

Every ambiguous-band row the judge reviews is persisted to
`data/judgments/<experiment>.jsonl` (`kind: calibration`) and aggregated into
`scores.judge_calibration`:

- `n_judged` / `n_scored` — rows reviewed / rows with a scored verdict;
- `agree_rate` — deterministic strong (≥ 0.85) & judge `accurate`, or
  deterministic weak (≤ 0.5) & judge `inaccurate`, over scored rows;
- `judge_strict` / `judge_lenient` — deterministic strong but judge
  `inaccurate` (strict) / deterministic weak but judge `accurate` (lenient) —
  a systematic lean means trusting the judge more broadly needs calibration.

## 10. Chained error-propagation ablation (`--handoff-scope ground_truth`)

`scores.ablation` on the SAME documents compares the specialist under the
predicted-subtype handoff vs the ground-truth-subtype handoff:

- `predicted_handoff_overall` / `ground_truth_handoff_overall` — extractor
  scores with each cue;
- `sorter_loss_pp` — the gap: sorter routing error, isolated from specialist
  error (same model, prompt, and documents — only the cue differs).

## 11. Cost scoring (every run)

OpenRouter usage payloads carry no cost, so every run is cost-scored
deterministically from its recorded prompt/completion token counts × verified
per-model prices (`src/cost_models.py`): qwen $0.03/$0.13 per 1M (in/out),
deepseek-v4-flash $0.05/$0.25, deepseek-v4-pro $0.435/$0.87 (unknown models
resolve by prefix or honestly report None). `tokens_summary(model=)` stamps
`cost_estimated_usd` on every record; historical records were backfilled
(`scripts/backfill_cost_estimates.py`, documented one-time append-only
exception). The site shows billed OpenRouter totals when the activity CSV is
ingested, and the estimate otherwise — never a fabricated number.
