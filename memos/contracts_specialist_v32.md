# Contracts Specialist v32 — effective_date rule_contradiction repair (full-corpus diagnosis)

**Research question:** The full-corpus 509-doc extraction runs (v28@510 0.8631 /
v31@510 0.8737) leave `effective_date` at 0.8577 — one of the weakest fields, with
**51/509 docs (10%) scoring 0.0**. Many of those misses are NOT boundary noise: the
model's own reasoning trace quotes the right date and then either suppresses it to
null or emits a different date. Is there a prompt rule that actively contradicts the
ground-truth convention, and what does a corrected rule recover on the full corpus?

**Companions:** KANBAN-029 (this arm); memo `contracts_specialist_v31.md`
(v31 champion, full-corpus A/B); memo `contracts_specialist_v30.md` (noise floor
±0.03 @ 50 docs). GT source: `build_expected_fields` (CUAD clause labels,
`answers[0]` = Agreement Date when both Agreement Date and Effective Date are
labeled) + `score_date_field` (containment / partial-credit / null-template path).

## Answer, Response, + Summary of Results

**Short answer: yes — a rule_contradiction.** The v12-era field rule says
"when both appear, output the date the agreement takes effect per its own
definition (the defined term wins)." But the CUAD ground truth maps BOTH
"Agreement Date" and "Effective Date" onto this field and holds the
**Agreement/execution date as `answers[0]` in 493/493 docs** (verified on the
full corpus: when both dates are labeled, GT = the Agreement Date answer every
time). So on the **26 docs where the two dates differ**, the prompt tells the
model to emit the defined Effective Date and the GT holds the Agreement Date →
6 score 0.0 and 14 partial (Monsanto AG 2017-08-31/EF 1998-09-30, IMAGEWARE
1994-01-31/1993-12-10, PACIRA 2009-10-15/2007-08-10, ArcGroup 2017-11-27/2018-04-01,
UnionDental, NETGEAR, …). A second linked facet: when the model cannot resolve a
clean defined term it leaves the field **null even though an execution date is
stated** (GULFSOUTH reasoning quotes "executed as of the 14th day of December,
1997" → null; XYBERNAUT "May 1, 2002" → null; ADMA "22 Dec. 2017" → null;
Neoforma "November 19, 1999" → null) — 23 null-when-date-present docs.

**The corrected rule recovers an estimated +0.004 to +0.0142 composite** on the
510-doc surface. **Ceiling simulation: `effective_date` field score 0.8224 →
0.9363 = +0.1139 field points ÷ 8 scored fields = +0.0142 composite** — measured
against the champion's ±0.011 noise band (v31 CI [0.8625, 0.8852], half-width
0.0113), so the ceiling sits just OUTSIDE the band and a full-510 A/B can resolve
it. Tie-break flip alone is +0.004 (measured on the 26 differing-date docs, all
26 Agreement Dates verified verbatim-present in the doc text so the rule CAN
fire); the null-when-date-present facet adds ~+0.005. A conservative realized
ceiling from the actual v31 baseline (effective_date 0.8577 → 0.9363 = +0.0786 ÷
8 ≈ +0.0098) is also outside the band. The 50-doc and sample5 surfaces hold ZERO
of the 26 differing-date docs, so the A/B must run on the full 510 surface.

### The candidate frontier (Phase 0/5 — what v32 must beat or complement)

| Frontier cell | Version | Surface (identity) | Score | Role |
|---|---|---|---|---|
| Overall + cost champion | `contracts_specialist_v31` | 510-doc chunked full corpus (fp …, seed 42, temp 0.1) | 0.8737 (CI [0.8625, 0.8852]) | release champion; leanest prompt (−5.7% system tokens) |
| Prior champion (superseded) | `contracts_specialist_v28` | 510-doc chunked, same identity | 0.8622 | replaced by v31 (+0.0116, P=0.021) |
| 50-doc re-baseline reference | `contracts_specialist_v28` | 50-doc chunked, seed 42 | 0.9228 | NOT comparable — overstates the champion ~6pp |
| Unmeasured logic repairs | `v29`, `v30` | 50-doc chunked | inside band | CoC-definition carve-out, chunk-mode scalar quoting |
| **Candidate in flight** | `contracts_specialist_v32` | 510-doc chunked full (reserved) | — | effective_date rule_contradiction repair — this card |

### The failure cluster (from the v31@510 reasoning-trace corpus)

| sub-mechanism | docs | model reasoning evidence | mechanism |
|---|---|---|---|
| tie-break wrong-date | 26 | Monsanto emits EF 1998-09-30; GT AG 2017-08-31 | `rule_contradiction` — "defined term wins" vs GT `answers[0]` = Agreement Date |
| null-when-date-present | 23 | GULFSOUTH quotes "executed as of the 14th day of December, 1997" → null | `under_extraction` — same rule's over-preference for a "defined term" suppresses the execution date |
| blank-template fabrication | 11 | "April __, 2005" → 2005-04-04 | `hallucination` — invents a day for a blank template (banked for v33) |

The dominant, single root cause: **the effective_date rule's tie-break
contradicts the scorer's GT convention.** The fix is one field-rule rewrite.

### The counterfactual (26 differing-date docs, same surface)

All 26 differing-date docs carry the Agreement Date verbatim in the document
(verified 26/26). Emitting the Agreement Date instead of the defined Effective
Date moves 6 docs 0.0→1.0 and 14 docs 0.33/0.67→1.0 = +11.64 field points
≈ +0.004 composite (tie-break only). The null-when-date-present facet adds
the recovered execution dates on 23 more docs ≈ +0.005. Blank-template null
(a separate, smaller lesson) is banked for v33.

*Sources:* `reports/experiment_log.jsonl` v31@510 record
(`qwen3.7-flash_contracts_specialist_v31_extraction_langfuse_510_full`),
per-row `field_scores`/`predicted.reasoning.entries`, CUAD clause labels from
`mailroom-cuad-contracts-full` (509 rows), `src/cuad_ground_truth.py`
(`build_expected_fields`), `src/field_scoring.py` (`score_date_field`).

## What questions or uncertainties remain?

- **Realized vs ceiling:** the +0.010-0.014 estimate assumes the model reliably
  follows the corrected rule; the A/B on the full 510 surface (with the v31
  champion as control and the v31 CI [0.8625, 0.8852] as the noise band) is the
  measurement.
- **Noise floor:** the 510-surface identical-prompt band has not been separately
  re-run; the v31 CI (half-width ±0.011) is the closest control available. The
  noise-floor control `qwen3.7-flash_contracts_specialist_v31_extraction_langfuse_510_rerun`
  (identical-prompt rerun, same manifest/identity) is reserved alongside the v32
  candidate so the v32 delta is interpreted against a proper band, not just the
  CI. A candidate delta inside that band ships as an unmeasured logic repair.
- **Banked lessons:** blank-template fabrication (11 docs → null, never invent a
  day) is a distinct, smaller lesson reserved for v33; the under-extraction nulls
  that the tie-break fix does not reach are part of the same family and get
  re-checked after the v32 A/B.
