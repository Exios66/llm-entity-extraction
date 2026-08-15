# 10 — Problems: contracts-specialist prompt iterations

---

## The question

The specialist extracts nine fields from each contract; the iterations
v15→v26 chased *"why does the model miss these spans?"* and, later,
*"why can't we MEASURE its near-misses?"*. This deck catalogs the
problems; [11-fixes-contracts-specialist](11-fixes-contracts-specialist.md)
documents what fixed each.

---

## 1. Scope ambiguity — which clauses even count?

`key_obligations` is scoped to the CUAD restriction/covenant families, but
the early prompt carried a terse 26-family list that did not match the
41-category catalog the ground truth samples. General operative duties
(delivery mechanics, staffing, routine payments, warranties, pure
indemnification) are NOT expected items — but family clauses buried inside
indemnity/damages sections ARE.

**Measured effect:** 160 ground-truth spans unmatched at token level on
the 50-doc series; the miss table by family — license grant 40, minimum
commitment 12, IP ownership 10, anti-assignment 9, audit 6, revenue
sharing 6, cap liability 5 — motivated the family-fidelity catalog.

## 2. Boundary/grain divergence at token level

The model matched the SUBSTANCE but not the SPAN: ground-truth items are
atomic fragments (~10–25 words); an item much longer dilutes similarity
below the match threshold, an item much shorter cannot reach it. The
diagnostics chain (v15→v18) empirically **refuted the containment
hypothesis — 0/160 unmatched spans were embedded inside longer predicted
items**: the residual was scope (which families), not segmentation.
*(Later finding, v27 diagnostic 2026-08-15: the "10–25-word GT grain"
claim itself is being re-examined — measured GT spans run 21–84 words
median and correlate ~0 with score; the working hypothesis shifted from
grain to SENTENCE CHOICE inside multi-requirement family sections.)*

## 3. Over-extraction and duplication

- 225 near-duplicate items in v18 (sentence PLUS its own fragment = two
  items; overlapping wording double-counted).
- Textbook over-extraction case (the pilot block): 43 predicted vs 18
  expected spans → span-count drift +10.5, raw precision 0.31 — the model
  invented or split spans, which a recall-only view never shows.

## 4. Abbreviation and over-deduping (the v21→v22 loss)

The v21 span-level audit found **38 v18-matched GT spans lost**:
(1) ellipsis abbreviation — 23.6% of v21 items contain "...", vs 15.8% in
v18 — a truncated quote cannot match its span; (2) over-deduplication —
LegacyEducation fell 19 → 12 items as records, insurance, sell-off and
assignment-exception clauses were dropped as "duplicates".

## 5. Long documents: truncation and chunking

Contracts up to 335k chars (median 33k) exceed any single-call budget.
Head-only truncation loses the MIDDLE — exactly where obligation families
concentrate; and a truncated JSON (max_tokens overrun) zeroes the row.
The 50+ verbatim clauses of dense agreements exceed a 16k-token output
budget.

## 6. The reasoning confound (prompt vs setting)

v19's +3.0pp ko gain was initially credited to the worked examples — it
was actually the **reasoning_effort=max** setting (2.6× cost) plus a
1/50 parse-error row (Ediets EX-10.4 — max reasoning overran the 32k
structured-output budget). At fixed reasoning=none, v19/v20 content
scored ko 0.8385 vs v18's 0.8535: the prompt was neutral-to-worse; the
SETTING carried the gain. The extractor now defaults to
reasoning_effort=none — thinking models burn the whole token budget on
reasoning otherwise.

## 7. Scorer-side problems the iterations surfaced

- **Null-expectation dates:** blank-template/label-only expected dates
  ("_____ day of ________, 19____", "Effective Date:") held no real date,
  yet a null prediction scored 0.0 — and the guard fired on parseable
  compact dates ("11/4/10") scoring three PERFECT matches 0.0.
- **Partial-GT party labels:** role labels ("Consultant", "Member",
  '"we," "us," or "our"') were never instantiated even when the name was
  extracted — 3 of 4 zero-parties docs in v19.
- **document_name** full-token containment was not scored as a match
  (0.960 → 0.991 after the fix).

## 8. Self-inflicted: v24's leading-phrase rule (containment)

The v24 metrics-aligned format discipline told `term_length` to LEAD with
the canonical duration phrase ("two (2) years"). The model **replaced**
the clause opener with the phrase — and the CUAD ground-truth span for
Ediets IS the opener ("This Agreement will become effective as of the
Effective Date and, unless sooner terminated pursuant to Sections 3.1"):
containment **1.0 → 0.3333**. The format fix broke the very score it was
meant to serve.

## 9. Self-inflicted: v25's template leakage

v25's additive-prefix wording plus a VERBATIM worked example recovered
Ediets (containment 1.0) — but the model then copied the example's
sentence template into OTHER documents with different openers
(Ritter "The initial term of this Agreement shall commence...", Phasebio
"The term of this Agreement (the "Term") will commence..."): containment
0.7059 / 0.2222. A worked example with full clause text is a leakage
vector.

## 10. Unparseable output vs the new regression diagnostics

The new MAE/R² metrics can only count pairs where BOTH sides parse.
Prose dates, duration language buried in riders, and money amounts nested
inside prose sentences produce no pairs — the diagnostics report the
support size (`date_n_pairs` etc.) and it is often small.

## 11. No reasoning trace

The extractor returned values with no per-field evidence: when a run
failed, there was no trace of WHY the model picked a span — no
failure-insight material comparable to the sorter's.

---

## The lesson

The specialist's problems came in three waves: **scope** (which families,
which grain — v15→v19), **fidelity** (verbatim completeness, dedupe
discipline, field formats — v20→v23), and **traceability** (reasoning +
metrics-aligned formats — v24+). Two of the hardest problems were
self-inflicted by prompt rules (v24, v25) and were only caught because the
A/B surface was identical and small enough to diff per document.

*Next: [11-fixes-contracts-specialist](11-fixes-contracts-specialist.md).*
