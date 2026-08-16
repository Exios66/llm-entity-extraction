# Sorter Prompt Iterations — Development Roadmap & Timeline

**Source of record:** `src/prompts.py` (versioned prompt constants + changelog headers)
**Compiled:** 2026-08-16 · **Champion:** `sorter_v13` (strict **0.9430** / equiv 0.9470, full-509 CUAD) · **Candidate:** `sorter_v15`

> **Timeline note.** The source records iteration *cycles* (eval run → rule → A/B), not calendar dates — the only dated entry is the LegalBench subtask series (2026-08-15). The timeline below is therefore expressed as ordered development phases (T0–T9), each gated by a measured eval surface.

---

## I. Executive Summary

The Sorter began as a 6-class legal document classifier (v0) and evolved through **15 mainline iterations** into a hierarchical classifier: primary doc-class → contract subtype (25 CUAD families + `other`) — later extended with a doc-class branch (merger_agreement + doc_subclass) and a vision branch.

**Headline trajectory (full-509 CUAD surface):**

| Milestone | Strict accuracy | Delta driver |
|---|---|---|
| v5 baseline (post other-guard) | 0.8585 | first full-corpus measurement |
| v6 (corpus-convention rules) | **0.9312** | +7.3pp — largest single jump |
| v13 ★ champion | **0.9430** | title-wins doctrine + inversion repairs |
| v15 (candidate, pending A/B) | target ≥ 0.9430 | license-primary title guard |

**What actually moved the numbers:** not generic prompt polish, but *data-backed rules derived from named miss clusters* — each version header cites the exact documents, cluster sizes (e.g. 13/72, 17/72), and the model's own reasoning traces that motivated the rule.

**Three doctrines emerged and got validated:**
1. **Title-wins doctrine** (born v9, rules 23/24, validated +2.88pp) → extended to marketing (v10), alliance (v12), maintenance (v13), license-primary (v15).
2. **Corpus-convention rules** — "the ground truth follows the folder" (CUAD/MAUD/S-1 exhibit conventions): rules 9/10, 12, 13, 22, 28, 35.
3. **Noise-band discipline** — champion reruns as controls, ±0.006 identical-prompt band at 509, `P(Δ≤0)` reporting (v10).

---

## II. Lineage Map

```
MAINLINE — contract subtype surface (CUAD)
──────────────────────────────────────────
v0 ─ v1 ─ v2 ─ v3 ─ v4 ─ v5 ─ v6 ─ v7 ─ v8 ─ v9 ─ v10 ─ v11 ─ v12 ─ v13 ★ champion
                                                                   │
                                                                   ├── v14  (logic repair — NOT promoted; rule 30 banked)
                                                                   │      ╲ lesson folded into v15
                                                                   └── v15  (champion candidate: v13 + rule 31)

DOCCLASS EXPANSION — KANBAN-033 (built on v14 text)
───────────────────────────────────────────────────
v14 ── docclass_v0 ─┬─ docclass_v1  (rule 34 — banked: byte-identical to v0 on 30-doc surface)
                    ├─ docclass_v2  (rule 35 — A/B winner: exact 0.8000)
                    │        │
                    └────────┴─► docclass_v3  (Phase 3.5 MERGE of 34+35 on v0 base)
                                    │
                                    ├─ docclass_v4  (rule 36)      ──► docclass_v6 (rule 36 SHARPENED)
                                    └─ docclass_v5  (rule 37)

VISION LINE
───────────
sorter_vision_v0 (RVL-CDIP-style cascade) ── docclass_vision_v0 (embeds docclass rules 31–35,
                                             UNREADABLE → text fallback)

SISTER LINEAGE (appendix C)
───────────────────────────
legalbench_task_v0 ─ v1 ─ v2 ─ v3 ─ v4 ─┬─ v4_CRE (competitive_restriction_exception)
                                         └─ v4_CNTS (covenant_not_to_sue)
```

**Derivation discipline:** from v6 onward every version is built by surgical `.replace()` on its parent — the diff is the changelog. A version that has run is **never mutated** (e.g. docclass v6 revises rule 36 as a *new* version; v4 stays byte-identical).

---

## III. The Iteration Operating System

Every cycle follows the same anatomy (visible in every version header):

```
1. OBSERVE      eval run on a fixed surface (Langfuse-tracked run IDs, e.g.
                qwen3.7-flash_sorter_v6_subtype_langfuse)
2. DECOMPOSE    misses clustered by mechanism with counts + the model's own
                reasoning traces quoted (13/72, 17/72, …)
3. DRAFT        ONE rule per iteration; extra clusters stay banked
4. RISK-SCAN    counterfactual check over the full corpus:
                reward / risk / keep (e.g. v10: reward 7+Dynamex, risk 1, keep 10)
5. A/B          candidate vs champion rerun on the same surface;
                ±0.006 noise band / P(Δ≤0) as the significance floor
6. DECIDE       PROMOTE (score gain) · BANK (logic repair, no surface movement)
                · ESCALATE (GT artifact → data side)
```

**Invariants:**
- The **version key IS the experiment identity** (manifests, experiment log, `get_prompt()`, Langfuse sync all reference it) — a changed string = a new key.
- Rules cite **named documents** (COLOGUARD, TAT-14, Zounds, PACIRA…) so every rule is auditable back to a row.
- Surfaces are never mixed: 195-doc medium sample, 243/250-doc stratified A/B, 509-doc full CUAD, 30-doc / 676-doc docclass — scores across surfaces are **not comparable**.

---

## IV. Timeline — Mainline Sorter (v0 → v15)

### T0 · Bootstrap — `v0`
**Shipped:** 6-class classifier (contract, corporate_record, due_diligence, correspondence, compliance_filing, court_opinion) with confidence-calibration rules 1–5: full 0.0–1.0 range, 0.90+ only with cited concrete evidence, 0.50–0.85 for ambiguous docs, classify substantive form not filing wrapper.
**Status:** baseline; still the `"sorter"` default alias.

### T1 · The subtype dimension — `v1`
**Why:** the mailroom needs to know *which* contract family to route to — per the CUAD dataset card, the family decides the specialist's expected fields.
**Shipped:** CONTRACT SUBGROUP dimension — 25 CUAD contract families; template placeholders `{{doc_type_descriptions}}` / `{{contract_subtypes}}`; rules 6–7 (substantive agreement type, `other` fallback, `null` for non-contracts).

### T2 · Calibration & hybrids — `v2 → v3`
**v2 (chained-eval fixes):**
- Endorsement was described too narrowly ("celebrity/influencer" only) — product/insurance endorsement riders fell through to `other` → *"Endorsement riders attached to insurance/annuity/other agreements ARE endorsements."*
- HYBRID agreements ("Distribution and Development Agreement") followed title word order → **rule 8**: weigh the *operative* clauses, not the title order.
- Confident 0.95 subtype picks on torn decisions → **rule 9**: subtype uncertainty must lower confidence.

**v3 (remaining chained-eval error):** a "Distribution and Development Agreement" with *both* families' machinery was labeled `distributor`, but the corpus files it under Development → **DEVELOPMENT PREFERENCE** (development machinery beats the commercial family even when commercial text occupies more words) + **HYBRID CONFIDENCE CAP** (two-family hybrids capped at 0.85, runner-up named in reasoning).

### T3 · The overcorrection cycle — `v4 → v5` *(first measured A/B)*
**v4 (precision audit):** `"other"` existed only in the rules, never in the option list (schema enum: 26 values; prompt listed 25) → complete, self-contained key list + **STRICT KEY DISCIPLINE** (never a label, paraphrase, title, or null for a contract).
**Result — regression:** 195-doc stratified sample: **v4 0.810 vs v3 0.836**. The discipline framing made the model over-correct to `other` for title-obvious contracts (AGENCY / SPONSORSHIP / FRANCHISE AGREEMENT → `other`; 9 regressions vs 4 fixes).
**v5 (the fix): OTHER-GUARD** — `other` becomes nearly unreachable: a title or operative clause naming a family settles the pick; when torn between two families, lower the confidence instead of escaping to `other`. Lesson: *guard rails need guard rails.*

### T4 · Full-corpus era — `v6` *(the biggest jump)*
**Data:** first 509-contract full-CUAD run (`qwen3.7-flash_sorter_v5_subtype`: strict **0.8585**, equiv 0.8743, 72 misses) decomposed into 5 clusters:

| Cluster | Misses | Rule shipped |
|---|---|---|
| SEC Joint Filing Agreements (13D/13G) → `other`/non-contract | 13/72 | R12: joint filing = `joint_venture` (corpus: "Joint Venture _ Filing") |
| Maintenance hybrids & financial-sense maintenance | 17/72 | R13: license+maintenance → maintenance; financial-sense maintenance IS maintenance |
| Marketing / remarketing confusion | 10/72 | R15: remarketing = marketing · R16: marketing core guard |
| Hosting misread as license/development | 8/72 | R14: hosting stays hosting; dev-preference doesn't apply |
| Rule-10 development-preference overreach | — | R10 exception: operating core (manufacturing/marketing/hosting) wins |
| Schedules re-classified from their own title | — | R17: ANNEX INHERITANCE — parent's family governs |

**Result:** `qwen3.7-flash_sorter_v6_subtype_langfuse` → strict **0.9312**, 35 fails (**+7.3pp** — the single largest gain in the program).

### T5 · Stratified A/B era & the title-wins doctrine — `v7 → v9`
Measurement moves to the 243-doc stratified A/B (not comparable to 509 scores).

**v7** (from v6's 35 fails): R18 consortium O&M is maintenance (TAT-14 submarine cable — joint-governance wrapper ≠ joint_venture) · R19 development over license (license grant = delivery mechanism for developed IP) · R20 promotion guard. → **0.8765**, 30 fails.

**v8** (from v7's 30 fails): R21 "Collaborative Development and Commercialization" agreements are development — JSC governance is how partners run the development, not the family; "Franchise Development Agreement" → development · R22 "Intellectual Property Agreement"-titled docs are `ip` even with a license-grant or JV core. → **0.8971**, 25 fails.

**v9** (from v8's 25 fails — the doctrine is born): **R23 PROMOTION TITLE WINS** (COLOGUARD, CO-PROMOTION, PROMOTION AND DISTRIBUTION) · **R24 OUTSOURCING TITLE WINS** (Paratek, NICELTD — the outsourced function is the mechanism, not the family) · R25 customization schedules are maintenance. → **0.9259**, 18 fails. **Title-wins validated at +2.88pp.**

### T6 · The marketing campaign & noise-band discipline — `v10 → v11`
**v10:** the marketing cell is the worst family on *both* surfaces and unchanged since v6 (5/10 @243, 7/17 @509 — 0.5–0.588). All 7 full-corpus fails are marketing-titled docs re-classified by machinery (Monsanto→agency, Zounds→manufacturing, Principal→endorsement, Pacira→distributor, Todos→reseller, Vertex→joint_venture, Audible→co_branding). **R26 MARKETING TITLE WINS** with two carve-outs: (a) license-primary titles, (b) operational-service families (transportation/hosting — protects the Dynamex counterfactual). Counterfactual: reward 7 + Dynamex, risk 1 (protected), keep 10.
**Result:** 0.9342 vs champion rerun 0.9300 — `P(Δ≤0)=0.717`, **inside the noise band**. R26 recovered Monsanto/Principal/Todos/Dynamex but regressed Cybergy + SteelVault: both content-titled **"Marketing Affiliate Agreement"** — the model extended R26's "alongside" list to affiliate machinery.

**v11:** **R27 AFFILIATE IS NOT MARKETING** — affiliate/referral machinery (referral fees, affiliate links, program recruiting) is its own family even when recitals call it a "marketing agreement". Draws the boundary the R26 over-fire exposed.

### T7 · Inversion repairs & the champion — `v12 → v15`

**v12 (KANBAN-013 close-out):** v9@509 leaves strategic_alliance at 22/27 — all 5 fails explicitly titled "STRATEGIC ALLIANCE AGREEMENT", two of them a **rule-21 INVERSION** (the model quotes rule 21 *backwards* to justify collaboration). Counterfactual verified 0-risk: all 32 alliance-titled docs @509 are GT strategic_alliance. **R28 STRATEGIC ALLIANCE TITLE WINS**, explicitly overriding rule 21's collaboration reading. *One rule per iteration: cooperation-title and non-alliance inversion lessons stay banked.* → `v12@509`: **0.9234**, 39 fails.

**v13 (the champion):** maintenance cell stuck at 30/34 with 3 deterministic fails across v9-clean/v12 (SUNTRONCORP, WELLSFARGO yield maintenance, PRIMEENERGY completion & liquidity → `other`; AtnInternational network build → service). Root cause = **rule-13 INVERSION**: the model quotes rule 13 backwards ("financial-sense maintenance is classified under 'other'") while the rule says the opposite. Control rows prove the mechanism (the two financial-sense docs quoted *correctly* pass). **R29 MAINTENANCE TITLE WINS**; counterfactual 0-risk (all 34 maintenance-titled docs GT maintenance). → `v13@509`: **strict 0.9430 / equiv 0.9470, 29 fails — promoted to champion.**

**v14 (logic repair — NOT promoted):** marketing cell frozen at 14/17 since v12; 3 deterministic fails (Zounds, PACIRA, Audible). Mechanism = **rule-26 NARROWING** — Zounds quotes rule 26 and then *defeats it*; PACIRA applies rule 9's hybrid read over the marketing title; Audible lets the first-named family win. **R30 MARKETING TITLE WINS — STRENGTHENED** (not defeated by machinery re-reads, hybrid reads, or title family order). The A/B flagged the counterfactual: carve-out (a) cited only the exact phrase "Content License Agreement", and Playboy's "CONTENT LICENSE, MARKETING AND SALES AGREEMENT" regressed license→marketing. Rule 30 banked.

**v15 (champion candidate):** built on **v13**, folding in the banked v14 lesson. Evidence base: **cross-model failure traces on the identical v13 prompt** (qwen3.7-flash 0.9430 · deepseek-v4-flash 0.9332 · gpt-5-nano 0.8978 · llama-4-scout 0.8880 · gpt-4.1-nano 0.8782) — LejuHoldings "Content License Agreement" fails in **all five models**. **R31 LICENSE-PRIMARY TITLE WINS**: widens carve-out (a) to *any* license-primary title; a "Content License Agreement" is never `other` and never `ip`; carve-outs preserved (R13 maintenance, R14 hosting, R19/21 development, R26 marketing-core). **Target:** strict ≥ 0.9430 @509 vs v13-clean baseline, ±0.006 noise band as significance floor. *Status: pending A/B.*

---

## V. Metrics Progression

> ⚠️ Surfaces differ — compare only within a surface.

**Mainline (contract subtype):**

| Cycle | Version | Surface | Strict | Equiv | Fails | Note |
|---|---|---|---|---|---|---|
| T3 | v3 | 195-doc medium | 0.836 | — | — | pre-A/B reference |
| T3 | v4 | 195-doc medium | 0.810 | — | — | ⚠ regression (other over-fire) |
| T4 | v5 | 509 full | 0.8585 | 0.8743 | 72 | other-guard baseline |
| T4 | v6 | 509 full | 0.9312 | — | 35 | +7.3pp corpus-convention rules |
| T5 | v7 | 243 A/B | 0.8765 | — | 30 | surface change |
| T5 | v8 | 243 A/B | 0.8971 | — | 25 | |
| T5 | v9 | 243 A/B | 0.9259 | — | 18 | title-wins +2.88pp |
| T6 | v9 | 509 full | 0.9116 | — | 45 | marketing cell 7/17 |
| T6 | v10 | 243 A/B | 0.9342 | — | — | champion rerun 0.9300; P(Δ≤0)=0.717 |
| T7 | v12 | 509 full | 0.9234 | — | 39 | alliance rule |
| T7 | **v13 ★** | 509 full | **0.9430** | 0.9470 | 29 | **champion** |
| — | v15 | 509 full | ≥0.9430 target | — | — | pending |

(v11's run result is not recorded in the source file.)

**Docclass (KANBAN-033):**

| Run | Version | Surface | doc_type | subclass | exact |
|---|---|---|---|---|---|
| pilot (n=5) | v0 | 5-doc | 0.60 | 0.40 | — |
| A/B control | v0 | 30-doc | 0.8333 | 0.5000 | 0.6667 |
| A/B winner | v2 (R35) | 30-doc | **1.0000** | 0.7000 | **0.8000** |
| A/B | v1 (R34) | 30-doc | byte-identical to v0 (target row absent from sample → banked logic repair) |
| full corpus | v3 (merge) | 676-doc | 5 doc_type misses → arms v4/v5/v6 |

---

## VI. Timeline — Docclass Expansion (KANBAN-033)

**T8 · Hierarchical classification.** New task: shared 6 classes **+ merger_agreement** (MAUD corpus) with a **second-level `doc_subclass`** — consideration type for mergers (MAUD expert GT: all_cash / all_stock / mixed / election / other), record type for corporate records. Tertiary level deliberately absent (dataset metadata ≠ classification dimension). Built on v14's text; runner injects extended class list + `DOCCLASS_SCHEMA`.

| Version | Rule | Story |
|---|---|---|
| v0 | R31–R33 | merger_agreement class (title + M&A machinery); SEC-exhibit corporate records stay corporate_record; doc_subclass schema. Pilot: 0.60/0.40 on n=5. |
| v1 | R34 | **Embedded-records scope guard** — pilot miss: Roche/Geronimo/GenMark APM → corporate_record/bylaws because "BYLAWS OF THE SURVIVING CORPORATION" sits as Exhibit C inside the merger agreement (rule-32 over-fire; contradicted rules 17/31). Parent's class governs. Banked: byte-identical to v0 on the 30-doc surface (target row absent). |
| v2 | R35 | **RRA exhibit convention** — NMI Holdings RRA (EX-4.4) → contract/other ("does not map to the subtype taxonomy"). S-1 exhibit catalog files EX-4.x as record types → corporate_record/rights_instrument. Scoped to SEC exhibit context. **A/B winner: exact 0.8000, all 5 EX-4.x rows recovered, 0 regressions.** |
| v3 | R34+R35 | **Phase 3.5 MERGE** of the two disjoint arms on the same v0 base. Remaining 30-doc fails all GT artifacts (3 MAUD consideration gaps, 3 S-1 streamer artifacts) → escalated to the data side. Advanced to full-676 (`..._docclass_v3_docclass_full676`). |
| v4 | R36 | From full-676's 5 doc_type misses: ADAMAS/SUPERNUS APM with CVR consideration read as a standalone CVR instrument; CONTANGO "TRANSACTION AGREEMENT" hit a rule-35 over-fire. **M&A package machinery governs ancillary instruments.** Diag30 A/B: recovered contract_2 deterministically (2/2), not contract_33. |
| v5 | R37 | From the same run: FEDERAL… EX-99 package opens with a "LIMITED POWER OF ATTORNEY" — rule 34 didn't fire because the record text *leads* the package. **Agreement-package composition:** scan past record text to the parent agreement. |
| v6 | R36′ | **Sharpened R36** — v4's miss showed the model second-guessing against rule 31's enumeration ("does NOT explicitly list 'TRANSACTION AGREEMENT'") and treating a two-agreement file as a hybrid. Declares rule-31's list *illustrative*; primary agreement governs multi-agreement files. v4 kept byte-identical: *never mutate a version that has run.* |

**Open:** v4/v5/v6 are parallel arms off v3 — a Phase 3.5-style merge + full-676 validation is the next gate.

---

## VII. Timeline — Vision Line

**T9 · Image classification.**
- `sorter_vision_v0` — RVL-CDIP-style cascade: ordered checks 1–6 judged by document **function**, visible-evidence scratchpad ("none" / evidence per check, stop at first match), runner-up line, tag-based output (`<label>/<confidence>/<reasoning>`), `## Output format` split marker for system+image payload. Guards: demand letter *about* a contract is correspondence; exhibit wrapper doesn't convert the agreement.
- `docclass_vision_v0` — vision twin of docclass v3 (embeds rules 31–35), 7 classes + `<subclass>`, worked examples (embedded-bylaws APM, EX-4.4 RRA, specimen stock certificate), and **`<label>UNREADABLE</label>` → text-path retry** (vision-primary-with-text-fallback, `run_langfuse_docclass_eval.py --input-mode vision|vision-primary`). *Status: built, first measured run pending.*

---

## VIII. What the Iterations Taught — Doctrine & Failure-Mode Taxonomy

**Validated doctrines**
1. **Title-wins** (R23/24 → 26 → 28 → 29 → 31): a title naming the family beats opposing machinery — validated +2.88pp at v9, then extended one family per iteration with counterfactual risk scans each time.
2. **Corpus convention** ("ground truth follows the folder"): encode CUAD/MAUD/S-1 filing conventions explicitly (R9/10, 12, 13, 22, 28, 35) rather than fighting them with legal reasoning.
3. **Surgical derivation** (`.replace()` chains) + immutable run versions.
4. **One rule per iteration**, banked excess clusters, explicit promotion criteria per version header.

**Recurring failure modes (each spawned a rule class)**
| Failure mode | Example | Counter-rule |
|---|---|---|
| Overcorrection | v4 strict-key discipline → `other` flood (9 regressions) | v5 OTHER-GUARD |
| Rule inversion — model quotes a rule *backwards* | R13 quoted in reverse (v12 maintenance); R21 quoted in reverse (v9 alliance fails) | R29, R28 restate meaning with literal worked examples |
| Rule narrowing — model cites a rule then defeats it | Zounds quotes R26, then rules manufacturing anyway | R30 strengthened form |
| Machinery-over-title | JV governance, license grants, distribution terms steal the titled family | title-wins doctrine |
| First-named-family precedence | Audible "CO-BRANDING, MARKETING AND DISTRIBUTION" → co_branding | R30: order irrelevant |
| Enumeration gaps | `other` missing from option list; R31 list missing "TRANSACTION AGREEMENT" | complete lists / "illustrative, not exhaustive" |
| Good-rule over-fire | R32 on embedded bylaws; R35 inside M&A deals; R26 on affiliates; R10 on operating cores | scope guards & carve-outs (R34–37, R27, R10-exception) |
| GT artifacts | MAUD consideration "other" GT with explicit cash price; S-1 streamer mislabels | **not prompt-fixable — escalated to data side** |
| Runner artifacts | LegalBench 512-token reasoning truncation | runner fix, banked (never a prompt rule) |

---

## IX. Forward Roadmap (Backlog)

| # | Item | Type | Gate / target |
|---|---|---|---|
| 1 | **v15 A/B** on full-509 vs v13-clean baseline | Validation | strict ≥ 0.9430 outside the ±0.006 noise band |
| 2 | v16 candidates: **collaboration-title cluster (3 fails)** + **rule-21 inversion (non-alliance)** — banked since v12 | Prompt | one rule per iteration; counterfactual risk scan first |
| 3 | **Rule 30 reproposition** (v14's strengthened marketing rule) now shielded by R31's license-primary guard — HEMISPHERX boundary noted | Prompt | only if marketing cell regresses post-v15 |
| 4 | **Docclass merge decision**: v4 (R36) vs v5 (R37) vs v6 (R36′) → Phase 3.5 merge on v3 base | Prompt | full-676 validation, 0 doc_type regressions |
| 5 | **GT artifact escalations**: 3 MAUD consideration GTs, 3 S-1 streamer labels, a42 articles_of_incorporation label | Data side | corpus relabel; prompt explicitly not touched |
| 6 | **Vision line first measured runs** (vision_v0, docclass_vision_v0; vision-primary + text fallback) | Eval | baseline the image surface |
| 7 | **Efficiency horizon**: sorter now carries rules 1–31; token-audit/compression refactor once accuracy plateaus (precedent: contracts-specialist v31 refactor, 8,377-token prompt) | Prompt | accuracy must stay inside noise band |
| 8 | **Model-specific calibration**: v13 cross-model spread 0.8782–0.9430 (qwen3.7-flash vs gpt-4.1-nano) suggests per-model rule variants or routing | Strategy | decide after v15 settles |
| 9 | LegalBench (KANBAN-026): runner fix for reasoning truncation; continue `v4_<subtask>` series; banked row 39 | Runner/prompt | see Appendix C |

---

## Appendix A — Run-naming & traceability conventions
Run IDs encode the experiment: `{model}_sorter_{version}_{surface}` (+ `_langfuse` when traced), e.g. `qwen3.7-flash_sorter_v6_subtype_langfuse`, `qwen3.7-flash_sorter_docclass_v3_docclass_full676`. Prompt fingerprints (fp d460e8ac…, d3d7b335…, 5602b71f…, 946ac1c4…) pin the exact string that ran. Standard eval settings: seed 42, temp 0.1, reasoning medium (exceptions documented per run).

## Appendix B — Version registry
All keys resolvable through `PROMPT_VERSIONS` / `get_prompt()`: `sorter_v0…v15`, `sorter_docclass_v0…v6`, `sorter_docclass_vision_v0`, `sorter_vision_v0`. Archived lineage (contracts specialist v1–v16) lives frozen in `src/prompts_archive.py` — pre-documentation era, no research memos; constants imported back so historical experiment identities stay resolvable.

## Appendix C — Sister lineage: LegalBench task classifier (KANBAN-026, GEPA)
Same iteration doctrine applied to LegalBench multi-class tasks (dated entry: subtask series registered 2026-08-15):
- **v0** (format-only, zero doctrine): @94, 4 runs temp 0.0 → 0.7766/0.7872 band; 18 deterministic fails in 3 hearsay clusters.
- **v1** (+ hearsay doctrine rule, regression-scanned vs all 71 correct rows): → **0.8511** (80/94). Full-reasoning diagnostic split the 14 fails: 8 runner artifacts (banked) + 6 genuine, each with quoted model reasoning.
- **v2** (purpose-first ACT/STATE carve-out + knowledge-contradiction repair of v1's own self-contradicting example; regression-scanned vs all 80 correct rows).
- **v3** (+ prohibition-clause special case — shipped with a stray-quote and rule-numbering collision).
- **v4** (hygiene fix only: stray quote removed, rule renumbered 6→7) → base for subtask-specific versions.
- **v4_CRE** (+ conditional-permission carveout rule — from a deterministic 0.8333 fail on the 6-row CRE surface; IGER/CERES permission-structure shape).
- **v4_CNTS** (+ conduct-restriction covenant rule — from an oscillating 1.0/0.8333 fail; Allied/Newegg impair/tarnish covenant; weaker evidence → graded logic repair).
