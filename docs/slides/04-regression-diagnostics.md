# 04 — Regression diagnostics: MAE, R², and the master-labels ground truth

---

## Why binary scores aren't enough

A date that is off by 1 day and a date off by 10 years BOTH score 0.0 at the
content level. To improve a prompt you need to know **how wrong** the
near-misses are, and in **which direction**. That is what the regression
diagnostics (`scores.diagnostics`, `src/metrics.py` — a re-export shim for
the `llm-dojo-scoring` package's `llm_dojo_scoring.diagnostics`) measure —
against the curated ground truth.

**Ground truth source**: the master-labels CSV
(`master_clauses.csv`, default `../llm-mailroom/data/cuad/master_clauses.csv`)
carries normalized answers per contract + CUAD category
(`Effective Date-Answer = "5/8/14"`, `Renewal Term-Answer = "2 years"`).
Raw CUAD clause text is the fallback. Diagnostics degrade gracefully when
the CSV is absent.

---

## Mean Absolute Error (MAE) — the near-miss ruler

```
MAE = mean |predicted − expected|        over parseable pairs only
Median AE = median of the same absolute errors   (robust to outliers)
```

| Domain | Units | Fields | Example pair |
|---|---|---|---|
| Date | calendar days | `effective_date` | pred `2024-01-17` vs exp `2024-01-15` → **2 days** |
| Duration | calendar days | `term_length`, `renewal_terms` | pred `"2 years"` vs exp `"1 year"` → **365 days** |
| Money | USD | `contract_value`, `demand_amount` | pred `$250,001` vs exp `$250,000` → **$1** |

Only rows where BOTH sides parse count — unparseable predictions are
excluded, and the **pair count tells you how much evidence the number rests
on**: `date_n_pairs`, `duration_n_pairs`, `money_n_pairs`. A `term_length`
expected value that is really an expiration date ("...terminate on June 30,
2010") feeds the DATE buckets, not the duration buckets.

---

## Worked example — date MAE

| Doc | Predicted | Expected (master) | Error (days) |
|---|---|---|---|
| A | `2024-01-15` | `1/15/2024` | 0 |
| B | `2024-01-15` | `January 15, 2022` | 730 |
| C | `2024-01-16` | `2024-01-15` | 1 |
| D | `TBD` | `2024-01-15` | (unparseable — excluded) |

```
MAE       = (0 + 730 + 1) / 3  = 243.7 days
Median AE = 1 day              ← most docs are exact; one is way off
date_n_pairs = 3
```

**Read**: the median says most dates are exact; the MAE says one outlier
dominates the mean. Median vs MAE divergence is itself diagnostic — follow
the outlier docs in the per-document results.

---

## R² — the coefficient of determination

```
R² = 1 − SS_res / SS_tot
SS_res = Σ (pred − exp)²          SS_tot = Σ (exp − mean(exp))²
```

The share of ground-truth variance the predictions explain, over the SAME
parseable pairs (dates encoded as ordinal days — translation-invariant).

| R² | Meaning |
|---|---|
| **1.0** | predictions reproduce the ground truth exactly |
| **0.0** | as good as predicting the mean (constant predictor) |
| **negative** | WORSE than the mean — kept, not clamped: the extraction is anti-correlated with the truth (systematic direction error) |
| **null** | undefined — < 2 pairs, or zero expected variance (all expected dates identical, `SS_tot = 0`) |

Worked example (same 3 pairs as above, expected = 15 Jan 2024, 15 Jan 2022,
15 Jan 2024):

```
SS_res = (0)² + (730)² + (1)² = 532,901
SS_tot = 0² + 730² + 0²       = 532,900
R²     = 1 − 532901/532900    ≈ −1.0   ← worse than predicting the mean
```

One catastrophic outlier drives R² negative even when two of three docs are
exact — exactly the signal MAE alone cannot show.

---

## Money MAE — cents matter

Money values compare EXACT (within a cent) at the content-score level, but
the diagnostics still measure the distance:

| Doc | Predicted | Expected | |Δ| (USD) |
|---|---|---|---|---|
| A | `$10,000,000` | `$10,000,000` | 0 |
| B | `$10,000,001` | `$10,000,000` | 1 |
| C | `$10.5M` | `$10,500,000` | 0 |

`money_mae_usd = $0.33`, `money_n_pairs = 3` — the model's amounts are
exact to within a dollar; the "binary miss" on B was a $1 rounding artifact.

---

## Span-count drift (recap from deck 03)

```
span_count_mae         = mean |n_predicted − n_expected|   symmetric
span_count_signed_mean = mean (n_predicted − n_expected)   direction
```

Reported overall and per list field. Use it to decide whether a prompt
iteration should tighten scope (over-extraction) or expand it
(under-extraction).

---

## Reading a real diagnostics block

A genuine block from a 2-doc pilot (`pilot_diag_v22_sample2`,
`contracts_specialist_v22`, seed 42, master labels CSV active):

```
| Domain   | MAE      | Median AE | R²   | n pairs |
|----------|----------|-----------|------|---------|
| Date     | 0.0 d    | 0.0 d     | 1.0  | 2       |
| Duration | 185.0 d  | 185.0 d   | —    | 1       |
| Money    | —        | —         | —    | 0       |
```

```
span_count_mae         = 5.0 items      signed mean = +5.0   (n docs = 5)
  key_obligations: MAE 10.5, signed +10.5     ← the story is here
list_precision 0.3125 · list_recall 0.9286   (43 predicted vs 18 expected)
field decomposition: exact 0.9167 · partial 0.0833 · miss 0.0
```

**Interpretation**: the model finds the dates exactly (MAE 0, R² 1.0) and
never misses a field outright (miss rate 0) — but on `key_obligations` it
emits 43 items where the annotator labeled 18. Recall is high (0.93) while
raw precision collapses (0.31): **systematic over-extraction** (the GT is a
partial sample, so this is partly label coverage — but +10.5 items/doc says
the prompt's scope is too permissive). The duration MAE rests on ONE pair —
evidence-thin, do not over-read. Money had no parseable pairs at all.

This is the classic diagnosis-to-iteration flow: the composite (0.9910)
looks solved; the diagnostics say the next prompt iteration should tighten
`key_obligations` scope, not touch dates.

---

## Pitfalls

- **Always read the pair count** (`*_n_pairs`) with MAE/R² — 2 pairs is a
  hint, 500 pairs is a fact.
- **R² null ≠ 0** — null means undefined (too few pairs / no variance).
- **Negative R² is a real signal** — systematic direction error.
- **Master CSV is best-effort** — absent ⇒ raw clause-text parsing; the
  record's `data_source.master_labels` says what was used.

## Next

- [05-factuality-audit](05-factuality-audit.md) — fabrication detection
