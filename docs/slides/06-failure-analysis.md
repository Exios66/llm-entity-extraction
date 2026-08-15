# 06 — Failure analysis: error decomposition, confusion matrices, failure insights

---

## The question

The composite score says HOW MUCH. Failure analysis says **WHERE the loss
comes from** — which fields, which error shapes, which families — so the
next prompt iteration targets a real residual instead of guessing.

Three tools, one diagnostic ladder:

1. **Error decomposition** (run-level, per field) — where content-score loss
   concentrates.
2. **Confusion matrices** (classification runs) — which classes get
   confused with which.
3. **Failure insights** (subtype runs) — per-failed-row reasoning from the
   model.

---

## 1. Error decomposition — exact / partial / miss

Every scored (doc, field) pair is binned by its content score:

| Band | Definition | What it usually means |
|---|---|---|
| **exact** | score = 1.0 | correct extraction |
| **partial** | 0 < score < 1 | right substance, wrong boundary/format (fuzzy match, partial credit) |
| **miss** | score = 0.0 | missing or wrong |

Run-level: `field_exact_rate`, `field_partial_rate`, `field_miss_rate`
(+ `n_fields_scored`). Per-field: `error_decomposition.<field>.{exact_rate,
partial_rate, miss_rate}` and `field_presence_per_field` (did the model
populate the field at all?).

### Worked example (20 scored pairs)

| Field | exact | partial | miss | presence | Reading |
|---|---|---|---|---|---|
| `effective_date` | 0.90 | 0.05 | 0.05 | 1.0 | nearly solved |
| `parties` | 0.50 | 0.30 | 0.20 | 0.95 | boundary/format problems dominate (partial ≫ miss) |
| `governing_law` | 0.35 | 0.10 | 0.55 | 0.45 | half the time not even populated → presence problem, prompt-level |

Rule of thumb: **partial-heavy → grain/boundary work; miss-heavy + low
presence → scope/existence work; exact-heavy everywhere → the field is
solved, move on.**

---

## 2. Confusion matrices (classification)

Expected × predicted counts, diagonal = correct. For the sorter (doc_type +
25 contract subtypes) the run reports expected-vs-predicted matrices; the
subtype eval adds strict vs equivalence-aware accuracy.

| expected \ predicted | reseller | distributor | license | … |
|---|---|---|---|---|
| **reseller** | **20** | 5 | 0 | |
| **distributor** | 4 | **18** | 0 | |
| **license** | 0 | 2 | **14** | |

- Off-diagonal clusters = systematic family confusion (fixable by prompt
  rules; e.g. reseller↔distributor are a recognized equivalence family).
- The subtype eval reports BOTH strict accuracy (exact CUAD folder) and
  family-level equivalence accuracy (`reseller↔distributor`,
  `maintenance↔license`, `development↔license`, `affiliate↔joint_venture`)
  — a defensible family routing is a partial win, never silently counted as
  a strict win.

---

## 3. Failure insights (subtype runs) — the model's own reasoning

`scores.sorter.failure_insights`:

```json
{
  "n_failed": 18,
  "mode_counts": {
    "function_over_form": 6, "other_fallback": 5,
    "equivalent_family": 4, "family_confusion": 3
  }
}
```

Per failed row: `{expected, predicted, mode, equiv_recovered, reasoning}`
— with the model's FULL reasoning, so a prompt rule can be written for each
failure mode:

| Mode | Meaning | Typical prompt fix |
|---|---|---|
| `function_over_form` | doc_type missed on substance vs title | title-wins / function-wins rule |
| `other_fallback` | fell to a generic class | expand family enumeration |
| `equivalent_family` | defensible family, strict miss | equivalence table covers it |
| `family_confusion` | genuinely confused families | separation rule + examples |

The v9 sorter iteration is the template: 18 fails, one-off long tail, no
cluster > 2 → ~0.93 is the practical plateau (KANBAN-013).

---

## The A/B template (same surface only)

1. Diagnose with data (this deck) → pick ONE change.
2. New prompt version constant (version key = identity; never mutate a run
   prompt).
3. Same dataset, same seed, same sample → compare strict + equiv + cost.
4. Only same-surface deltas are valid comparisons — never compare across
   samples.
5. Headline deltas need the 95% bootstrap CI on the difference: a 5-doc
   0.94-vs-0.88 gap is a CI overlap, not a win.

---

## Pitfalls

- Decomposition rates need support: 20 scored pairs ≠ 2000.
- Partial ≠ harmless: boundary drift on `parties` can mean wrong legal
  entity.
- `equiv_recovered` rows are NOT strict wins — always quote strict AND
  equiv.
- Absent failure insights = older records; regenerate from stored rows /
  Braintrust spans before diagnosing.

## Next

- [07-reading-the-log](07-reading-the-log.md) — reading the experiment log
