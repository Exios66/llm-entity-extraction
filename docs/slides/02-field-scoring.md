# 02 — Field-type-aware scoring: how one value becomes a score

---

## The principle

Exact-match-on-extraction treats every field identically — which is wrong.
"March 3, 2024" ≠ "03/03/2024" as strings, but they are the same date.
`$250,001` ≠ `$250,000` as strings, but they are $1 apart in substance.

So every field is scored by its declared type
(`config/taxonomy.yaml → doc_classes[].field_types`; unmapped fields fall
back to a name heuristic). Each type has its own scorer in the
`llm-dojo-scoring` package (`llm_dojo_scoring.field_scoring` — the repo's
`src/field_scoring.py` is a thin re-export shim), and the per-field score
feeds the composite:

```
overall_extraction_score = mean of per-field content scores
                          (over expected fields with a non-null expectation)
```

---

## Example 1 — `date` (`effective_date`)

| Side | Value |
|---|---|
| **Expected (ground truth)** | `"March 3, 2024"` |
| **Predicted (model)** | `"03/03/2024"` |
| **Score** | **1.0** |

Both sides parse to the canonical `datetime.date(2024, 3, 3)` → exact match.

Partial credit when both sides parse but disagree:
year+month shared → **0.67**; same date within a 45-day cluster (execution
date vs defined effective date) → **0.67**; year-only shared → **0.33**.
A bare year ("2024") never earns full credit.

**Null-expectation rule**: a blank-template or label-only expected date
(`"_____ day of ________, 19____"`, `"Effective Date:"`) holds NO real
date — the expectation is null. A null prediction then scores **1.0** (the
model is correct to find nothing); any non-empty prediction scores **0.0**.

---

## Example 2 — `money` (`contract_value`)

| Side | Value |
|---|---|
| **Expected** | `"$250,000"` |
| **Predicted** | `"$250,001"` |
| **Score** | **0.0** |

Strip `$`/commas, expand `K`/`M`/`B` suffixes → float compare within **one
cent**. Legal amounts are exact: `$250,001 ≠ $250,000` is a miss at the
content-score level — but note the MAE diagnostics will still quantify it as
a **$1 error** (deck 04), which a binary score throws away.

---

## Example 3 — `name` (`parties`, `governing_law`)

| Side | Value |
|---|---|
| **Expected** | `"FRANCHISE AGREEMENT"` |
| **Predicted** | `"Goosehead Insurance Agency, LLC Franchise Agreement"` |
| **Score** | **1.0** |

Normalized fuzzy matching: max(Jaro-Winkler, token-set ratio), JW only
trusted when token sets share ≥ 1 token (JW is dangerously lenient on
disjoint short-vs-long names). **Containment first**: every expected token
inside the prediction → 1.0 (short titles contained in longer extracted
titles are matches).

**Embedding rescue**: when the string score is below 0.7, a cosine
similarity signal (local `all-MiniLM-L6-v2`, OpenRouter fallback) is taken
as `max(string_score, sim)` — never overrides a confident string match,
never rescues an empty value.

---

## Example 4 — `free_text` / `containment`

**free_text** (e.g. a party's obligations description): SQuAD-style token
F1 over lowercase token multisets.

**containment** (auto-applied to `governing_law`, `term_length`,
`renewal_terms`): share of the EXPECTED text's stopword-filtered tokens
covered by the prediction.

| Side | Value |
|---|---|
| **Expected (label)** | `"This Agreement shall be governed by the laws of Nevada"` |
| **Predicted** | `"...governed by the laws of Nevada, excluding conflicts rules"` |
| **Score** | **1.0** |

Verbatim-clause labels are one sentence of a longer passage — returning the
expected sentence plus riders/citations scores 1.0; truncating the expected
text scores below 1.0 (missing tokens lower coverage).

---

## `id` (docket / filing / reference numbers)

Normalize (uppercase, strip punctuation/whitespace, drop corporate
suffixes) → exact match. No fuzzy credit — reference numbers are exact.

---

## Where to look in code

| What | Where |
|---|---|
| Scorer dispatch | `FIELD_SCORERS` in `llm_dojo_scoring.field_scoring` (via `src/field_scoring.py` shim) |
| Type mapping per doc class | `config/taxonomy.yaml → field_types` |
| Composite assembly | `score_extraction()` in `llm_dojo_scoring.field_scoring` |
| Null-expectation date rule | `_date_expected_is_null()` + `score_date_field()` |
| Settings wiring | `src/dojo_config.py` → package `Settings` |

---

## Pitfalls when interpreting per-field scores

- A **0.0** date can still be a near-miss — check the MAE diagnostics.
- A **1.0** money value is exact to the cent; a 1.0 name can be a
  containment match (label inside a longer extracted title).
- Fields with `partial_gt` semantics (deck 03) are NOT scored by F1 — extra
  correct extractions don't cut the score.

## Next

- [03-entity-lists](03-entity-lists.md) — lists, bipartite matching, P/R/F1
