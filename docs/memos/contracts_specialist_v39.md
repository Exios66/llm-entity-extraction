# contracts_specialist_v39 — the maximize-everything crossover (payment fold + precision guard + within-category completion)

**Research question**: Which single prompt mutation lifts ALL of F1, F2, recall, AND precision on the 255-doc chunked half-corpus under the corrected scorer — and what is the residual failure mass it targets?

**Companions**: `contracts_specialist_v36.md`, `contracts_specialist_v37_design.md`, `contracts_specialist_v38.md`, KANBAN-058 (corrected-scorer card), KANBAN-059 (this iteration).

## Answer, Response, + Summary of Results

**Short answer**: v39 = v37 (which embeds v36 + the payment fold) + 4 surgical `.replace()` edits: (1) enumeration entry 27 = Termination For Convenience WITH the WITHOUT-CAUSE boundary (the precision lever — 53 of 71 outputs are fp, the largest fp category, and the entry was missing entirely); (2) R2 money-family boundary clarifications (fee/royalty CAP ≠ liability cap; service fees ≠ Revenue/Profit Sharing; price-change notice duty ≠ Price Restriction); (3) WITHIN-CATEGORY COMPLETION in the grain rule (every distinct clause sentence of a present category quoted as its own item, first word through final period); (4) R2 one-item-per-clause-sentence strengthen. The recall lever is the measured 556 near-misses = mostly multi-label under-quoting (35% of positive pairs carry ≥2 GT clause sentences; the model quotes a subset). Prediction: P 0.68–0.72 / R 0.32–0.35 → F1 0.44–0.47, F2 0.36–0.39 vs v37's F1 0.4170 / F2 0.3382.

### Corrected-scorer state (KANBAN-058 landed; all records re-scored, zero LLM spend)

| version | F1 | F2 | recall | precision | jaccard | false-nr |
|---|---|---|---|---|---|---|
| v34 | 0.1740 | 0.1278 | 0.1085 | 0.4378 | 0.2929 | 0.465 |
| v35 | 0.1777 | 0.1310 | 0.1115 | 0.4372 | 0.3078 | 0.433 |
| **v36 (champion)** | 0.4073 | 0.3243 | 0.2855 | **0.7107** | 0.4806 | 0.3367 |
| **v37** | **0.4170** | **0.3382** | **0.3004** | 0.6820 | **0.4981** | **0.3260** |
| v38 | 0.4111 | 0.3283 | 0.2894 | 0.7093 | 0.4885 | 0.3369 |

Per-doc paired bootstrap (254 shared docs, seed 42): v36 vs v37 Δ +0.0100 CI [−0.0191, +0.0388] P(v37) 0.248; v36 vs v38 Δ +0.0095 CI [−0.0134, +0.0317] P(v38) 0.211 — both inside band; champion = v36. **v37 owns every run-level recall-side metric at a precision cost (0.6820 vs 0.7107) — the exact trade the v39 guard targets.**

### FP audit of v37's +40 fp (corrected scorer, per-category)

| category | v36 fp | v37 fp | Δ | verdict |
|---|---|---|---|---|
| Termination For Convenience | 47 | 53 | +6 | **GENUINE errors** — term-of-agreement clauses, for-cause/default/product-discontinuation terminations tagged as convenience; no enumeration entry exists (guard-list name only) → **precision lever** |
| Revenue/Profit Sharing | 7 | 13 | +6 | mixed — service fees / cost-sharing are genuine errors; per-unit fees defensible |
| Third Party Beneficiary | 26 | 31 | +5 | **GT-label noise** (disclaimer clauses ARE in-category per CUAD) — must NOT suppress |
| Uncapped Liability | 1 | 6 | +5 | mostly genuine — royalty/fee "CAPs" tagged as liability caps; hold-harmless tagged as uncapped |
| License Grant | 8 | 12 | +4 | review pending |
| Cap On Liability | 7 | 10 | +3 | mixed |
| Post-Termination | 17 | 20 | +3 | mixed |
| Non-Compete | 3 | 6 | +3 | review pending |
| Change Of Control | 7 | 1 | −6 | improved |
| Non-Disparagement | 19 | 14 | −5 | improved |
| Price Restrictions | 13 | 14 | +1 | **NOT the 24-fp inflation under the corrected scorer** — mixed (cost-plus formula / IRR cap defensible; price-increase notice duty marginal) |

### Near-miss decomposition of v37's 556 near pairs (corrected scorer)

- **371 (67%) "quote_style" — actually MULTI-LABEL UNDER-QUOTE**: label == span byte-identical for the quoted label(s); the pair fails because the category carries **≥2 GT clause sentences and one or more are never quoted**. 35% of all 6,702 positive pairs are multi-label (2,371). NETGEAR Insurance: 3 labels, certificate sentence missing; NETGEAR Cap On Liability: 9 labels, 6 missing; Termination For Convenience: 2 near-duplicate labels ("terminated"/"canceled" variants), one unquoted. **No curly-vs-straight quote artifact anywhere (0 in GT, 0 in spans).**
- 88 (16%) sibling_or_other — the quoted sentence is a different clause sentence of the same category (often the label's neighbor).
- 63 (11%) preamble_drop — the quote starts mid-sentence, dropping the label's leading phrase.
- 19 (3%) paraphrase — genuine rewording.
- 15 (3%) dash_gt — GT labels carrying `---` runs (74 labels; GT debt, flagged to KANBAN-058 follow-up).

The 371 + most of the 88/63 share ONE root: **the model quotes the category's strongest sentence(s) but not every distinct clause sentence** — the v36 grain rule quotes what the model finds; it does not force within-category completion. That is the v39 recall lever, and it is fp-neutral (extra quotes land inside already-present categories; fp is defined on GT-absent categories).

### The v39 mutation (ONE lesson per part; base constants byte-identical)

Derivation chain asserted in tests: `V37.startswith(V36[:300])`, `V39.startswith(V37[:300])`. v37 embeds the payment fold (4 edits: R2 PAYMENT TERMS & MONETARY CLAUSES scan family, canonical tag discipline, contract_value trigger extension, Uncapped/Liquidated appends) — that is part (a), inherited. v39 adds:

1. **Entry 27 = Termination For Convenience** (before WORKED SPAN EXAMPLES): WITH the WITHOUT-CAUSE boundary shapes + NEVER shapes (term/expiration clauses, default/breach/insolvency/cause, regulatory/discontinuation events) + measured "53 of 71 outputs are false positives" stat. Also helps the 21 absent fn on the category.
2. **R2 money-family boundary clarifications** (after "A fee or payment amount alone is NOT a price restriction."): fee/royalty/price CAP ≠ liability cap (Cap/Uncapped cover liability-limitation language only); service fees/cost-sharing ≠ Revenue/Profit Sharing (only sharing percentages + per-unit royalties count); price-change notice duty ≠ Price Restriction unless it caps amounts or frequency.
3. **WITHIN-CATEGORY COMPLETION** appended to the grain rule's "Never quote mid-obligation…" sentence: a category with several clause sentences is INCOMPLETE until EVERY distinct sentence is quoted as its own item; quote from FIRST WORD, never drop a leading phrase, never stop short of the final period (35% / 556-of-1,678 stats inlined).
4. **R2 checklist strengthen**: "at least one item AND at least one reasoning entry" → "ONE item AND ONE reasoning entry PER DISTINCT CLAUSE SENTENCE".

Contradiction check: entry 27's NEVER-shapes vs the v36 term rules (term/expiration stays out of TFC); carve-out shapes don't touch Non-Compete/ROFR entries; the completion rule does not conflict with "several clauses under one category keep one entry each" (that rule governs one clause → one item; completion governs one category → every sentence). Third Party Beneficiary deliberately untouched (GT noise).

### Tests

`test_contracts_v39_payment_fold_precision_and_completion` (tests/test_prompts.py): registration + derivation chain; part (a) fold phrases present; entry 27 + boundary + 53/71 stat; money-family boundary clarifications; WITHIN-CATEGORY COMPLETION + 35%/556 stats + FIRST WORD + PER DISTINCT CLAUSE; guards preserved (never fabricate, ADDING-only, verbatim grain, CATEGORY-LEVEL COMPLETENESS); v37/v36 free of the v39 additions; v38 not in the chain. **64 prompt tests + 19 contracteval/ab-paired + 12 eval smokes green.** Runner dry-run accepts v39 (255 rows, seed 42, chunked 90k/8k, Langfuse llm-dojo, reserved name `qwen3.7-flash_contracts_specialist_v39_extraction_chunked_half`, manifest `data/manifests/extract_v39_half.jsonl`).

### Interpretation

1. The corrected scorer reframed the whole chase: the champion gate (v36) is paired per-doc; the highest run-level numbers (v37) are the crossover material. v39 is the explicit synthesis — payment recall from v37, precision recovery targeted at the ONE genuinely prompt-fixable fp cluster (TFC 53), and recall mass from the measured multi-label under-quote.
2. The 371 "quote_style" bucket turned out to be a misnomer — byte-identical quoted labels on multi-label pairs. The lesson is structural (quote EVERY clause sentence), not stylistic; the fix rule is stated as a family rule testable on all docs of the category, not document recall.
3. Precision risk of the completion rule is ~zero by construction (fp is defined on GT-absent categories; extra quotes land inside present ones); the money-boundary clarifications + TFC entry carry the precision burden (−20-30 fp projected).
4. F2 frontier math (F2 = 5PR/(4P+R)): v37 baseline 0.3382; P 0.68/R 0.32 → F2 ≈ 0.358; P 0.70/R 0.345 → F2 ≈ 0.384; each +0.01 recall ≈ +17 TP.

*Sources*: re-scored records in `reports/experiment_log.jsonl` (v34–v38 half-corpus runs), `data/cuad/master_clauses.csv` + `src/contracteval.py` (corrected `load_master_gt`, `build_category_output`, `contracteval_classified`), per-category tp/fp/fn tables computed during this iteration, `tests/test_prompts.py::test_contracts_v39_payment_fold_precision_and_completion`.

## What questions or uncertainties remain?

1. **Conversion rate** — the A/B vs v36 is the only arbiter: does the completion rule fire on other docs of the same categories (generalization) without over-quoting (fp on present-but-GT-sparse categories)? The 556 near-mass projects +40-100 TP; the TFC boundary projects −20-30 fp; the actual conversion is the swing.
2. **The absent mass** (536 in v36 / ~600 in v37) is untouched by v39 — the v38 lever under-converted (+9 TP only). Whether the completion rule partially absorbs it (categories whose first sentence was quoted but whose tail sentences were never found) is an open measurement.
3. **Third Party Beneficiary 31 fp** — GT-label noise per CUAD's own categorization; a scorer-side re-baseline (KANBAN-058 follow-up) is the right venue, not a prompt carve-out.
4. **GT debt**: 74 dash-run labels, 18 literal-newline cells, and the near-duplicate Termination For Convenience labels ("terminated" vs "canceled") remain scorer/GT-side.
5. **n_positive drift**: v38's record carries 1,686 positives vs v36/v37's 1,678 — worth verifying n_docs when the v39 record lands (a +8 pair swing changes the denominator).
