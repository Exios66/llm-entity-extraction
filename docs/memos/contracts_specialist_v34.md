# contracts_specialist_v34 — anti-collapse extraction + ContractEval-rubric KPIs

**Research question:** How do we stop the extraction agent from collapsing
expected fields or clause groups, align its output with the ground-truth
labels, and track its performance over time on ContractEval's own rubric
(F1 / F2 / Jaccard / false-"no related clause") — the way the ContractEval
task is tracked?

**Companions:** KANBAN-054 board card; `memos/contracteval_mapping_benchmark.md`
(the evidence base); `src/prompts.py` (v34); `src/contracteval.py::run_kpis`;
`scripts/reporting/backfill_extraction_kpis.py`; `run_extraction_eval.py`
(KPI injection); `SCORING.md`; upstream `llm-dojo-scoring@v0.4.0`
(`contracteval_metrics`, `get_jaccard`).

## Answer, Response, + Summary of Results

**Short answer:** Two changes. (1) **Prompt v34** adds three surgical rules to
v33: R1 FIELD-PRESENCE SELF-CHECK (a schema field is null only when the
document genuinely does not state it), R2 CATEGORY-LEVEL COMPLETENESS (the 32
canonical CUAD YES/NO categories as a post-extraction checklist — a present
category with zero tagged items is INCOMPLETE; additive only), R3 VERBATIM
QUOTING at the GT span grain (quote word-for-word; the GT label is the
clause's own text; a paraphrase scores as a miss). (2) **KPIs**: every
extraction run record now carries `scores.contracteval_kpis` — the pooled
ContractEval confusion (accuracy/P/R/F1/F2), token-set Jaccard over positive
pairs, the false-"no related clause" rate, and the semantic coverage bands —
computed offline and deterministically per run (mapping in-repo
`src/contracteval.py`, metric math upstream v0.4.0), rendered in the
experiment-log markdown, charted in the site trends (F2-led, per human
decision 2026-08-19), and backfillable over historical records. The
discriminating axes for a one-pass extractor stay recall / F2 / Jaccard /
false-nr + the semantic bands (precision is structurally 1.0).

### 1. The evidence the rules are built on (baselines, v32 @ 510 docs)

| Signal | v32@510 | v34 target |
|---|---|---|
| Field presence — `contract_value` | 0.3939 | ≥ 0.7 (R1) |
| Field presence — `renewal_terms` | 0.3698 | ≥ 0.7 (R1) |
| Field presence — `effective_date` / `term_length` | 0.8818 / 0.8271 | ≥ 0.93 (R1, existing rules) |
| key_obligations list recall (bipartite) | 0.781 | ≥ 0.82 (R2+R3) |
| key_obligations predicted / expected items | 8,867 / 3,713 | closer to 1:1 at span grain (R3) |
| ContractEval verbatim recall (mapping) | 0.089 | ≥ 0.15 (R3) |
| Semantic coverage ≥ 0.7 (mapping) | 0.427 | ≥ 0.50 (R2) |
| False-"no related clause" (mapping) | 0.670 | ≤ 0.55 (R2) |

### 2. The KPI block (per-run, offline, deterministic)

`run_kpis(record, master_gt)` = `evaluate_record` + `coverage_bands` over the
run's own rows against the committed `data/cuad/master_clauses.csv`
(509/509 join on the full corpus). Verified on the stored v32@510 record
(`docs/data/runs/107.json`): 14,592 pairs / 3,243 positive / recall 0.0857 /
F1 0.1579 / F2 0.1049 / Jaccard mean 0.2129 / false-nr 0.6818 / semantic
ge0.7 0.4332 — consistent with the mapping memo (small deltas: the stored run
record omits error rows). The block degrades gracefully (absent when no rows
join the GT, like `diagnostics`); the runner drops it when `n_pairs == 0`.

### 3. A/B protocol (50-doc chunked surface only — human decision)

Same-surface discipline (noise floor ±0.03, `memos/contracts_specialist_v30.md`
protocol): sample5 pilots (seed 42, chunked) then the 50-doc chunked A/B,
v33 (champion control) vs v34, both measured on the raw scores (overall,
field presence, category_presence, list diagnostics) AND the new KPI block
(F2 / Jaccard / false-nr / semantic bands). A delta inside ±0.03 overall is a
logic repair, not a win; the KPI axes are the secondary arbiter for the
recall-direction bets R2/R3. Full-corpus KPI baseline stays v32 until the
next full run on the eval machine.

### Interpretation

1. **The collapse problem decomposes into three levels, and v27-v33 fixed
   two of them.** v27/v28 fixed section-level collapse (multi-item family
   sections); v32 fixed the effective_date tie-break; v33 fixed the routing
   granularity (canonical category tags). The mapping benchmark shows the
   remaining levels: field-level nulls (presence 0.39/0.37) and category-level
   omission (67% of present categories produced no mapped item; only 42.7% of
   positive pairs covered at ≥0.7). R1/R2 target exactly those; R3 targets the
   paraphrase penalty that kept verbatim recall at 0.089.
2. **F2 > F1 for this task.** With precision structurally 1.0, F1 merely
   tracks recall at half weight; F2 (β=2) weights recall where the one-pass
   extractor actually loses points (missing categories / paraphrased clauses).
   Jaccard and false-nr measure output effectiveness and laziness — the
   "did we emit anything for a present category" check.
3. **The KPI block is a tracking instrument, not a scorer replacement.** It
   sits alongside `overall_extraction_score` / `category_presence` /
   `diagnostics` (human decision 2026-08-19). The site chart leads with F2,
   Jaccard, semantic ≥0.7, and false-nr so trend history shows the recall
   direction; F1 is available for ContractEval parity.
4. **R3 must not resurrect the v17 dilution regression.** The rule is
   word-for-word quoting *at the GT span grain* — cut preamble/riders, never
   reword what remains. Over-long full-clause quotes dilute similarity and
   score as misses (the v17 lesson); the grain anchor is the guard.

*Sources:* `memos/contracteval_mapping_benchmark.md`; `docs/data/runs/107.json`
(v32@510 diagnostics + mapping KPIs recomputed above); `src/prompts.py`
v17/v27-v33 banners; upstream `llm_dojo_scoring.tasks.contracteval_metrics`
(mirrors arXiv 2508.03080 `Evaluation.py` / `open_source_model.py`).

## What questions or uncertainties remain?

1. **A/B results pending** — the sample5 pilots and the 50-doc chunked A/B
   run on the eval machine (keys + local log live there); this memo's tables
   are baselines and targets, not results. A v34 win on the chunked surface
   must clear the ±0.03 noise floor AND move the KPI axes in the expected
   direction (F2 / Jaccard / semantic ≥0.7 up, false-nr down).
2. **R2's checklist cost** — the 32-category checklist adds reasoning-token
   pressure; if the sample5 pilot shows token growth >15% with no KPI move,
   the checklist needs a cheaper formulation (v31's compression lesson).
3. **Backfill timing** — `backfill_extraction_kpis.py` rewrites the
   experiment log on the eval machine (documented one-time backfill); the
   historical trend chart only fills in after that + `build_site.py` regen.
4. **Chained/eval-machine surfaces** — the chained runner does not yet carry
   the KPI block (own runner, future card); the subtype/docclass tasks have
   their own headline metrics, so "core extraction KPIs" scope is the
   contract-extraction task for now.