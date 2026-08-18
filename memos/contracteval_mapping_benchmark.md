# ContractEval mapping benchmark + the key_obligations scoring bottleneck

**Research question:** How does this repo's one-pass contract-extraction
pipeline score against ContractEval (arXiv 2508.03080) on CUAD with
ContractEval's own rubric — and what does the gap tell us about the
key_obligations scoring bottleneck (issue #21)?

**Companions:** KANBAN-051 board card + issue #21 (SCORING FIXES &
CORRECTIONS), the llm-dojo-scoring v0.3.0 upstream release (disaggregation +
category-presence routing), `src/contracteval.py`,
`scripts/reporting/run_contracteval_mapping.py`,
`reports/contracteval_benchmark.md`.

## Answer, Response, + Summary of Results

**Short answer:** On ContractEval's exact rubric (TP = every ground-truth
label span **verbatim-contained** in the answer, pooled over the 32 CUAD
YES/NO obligation categories × 509-doc full corpus), the champion
**qwen3.7-flash contracts_specialist_v32 scores F1 0.164 / F2 0.109 /
Jaccard 0.215 / false-"no related clause" 0.670** — far below ContractEval's
GPT-4.1 (F1 0.641) — but the gap is dominated by a **paraphrase penalty, not
missing extraction**: 42.7% of positive-label pairs are covered by a
predicted span at token-containment ≥ 0.7 (and 58.4% at ≥ 0.5), while only
9.2% satisfy ContractEval's exact-substring rule. The pipeline quotes
operative language but rephrases it, so a verbatim-containment rubric
systematically undervalues it. llama-4-scout v31 is dramatically weaker on
both lenses (F1 0.034; ≥ 0.7 coverage 9.3%).

## Results

### 1. ContractEval parity (stored full-corpus runs, pooled)

32 YES/NO obligation categories per document; GT spans from the committed
`data/cuad/master_clauses.csv` (row-joined by aggressive filename
normalization — 509/509 in the champion run). ContractEval metric code copied
verbatim (confusion logic from `open_source_model.py`, rates/Jaccard from
`Evaluation.py`).

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr |
|---|---|---|---|---|---|---|---|---|---|
| qwen3.7-flash v32 (champion) | 15,968 | 3,505 | 0.800 | 1.000 | 0.089 | 0.164 | 0.109 | 0.215 | 0.670 |
| qwen3.7-flash v31 | 16,096 | 3,556 | 0.799 | 1.000 | 0.090 | 0.166 | 0.110 | 0.214 | 0.680 |
| llama-4-scout v31 | 16,256 | 3,578 | 0.784 | 1.000 | 0.017 | 0.034 | 0.022 | 0.045 | 0.934 |

ContractEval Table III: GPT-4.1 F1 0.641 / F2 0.672 / Jacc 0.472 / false-nr
0.071; GPT-4.1-mini 0.644/0.678/0.435/0.072; Claude Sonnet 4 0.523/0.578/
0.458/0.025; Gemini 2.5 Pro 0.497/0.604/0.506/0.011; Qwen3-8B(thinking)
0.540/0.512/0.391/0.110.

### 2. The semantic-coverage companion (contained-label lens)

Best predicted-span token-containment against the GT label, per positive pair
(the repo's field-type-aware convention; verbatim = ContractEval's rule):

| Run | n_pos | verbatim | ≥0.7 | ≥0.5 | ≥0.3 |
|---|---|---|---|---|---|
| qwen3.7-flash v32 | 3,505 | 0.092 | 0.427 | 0.584 | 0.768 |
| qwen3.7-flash v31 | 3,556 | 0.092 | 0.421 | 0.574 | 0.761 |
| llama-4-scout v31 | 3,578 | 0.018 | 0.093 | 0.139 | 0.293 |

### Interpretation

1. **The verbatim rule is the wrong yardstick for a paraphrase extractor.**
   ContractEval's models are *instructed* to return exact sentences; ours is
   instructed to quote operative language but still paraphrases (whitespace,
   truncation, restatement). The 9.2%-verbatim vs 42.7%-≥0.7 containment gap
   is structural, not a coverage failure. This is *why* this repo abandoned
   exact-match-on-extraction for field-type-aware containment/similarity
   scoring in the first place (README "Scoring"; issue #21 assumes the same).
2. **The mapping scorer is sound but has a structural precision artifact:**
   a one-pass extractor never claims a category the GT marks absent, so
   precision is 1.0 by construction and F1 tracks recall. The honest
   comparison axes versus ContractEval are recall / F2 / Jaccard /
   false-"no related clause"; F1 is NOT directly comparable.
3. **The real bottleneck is extraction coverage of specific categories, not
   the 0.6 Hungarian threshold.** Even at the lenient ≥0.7 containment band,
   the champion covers only 42.7% of expected category clauses — the model is
   missing or paraphrasing ~57% beyond recognition. Issue #21's disaggregation
   (v0.3.0) fixes the *scoring* of what is extracted; the benchmark says the
   bigger lever is category-directed extraction coverage (the v33 retag routes
   reasoning evidence per category and is the first step).
4. **llama-4-scout is not competitive on clause extraction** (≥0.7 coverage
   9.3% vs 42.7%), consistent with its flash-tier classification role.

## What questions or uncertainties remain?

- **Would verbatim recall jump with a quote-faithful prompt?** A v33-style
  prompt that also demands verbatim sentence quoting (ContractEval's system
  prompt does exactly this) would test whether the paraphrase penalty is a
  prompt effect. Candidate follow-on: A/B v32 vs a quote-faithful v34 on the
  same 510 surface.
- **Is the mapping best-match floor (0.5) fair?** It only affects which
  categories a *partially*-covering span feeds; pair-level TP still requires
  full label containment, so F1/recall are robust to the floor; Jaccard and
  false-nr are mildly sensitive.
- **The string-answer categories (Parties, Effective Date, ...) are
  excluded** — a full 41-category parity would need a per-question harness,
  which is precisely what a ContractEval-style runner (not built here) would
  provide.
- **Denominator note:** ContractEval hardcodes its false-rate denominator to
  1,244 positives; this benchmark uses its own n_pos (~3.5k), so the
  false-nr rates are not unit-comparable to Table III — report the rate with
  its n_pos.

*Sources:* ContractEval arXiv 2508.03080 + `Evaluation.py` /
`open_source_model.py` (github.com/olivialiu121/ContractEval); CUAD
ground truth `data/cuad/master_clauses.csv`; experiment log
`reports/experiment_log.jsonl` (qwen3.7-flash v31/v32 + llama-4-scout v31
full-corpus extraction runs); llm-dojo-scoring v0.3.0.
