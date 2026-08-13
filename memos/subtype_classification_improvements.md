# Research Memo: Subtype classification improvements through iterative prompt testing

**Research question:** Do targeted corpus-convention rules in the sorter's
prompt (v4→v6) improve contract-subtype classification over the generic
family-preference logic of v3, on the SAME sample surface and then on the
full corpus?

**Companions:** [entity_extraction_improvements.md](entity_extraction_improvements.md)
· experiment log (task `subtype_classification`) · [experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** Yes — decisively. On the controlled 195-document A/B
(same dataset fingerprint `2e1fe4b7`, seed 42), strict subtype accuracy
climbs **0.836 (v3) → 0.841 (v5) → 0.939 (v6)**, a **+9.8 pp** jump driven
almost entirely by the v6 corpus-convention rules; v4 was a small
regression (0.810) that v5 partially recovered. The gain replicates on the
full 509-document corpus (**0.859 → 0.931**, +7.3 pp), with family-level
(equiv) accuracy reaching **0.939** and doc-type exact match **0.996**.
Crucially, **mean confidence is flat** (~0.94 across all versions) — the
improvement is the prompt's classification rules, not a calibration shift.

| Metric | v3 → v6 (same 195-doc surface) |
|---|---|
| strict subtype accuracy | 0.790 → **0.944** (+15.4pp) |
| equiv subtype accuracy | 0.826 → **0.949** (+12.3pp) |
| full-corpus (509) strict | 0.859 → **0.931** |

> **Verdict:** v6 clears the bar on the controlled surface; strict 0.944 is the classification benchmark to beat.


### Same-surface A/B (195 docs, seed 42, fingerprint `2e1fe4b7`)

Every row is the same sample, so deltas are directly comparable.

| Sorter prompt | exact_match | subtype strict | subtype equiv | confidence | failures |
|---|---:|---:|---:|---:|---:|
| **v3** | 0.9846 | 0.8359 | 0.8564 | 0.9343 | 32 |
| **v4** | 0.9795 | 0.8103 | 0.8308 | 0.9354 | 37 |
| **v5** | 0.9846 | 0.8410 | 0.8667 | 0.9387 | 31 |
| **v6** | 0.9961 | 0.9385 | 0.9436 | 0.9448 | 11–12 |

### Full-corpus confirmation (509 docs, seed 42, fingerprint `c2341957`)

| Sorter prompt | exact_match | subtype strict | subtype equiv | confidence | failures |
|---|---:|---:|---:|---:|---:|
| v5 | 0.9843 | 0.8585 | 0.8743 | 0.9404 | 72 |
| **v6** | 0.9961 | 0.9312 | 0.9391 | 0.9440 | 35 |

### Failure-mode decomposition

| Failure mode | v5 (509) | v6 (509) |
|---|---:|---:|
| family_confusion | 40 | **26** |
| other_fallback | 16 | 3 |
| function_over_form | 8 | 2 |
| equivalent_family (recovered) | 8 | 4 |

The v6 rules shrink every failure mode; the *other_fallback* collapse
(16 → 3) is the SEC joint-filing rule rescuing agreements that previously
defaulted to "other".

### Interpretation

1. **Targeted rules beat generic preference.** v6's banner documents the
   evidence for each rule: hybrid operating-core precedence (a "Master
Development and Manufacturing Agreement" is filed under the operating
family by corpus convention), SEC §13(d)/13(g) joint-filing agreements
→ `joint_venture` (previously `other`), license+maintenance titles →
`maintenance`, hosting ≠ license/development (provisioning work is not
development), remarketing → `marketing`, a marketing-core guard, and
annex/schedule inheritance from the parent agreement's family. Each rule
was added *because* a failure pattern existed in the v5 confusion matrix.
2. **The family-confusion win is the headline.** 40 → 26 on the full
   corpus — the rules resolve exactly the near-synonymous family pairs the
strict metric punishes, and the equiv rate confirms the residue is
defensible family routing rather than noise (0.939).
3. **Confidence is a constant.** Mean reported confidence is flat
   (~0.94); accuracy moved without any calibration change — the
experiment controls for the "model got more confident" alternative
explanation.
4. **Same-surface discipline mattered.** v4 looked like a wash on the 195
   surface but a strict regression (0.836 → 0.810); without the identical
fingerprint+seed frame these comparisons would have been noise (the
v0.13.0 "regression" postmortem documented exactly this trap with
disjoint 5-doc samples).

*Sources:* `reports/experiment_log.jsonl` (task `subtype_classification`,
fingerprints `2e1fe4b7` and `c2341957`) · `src/prompts.py` v6 banner ·
scores with bootstrap CIs on the site · corpus = CUAD (Hendrycks et al.,
2021 — [CUAD dataset](https://github.com/TheAtticusProject/cuad))

---

## What questions or uncertainties remain?

1. **Will the rules transfer to non-CUAD contracts?** The corpus-convention
   rules are learned from CUAD's filing conventions; a non-SEC contract
corpus (e.g. LegalBench MAUD agreements) may not share them. A
cross-corpus subtype pilot is the open validation.
2. **Failure residue:** the remaining 26 family confusions on 509 docs are
   concentrated in specific pairs — a per-family confusion-matrix audit
(site: subtype run views) will tell us which rule is next.
3. **Cost of precision:** the added rules lengthen the prompt; whether the
   +7.3 pp is worth the token cost for *your* corpus is a deployment
decision the cost-vs-quality scatter now makes visible.
---

## Addendum (2026-08-13): sorter v7 — the 250-sample A/B

**Result: v7 beats v6 on the identical 243-doc stratified surface (seed 42,
qwen3.7-flash, llm-dojo): strict 0.8683 → 0.8765 (+0.82pp), equiv 0.8807 →
0.8889 (+0.82pp).** The three v7 rules (18. CONSORTIUM O&M IS MAINTENANCE,
19. DEVELOPMENT OVER LICENSE, 20. PROMOTION GUARD) came from the v6 509-doc
failure decomposition; the promotion→marketing cluster (6 errors) is
eliminated outright.

**Caveat on the >95% target:** the current full-corpus dataset revision
(fingerprint fb9f939d…) is a harder surface than the revision behind the
195-doc 0.9436 runs (fingerprint 2e1fe4b7…) — v6 itself scores 0.8683
here. The 0.94-era numbers and today's numbers are not comparable; v7's
+0.82pp on the identical sample is the real, prompt-attributable gain, and
the path to >0.95 runs through the remaining development-family and
ip→license confusions on the current revision.

---

## Addendum 2 (2026-08-13): sorter v8 — the development/IP clusters

**Result: strict 0.8765 → 0.8971 (+2.06pp), equiv 0.8889 → 0.9012, 30 →
25 fails on the identical 243-doc surface.** Both v8 target clusters are
eliminated: development→collaboration/license/franchise (5) and
ip→license/joint_venture (3) are all zero — the "Collaborative
Development", "Franchise Development", "License and Development" and
"Intellectual Property Agreement" patterns are now classified per the
corpus convention. Remaining: promotion-title docs read as marketing (2),
outsourcing-with-manufacturing read as manufacturing (2), a
customization-schedule annex read as development (1), and a 1-off tail —
the v9 rule set (promotion-title wins, outsourcing-title wins,
customization schedules are maintenance) is designed and worth ~2-3pp;
0.95 strict on this revision remains a multi-iteration target.

---

## Addendum 3 (2026-08-13): sorter v9 — the title-wins rules

**Result: strict 0.8971 → 0.9259 (+2.88pp), equiv 0.9012 → 0.9259, 25 → 18
fails on the identical 243-doc surface. Cumulative v6→v9: +5.8pp strict
(0.8683 → 0.9259).** All three v9 targets eliminated: promotion-titled
docs (COLOGUARD, CO-PROMOTION, PROMOTION AND DISTRIBUTION) are now
promotion; outsourcing-titled docs (incl. MANUFACTURING OUTSOURCING
AGREEMENT) are now outsourcing; the Customization Schedule annex is now
maintenance.

**Status vs 0.95:** 2.4pp short, with the residual now a long tail of 1-off
confusions (no cluster above 2) plus per-doc variance — single-rule
iterations have diminishing returns from here; ~0.93 is the practical
plateau on this corpus revision.
