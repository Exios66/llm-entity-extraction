# Contracts Specialist v31 — token-efficiency refactor (A/B blocked by weekly key limit)

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

**Short answer:** v31 (derived from v30, base untouched) removes 2,679 chars
(**−8.0%**, 8,377 → 7,700 system tokens) with every operative constraint
preserved: the v23 worked-example block is distilled from 10 verbatim quotes
into one-line family-boundary guidance (the lesson, not the text), and the
EXHAUSTIVENESS / RE-SCAN / VERBATIM / SIZE-CALIBRATION boilerplate is merged
with its overlapping neighbours. 349 tests green, all 28 family-catalog
entries + multi-item rule + CoC carve-out + chunk scalar quoting + term_length
discipline + reasoning trace intact. **The accuracy A/B is BLOCKED: the
OpenRouter weekly key limit (403) hit mid-run — v28@510 completed 217/509
rows and v31@510 completed 0 — the A/B resumes after the key resets** (both
runs are manifest-resumable, ~$0.19 each).

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
| **v31** | **7,700** | **−8.0% (2,679 chars), same operative rules** |

### The v31 compression (six surgical replacements on v30)

1. **v23 worked-example block (2,810 → ~1,160 chars, −1,646):** the 10
   verbatim quotes + negative examples become one-line family-boundary
   guidance — "audited-financial-statement delivery and revenue remittance
   ARE Audit Rights / Revenue/Profit Sharing items; … mark-HYGIENE duties
   on goods are operational, never family clauses." The lessons survive; the
   quotes do not (GEPA: examples carry the lesson, not the text).
2. **EXHAUSTIVENESS opening** (−246): "scan the document section by section
   (Section 1, 2, 3…)" boilerplate merged with its own "5–15 vs 20+" count
   claim.
3. **RE-SCAN DUTY** (−278): duplicated family lists + truncation advice
   tightened (both-sides scan and never-fabricate preserved).
4. **VERBATIM COMPLETENESS** (−192): merged with the fragment rule.
5. **SIZE CALIBRATION** (−92): quota warning tightened.
6. **Atomic-fragment paragraph** (−225): preamble list + example contrast
   compressed; the 15-word worked example stays (short, load-bearing).

### The scale-up attempt (blocked, infrastructure proven)

- Full-corpus surface identified: `mailroom-cuad-contracts-full` (509 rows;
  the 50-doc `mailroom-cuad-contracts` dataset is the sample, not the
  corpus). 510-doc chunked runs cost ~$0.19 each and take ~15–25 min.
- v28@510 (champion baseline): **217/509 rows completed** before the weekly
  key limit hit — partial, biased subset; the 0.8558 on the record must NOT
  be cited as a full-corpus number. Resume path:
  `run_langfuse_extraction_eval.py --dataset mailroom-cuad-contracts-full
  --sample 510 --seed 42 --prompt-version v28 --chunked --manifest
  data/manifests/v28_510_chunked.jsonl` (resumes the 217 done rows).
- v31@510: 0/509 rows (limit fully exhausted) — rerun fresh after reset.
- Reasoning-trace corpus: the partial run already yields 217 docs × ~20–30
  per-field reasoning entries; a full-corpus mine (NEAR/MISS classification
  at scale) is the next iteration's reflection substrate once unblocked.

### Interpretation

1. The compression is verified at the prompt level; its accuracy effect is
   UNMEASURED until the key resets — v31 is registered and test-pinned, not
   claimed. The 50-doc noise floor (±0.03) says the expected effect is
   within-band anyway; the 510-doc surface (noise ~±0.013) is where a
   sub-1pp regression would be visible.
2. Token economics: the system prompt is ~31% of each chunk call at v30
   (8.4k of ~26.5k prompt tokens/doc); v31's −0.5k system tokens/doc
   compounds across ~1,000 calls per full-corpus run and every production
   chained/vision call — the point is the reversed growth curve (8.4k → 7.7k)
   and the discipline (efficiency over bloat), not a single-run saving.
3. The full-corpus surface matters: the 50-doc sample is a favorable draw;
   the true full-corpus number for the v28 champion is yet unknown (partial
   217-doc slice ≈ 0.86, biased). The KANBAN-021 resume completes it.

*Sources:* `reports/experiment_log.jsonl` — `..._v28_extraction_langfuse_510`
(217/509), `..._v31_extraction_langfuse_510` (0/509, 403s),
`..._v31_sample2_probe` (403 confirmed); `src/prompts.py`
CONTRACTS_SPECIALIST_PROMPT_V31 banner; prompt token audit script.

## What questions or uncertainties remain?

- v31's accuracy vs v30/v28 on the full corpus — BLOCKED, resumes after the
  weekly key limit resets (both manifests ready).
- The true full-corpus champion number (v28@510 complete) — same blocker.
- The partial 217-doc slice: usable as a reasoning-trace seed, not as a score.
