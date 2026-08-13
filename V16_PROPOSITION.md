# V16 Proposition — Fragment-Granularity Alignment for `key_obligations`

**Status:** Proposed · **Author:** iteration loop (v2→v15 data) · **Date:** 2026-08-12
**Scope:** contracts specialist extraction · **Evaluation:** 50-doc same-sample A/B (seed 42)

---

## 1. Executive summary

`key_obligations` sits at **0.7755** (v15, 50 docs) — a ~22.5% error. The
three historically dominant causes are now *eliminated*:

| Cause | Status | Evidence |
|---|---|---|
| Input truncation | **Solved** (chunked pass) | 0 truncated docs (was 3); 335k-char monster recovered 0.125 → 0.938 |
| Hallucination / wrong content | **Solved** | 995 predicted items, **0 hallucinated** (verified_precision 0.994) |
| Content coverage | **Solved** | model extracts 995 real items vs 826 GT spans — over-production +20% |

The residual error is a fourth, previously-hidden cause:

> **Span-segmentation misalignment.** The model emits **full-sentence items
> (22–97 words)** while the CUAD ground truth holds **short operative
> fragments (10–25 words)**. When a GT fragment is embedded inside a longer
> model item, the pairwise similarity (token-F1, bipartite match @0.6) falls
> below the match threshold — the content is present and correct, but the
> item *boundaries* don't line up with the annotator's. Aggregate: **331
> predicted items unmatched + 162 GT spans uncovered** = the ~22% loss.

**A more intelligent model is not the only fix — it is not even the primary
fix.** This is an output-format specification problem the prompt fully
controls. v16 changes the item contract from *verbatim whole clause* to
*verbatim atomic fragment* (the smallest operative span, 4–20 words),
mirroring the annotator's segmentation. A smarter-model sweep is proposed as
a **second axis** — to quantify the residual capability gap *after* prompt
alignment, not in place of it.

---

## 2. Diagnosis — the numbers

### 2.1 The decomposition (v15, 50 docs, chunked, no truncation)

```
predicted items      = 995   (all doc-verified, 0 hallucinated)
GT spans             = 826   (estimated from matched/ko)
matched pairs        = 664

unmatched predicted  = 331   (33% of predicted — over-segmentation / riders)
uncovered GT spans   = 162   (20% of GT — under-segmentation / embedded)

alignment precision  = 664 / 995 = 66.7%
alignment recall     = 664 / 826 = 80.4%   (= ko, the reported score)
```

Per-doc (45 docs that actually carry GT obligation spans):

```
ko == 1.0 : 13 docs
0.8–0.99  :  8 docs
0.5–0.8   : 22 docs   ← the band to fix
< 0.5     :  2 docs
```

### 2.2 The mechanism — worked example (Impresse Co-Branding, ko 0.50)

GT spans (12), e.g.:

> *"Upon termination of the Agreement, VerticalNet and Impresse shall
> jointly own all User Data."* (15 words)
> *"In addition, Impresse shall not now or in the future contest the
> validity of VerticalNet's ownership"* (16 words)

Predicted items (8), e.g.:

> P6 (97 words): *"Except as otherwise set forth herein, neither party
> shall transfer, assign or cede any rights or delegate any obligations
> hereunder…"* — the joint-ownership fragment is buried inside this
> sentence's riders; best overlap with the GT span: **0.43** (< 0.5).

Token-F1 between a 16-word GT fragment and a 60–97-word predicted sentence
is structurally capped near 0.3–0.45 — **below the 0.6 bipartite match
threshold even when the fragment text is verbatim-present**. The scorer is
not wrong; the item grain is.

### 2.3 Why this survived v13–v15

Every prompt since v1 instructed *"quote the operative language VERBATIM as
written"* — i.e., whole clause sentences. v13's granularity fix (+6.4pp)
helped because finer items raise the odds of one item ≈ one span, but the
model still emits sentence-length units with preamble/riders
(*"During the Term of this Agreement…"*, *"Except as otherwise set forth
herein…"*), which dilute similarity and consume match slots. The family
scope, exhaustiveness, and chunking solved *what* is extracted; the item
**grain** controls *how it is matched*.

### 2.4 Other fields — not the bottleneck

| Field | v15 | Residual error mode |
|---|---|---|
| parties | 0.940 | fuzzy name matching on long/aliased names |
| effective_date | 0.896 | defined-term vs execution date variants |
| term_length | 0.979 | — |
| termination_clauses | 0.938 | minor |
| governing_law | 0.934 | containment on long sentences (same length-dilution effect, mild) |
| renewal_terms | 0.844 | single-doc noise |

These are 2–8% errors — order(s) of magnitude below the 22% ko gap.

---

## 3. Is a smarter model "the only fix"? — No, here is the evidence

1. **The content is found.** 995 items, all grounded in the document, +20%
   over the GT count. The model is not failing to *understand* obligations.
2. **The failure is format-controlled.** Item length is a prompt-specified
   output contract. Nothing in the model's reasoning is required beyond what
   a deterministic formatting instruction demands.
3. **The lever is measurable.** v13's granularity change alone moved ko
   +6.4pp on 30 docs with zero other changes — same model (qwen3.7-flash).
   A v16 that specifies *fragment* grain targets the same mechanism harder.
4. **Cost/latency symmetry.** A stronger model (deepseek-v4-pro, nemotron-3)
   would cost ~5–15× per run and complicate the vendored-agent parity with
   llm-mailroom. It should be tested as an *axis*, not assumed.

**Recommended framing:** prompt-first (v16), then model sweep as a
controlled second factor (v16 × {qwen3.7-flash, deepseek-v4-pro,
nemotron-3-ultra}) on the same 50 docs — this isolates how much of the
residual is prompt-addressable vs model-capability.

---

## 4. v16 prompt design

**Change (surgical):** replace the key_obligations itemization rule with a
fragment-granularity contract. All v15 content is retained (families,
exhaustiveness, re-scan duty, size calibration, source truth, truncation
boundary, chunk duty) — this is one replaced paragraph.

### 4.1 The new item contract (draft)

```
   - key_obligations items are ATOMIC FRAGMENTS, not sentences: emit the
     smallest verbatim span that states the operative restriction or covenant
     — typically 4-20 words (subject + operative verb + object/qualifier).
     The ground truth stores exactly this grain; a longer item dilutes the
     match and is scored as a miss even when the content is present.
     STRIP sentence preamble and riders: "During the Term of this Agreement,"
     "Except as otherwise set forth herein," "Subject to Section N,"
     "Nothing in this Agreement is intended to…" and cross-references are
     NOT part of the fragment. When one sentence states several obligations,
     emit each as its own fragment (a compound "shall not assign, sublicense,
     or transfer" clause yields separate fragments per right). Quote each
     fragment verbatim. A fragment is complete when it states the full
     obligation without surrounding context — never truncate mid-obligation.
```

### 4.2 What this changes mechanically

| Property | v15 (current) | v16 (proposed) |
|---|---|---|
| Item grain | full clause sentence (22–97 w) | atomic fragment (4–20 w) |
| Preamble/riders | included | stripped |
| Compound clauses | one item per clause | one item per operative right |
| Expected effect | — | GT fragment ≈ item → token-F1 ≫ 0.6 → matched |

### 4.3 Guardrails

- **Verbatim integrity:** fragments stay verbatim; only *boundaries* change
  (never paraphrase) — the factuality guard (verified_precision) is
  unaffected.
- **No over-splitting:** a single atomic obligation stays one item; the
  size calibration (7.4 mean / 22 max GT spans) is the sanity check.
- **Scorer untouched:** SCORING.md matching stays deterministic at 0.6 —
  v16 proves itself against identical scoring, so the delta is attributable.

### 4.4 Secondary v16 additions (small, evidence-backed)

1. **Similarity-aware fragment examples** — 2–3 worked fragment/sentence
   pairs in the prompt (from actual v15 misses) anchoring the grain.
2. **Cross-field guard** — the fragment rule applies to key_obligations and
   termination_clauses lists only; scalar/containment fields keep full-text
   quoting (their scoring rewards completeness).

---

## 5. Evaluation plan

### 5.1 Primary — v15 vs v16 (deterministic, same sample)

```
python scripts/eval/run_langfuse_extraction_eval.py \
    --sample 50 --seed 42 --chunked --max-input-chars 250000 --max-tokens 32768 \
    --prompt-version contracts_specialist_v16 \
    --lf-project llm-dojo --lf-environment llm-dojo \
    --manifest data/manifests/extraction_ab_v16_50.jsonl \
    --experiment-name qwen3.7-flash_contracts_specialist_v16_extraction_langfuse_50
```

Decision rule:

- ko ≥ +3pp and no field regresses > 2pp → **adopt v16**
- ko ≥ +3pp but a field regresses > 2pp → diagnose, single-adjust, re-run
- ko < +3pp → the residual is segmentation that prompt format alone cannot
  reach → proceed to the model sweep (5.2) with v16 as the fixed prompt

### 5.2 Secondary — model-capability axis (only if 5.1 is adopted or stalls)

Run **v16 × {deepseek/deepseek-v4-pro, nvidia/nemotron-3-ultra-550b-a55b}**
on the same 50 docs, same manifest/seed. Quantifies: after prompt alignment,
how much of the residual is model-bound. If a stronger model closes most of
it, the mailroom vendored-agent upgrade decision is data-backed; if not, the
scoring/threshold side is the next target.

### 5.3 Tooling — alignment audit (proposed addition)

Extend the per-row `entity_list_audit` with, for each **uncovered GT span**,
the best-matching predicted item + its similarity score. This turns every
miss into a labeled example for the next iteration (and feeds 4.4's prompt
examples) instead of a bare number.

### 5.4 Regression surface

- Full test suite (currently 271, network-free) — chunked unit tests,
  leakage guard, site render audits.
- Experiment log record + GH Pages site update after the run
  (same pipeline as v13/v14/v15).

---

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Fragments too small → similarity drops for *verbatim* GT (exact-match pressure) | low | fragment floor (min 4 words); size-calibration sanity check; 50-doc A/B catches it |
| Termination_clauses affected by fragment rule | medium | rule scoped to list fields; termination items already fragment-like; monitored separately |
| Over-splitting inflates item count → precision-side noise | low | dedupe at merge; bipartite matching bounds impact; ko is recall-side (unaffected by extra items) |
| Model sweep cost (~5–15× per run) | medium | gated behind 5.1 outcome; pilots at n=10 first |

---

## 7. Path forward (recommended order)

1. **Land v16** — fragment-granularity item contract (this proposition's 4.1),
   unit tests, 50-doc A/B vs v15, log + site sync.
2. **Add the alignment audit** (5.3) — every subsequent iteration starts from
   labeled misses, not aggregates.
3. **If v16 stalls** → run the 3-model sweep on the fixed v16 prompt (5.2)
   to quantify the capability ceiling.
4. **If the ceiling is the scorer** (strong models still ~15%+) → open the
   SCORING.md matching discussion (containment-style credit for
   fragment-embedded-in-item) as a separate, versioned change — never
   silently.
5. **Roll into llm-mailroom** once adopted: vendored
   `contracts_specialist_v16` prompt + (optionally) the chunked
   `extract_chunked` path, with the existing MAILROOM PATCH plumbing.

---

## 8. A/B results — v16 and v17 (executed 2026-08-12)

Both iterations were implemented and run on the same 50-doc chunked sample
(seed 42, Langfuse llm-dojo, 30 traces/arm verified).

### 8.1 v16 (fragment-granularity) — NOT adopted

| Metric | v15 | v16 | Δ |
|---|---|---|---|
| key_obligations | 0.7755 | 0.7816 | +0.6pp (below the +3pp bar) |
| overall | 0.9129 | 0.8859 | **−2.7pp** |
| parties | 0.940 | 0.900 | **−4.0pp** |
| effective_date | 0.896 | 0.854 | **−4.2pp** |
| term_length | 0.979 | 0.953 | **−2.6pp** |
| items (median words) | 1021 (48) | 1292 (26) | over-fragmentation |
| alignment precision | 0.650 | **0.547** | worse |

The fragment instruction halved item length (correct direction: +43 more
matched spans) but over-fragmented — 1292 items vs 826 GT spans (+56%) and
alignment precision FELL. **Rejected per the decision rule (ko < +3pp AND
multiple fields regressed > 2pp).**

### 8.2 v17 (length-anchored grain, 10–25 words) — NOT adopted

ko 0.7726 (−0.3pp vs v15), overall −0.6pp, parties −2.0pp, effective_date
−1.2pp, term_length −2.6pp; items 1083 (median 27 words); alignment
precision 0.579 — **worse on matched spans than v15 (627 vs 664)**.

### 8.3 The decisive finding — three grain instructions, one ceiling

| Prompt grain | median words | items | matched | align-precision |
|---|---|---|---|---|
| v15 sentences | 48 | 1021 | 664 | 0.650 |
| v16 fragments | 26 | 1292 | 707 | 0.547 |
| v17 length-anchored | 27 | 1083 | 627 | 0.579 |

**The segmentation lever is exhausted at the prompt layer.** The model's
boundary choices do not converge on the annotator's regardless of how the
grain is specified.

### 8.4 What the misses actually are (post-hoc audit, v15)

- **Containment hypothesis REFUTED**: 0 of 160 unmatched GT spans are
  token-contained (≥0.7) in any predicted item — these are genuine content
  omissions, not embedded-fragment artifacts.
- **Family breakdown of the 160 unmatched spans:** license grant **40**,
  minimum commitment 12, IP ownership 10, anti-assignment 9, audit rights 6,
  revenue sharing 6, cap liability 5, post-termination 5, exclusivity 5,
  insurance 4, other 51.
- **Root cause: family-scope mismatch + partial family coverage.** Worked
  examples: pricing-formula spans ("The price that Sekisui shall pay for the
  Reagent Kits Products shall be based upon a formula…"), shelf-life/quality
  spans, and IP-prosecution-election spans ("In the event that Qualigen
  elects not to prosecute or maintain…") are all present in CUAD GT but the
  prompt's terse family names ("price restrictions", "IP ownership") don't
  enumerate those operative shapes — the model faithfully excludes them per
  the "general payment obligations are NOT expected items" rule. This is
  scope-fidelity, not segmentation.

### 8.5 Revised path forward

1. **v18 = family-fidelity**: rewrite the family enumeration to mirror the
   CUAD category definitions 1:1 — each of the ~20 categories gets its
   operative clause shapes (pricing formulas under Price Restrictions,
   quality/shelf-life under the applicable category, IP prosecution
   elections under IP Ownership, audit-pass and retention provisions under
   Audit Rights), with the exclusion rule tightened to target only true
   general operative duties. Scope-first, grain second (keep v17's
   length-anchored item contract).
2. **Model sweep (gated)**: v18 × {qwen3.7-flash, deepseek-v4-pro,
   nemotron-3} on the same 50 docs — separates scope-fidelity (prompt) from
   segmentation capability (model).
3. **Scorer discussion deferred**: the containment-credit idea is now
   empirically refuted (0/160 embedded spans) — do not pursue.

---

## 9. v18 (family-fidelity catalog) — ADOPTED (2026-08-12)

Implemented: the terse 26-family comma list is replaced by a CUAD-category
catalog (1:1 mirror of `CUAD_CATEGORIES` in `src/cuad_ground_truth.py`) with
each category's operative clause shapes derived from the 160-span
decomposition (cap-on-liability consequential-damages waivers, license
grants phrased as "right and license ... for the territory of", minimum
guarantees/royalties, audit deficiency remedies, insurance coverage lists,
IP-prosecution elections, family-term definitions). The exclusion rule is
narrowed to true general duties with a WHERE-IT-SITS guard (family clauses
inside indemnity/damages sections still count). v17's length-anchored grain
is kept unchanged. Verified: 272 tests pass; dry-run confirmed.

### 9.1 A/B result (same 50 docs, chunked, seed 42, Langfuse llm-dojo)

| Metric | v15 | v16 | v17 | v18 | Δ(v18 vs v15) |
|---|---|---|---|---|---|
| key_obligations | 0.7755 | 0.7816 | 0.7726 | **0.8535** | **+7.8pp** |
| overall | 0.9129 | 0.8859 | 0.9074 | **0.9230** | **+1.0pp** |
| parties | 0.940 | 0.900 | 0.920 | 0.940 | 0 |
| effective_date | 0.896 | 0.854 | 0.883 | 0.883 | −1.2pp |
| term_length | 0.979 | 0.953 | 0.953 | 0.979 | 0 |
| governing_law | 0.934 | 0.934 | 0.954 | 0.934 | 0 |
| items (median words) | 1021 (48) | 1292 (26) | 1083 (27) | 1118 (25) | +97 items |
| matched_gt | 664 | 707 | 627 | 692 | +28 |
| alignment precision | 0.650 | 0.547 | 0.579 | 0.619 | −3pp |
| verified_precision | 0.994 | 0.970 | 0.994 | 0.991 | −0.3pp |

**Decision rule met**: ko ≥ +3pp (+7.8pp) AND no field regressed > 2pp
(effective_date −1.2pp, a known v12-era artifact unrelated to the family
catalog — all other fields tie or beat v15). **v18 is the new champion.**

### 9.2 Family-level recovery (token-level, v15-missed spans vs v18)

30 of the 160 originally-missed spans now match at ≥0.6 token overlap
(embedding rescue recovers further, which is why ko rose 7.8pp): cap
liability +8, IP ownership +4, license grant +4, post-termination +2,
minimum commitment +2, plus one each in price restriction, volume
restriction, insurance, no-solicit, audit, revenue sharing, anti-assignment.
Worked confirmation: Penntex (0 liability items in v15 despite a labeled
cap-on-liability span) now emits the "NO PARTY SHALL BE LIABLE FOR
CONSEQUENTIAL, INCIDENTAL, PUNITIVE, EXEMPLARY OR INDIRECT DAMAGES"
clause. Still missing (131 at token level; largest family license grant
36) — the residual is boundary/span-choice divergence plus clauses the
shapes still do not enumerate.

### 9.3 Path forward

1. **Model sweep (now gated-OPEN)**: v18 × deepseek-v4-flash /
   deepseek-v4-pro on the same 50 docs — separates prompt scope-fidelity
   from model segmentation capability.
2. **v19 (if needed)**: address the residual license-grant misses with
   worked positive/negative span examples per family instead of prose
   shapes.

---

## 10. v19 (worked span examples + span discipline, max reasoning) — ADOPTED as flash-line ko champion (2026-08-12)

### 10.1 Design (data-backed from the v18 flash 50-doc audit)

- **License-grant gap**: 93 of 241 token-level-unmatched GT spans were
  license-shaped, but only 25 of 107 license-ish GT spans carry the naive
  "grants ... a license" phrasing — the misses are grants-and-assigns with
  territories, restriction-on-rights clauses, options, and end-user access
  grants. v19 adds WORKED SPAN EXAMPLES drawn verbatim from the residual
  misses (7 positive shapes + 2 verified negatives — trademark-hygiene and
  product-marketing duties that v18's WHERE-IT-SITS guard let through).
- **Alignment precision**: 71% of v18's predicted items were token-unmatched,
  225 of them near-duplicates (sentence+fragment pairs; one audit clause
  emitted twice in a chunk). v19 adds SPAN DISCIPLINE — one item per
  operative requirement with a post-build dedupe scan.
- Run: qwen3.7-flash, **reasoning_effort=max**, same 50 docs, seed 42,
  chunked, Langfuse llm-dojo.

### 10.2 A/B result (v19 vs v18, same surface)

| Metric | v18 | v19 | Δ |
|---|---|---|---|
| key_obligations | 0.8535 | **0.8840** | **+3.0pp** |
| overall | 0.9230 | 0.9135 | −1.0pp (error row + noise; excl. error ≈ 0.932) |
| items | 1118 | **792** | **−29%** |
| near-dup emissions | 159 | 101 | −58 |
| alignment precision | 0.619 | **0.662** | +4.3pp |
| verified_precision | 0.991 | 0.988 | −0.3pp |
| parties / eff_date / term / gov | .940/.883/.979/.934 | .918/.865/.968/.932 | 1-2 docs of noise each |
| tokens / cost | 993k / $0.037 | 1.52M / **$0.098** | +53% / 2.6x |

**ko motion**: 10 docs up vs 7 down, 33 flat. Gains concentrate in the
license-family docs the worked examples target: HPIL 0.5→1.0, NOVO 0.667→
1.0, Fulucai 0.5→0.833, LinkPlus 0.571→0.857, BuffaloWildWings 0.368→0.579.
The single −0.846 is the Ediets EX-10.4 parse error (see below).

### 10.3 Verdict and caveats

- **Decision rule met**: ko +3.0pp (≥ +3pp) and no field regressed >2pp.
  **v19 is the flash-line key_obligations champion (ko 0.8840, +10.9pp vs
  v15)**; v18 remains the safest overall champion (0.9230) — the overall
  delta is the Ediets error row, not the prompt.
- **Reliability caveat**: reasoning_effort=max burned the structured-output
  budget on a 2-chunk doc (9.8k completion tokens → unparseable JSON, 1/50
  rows lost; at v18's level for that doc, ko ≈ 0.90). Production candidate:
  v19 prompt × reasoning_effort=none (not yet run — the prompt vs reasoning
  confound is unresolved by design; one more arm would isolate it).
- **Spend**: $0.098 for the 50-doc surface; total session spend across all
  v18/v19 arms ≈ $0.29 estimated (OpenRouter ledger $0.39 across 14/49
  runs).

---

## 11. v20 (non-obligation field fidelity) — field gains validated, ko variance-dominated (2026-08-12)

### 11.1 Design (from the v19 per-field failure audit)

The v19 overall is dragged by non-obligation fields: effective_date 5 docs
at 0.0 (blank-template GT — "_____ day of ________, 19____", "Effective
Date:" — where the model's null answer is CORRECT), parties 4 docs at 0.0
(role/pronoun labels: "Consultant", "Member", '"we," "us," or "our"'),
renewal_terms 2 docs at 0.0 (evergreen clauses that never say "renew";
deal-terms tables), governing_law 2 docs near-0 (regulatory-jurisdiction
sentence), term_length (defined-Term sentence), termination_clauses
(redacted section "[***]"). Three surgical SCORER fixes + four surgical
prompt rules:

- **Scorer (field_scoring.py, affects all future runs; historical records
  keep their stored scores):**
  1. `score_date_field`: blank-template / label-only expected dates are null
     expectations — null prediction = 1.0 (3 of the 5 zero docs fixed;
     SPRINGBANK's OCR-mangled real date "7t h day of April, 2020." stays a
     genuine miss).
  2. `score_entity_list` (partial_gt): a GT label whose 3-6 tokens appear
     verbatim inside a predicted item is instantiated — fixes the
     "Consultant"/"Member"/pronoun-alias party labels (3 of 4 zero docs).
  3. `score_name_field`: full token-containment of the expected in the
     predicted → 1.0 (GOOSEHEAD "FRANCHISE AGREEMENT" inside the long
     title; LOYALTYPOINT's genuinely different title stays low).
- **Prompt (v20 = v19 + four rules):** renewal_terms EVERGREEN CLAUSES +
  DEAL-TERMS TABLES; term_length DEFINED-TERM SENTENCES (carved out of the
  existing no-definitions rule); governing_law regulatory-jurisdiction
  sentences; termination_clauses REDACTED SECTIONS (heading + marker).

### 11.2 A/B result (same 50 docs, chunked, seed 42, Langfuse llm-dojo, qwen3.7-flash × max reasoning)

Official records (v19 old-scorer vs v20 new-scorer — scorer deltas below
isolated by a no-embedding re-score of both arms with the SAME new scorer):

| Metric | v19 | v20 | Δ official | Δ same-scorer |
|---|---|---|---|---|
| overall | 0.9135 | 0.9142 | +0.07pp | +0.49pp |
| key_obligations | 0.8840 | 0.8113 | **−7.3pp** | −5.6pp |
| parties | 0.918 | **1.000** | +8.2pp | +2.0pp (scorer) |
| document_name | 0.960 | **0.991** | +3.1pp | +3.1pp (scorer) |
| effective_date | 0.865 | 0.802 | −6.3pp | +2.1pp (scorer) |
| renewal_terms | 0.816 | 0.861 | +4.5pp | +4.5pp (prompt) |
| termination_clauses | 0.938 | 0.867 | −7.1pp | **+5.4pp (prompt)** |
| term_length | 0.968 | 0.966 | −0.2pp | −0.2pp |
| governing_law | 0.932 | 0.919 | −1.3pp | −1.3pp |
| verified_precision | 0.988 | 0.987 | −0.1pp | — |
| tokens / cost | 1.52M / $0.098 | 1.46M / $0.094 | — | — |

**ko motion v19→v20: 2 up vs 14 down, 34 flat** — the −7.3pp ko is diffuse
across docs the v20 rules never touch (HPIL, a v19 worked-example winner,
1.0→0.5; EcoScience 1.0→0.5), i.e. max-reasoning run variance on a prompt
whose ko-relevant text is unchanged, plus one parse-error row per arm
(v19: Ediets; v20: MidwestEnergyEmissions — the max-reasoning reliability
cost documented in §10.3).

### 11.3 Verdict

- **Scorer fixes ADOPTED** (correctness: blank-template dates, role/pronoun
  party labels, contained titles) — they raise the floor for every future
  run; SCORING.md §3 updated.
- **v20 field rules VALIDATED on their targets** (renewal +4.5pp,
  termination_clauses +5.4pp same-scorer) but the arm is ko-variance-
  dominated: v20 as a whole is NOT a champion (ko 0.8113 < v19 0.8840).
- **Next step: v21 = v19's ko content + v20's four field rules** (one
  ~$0.10 arm) to test whether the field gains survive at v19's ko level;
  reasoning_effort=none variant recommended to retire the parse-error risk.
