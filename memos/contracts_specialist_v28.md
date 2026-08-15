# Contracts Specialist v27/v28 — the multi-item family-section rule

**Research question:** Why does `key_obligations` plateau ~0.76–0.83 on the
50-doc chunked surface while every other field scores ≥0.85 — and which
surgical prompt rule closes the gap without regressing the champion (v26)?

**Companions:** KANBAN-004 (issue #3, closed); KANBAN-017 (v26 term_length
arm, the champion base); `V16_PROPOSITION.md` §14.3/§15.1 (the 30-span
residual); memo `contracts_specialist_v23.md` (worked-example arm).

## Answer, Response, + Summary of Results

**Short answer:** The residual is not boundary-shift or abbreviation — it is
**wrong-span at sentence level inside multi-requirement family sections**:
the model quotes ONE sentence per section while the ground truth holds 3–10
distinct requirement sentences from that same section. A single rule — "a
family section is MULTI-ITEM; each distinct requirement sentence is its own
item" (v27), sharpened in v28 with a definitions-are-never-items criterion
and an additive-only re-scan — wins **+4.48pp overall (0.8780→0.9228,
bootstrap 95% CI [+0.0094, +0.0907], P(Δ≤0)=0.004)** on the same-surface
50-doc chunked A/B, with key_obligations +11.4pp (0.7606→0.8747; 20
recovered vs 4 regressed docs).

### Diagnosis (all runs reviewed: v19–v26 sample5 + v22/v23 50-doc + ko arms)

1. **The miss mechanism, quantified.** For every doc in both surfaces I
   computed the pairwise similarity matrix (Hungarian-threshold ≥0.6,
   `src.field_scoring._element_similarity`, free_text) between predicted
   key_obligations items and the GT spans from `build_expected_fields`.
   ~60–70% of misses are **NEAR (sim 0.35–0.59)**: the model found the
   family SECTION but quoted the wrong sentence of it.
   - Ritter: emitted "procure and maintain insurance" but not
     "The Insurance shall be primary for all purposes…" nor the
     additional-insured sentence (Insurance GT n=7); the audit section's
     10 GT spans → ~0 emitted; price-formula (Revenue/Profit Sharing)
     replaced by the exclusivity sentence.
   - Buffalo (franchise): ROFR/insurance/license/minimum-commitment
     near-misses — the doc's GT spans 19 with median 44 words.
   - HPIL: the "sole and exclusive remedy… limited to" cap-on-liability
     clause was NEVER emitted (0.5 across v22/v23@50 and v24–v26).
   - NOVO (JV), Goosehead (franchise, 8 near-misses), Penntex: same shape.
2. **The grain myth.** The prompt asserted the GT grain is 10–25 words; the
   actual GT spans have median length 21–84 words. But median span length is
   uncorrelated with score (r = −0.023): the driver is sentence CHOICE, not
   length.
3. **The truncation confound.** The historical sample5 A/B surface ran
   `chunked=false`; Phasebio collapses to 0.125 there vs 0.94 chunked — the
   pilot surface is unusable for key_obligations. All A/Bs in this arm were
   re-run chunked (`--chunked`, 90k windows, 8k overlap).
4. **v23's lesson.** Worked examples fixed Midwest (0.143→1.0, cap fragment)
   but the residual shape is structural — examples add shapes, not the
   enumeration discipline.

### The mutation (two versions, one rule)

- **v27** = v26 + "A FAMILY SECTION IS MULTI-ITEM: … EACH distinct
  requirement sentence is its own item … NEVER collapse a section into its
  first or most prominent sentence" (with the concrete high-miss sections
  named: insurance, audit/records, license, option/ROFR, exclusivity,
  non-compete, liability, assignment).
- **v28** = v27 + the two trace lessons from v27's A/B: (1) a requirement
  sentence is OPERATIVE language (shall/will/may not/consent/entitled);
  definitional sentences ("X means…", "any X Property or improvements
  thereto which are used…") are NEVER items — v27's Cardax run emitted
  definitional IP fragments and dropped the royalty/merger-assignment
  spans; (2) the completion re-scan only ADDS items, never removes or
  replaces — v27's "go back and emit" shifted attention off other families
  (Ritter dropped mark-ownership + liquidated damages).

### Evidence (same-surface identity: seed 42, qwen3.7-flash, chunked 90k/8k,
current scorer, identical dataset fingerprint)

| Surface | v26 | v27 | v28 |
|---|---|---|---|
| sample5 chunked overall | 0.8944 | 0.9535 | **0.9837** |
| sample5 chunked ko mean | 0.790 | 0.832 | **0.893** |
| 50-doc chunked overall | 0.8780 | — | **0.9228** |
| 50-doc chunked ko mean | 0.7606 | — | **0.8747** |

50-doc A/B detail: per-doc overall 22 wins / 8 losses; ko 20 recovered vs 4
regressed (regressions are single-span losses on docs v26 already scored
≥0.85 — Ediets −0.15, LegacyTechnology −0.14, LinkPlus −0.14, Innerscope
−0.10 — no new family pattern). term_length 0.814→0.854; document_name /
effective_date / governing_law / parties / termination_clauses equal or
better; renewal_terms −0.042 (n=21, out of rule scope — unresolved). Tokens
+6.7% for +4.48pp — accepted Pareto trade.

### Interpretation

1. The rule fires on the CLUSTER, not the sample: the same near-miss shape
   appears on franchise (Buffalo, Goosehead), pharma distribution (Ritter),
   JV (NOVO), midstream (Penntex), insurance (Goosehead), and licensing
   (ArmstrongFlooring +0.78, Impresse +0.83) docs — 20 recovered across the
   corpus.
2. Two iterations were needed: v27's raw rule over-applied (definitions as
   items, attention shift); v28's operative-language criterion + additive
   re-scan recovered Cardax and stabilized Ritter at scale.
3. The A/B surface discipline matters more than the rule: the unchunked
   sample5 surface is truncation-confounded and noisy (v28 measured 0.9270
   there vs 0.9837 chunked on the same 5 docs). Future specialist arms must
   A/B on the chunked surface.

*Sources:* `reports/experiment_log.jsonl` records
`qwen3.7-flash_contracts_specialist_{v26,v27,v28}_sample5[_chunked]` and
`..._extraction_langfuse_50(_v28ab)`; pairwise sim-matrix analysis vs
`build_expected_fields` GT (CUAD_v1.json); `src/prompts.py`
CONTRACTS_SPECIALIST_PROMPT_V27/V28 banners.

## What questions or uncertainties remain?

- The 4 regressed docs (Ediets, LegacyTechnology, LinkPlus, Innerscope):
  are they sampling noise (±1 span at temp 0.1) or a shared shape? Ediets
  recovered +0.15 in sample5 and regressed −0.15 at 50-doc — evidence of
  noise, but a dedicated per-span diff on those 4 is cheap and should
  precede any further rule.
- renewal_terms −0.042 (0.848→0.806, n=21) is outside the rule's scope;
  needs its own diagnostic (chunk-merge variance vs prompt).
- The chunked v26 term_length collapse in the sample5 chunked pair (0.17
  vs 1.0 unchunked) suggests chunk-mode × term_length interaction worth a
  dedicated arm.
- Gridiron's v23 degenerate `":"` output (1-off) remains unexplained.
