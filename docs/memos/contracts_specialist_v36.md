# contracts_specialist_v36 — full-sentence span-grain reconciliation (KANBAN-056)

**Research question:** v34/v35's one-pass extractor identifies the right clauses but
scores 8% ContractEval recall / 31% key_obligations exact with 67% partial — is the
residual a span-grain instruction failure inside the prompt, and does a
full-clause-sentence quoting rule convert the near-miss cluster into matches?

**Companions:** `memos/contracts_specialist_v34.md` (R1/R2/R3 + KPI tooling),
`memos/contracteval_mapping_benchmark.md` (the verbatim-vs-containment wall),
KANBAN-054/055/056 cards, `scripts/reporting/ab_paired_compare.py`.

## Answer, Response, + Summary of Results

### Short answer

Yes — the dominant failure is a **rule_contradiction inside the prompt**: the v10-era
fragment-grain instructions ("ATOMIC FRAGMENTS … typically 10-25 words", "STRIP
sentence preamble and riders", "a list of a few long merged sentences signals missed
spans: split them") sit beside v34's R3 verbatim rule, and the model follows the
concrete numeric instruction — it quotes the sentence's opening words and drops the
continuation. Under expected-within-predicted containment scoring the GT label IS the
annotator's stored clause sentence, so a fragment can never match. `v36` replaces every
fragment-grain instruction with full-clause-sentence grain (one item per distinct
sentence, quoted verbatim in full), guards `term_length` against duration-only output,
and carves out the effective_date blank-placeholder fabrication. Mutation shipped,
A/B pending.

### The v34/v35 A/B (the substrate)

Surface: 255 docs from `mailroom-cuad-contracts-full` (510), seed 42, chunked 90k/8k
overlap 8k, qwen3.7-flash, temp 0.1, reasoning none, Langfuse llm-dojo (~$0.23/run).

| metric | v34 (champion) | v35 |
|---|---|---|
| overall | **0.8738** (CI [0.8595, 0.8882]) | 0.8670 |
| field_presence | 0.9711 | 0.9709 |
| verified_precision | 0.9904 | 0.9909 |
| KPI F1 / F2 / Jaccard | 0.1331 / 0.0963 / 0.2803 | 0.1408 / 0.1024 / 0.2955 |
| KPI recall / false-nr / laziness | 0.0813 / 0.4775 / 0.8632 | 0.0866 / 0.4437 / 0.8554 |
| semantic verbatim / ge0.7 / ge0.3 | 0.0819 / 0.3879 / 0.7361 | 0.0896 / 0.3980 / 0.7491 |
| term_length (paired mean) | **0.8006** | 0.7580 |
| key_obligations per_field | 0.7612 | 0.7618 |

Paired A/B (identical 255 docs, bootstrap 2000, seed 42): Δ +0.0068 (v34−v35),
CI [−0.0034, +0.0169], P(win) 0.909 → **inside the noise band → LOGIC REPAIR, v34
stays champion**; v34 beats on term_length +0.0523 (CI [0.004, 0.102]); v35's KPI
direction (recall +0.005, laziness −0.008, verbatim +0.8pp) is positive but small.

### Failure diagnosis (sim-matrix over the 255 docs, expected-vs-predicted containment)

`key_obligations` — 1600 expected labels: **MATCH 572 (35.8%) / NEAR 448 (28.0%) /
MISS 580 (36.3%)**. Direction breakdown of the 448 NEAR (token-coverage analysis):

| direction | n | signature |
|---|---|---|
| **TRUNCATION (pred ⊆ GT, ≥70% of pred tokens in GT)** | **146** | item = sentence head; continuation dropped |
| overlap_partial (ellipsis-condensed / mixed) | 265 | "Parent shall... contribute, assign..." style |
| GT barely covered in long item (over-quote/paraphrase) | 37 | restructured long paraphrase |

Evidence (v34 rows): NETGEAR GT `"Distributor shall be the only distributor appointed
by NETGEAR in the Territory, subject to Distributor conducting mutually agreed to
marketing activities as described in..."` vs PRED `"Distributor shall be the only
distributor appointed by NETGEAR in the Territory"` (0.36); VertexEnergy GT
`"It is agreed that only Bunker One will be marketing this JSMA and the JSMA Output
towards various customers, but if a Party receives a Nomination..."` vs PRED
`"only Bunker One will be marketing this JSMA and the JSMA Output towards various
customers"` (0.40); INGEVITY `"Parent shall... contribute, assign, transfer..."` with
literal "..." ellipses in the predicted item. The CORALGOLD row shows the family-level
tail: 5 GT labels (post-term covenant, Change-of-Control termination, anti-assignment,
stock-option treatment, termination-at-any-time) vs 1 predicted item — R2's checklist
did not force a re-scan on sparse-family docs.

`term_length` — 208 expectations: MATCH 187 / NEAR 5 / **MISS 16**, all duration-only
outputs (`"two (2) years"` alone — AllisonTransmission, Webmd, BerkshireHills, v34
rows) or wrong-clause picks. The v35 run's paired term_length regression (0.7580 vs
0.8006) is the same condensing habit shifting quote lengths.

`effective_date` — 250 expectations: MATCH 207 / MISS 41 (16 at score 0.0). Of the 16
zero rows: **5 fabricated fills of blank template dates** (GT `"April __, 2005"` → PRED
`2005-04-01`; the scorer's `_date_expected_is_null` satisfies a blank with null = 1.0,
a guessed fill = 0.0), 8 null-despite-real-date (defensible in part — `"[•], 2020"`
is unscoreable either way), 3 wrong-date picks. Only the blank-fill cluster is
prompt-fixable.

`parties` — 254 expectations: MATCH 214 / MISS 37, dominated by GT defined-term
artifact labels (`"Party A and Party B"`, `"persons and entities listed on Schedule A"`,
`"the Consultant"`) — **NOT rule material** (model's entity extraction is correct;
the labels are reference-form annotations). `contract_value` 0.396 / `renewal_terms`
0.337 diagnostic presence = non-empty rate over ALL 255 docs — a base-rate artifact:
neither field appears in `expected` (CUAD has no contract_value category;
renewal_terms matches 74/79 = 94% on expected docs), so the composite is untouched.
Both flagged, not rule-ified.

### Root cause (one sentence)

The prompt's own fragment-grain instructions contradict R3's verbatim rule
(`rule_contradiction`), and the model resolves it toward the concrete numeric
instruction — truncating clause sentences to 10-25-word heads that can never contain
the GT label under expected-within-predicted containment scoring.

### The mutation — `CONTRACTS_SPECIALIST_PROMPT_V36` (base = v35, 7 surgical edits)

1. **Grain reconciliation (key_obligations):** "ATOMIC FRAGMENTS…10-25 words…STRIP
   preamble and riders…one fragment per right" → "FULL CLAUSE SENTENCES, quoted
   verbatim and in full…the annotator's stored clause SENTENCES…matching is by token
   containment…never a truncated sentence head" with the measured 146/448 stat and the
   Bunker One / Licensee examples inlined. Multi-obligation sentences stay ONE item
   (the full sentence covers every label inside it — the old per-right split is
   removed as another fragment relic).
2. **SPAN-DISCIPLINE completion:** "…exactly once at the 10-25-word span grain" →
   "…at the full-sentence span grain".
3. **R3 trim sentence:** "trim to the operative core at the 10-25-word span grain by
   CUTTING the preamble and riders" → "quote the COMPLETE clause sentence(s) — never
   trim to a core fragment".
4. **SIZE-CALIBRATION:** "a list of a few long merged sentences signals missed spans:
   split them" → "split MERGED MULTI-SENTENCE items at sentence boundaries, never a
   sentence itself".
5. **v35's ITEM-LEVEL CATEGORY GUARD re-cast:** "quote the operative words of that
   duty" → "quote that duty's FULL clause sentence(s) verbatim…the sentence may
   appear once per category tag (dedupe applies only within the same category)" —
   the guard's KPI direction was measured positive (recall 0.0866 vs 0.0813), and the
   re-cast removes its fragment-quoting contradiction with the new grain rule.
6. **term_length duration-only guard:** after the existing "quote the ENTIRE term
   clause verbatim AFTER it" rule — "A quote consisting of ONLY the duration phrase
   ('two (2) years' with no clause after it) is a MISS — measured…16 of 208…The full
   term sentence(s) ALWAYS follow the prefix."
7. **effective_date blank-placeholder carve-out:** "A date line whose day or month is
   a BLANK PLACEHOLDER ('April __, 2005'…) is NOT a stated date — output null, never
   a fabricated fill…null satisfies the blank expectation (measured: 5 of 16…)."

Also fixed inside the replaced block: the duplicated "Quote each fragmentQuote each
fragment" typo.

**Not merged (Phase 3.5 discipline):** v35's guard as-is was NOT merged — its
fragment-quoting language contradicts the grain rule (same-section conflict); it was
re-cast instead. Parties alias emission, contract_value/renewal_terms strengthening,
and the `[•]`-date handling were deliberately NOT rule-ified (GT artifacts / base-rate
artifacts / unscoreable — anti-overfitting doctrine).

### Evidence & verification (pre-A/B)

- All 7 `.replace()` anchors verified unique in v35; v0-v35 byte-identical (chain
  assertions); `PROMPT_VERSIONS["contracts_specialist_v36"]` registered.
- `test_contracts_v36_full_sentence_grain` pins: grain sentences present, every
  fragment relic absent from v36 but present in v35 (base untouched), guard re-cast,
  term_length/effective_date guards, v34's R1/R2/R3 preserved. 61 prompt tests green.
- Runner dry-run accepts the version; run name reserved on the board.

### Interpretation

1. The truncation cluster (146 pure + 265 condensed = 411/448 NEAR) is the single
   largest fixable mass on the surface — larger than v34's R1/R2/R3 targets combined,
   and it is an instruction-level defect (the prompt literally teaches the wrong
   grain), not a model capability gap: the model quotes the words it is told to quote.
2. Full-sentence quoting is strictly safer under the current scorer: containment
   similarity is asymmetric (expected-within-predicted), so a longer verbatim quote
   covers every GT label inside it while a fragment covers none. The old "longer item
   dilutes similarity" belief predates the containment rubric (v10 era).
3. Item counts should drop (fragments merge into full sentences: 14.8 predicted
   items/doc vs 6.9 GT labels on v34) — KPI precision (0.368) and span-count drift
   (+7.8 signed mean on key_obligations) should improve as a side effect.
4. Cost/robustness: the edit adds ~1.2 KB of prompt text (one pass, same chunking) —
   no token-budget change; schema untouched (schema_valid 1.0 risk ≈ 0).
5. Caveats: (a) the half-corpus surface may under/overstate vs the v32@510 full-corpus
   anchor 0.8807 — the 255-doc sample-efficiency boundary (KANBAN-049) is 25-50%, so
   this surface is adequate but the full run remains the generalization tiebreaker;
   (b) over-quoting risk on docs where GT labels are SHORT — contained either way;
   (c) v35's guard interference with term_length (unknown mechanism) is shielded by
   the duration-only guard but only the A/B can settle it.

*Sources:* `reports/experiment_log.jsonl` (last two records), manifests
`data/manifests/extract_v{34,35}_half.jsonl` (expected/predicted per row),
`scripts/reporting/ab_paired_compare.py` output, sim-matrix recomputed with
`llm_dojo_scoring.field_scoring._element_similarity`, `src/prompts.py` v34/v35/v36.

## What questions or uncertainties remain?

1. Does the A/B move the composite outside the noise band (±0.03, CI-excludes-zero
   gate)? Projection: key_obligations NEAR→MATCH conversion is worth ~+0.08-0.10 on
   the field (1/8 weight → ~+0.01-0.013 composite) if even half the 411 fixable labels
   convert; term_length recovery adds ~+0.005. Verdict threshold: paired CI excluding
   zero with P(win) ≥ 0.9.
2. Does full-sentence quoting depress item counts enough to hurt the entity-list
   disaggregation path (multi-clause items) or category-presence routing? The guard
   re-cast and per-category dedupe are the designed answer; the A/B's category_presence
   (0.7078 baseline) will tell.
3. Is the v35 guard's term_length interference real? If v36 (with the re-cast guard)
   still shows term_length noise, a v36-minus-guard arm is the next frontier cell.
4. Parties GT-grain artifacts and the `[•]`-date cluster remain score-bound — a
   GT-rebaseline (master labels cleanup) is the unblocking move, not a prompt rule.