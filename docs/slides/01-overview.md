# 01 — Overview: the pipeline and what "success" means

---

## The 90-second map

```
CUAD contracts ──▶ Braintrust dataset ──▶ eval runner
                                               │
                    sorter agent ──▶ specialist agent (extraction)
                                               │
                              deterministic scoring (local)
                                               │
            overall_extraction_score ──▶ scores.diagnostics
            + per-field content scores         │
            + factuality audit                 ▼
                                      experiment log + site
```

- **What is scored**: the JSON each specialist agent returns (fields like
  `parties`, `effective_date`, `term_length`, `key_obligations`,
  `governing_law`).
- **Against what**: the CUAD ground truth — per-document expected fields
  derived from the contract's type (41 CUAD clause categories; 9 map to
  schema fields, 32 are YES/NO presence categories).
- **Preferentially**: the curated **master labels CSV**
  (`master_clauses.csv` — normalized answers like `"5/8/14"`, `"2 years"`)
  is the preferred parse source for the regression diagnostics; raw CUAD
  clause text is the fallback.

---

## What "success" means (and what it does NOT mean)

| Not success | Success |
|---|---|
| Exact-match on extracted text | A field-type-aware content score in `[0,1]` |
| One number for everything | A composite **plus** run-level diagnostics that say WHY |
| LLM-judge opinions as ground truth | Deterministic formulas (reproducible, no API drift) |

The composite tells you **how much** was extracted correctly. The
diagnostics tell you **how wrong** the near-misses were (MAE, R²), **which
direction** the errors point (span-count signed mean, error decomposition),
and **whether the model invented anything** (factuality audit).

---

## The metric families

| Family | Metrics | Answers |
|---|---|---|
| Content accuracy | `overall_extraction_score`, per-field scores, `field_presence` | How much correct content per field? |
| List quality | Precision / recall / F1 (macro + micro), GT coverage | For parties/obligations: matched items vs predicted/expected |
| Regression error | MAE, median AE, R² (date / duration / money) | How far off are the near-misses, in days/$? |
| Volume drift | span-count MAE + signed mean | Does the model over- or under-extract spans? |
| Factuality | `verified_precision`, `hallucination_rate` | Does the model fabricate? |
| Schema | `schema_valid` | Did the model return parseable JSON? |
| Error shape | exact / partial / miss decomposition | Where does the loss come from? |

---

## A run's anatomy (what the experiment log stores per run)

```
experiment_name        model + prompt version + suffix  (the identity)
data_source            dataset, fingerprint, master_labels path
parameters             sample, seed, reasoning_effort, max_input_chars, ...
scores                 overall_extraction_score (+ 95% CI),
                       per_field, entity_list_f1, verified_precision,
                       diagnostics {list P/R/F1, MAE/R², span-count, decomp}
results[]              per-document: predicted, field_scores, audits, tokens
tokens                 prompt/completion totals + estimated cost
```

**Naming is identity**: `{model}_{prompt-version}_extraction[_suffix]`.
Prompt version IS the experiment identity — never mutate a prompt string
after it has run.

---

## The golden rules when reading any number here

1. **Compare same surfaces only** — same dataset fingerprint + seed +
   sample size. A 50-doc run and a 195-doc run are NOT comparable.
2. **Read the support size** — `date_n_pairs`, `duration_n_pairs`,
   `money_n_pairs` say how much evidence an MAE/R² row rests on.
3. **A binary score hides near-misses** — a wrong date that is off by 1 day
   and one off by 10 years both score 0.0. That is exactly what MAE/R² exist
   for.
4. **Samples lie at small n** — every headline carries a 95% bootstrap CI;
   trust the CI, not the point estimate.

---

## Next

- [02-field-scoring](02-field-scoring.md) — how a single value becomes a score
