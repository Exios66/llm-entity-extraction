# Contracts Specialist v29/v30 — follow-up arm: the noise floor

**Research question:** What are the "not fixed & follow-ups" from the
KANBAN-004 close-out — the renewal_terms dip, the chunked-mode ×
term_length interaction, Gridiron's degenerate output, the 4 regressed
docs — and what is the actual resolution limit of the 50-doc chunked A/B
surface?

**Companions:** KANBAN-020 (this arm); memo `contracts_specialist_v28.md`
(v27/v28 multi-item rule, whose "uncertainties" this memo resolves);
KANBAN-004 (issue #3, closed).

## Answer, Response, + Summary of Results

**Short answer:** Every follow-up resolves into one of three buckets —
(1) **run-to-run noise, now quantified**: an identical-prompt rerun of the
v28 champion on the same 50-doc surface differs by −0.0293 overall with
~12 docs moving >±0.02 on key_obligations — the surface's resolution limit
is ±0.03, and the renewal_terms dip (1 doc, NOVO), the term_length
"collapse" (3 docs, sampling), and 3 of the 4 regressed docs are all inside
it; (2) **one genuine rule-vs-rule contradiction, now fixed**: v28's
"definitions are NEVER items" contradicted the v10-era re-scan note ("the
defined term itself"), suppressing Ediets' Change-of-Control definition
spans — v29 adds the carve-out (CoC-family definitions ARE items); (3)
**one genuine quoting-relaxation gap, now patched**: chunked mode licensed
prefix-only/null term_length quotes — v30 adds chunk-mode scalar-quoting
discipline. **v29 and v30 measure inside the noise band (paired deltas
−0.0264 / −0.0382 vs the identical-prompt rerun's −0.0293) — they ship as
logic repairs, explicitly unmeasured, and v28 remains the champion (its
+0.0448 vs v26 re-validates at P=0.004).** Gridiron's `":"` output was a
1-off: fresh v26/v28 runs both score 1.0 there.

### The follow-ups, resolved

1. **renewal_terms dip (−0.042, n=21) = one doc, quote-truncation
   variance.** NOVO 1.0→0.111: v26 quoted the renewal clause plus its
   follow-on rider, v28 trimmed to the first sentence. 1 pair — evidence
   floor says no rule. No pattern across the other 20 docs.
2. **chunked × term_length = sampling, not a stable prompt gap.** The
   sample5 collapse (v26 chunked 0.102) was small-n luck: at 50-doc scale
   term_length runs 0.777–0.854 across identical/champion/candidate runs —
   a ±0.08 band. The v26-chunked failures (Ritter prefix-only "five (5)
   years", Phasebio null, Ediets opener-dropped) share one mechanism —
   chunk mode relaxing the quoting rules ("quote the VISIBLE operative
   language faithfully and stop at what you can see") — so v30 patches the
   CHUNK DUTY text; its effect is unmeasurable below the band.
3. **Gridiron degenerate `":"` = resolved by drift.** v26@50ab and v28@50
   both score 1.0 with 3 clean items. The v23-era failure was a 1-off
   stochastic output, not a prompt property.
4. **The 4 regressed docs = 1 rule-driven, 3 noise.** Per-span sim-matrix
   diff: Ediets lost 2 Change-of-Control DEFINITION spans (1.00→0.45/0.40)
   — rule-driven (v28's definitions criterion; corpus exposure: 3 of 121
   CoC docs are definitional) → fixed by v29's carve-out (Ediets recovers
   0.692→0.769 in the v29 run). LinkPlus (−1 litigation span), Innerscope
   (−1 assignment collision), LegacyTechnology (−1 assignment collision)
   show no family pattern and are inside the rerun band.
5. **`--chunked` enforcement shipped.** `run_extraction_eval.py` (the
   Braintrust runner, which previously could NOT chunk) gains
   `--chunked/--chunk-chars/--chunk-overlap`, a dry-run truncation-confound
   warning when unchunked, and `chunked`/`n_chunks` audit fields on every
   row (`_last_chunked`/`_last_n_chunks` on the specialist).

### The noise floor (the arm's headline measurement)

Same-surface identical-prompt reruns (seed 42, 50 docs, chunked 90k/8k,
qwen3.7-flash, temp 0.1):

| Run | overall | ko mean | term_length |
|---|---|---|---|
| v26 | 0.8780 | 0.7606 | 0.814 |
| v28 (run 1) | 0.9228 | 0.8747 | 0.854 |
| **v28 (run 2, identical)** | **0.8935** | **0.8293** | **0.777** |
| v29 | 0.8964 | 0.8062 | 0.807 |
| v30 | 0.8847 | 0.8068 | 0.790 |

Paired bootstrap (per-doc overall, 2000 resamples, seed 42): v28-rerun vs
v28-run1 −0.0293 CI [−0.0514, −0.0109]; v29 vs v28 −0.0264 CI [−0.0570,
−0.0020]; v30 vs v28 −0.0382 CI [−0.0814, −0.0052]; **v28 vs v26 +0.0448
CI [+0.0087, +0.0891] P(Δ≤0)=0.004 (re-validated)**.

### Interpretation

1. The champion result (v28 > v26) is stable and far outside the noise
   band; the follow-up candidates (v29, v30) are inside the identical-prompt
   band — statistically indistinguishable from re-running v28. They ship
   as logic repairs (contradiction fix + quoting-discipline fix), labeled
   unmeasured; they do not displace v28.
2. The ±0.03 surface noise is the practical resolution limit of single-run
   50-doc A/Bs at temp 0.1. Future micro-rules need either temperature 0,
   multi-run averages, or a larger surface — or they must be accepted as
   logic repairs without a claimed win.
3. The rule-contradiction class (`rule_contradiction`) is now in the
   taxonomy: v28's criterion vs the v10 re-scan note was invisible to
   scores (1 doc) but is a real logic defect; the contradiction check is
   now part of every mutation (prompt-engineer Phase 3 step 6).

*Sources:* `reports/experiment_log.jsonl` —
`qwen3.7-flash_contracts_specialist_{v26,v28,v28_run2,v29,v30}_extraction_langfuse_50*`;
per-span sim-matrix diffs vs `build_expected_fields` GT (CUAD_v1.json);
`src/prompts.py` CONTRACTS_SPECIALIST_PROMPT_V29/V30 banners.

## What questions or uncertainties remain?

- v29's CoC carve-out and v30's chunk-quoting rule are unmeasured below the
  noise band. A temperature-0 rerun series (3× per version, averaged) would
  resolve whether either moves the composite by >1pp — a follow-up arm if
  the release needs it.
- The v26-vs-v28 gap (0.8780 vs 0.9228) is itself a single-draw estimate:
  the true champion margin is somewhere in [+0.009, +0.089]; a second v26
  rerun would tighten it.
- Whether temp 0.1 should become temp 0 for A/B surfaces (sorter v9 arm
  used medium reasoning; extraction has never tested temp 0) is an open
  protocol question.
