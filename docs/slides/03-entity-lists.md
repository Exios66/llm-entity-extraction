# 03 — Entity lists: bipartite matching, precision / recall / F1

---

## The problem

`parties`, `key_obligations`, and `termination_clauses` are LISTS. A list
extraction can be right on the substance but wrong on boundaries ("non-compete
for 2 years" vs "non-compete"), or order/shape ("Acme Inc." vs "Acme
Incorporated"). Scorers must match predicted items to expected items first.

**Method — optimal bipartite matching (Hungarian algorithm)**: build a
pairwise similarity matrix over predicted × expected items; find the
one-to-one assignment maximizing total similarity; any pair at or above the
threshold (0.6) counts as **matched**.

---

## Worked example — `parties`

| | Predicted (model) | Expected (GT) |
|---|---|---|
| items | `["Acme Corporation", "Beta LLC"]` | `["Acme Incorporated", "Beta LLC", "Gamma Partners"]` |

Pairwise similarities (item scorer: token coverage → embedding rescue):

| pred \ exp | Acme Incorporated | Beta LLC | Gamma Partners |
|---|---|---|---|
| Acme Corporation | **0.87** | 0.0 | 0.0 |
| Beta LLC | 0.0 | **1.0** | 0.0 |

Optimal assignment matches both predicted items (0.87 + 1.0). Gamma is
unmatched.

```
precision = matched / n_predicted = 2/2 = 1.0
recall    = matched / n_expected  = 2/3 ≈ 0.667
F1        = 2PR/(P+R)             = 2·1·0.667/1.667 ≈ 0.8
```

---

## Partial ground truth: why `key_obligations` is NOT scored by F1

CUAD clause-QA labels are **partial samples**, not exhaustive lists — the
model is usually MORE complete than the label set. For `partial_gt_fields`
(`parties`, `key_obligations`, `termination_clauses`):

- the reported list score is **ground-truth coverage** = `recall` over
  matched labels — extra correct extractions don't cut the score;
- role-word labels ("Shipper.", "Seller") count as matched whenever the
  prediction names at least one party;
- contained labels match unconditionally when a GT label of 3–6 tokens
  appears verbatim inside a predicted item ("Consultant" inside
  `Timothy Cabrera ("Consultant")`);
- **raw precision/recall/F1 are always kept** in `entity_list_scores` and in
  the run diagnostics — over-extraction is visible there.

---

## Macro vs micro — why both are reported

The run-level diagnostics report list P/R/F1 two ways:

| | Definition | Question answered |
|---|---|---|
| **Macro** `list_f1` | mean of per-doc F1 over `key_obligations` | Average document quality — every doc counts equally |
| **Micro** `list_micro_f1` | span-pooled: `Σmatched / Σpredicted` etc. | Bulk quality — each span/item counts equally |

Example, 2 docs:

| Doc | matched | predicted | expected |
|---|---|---|---|
| A (10 spans) | 9 | 10 | 11 |
| B (1 span) | 1 | 1 | 1 |

```
macro F1 = mean(F1_A, F1_B)          # B's perfect doc lifts the average
micro F1 = (9+1) / (10+1) and (9+1)/(11+1) pooled  # A's 10 spans dominate
```

If macro > micro, small docs do better; if micro > macro, the big docs carry
the quality. Both are stored (`list_micro_n_predicted` / `n_expected` /
`matched` let you recompute).

---

## Span-count drift — the volume signal

Beyond match quality, the diagnostics track **how many items** the model
emits vs the annotator:

```
span_count_mae           = mean |n_predicted − n_expected|   (symmetric)
span_count_signed_mean   = mean (n_predicted − n_expected)   (direction)
```

| Doc | predicted | expected | delta |
|---|---|---|---|
| A | 14 | 10 | +4 |
| B | 8 | 10 | −2 |
| C | 9 | 10 | −1 |

```
span_count_mae         = (4 + 2 + 1)/3 = 2.33 items
span_count_signed_mean = (4 − 2 − 1)/3 ≈ +0.33 items   → mild net over-extraction
```

Positive signed mean = systematic **over**-extraction (invented or split
spans); negative = systematic **under**-extraction (merged or omitted).
Zero means counts cancel even when individual docs drift.

---

## Entity-list audit — the factuality companion

Every list row also carries `entity_list_audit.<field>`:

```json
{
  "n_predicted": 3, "matched_gt": 2, "verified_in_doc": 3,
  "true_items": 3, "verified_precision": 1.0,
  "hallucinated": 0, "hallucination_rate": 0.0
}
```

Matched-by-similarity AND grounded-in-document are TRUE items; neither ⇒
hallucination (deck 05).

---

## Pitfalls

- **Macro ≠ micro** — quote both, never just "F1".
- **GT-coverage fields** — a high score on `key_obligations` does NOT mean
  the model didn't over-extract; read raw precision and span-count.
- **Threshold 0.6** — items below the bipartite threshold are unmatched,
  even if "kind of similar".
- **Support size** — `span_count_n_docs` and the pooled counts show how
  many documents the numbers rest on.

## Next

- [04-regression-diagnostics](04-regression-diagnostics.md) — MAE, R², money
