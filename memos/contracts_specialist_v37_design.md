# contracts_specialist_v37 — design (payment/monetary capture + canonical tag discipline) — KANBAN-056

**Research question:** the ContractEval-rubric F1 is 0.133 (recall 0.081, false-nr 0.478)
and per-category presence recall is 0.534 — where does the residual F1 mass live, and
does a payment/monetary capture rule (with canonical tag discipline) recover it?

**Companions:** `memos/contracts_specialist_v36.md` (grain reconciliation — running),
`memos/contracts_specialist_v34.md`, KANBAN-056 card. v37 constant NOT written yet —
held per human directive until v36's A/B verdict; this memo is the frozen design.

## Answer, Response, + Summary of Results

### Short answer

The payment/monetary families are the single largest coherent F1 mass on the surface:
**297 of 801 (37%) of the present-but-untagged (document, category) pairs are payment
families**, and the three worst presence-F1 categories are ALL money-adjacent (Price
Restrictions 0.000 with 24 false positives, Uncapped Liability 0.008, Volume Restriction
0.140, Most Favored Nation 0.400). The mechanism is NOT missing shapes (the prompt's
26-item enumeration already lists royalties, minimum commitments, price restrictions,
caps): it is (a) **canonical-tag discipline collapse** — 78/255 docs (31%) emit one
field-level `key_obligations` reasoning tag instead of per-category tags, hiding every
category on the document (115 of the 297 payment misses sit here; 50/78 of those docs
contain money-shaped items that were emitted but never tagged), and (b) **genuine scan
gaps** on properly-tagged docs (182/297: Uncapped 38, Post-Termination 34, Volume 24,
Minimum Commitment 24, Liquidated 10, Cap 10, Revenue 13). `contract_value` is never GT
on this surface (0/255 expected — the base-rate claim verified at record level), the
model fills it on 101/255, and **113/255 docs have payment GT but contract_value = null**
despite the existing never-null-when-visible rule. The v37 rule: a mandatory
PAYMENT & MONETARY CLAUSES scan family (measured clause shapes, full-sentence grain —
composes with v36), exact-canonical-tag enforcement (no field-level fallback), and a
contract_value trigger extension.

### Data findings (255-doc half-corpus, v34 record + manifests + master GT CSV)

**1. contract_value / money GT mass.**
- `contract_value` in expected_fields: **0/255 rows** (base-rate claim CONFIRMED at the
  record level — `src/cuad_ground_truth.py` never emits it; diagnostics `money_n_pairs
  = 0` is by design, not a scoring bug).
- Predicted contract_value: **101/255 non-empty** with real money values ("$5,000 per
  month", "$250,000.00", "€500 per hour", "$55,000 for First Contract Year, $70,000
  for Second…"). Money extraction is NOT near-zero at the content level — it is
  near-zero only in *scored* diagnostics (no GT → no pairs).
- **113/255 docs (44%) have ≥1 payment-category GT but contract_value = null**
  (NETGEAR distributor agreement, NANOPHASE with 8 payment categories). The v34 rule-10
  never-null trigger ("a '$' amount … counts") fires only on consideration/price
  language; payment schedules/royalties/commitments don't trip it.
- Master GT (CSV, all 510 rows annotated per category with literal Yes/No): payment
  families GT over the 255 docs — **200/255 docs have ≥1 of the 11 payment categories;
  687 positive (doc, category) pairs**. Master answers for YES/NO categories are
  literal Yes/No — the money CONTENT GT lives in the CUAD clause labels (expected
  key_obligations items: royalty percentages, minimum commitments, caps).

**2. Per-category presence confusion (255 docs × 35 categories; GT = master Yes,
PRED = reasoning-tag seen; presence-level P/R/F1).**
- ALL categories: P 0.671 / R 0.534 / F1 0.595; **fn = 801** untagged doc-category
  pairs (the laziness/false-nr mass: KPI laziness 0.863, false-nr 0.478 over 1,686
  positive pairs).
- **Payment family (11 cats): P 0.774 / R 0.568 / F1 0.655; fn = 297 = 37% of the
  total untagged mass** — the largest single family cluster.
- Payment per-category (fn / GT+ / F1): Audit Rights 19/98 / 0.863 · Insurance 21/81 /
  0.839 · Cap On Liability 29/127 / 0.769 · Revenue/Profit Sharing 31/78 / 0.676 ·
  Liquidated Damages 19/37 / 0.632 · Minimum Commitment 40/78 / 0.613 ·
  Post-Termination Services 43/87 / 0.579 · Most Favored Nation 8/11 / 0.400 ·
  Volume Restriction 32/35 / 0.140 · **Price Restrictions 9/9 / 0.000 (24 fp!)** ·
  **Uncapped Liability 46/46 / 0.000**.
- Non-payment zero-tag families: Warranty Duration 32/32 fn (the category is ABSENT
  from the prompt text entirely), Competitive Restriction Exception 39/39,
  Affiliate License-Licensor 11/11, Unlimited/All-You-Can-Eat 9/9 — v38 frontier cell.

**3. Mechanism decomposition of the 297 payment fn.**
- **115/297 (39%) on 78 field-collapse docs** — those docs' reasoning carries ONE
  field-level `key_obligations` tag instead of per-category tags; every category on
  the doc counts untagged. 50/78 of those docs (64%) contain money-shaped predicted
  items ("$", "royalt", "fee", "percent"…) — **emitted but untagged** (NEONSYSTEMS:
  three verbatim royalty items, zero category tags; TEARDROPGOLF: contract_value
  "$55,000/$70,000/$90,000" extracted, 0/6 payment categories tagged). Collapse docs
  also emit fewer items (9.0 vs 15.9 per doc) — the fallback correlates with
  under-extraction.
- **182/297 (61%) on properly-tagged docs** — genuine scan gaps: the model tags the
  doc's main families (License Grant, Exclusivity) and skips the money clauses
  (Uncapped 38, PostTerm 34, Volume 24, Minimum Commitment 24, Liquidated 10,
  Cap 10, Revenue 13, Audit 7, Insurance 8, Price 6, MFN 8).
- Tag vocabulary drift compounds it: non-canonical tags observed across the 255 docs —
  "Indemnification"/"Indemnification Obligations"/"Indemnity" (3 variants),
  "Non-Solicit Of Customers" (alias), "ROFR/ROFO/ROFN" (case), "Contract Value",
  "Termination For Cause", "Specific Performance" — the canonical guard list is
  bypassed.

### The v37 design (ONE rule, two inseparable parts — payment capture + canonical tags)

**Rule (primary, targets the R2 completeness block + the 26-item enumeration +
rule-10 contract_value triggers; does NOT touch v36's grain paragraphs, term_length
guard, or effective_date carve-out — Phase 3.5 disjoint):**

> **PAYMENT TERMS & MONETARY CLAUSES — a mandatory scan family.** Measured on the
> 255-doc half-corpus: 297 of 801 present-but-untagged (document, category) pairs are
> payment/monetary families; Price Restrictions 0/9, Uncapped Liability 1/46, Volume
> Restriction 3/35 tagged. Every money clause family below, when present, gets its OWN
> fully-quoted item (FULL CLAUSE SENTENCES, verbatim — the v36 grain) AND its own
> exact canonical tag in the reasoning entries — never a field-level `key_obligations`
> entry, never a sibling/generic tag (a royalty is `Revenue/Profit Sharing`, NOT
> `License Grant`; an insurance limit is `Insurance`, not `Cap On Liability`):
> Revenue/Profit Sharing (royalties, percentage-of-revenue/profit splits, commission
> entitlements — "royalty equal to the Specified Royalty Percentage of all revenues
> received"; "thirty percent (30%) of the Net Sales in excess of Eleven Thousand
> Dollars ($11,000) per calendar month"); Minimum Commitment (minimum purchase/order/
> royalty guarantees — "shall purchase at least", "minimum annual"); Volume Restriction
> (unit/output/inventory caps — "not more than X units"); Price Restrictions (price
> floors/caps, resale-price rules — "sell at prices no lower than", "may not increase
> more than once in any period of twelve consecutive months"); Liquidated Damages
> (damages/fee/penalty amounts — "a late fee of"); Cap On Liability (aggregate caps,
> damage exclusions — "in no event shall either party be liable"); Uncapped Liability
> ("nothing in this Agreement shall limit either party's liability", "liability shall
> not be subject to any cap"); Insurance (coverage lists, policy limits — "not less
> than $1 million per occurrence"); Most Favored Nation (pricing parity — "as
> favorable as", "no less favorable than the terms offered to any third party");
> Post-Termination Services (transition/continuation duties and fees after
> termination). Scan these families explicitly before finalizing: a present money
> clause with zero tagged entries is INCOMPLETE — same duty as the category checklist.
> **Canonical tag discipline:** every emitted item carries its EXACT canonical category
> tag; never collapse the list under one field-level entry (measured: 78 of 255
> documents fell back to a single field-level tag, hiding every category on the
> document).

**contract_value trigger extension (rule 10):** a payment SCHEDULE ("$55,000 for
First Contract Year, $70,000 for Second Contract Year"), a per-unit fee or royalty, a
minimum commitment amount, or an aggregate consideration phrase ALL count as visible
consideration — never null when any of these appear (measured: 113 of 255 docs have
payment GT but null contract_value). Unscored on this surface (0/255 GT) but drives
diagnostics presence 0.396 → high and disciplines the scan.

**Section targets:** (1) R2 CATEGORY-LEVEL COMPLETENESS block — insert the scan family
after the checklist paragraph; (2) enumeration entries 10-13 + 21-23 — append the
measured examples; (3) rule 10 FIELD-PRESENCE SELF-CHECK — extend the contract_value
triggers. One-pass preserved (a checklist duty, no new machinery).

**Instance-level frontier argument (Phase 3.5):** v36 (grain) wins on the truncation
rows across ALL families (146 pure + 265 condensed NEAR labels); v37 wins on a
DISJOINT row set — the 297 payment-fn doc-categories + 113 contract_value-null docs
(200/255 docs carry payment GT). Overlap is reinforcing, not conflicting: v37's
quote-fully language is drafted at v36's grain; v36's full-sentence items gain v37's
canonical tags. Both can coexist on the frontier; if both A/Bs win, v38 can merge them
formally.

### Verdict / recommendation

**Design frozen now; constant + launch AFTER v36's A/B verdict (do not launch blind).**
v37's base = the v36 constant in EVERY verdict scenario (v36's edits are wins or logic
repairs; nothing in them is revertible — full-sentence quoting is strictly safer under
asymmetric containment, and the guard re-cast was already part of v35). The rule
language is grain-compatible either way, so waiting costs nothing and prevents
misattribution if v36 shifts item counts. Launch: `--sample 255 --seed 42 --chunked
90k/8k`, manifest `data/manifests/extract_v37_half.jsonl`, name reserved
`qwen3.7-flash_contracts_specialist_v37_extraction_chunked_half`; A/B vs v34
(champion gate) AND vs v36 (rule attribution). **Prediction:** presence recall
0.534 → ~0.60+ if a third of the 297 fn recover; pair-level F1 0.133 → ~0.17-0.20 if
~100+ positive pairs convert (each newly tagged+quoted money clause is a new covered
pair); precision-side risk is the Price Restrictions confusion (24 fp) — the rule's
definitions should cut it.

### What was NOT fixed (future frontier cells)

- Sparse-family re-scan (v38): Warranty Duration (absent from prompt — add the
  enumeration entry; 32 fn), Competitive Restriction Exception (39), Affiliate
  License-Licensor (11), Unlimited/All-You-Can-Eat (9), Covenant Not To Sue (37),
  Non-Transferable License (52).
- General tag-discipline enforcement beyond payment families (the 78-doc collapse
  hides non-payment categories too — if v37's discipline phrasing wins, generalize it
  in v38).
- Over-quoting precision (span-grain overflow) — v36's grain change may already
  address it; re-measure on v36's verdict.
- Parties GT defined-term artifacts + `[•]`-date unscoreables + GT blank dates —
  GT-rebaseline territory, not prompt rules.

*Sources:* `reports/experiment_log.jsonl` (v34/v35 records incl. `contracteval_kpis`:
n_pairs 8,160, n_positive 1,686, precision 0.368, recall 0.081, F1 0.133, false-nr
0.478, laziness 0.863), `data/manifests/extract_v34_half.jsonl` (expected/predicted
per row), `data/cuad/master_clauses.csv` (510-row per-category Yes/No GT, normalized
filename join — 255/255 coverage), `src/prompts.py` v36 (rule 10, R2 block, 26-item
enumeration, canonical guard list), `src/cuad_ground_truth.py` (CUAD_CATEGORIES).

## What questions or uncertainties remain?

1. Does the 78-doc field-collapse correlate with v36's grain change (will full-sentence
   items make the collapse more or less likely)? Only v36's verdict + v37's run can
   tell; the discipline phrasing is designed to be robust either way.
2. How much of the 182 genuine-miss fn is chunk-boundary loss (money clauses in the
   middle 8k overlaps)? The 90k/8k windows should hold payment sections, but a
   chunk-related sub-cluster would need its own surface.
3. Does the contract_value trigger extension create FP content on non-payment docs
   (14 docs already emit contract_value without payment GT)? Unscored on this surface,
   so harmless here, but downstream llm-mailroom consumers should watch it.
4. Are the master-CSV Yes/No labels (literal) consistent with the CUAD clause-label
   GT used by `build_expected_fields`? Cross-checked on samples (royalty clauses
   present exactly on Revenue/Profit Sharing Yes docs) — a systematic audit is a
   GT-rebaseline card, not a prompt rule.