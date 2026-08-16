# Contracts Specialist v31 — token-efficiency refactor (full-corpus A/B complete)

**Research question:** The specialist prompt grew from 555 system tokens (v1) to
8,377 (v30) — +33% since v22 in eight versions, with v23's worked-example set
(2,810 chars of verbatim quotes) and accumulated overlapping rules as the main
bloat. Can the SAME operative rules be stated in measurably fewer tokens without
losing accuracy — GEPA's efficiency-over-bloat principle — and does the
full-corpus (509-doc) surface give the reasoning-trace corpus and the
large-sample measurement the 50-doc surface cannot?

**Companions:** KANBAN-021 (this arm); memo `contracts_specialist_v30.md`
(noise floor ±0.03 @ 50 docs); memo `contracts_specialist_v28.md` (v28
champion, +4.48pp vs v26 @ 50 docs).

## Answer, Response, + Summary of Results

**Short answer: v31 is a Pareto win — the full-corpus A/B (509 docs, chunked,
seed 42) shows v31 0.8737 vs v28 0.8622 overall (+0.0116, paired bootstrap 95%
CI [+0.0005, +0.0236], P(Δ≤0)=0.021) with the system prompt 5.7% leaner
(8,164 → 7,700 tokens/call).** The compression (2,679 chars, −8.0%,
v23 worked-example quotes distilled to one-line family-boundary guidance)
improved or held every field (term_length +0.058, termination_clauses +0.044,
governing_law +0.014, key_obligations −0.003, renewal_terms −0.003), produced
a 7,250-entry reasoning-trace corpus (14.2/doc), and — critically — the
50-doc surface overstates the champion by ~6pp: v28's true full-corpus number
is **0.8622, not 0.9228**. The A/B was initially blocked by the OpenRouter
weekly key limit; completed after a new key (sk-or-v1-e09f…) was installed.

### The token audit (the arm's diagnosis)

| version | system tokens (chars/4) | note |
|---|---|---|
| v1 | 555 | baseline |
| v10 | 1,931 | family catalog |
| v17 | 3,286 | |
| v18 | 5,123 | +55.9% — first worked-example set + scope rules |
| v22 | 6,309 | champion era |
| v23 | 6,920 | +9.7% — second worked-example set (2,810 chars) |
| v26 | 7,642 | term_length opener discipline |
| v30 | 8,377 | +33% vs v22 |
| **v31** | **7,700** | **−5.7% vs v30, same operative rules** |

### The v31 compression (six surgical replacements on v30)

1. **v23 worked-example block (2,810 → ~1,160 chars, −1,646):** the 10
   verbatim quotes + negative examples become one-line family-boundary
   guidance — "audited-financial-statement delivery and revenue remittance
   ARE Audit Rights / Revenue/Profit Sharing items; … mark-HYGIENE duties
   on goods are operational, never family clauses." The lessons survive; the
   quotes do not (GEPA: examples carry the lesson, not the text).
2. **EXHAUSTIVENESS opening** (−246): boilerplate merged with its own count
   claim.
3. **RE-SCAN DUTY** (−278): duplicated family lists + truncation advice
   tightened (both-sides scan and never-fabricate preserved).
4. **VERBATIM COMPLETENESS** (−192): merged with the fragment rule.
5. **SIZE CALIBRATION** (−92): quota warning tightened.
6. **Atomic-fragment paragraph** (−225): preamble list + example contrast
   compressed; the 15-word worked example stays (short, load-bearing).

### The full-corpus A/B (the scale-up, completed)

Same-surface identity: `mailroom-cuad-contracts-full`, 509 docs, seed 42,
qwen3.7-flash, chunked 90k/8k, current scorer, fresh key. v28@510 was resumed
via manifest (217 cached + 292 fresh rows); v31@510 run fresh.

| metric | v28@510 | v31@510 | delta |
|---|---|---|---|
| overall (record mean) | 0.8631 | 0.8737 | +0.0106 |
| overall (clean 504 paired) | — | — | **+0.0116** CI [+0.0005, +0.0236], P=0.021 |
| key_obligations | 0.7697 | 0.7662 | −0.0034 |
| term_length | 0.7302 | 0.7884 | +0.0581 |
| governing_law | 0.9096 | 0.9238 | +0.0141 |
| termination_clauses | 0.8901 | 0.9337 | +0.0436 |
| renewal_terms | 0.7925 | 0.7893 | −0.0031 |
| system prompt | 8,164 t | 7,700 t | **−464 (−5.7%)** |
| reasoning entries | — | 7,250 (14.2/doc) | |

Per-doc ko: 108 recovered vs 120 regressed (mean −0.0029 — noise). **The
50-doc surface overstates the champion by ~6pp: v28@510 full-corpus 0.8622
vs 0.9228 @ 50 docs** — the full-corpus number is the stable estimate
(mirrors the sorter's sample-size non-monotonicity finding).

### Interpretation

1. v31 ≥ v28 at full corpus with a leaner prompt — release-grade Pareto
   improvement: the efficiency objective is satisfied without an accuracy
   cost, and there is no regression cluster (ko/renewal within noise; four
   fields improve).
2. The 6pp 50-doc-vs-full gap is the sample-shape lesson the doctrine
   warned about: 50-doc A/B deltas stay valid for DIRECTION, but absolute
   scores must be read on the full surface.
3. 5 v31 rows errored (4 post-processing "NoneType not iterable" scoring
   crashes + 1 length-limit parse error, ~1%) — a runner edge case, not a
   prompt-quality signal; follow-up hygiene card.

*Sources:* `reports/experiment_log.jsonl` —
`qwen3.7-flash_contracts_specialist_{v28,v31}_extraction_langfuse_510_full`;
manifests `data/manifests/v28_510_chunked.jsonl` (resumed) +
`v31_510_chunked_full.jsonl`; `src/prompts.py`
CONTRACTS_SPECIALIST_PROMPT_V31 banner.

## What questions or uncertainties remain?

- The 4 scoring crashes ("NoneType not iterable") on v31 rows: reproduce and
  fix in the runner/scorer (hygiene card) — 1% of rows.
- The +0.0116 win is small; a v31 rerun at full corpus would confirm it is
  not a favorable draw (expected band ±0.009 at 509 docs).
- Whether the win mechanism is the removed v23 negative example's
  suppressive effect or the shorter prompt's attention focus — untested.
