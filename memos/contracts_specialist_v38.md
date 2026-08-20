# contracts_specialist_v38 — sparse-family shape completion + named re-scan (KANBAN-057)

**Research question:** the ContractEval-rubric F1 is 0.3277 (v36 champion, recall 0.2187,
precision 0.653, laziness 0.8492) — where does the residual miss mass live at the KPI
(verbatim-containment) level, what is genuinely prompt-fixable, and which ONE rule
recovers the most F1 on the next mutation?

**Companions:** `memos/contracts_specialist_v37_design.md` (payment lever), `memos/contracts_specialist_v36.md`
(grain reconciliation — the champion), KANBAN-057 card, KANBAN-058 (scorer/GT defect card).

## Answer, Response, + Summary of Results

### Short answer

A KPI-level fn decomposition of the v36 record over **1,686 positive pairs** (master GT
CSV + `build_category_output` + upstream `contracteval_classified`) shows **v36 FN =
1,319 splits into 493 whitespace-artifact (37%) + 242 `<omitted>`-placeholder GT labels
(18%) + 48 genuine near-misses (4%) + 536 ABSENT (41%)** — the first two buckets are NOT
prompt-fixable and are flagged to the scoring lane (KANBAN-058); the prompt lever is the
**536 absent pairs** (no quoted span reaches ≥0.7 token coverage of the GT clause),
concentrated in families the model never quotes. v38 = v36 + 2 surgical `.replace()`
edits: enumeration entries **27-29** (Warranty Duration, Competitive Restriction
Exception, Volume Restriction — absent/nameless families with real-clause shapes) +
an **UNDER-QUOTED FAMILY RE-SCAN** sentence in the R2 completeness block naming the
absent-heavy families. Projected F1 0.328 → 0.37-0.40 (80-130 new matched pairs) —
a candidate win outside the measured noise band, with the shape-conversion rate as the
swing factor.

### The decomposition (the artifact discovery)

Method: for every positive (doc, category) pair in the v36 record, classify the miss
using the repo's own KPI machinery (`build_category_output` → `contracteval_classified`
= every GT label span verbatim-contained in the synthesized output; best-span token
containment from the disaggregated predicted spans; GT labels from `load_master_gt`):

| bucket | pairs | % of FN | fixable by? |
|---|---|---|---|
| verbatim TP | 367 | — | — |
| **whitespace artifact** | **493** | 37% | scorer/GT (KANBAN-058) |
| `<omitted>`-label GT | 242 | 18% | GT cleaning (KANBAN-058) |
| genuine near-miss (0.7-0.99 containment) | 48 | 4% | prompt (small) |
| **absent (< 0.7 coverage)** | **536** | 41% | **prompt (v38)** |

The whitespace artifact: 502/1,686 positive labels carry `\n` or 2+ space runs from the
master CSV; `contracteval_classified` strips only ` \n\`` from the edges and compares the
raw substring — the extraction pipeline whitespace-collapses the model's spans, so
character- and token-complete quotes fail the TP predicate on the GT side. 695 GT labels
carry literal `<omitted>`/`[omitted]` placeholders that no model output can contain
(242 on positive pairs). Projected scorer fix alone: recall 0.219 → 0.51, F1 0.3277 →
~0.63, zero LLM calls (re-score stored records). This is the single largest available
improvement on the surface and it is NOT a prompt problem — the prompt iterations must
not compensate for it.

### The absent mass (v38's target)

Absent-fn leaders (v36): Post-Termination Services 55, Anti-Assignment 43, Cap On
Liability 43, Minimum Commitment 37, License Grant 33, **Warranty Duration 32 (absent
from the prompt entirely — `'Warranty'` not found in v36)**, Revenue/Profit Sharing 31,
**Competitive Restriction Exception 29 + Volume Restriction 29 (guard-list names but NO
enumeration shape entries)**, Covenant Not To Sue 25, Liquidated Damages 22,
Non-Transferable License 20, Change Of Control 23, Insurance 27, Audit Rights 24.

Two mechanisms: (a) **absent families** — the model doesn't know the shape (Warranty,
Competitive Restriction Exception, Volume Restriction); (b) **named-but-not-fired** —
Covenant/Post-Termination/Liquidated have shape-complete enumeration entries yet stay
absent-heavy, proving the generic R2 checklist self-check ("a category present in the
text but with ZERO tagged entries is INCOMPLETE — scan back") does not fire in practice;
the fix is a NAMED re-scan duty. Tag-collapse and vocabulary drift were measured and
REJECTED as levers: the KPI's best-match fallback routing maps quoted spans by GT-label
containment regardless of tags (only ~30 recoverable drift pairs), and the tag-collapse
residue (98/255 v36) is a reasoning-hygiene issue, not an F1 driver.

### The v38 rule (ONE change)

1. **Enumeration entries 27-29** (after entry 26): Warranty Duration (warranty-period
   clauses + commencement — real GT examples + "32 of 32 present clauses never quoted"),
   Competitive Restriction Exception (notwithstanding carve-out shapes + "39 of 39"
   stat), Volume Restriction (quantity/amount ceilings + "35 of 39" stat).
2. **UNDER-QUOTED FAMILY RE-SCAN** in the R2 block: names the absent-heavy families
   (Warranty, Competitive Restriction Exception, Volume Restriction, Covenant, Post-
   Termination, Liquidated, license variants, ROFR, Joint Ip Ownership) with the
   536/1686 stat, placed after the ADDING-only discipline and adjacent to the
   never-fabricate guard.

Precision risk ~zero: the target families carry 0-6 fp across the surface (distinctive
clause shapes; the fabrication guard stays). Contradiction check: carve-out ≠ Non-Compete,
Volume ceiling ≠ Minimum Commitment floor; re-scan spellings aligned to the guard list
(`Joint Ip Ownership`). Crossover decision: v37's payment block NOT folded (measured
F1-flat + precision 0.653→0.613 on the current scorer; its money quotes become assets
after KANBAN-058 — a v39 crossover candidate).

### Interpretation

1. The headline F1 (0.3277) is dominated by GT-side artifacts (55% of FN unfixable by
   any prompt); the honest prompt ceiling on this surface is recall ~0.35-0.40.
2. The v38 lever is the largest clean prompt-fixable mass: ~536 absent pairs, of which
   ~320 sit in the targeted families with near-zero fp risk.
3. v38's A/B vs v36 must run on the CURRENT scorer (same-surface identity; the
   whitespace noise is common to both arms) — the KANBAN-058 fix re-ranks both arms
   afterwards and does not invalidate the paired delta.
4. Shape-complete-but-not-fired is the deeper lesson: generic checklist language does
   not move this model; named families with measured stats do (v37's payment block
   behaved the same way — it moved false-nr because it named families).

*Sources:* `reports/experiment_log.jsonl` (v36/v37 records), `data/cuad/master_clauses.csv`,
`src/contracteval.py` (build_category_output, load_master_gt), upstream
`llm_dojo_scoring.tasks.contracteval_metrics/contracteval_classified`, v38 constant +
`tests/test_prompts.py::test_contracts_v38_sparse_family_shapes`.

## What questions or uncertainties remain?

- The shape-conversion rate: will the model quote the newly-shaped clauses at v36's
  full-sentence grain (conversion 25-40% → 80-130 matched pairs; < 25% → logic repair)?
- After KANBAN-058, the re-ranked baseline may change the frontier (v37's money quotes
  convert; v38's absent mass partially overlaps the artifact buckets).
- The `<omitted>` GT labels (695) need a corpus-side cleaning decision — CUAD's own
  label text vs the master CSV's placeholder convention.