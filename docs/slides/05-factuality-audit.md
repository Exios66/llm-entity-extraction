# 05 — Factuality audit: verified precision and hallucination rate

---

## The question

Precision answers "of what the model returned, how much matches the
labels?". But a model can return things that match NO label and yet are
true (the labels are partial samples!), or things that match NO label and
are ALSO not in the document (fabrications). The factuality guard separates
those two cases.

**Every predicted item must be TRUE**: it either

1. matches a ground-truth label (element scorer ≥ 0.6), OR
2. its content is present in the source document (normalized token coverage
   ≥ 0.7; dates grounded by parsing date candidates in any format from the
   document).

Items that are neither are **hallucinations**.

---

## The numbers

```
verified_precision = (GT-matched + doc-grounded) / n_predicted
hallucination_rate = (n_predicted − true_items) / n_predicted
```

| Tracker | Definition |
|---|---|
| `overall_verified_precision` | mean `verified_precision` over every audited field the model populated |
| `hallucination_rate` | mean share of predicted items that are neither matched nor grounded |
| per-field `verified_precision` (`--bt-scores full`) | the same per field |

---

## Worked example — `key_obligations`

| # | Predicted item | GT label? | In document? | Verdict |
|---|---|---|---|---|
| 1 | "Licensee shall pay royalties quarterly" | yes (0.87 match) | — | ✓ matched |
| 2 | "Licensee shall maintain records for audit" | no label | yes (token cov 0.8) | ✓ grounded |
| 3 | "Licensee shall pay a $5M signing bonus" | no label | NO (cov 0.1) | ✗ **hallucinated** |

```
n_predicted = 3, true_items = 2
verified_precision = 2/3 ≈ 0.667
hallucination_rate = 1/3 ≈ 0.333
```

A hallucinated clause is worse than a missed one — it can end up in a
downstream legal decision. This guard exists because it does.

---

## The audit record per field (`entity_list_audit`)

```json
{
  "n_predicted": 3,
  "matched_gt": 1,
  "verified_in_doc": 2,
  "true_items": 2,
  "verified_precision": 0.6667,
  "hallucinated": 1,
  "hallucination_rate": 0.3333,
  "doc_verification": true
}
```

**Post-hoc analysis is performed on these numbers directly (summed over
rows), never on recomputed scores** — so a scorer change can't silently
rewrite history.

---

## What the factuality guard does NOT do

| Not covered | Why / what to do |
|---|---|
| Grounded-but-wrong context | Coverage ≥ 0.7 is presence, not semantic truth — the judge pass (`--judge`) adds LLM review for ambiguous bands |
| Scalar fields' semantics | Scalar date/money values are grounded by parsing, not semantics — MAE/R² (deck 04) add the distance |
| Fabricated structure | A JSON object that parses but invents a field gets caught by presence/audit, not by `schema_valid` |

---

## Read it as a pair

| Pattern | Reading |
|---|---|
| High verified precision, low hallucination | Model extracts what's in the doc; misses are omissions (scope) |
| Low verified precision, high hallucination | Model invents plausible content (dangerous — fix prompt constraints) |
| High recall, low verified precision | Model over-extracts real text with wrong boundaries (grain, not scope) |

Pair it with span-count drift (deck 03) to tell "invented" from
"boundary-shifted".

## Next

- [06-failure-analysis](06-failure-analysis.md) — where the loss comes from
