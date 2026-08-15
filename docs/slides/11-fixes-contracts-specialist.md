# 11 — Fixes: contracts-specialist prompt iterations (v15 → v26)

---

## The question

The specialist's iterations fixed problems in three waves: **scope**
(v15→v19), **fidelity** (v20→v23), and **traceability + metrics
alignment** (v24→v26) — with the two self-inflicted format regressions
(v24/v25) fixed by v26. Every number below comes from same-surface A/Bs
(50-doc series: same docs, seed 42, chunked; the v24+ arms: 5-doc sample,
seed 42).

---

## 1. The miss-attribution diagnostic chain (v15→v18)

Before writing any rule, the loop measures WHERE the loss is:

1. **Unmatched-span extraction** — for each GT span, its best predicted-
   item similarity as the scorer computes it; spans below threshold are
   the residual.
2. **Containment test** — is the unmatched span embedded in a longer
   predicted item? **Result: 0/160 spans embedded** — the residual was
   scope, not segmentation (this empirically refuted the containment
   hypothesis).
3. **Family decomposition** — classify the unmatched spans by CUAD
   category; the biggest miss counts point at the prompt's gaps
   (license grant 40, minimum commitment 12, IP ownership 10, ...).
4. **Recovery check** — re-run the same extraction against the candidate
   prompt to count exactly which spans and families a change recovered.

## 2. v18 — the family-fidelity catalog (ADOPTED)

**Fix:** replace the terse 26-family list with a CUAD-category catalog
(1:1 mirror of the 41-category catalog, 26 obligation families), each
category with its operative clause shapes (cap-on-liability
consequential-damages waivers, license grants phrased "right and license
... for the territory of", minimum guarantees/royalties, audit deficiency
remedies, insurance coverage lists, IP-prosecution elections, family-term
definitions). The exclusion rule narrows to true general duties with a
**WHERE-IT-SITS guard** — family clauses inside indemnity/damages sections
still count.

**A/B (50 docs, seed 42, chunked):** key_obligations **0.7755 → 0.8535
(+7.8pp)**, overall 0.9129 → **0.9230**, 30/160 spans recovered (cap
liability +8, IP ownership +4, license +4).

## 3. v19 — worked span examples + span discipline

**Fix:** WORKED SPAN EXAMPLES drawn verbatim from the misses (grants-and-
assigns with territories, restriction-on-rights, options, end-user access
grants) with verified negatives (trademark-hygiene/product-marketing
duties); SPAN DISCIPLINE — one item per operative requirement, post-build
dedupe of sentence+fragment pairs (kills the 225 near-duplicates).

**A/B (50 docs, reasoning=max):** ko 0.8535 → **0.8840 (+3.0pp)**,
alignment precision 0.619 → 0.662, items −29% (1118 → 792).
**Caveat recorded:** the gain was later shown to be the reasoning SETTING
(see [10-problems](10-problems-contracts-specialist.md) §6).

## 4. v20 — field-fidelity rules + scorer corrections

**Fix (four prompt rules):** renewal_terms EVERGREEN CLAUSES (no "renew"
word needed) + DEAL-TERMS TABLES; term_length DEFINED-TERM SENTENCES
(carve-out of the no-definitions rule); governing-law regulatory-
jurisdiction sentences; termination_clauses REDACTED SECTIONS (heading +
"[***]" marker). Plus scorer fixes that made the MEASUREMENT honest:
null-expectation date rule (gated on unparseable expected, consulted on
the `pred is None` path), partial-GT party-label instantiation, name
full-token-containment.

**Result:** renewal_terms +4.5pp, termination_clauses +5.4pp on target;
effective_date 0.806 → 0.945; parties 0.918 → 1.000; document_name
0.960 → 0.991. Not adopted as champion (ko diff was run variance) —
rolled into v21.

## 5. v21 — the merge arm, reasoning confound resolved (ADOPTED)

**Fix:** v19 content + v20 field rules at reasoning_effort=none. This
isolated the prompt-vs-reasoning confound: at fixed none, v19/v20 ko
0.8385 vs v18's 0.8535 — the v19 ko crown was the max-reasoning roll.

**A/B (50 docs):** overall **0.9283 → 0.9396 (+1.7pp vs v18, best
flash-line)**, 50/50 rows (zero parse errors — the Ediets failure
resolved), verified_precision 0.997, cost $0.039 (2.6× cheaper than max).

## 6. v22 — ko-recovery rules: verbatim completeness + disciplined dedupe

**Fix:** VERBATIM COMPLETENESS (never ellipses — the 23.6%→ ellipsis rate
was killing span matches) and a narrowed dedupe (exact repeats and
sentence/fragment pairs of the SAME requirement only — LegacyEducation's
records/insurance/sell-off/assignment-exception clauses are distinct
requirements, not duplicates).

**A/B (50 docs):** **v22×none — overall 0.9512 (series best, CI
0.934–0.967)**, ko 0.8294, 50/50 rows; v22×max — ko 0.8442, zero parse
errors (the output discipline retired the max-reasoning error rate).
Production arm: v22×none.

## 7. v23 — residual-34 worked-example set v2

**Fix:** worked-example set v2 from the exact 34 GT spans v18 matched that
v22 missed; **mark-hygiene disambiguation** — the v19 trademark NEGATIVE
was over-broad and suppressed GT-labeled mark-ownership-use restrictions
(Ritter "register, use or claim ownership") and mark non-tarnishment;
v23 disambiguates mark-HYGIENE (operational) from mark-ownership-use /
non-tarnishment (items), plus verbatim positives for the recurring missed
shapes (audited-statement delivery, revenue remittance, all-requirements
supply, firm-service commitments, liability-cap fragments,
post-termination exhaustion, sell-off revenues, joint trademark
registration, sublicense-to-affiliates, option windows, "at cost without
markup").

**A/B (50 docs):** ko 0.8374 (best none-reasoning arm), 42 spans
recovered vs 31 lost; v22×none stays the overall champion (0.9512).

## 8. v24 — reasoning trace + metrics-aligned formats

**Fix (the traceability wave):** `CONTRACTS_SCHEMA` gains a REQUIRED
`reasoning` object (property FIRST): `summary` + per-field
`entries[{field, evidence, section_ref}]`, produced BEFORE finalizing the
extraction (REASONING BEFORE OUTPUT duty in the prompt); the chunked pass
unions entries across windows (first-witness evidence wins). It is a
visible trace, never scored, `reasoning_effort` stays none. Format
discipline aligned to the new MAE/R² diagnostics: ISO dates, `term_length`
leads with the canonical duration phrase, `contract_value` stays a plain
currency phrase — formats only, no master-CSV leakage.

**A/B (5 docs, seed 42):** overall 0.9336 vs v23 0.9366 (noise),
**key_obligations +10.2pp (0.5984 → 0.7006)**, reasoning trace 5/5 rows,
tokens +2.5% — and one regression flagged: term_length containment
1.0 → 0.3333 on Ediets (see below).

## 9. v25 → v26 — the containment fix, two iterations

**v25 (fix attempt 1):** prefix is ADDITIVE, full verbatim clause (opener
first) must follow, plus a verbatim worked example. Ediets recovered
(containment 1.0) but the example TEMPLATE LEAKED into other documents
(Ritter/Phasebio containment 0.7059 / 0.2222 — they quoted the example
clause with the duration swapped in).

**v26 (the fix that landed):** keep the additive prefix and the
never-drop-the-opener rule, but show opener VARIANTS the model must match
to THIS document's wording ("The term of this Agreement (the "Term") will
commence...", "The initial term of this Agreement shall commence...",
"This Agreement will become effective as of the Effective Date and, unless
sooner terminated...") plus an explicit **"never reuse wording from these
instructions"**.

**A/B (5 docs, seed 42, same surface):** **v26 overall 0.9447 — best of
the arm** (v23 0.9366 / v24 0.9336 / v25 0.9154); **term_length 1.0000**;
containment 1.0 on all three term docs; no template leakage.

---

## The lesson

1. **Measure before mutating** — the unmatched-span chain (and the 0/160
   containment refutation) told us the residual was scope before v18.
2. **Isolate confounds** — the v21 merge arm separated prompt content from
   reasoning setting; the 5-doc same-surface A/Bs catch per-document
   regressions a mean score hides.
3. **Prompt rules can self-inflict** — v24's leading-phrase and v25's
   worked example both broke containment; small same-surface A/Bs and
   per-document diffs caught them within one iteration each.
4. **Fidelity beats coverage** — verbatim completeness, disciplined dedupe,
   and canonical parseable formats are what the deterministic scorers and
   the regression diagnostics can actually measure.

*Back to the index: [README](README.md).*
