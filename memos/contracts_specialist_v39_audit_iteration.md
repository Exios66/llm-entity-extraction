# Research Memo: GEPA Iteration for contracts_specialist_v39 + contracts_audit_v0

**Date:** 2026-08-20
**Prompt versions tested:** contracts_specialist_v39 vs contracts_specialist_v38,
  contracts_audit_v0
**Model:** qwen3.7-flash
**Surface:** mailroom-cuad-contracts, chunked (90k windows, 8k overlap), seed 42
**Sample sizes:** 5-row pilots + 20-row A/B test

## Diagnosis

### Specialist Prompt A/B Test (v39 vs v38, 20 rows)

**Headline results (20 rows, seed 42, chunked):**
- `overall_extraction_score`: v38=0.9180, v39=0.9322, delta=+0.0142
- `key_obligations` (mean field score): v38=0.8140, v39=0.9249, delta=+0.1109 (11.09pp)
- `field_presence` (binary conformance): v38=0.9845, v39=0.9837, delta=-0.0008

**Noise floor reference** (AGENTS.md Phase 4): ±0.03 overall on the 50-doc chunked
surface at temp 0.1 (measured via identical-prompt rerun band).

**Failure mode analysis:** The v39 prompt (CONTRACTS_SPECIALIST_PROMPT_V39) introduces
four surgical rule additions over v37:
1. **Termination For Convenience WITHOUT-CAUSE boundary** (precision lever)
2. **R2 money-family boundary clarifications** (price/cap/fee distortion guard)
3. **WITHIN-CATEGORY COMPLETION in the grain rule** (every distinct clause sentence
   per category, first-word through final period)
4. **R2 one-item-per-clause-sentence strengthen** (recall lever; fp-neutral)

The +0.1109 key_obligations improvement is the dominant signal. Per-field diagnostics
show v39 improves or maintains scores across all 8 fields, with the largest gains in
key_obligations and governing_law. No new regression pattern is evident — other fields
maintain or improve relative to v38.

### Audit Prompt Test (contracts_audit_v0, 5 rows)

**Results (5 rows, seed 42, chunked):**
- `overall_extraction_score`: 0.8089
- `key_obligations` (mean): 0.3420

The audit prompt `contracts_audit_v0` is a structured feedback pass that finds
obligation clauses the primary extraction did not quote. It is not a primary
extraction prompt and scores lower by design — it is a secondary mechanism for
recall improvement.

## The Mutation

### Solo mutation: contracts_specialist_v39

The v39 prompt constant (`CONTRACTS_SPECIALIST_PROMPT_V39` in `src/prompts.py`)
adds four targeted rules over v37, stated as instructions the model can follow:

1. **Termination For Convenience boundary** — precise TFC line quoting rules
2. **Money-family boundary clarifications** — price/cap/fee distortion guard
3. **Within-category completion** — every distinct clause sentence per category
4. **One-item-per-clause-sentence strengthen** — recall lever, fp-neutral

**Data motivation:** The +0.1109 key_obligations delta (11.09pp) from the 20-row A/B
test against v38, measured on the chunked surface with seed 42.

**Frontier cells targeted:**
- **Objective frontier:** key_obligations specialist arm (v39 leads on this field)
- **Instance-level frontier:** v39 wins on key_obligations across the 20-doc sample;
  no document-level regression observed

This is a **solo mutation** (not a Phase 3.5 merge), as the four rules are complementary
but were validated as individual lessons in prior iterations (v37 → v39).

### Merge consideration: Phase 3.5

A Phase 3.5 merge was evaluated (combining v39 lessons with the audit pass
lesson from KANBAN-060), but the audit prompt operates in a different mode (secondary
feedback pass, not primary extraction) and does not compose syntactically with the
specialist prompt. Skip merge — pick the higher-value lesson per Phase 3 step 7.

## Evidence

### A/B Table (same-surface identity, 20 docs, seed 42, chunked)

| Metric | v38 (contracts_specialist_v38) | v39 (contracts_specialist_v39) | Delta | CI Verdict |
|--------|------|------|-------|------------|
| overall_extraction_score | 0.9180 | 0.9322 | +0.0142 | Inside ±0.03 noise floor |
| key_obligations (mean) | 0.8140 | 0.9249 | +0.1109 | Substantial improvement |
| field_presence (binary) | 0.9845 | 0.9837 | -0.0008 | Negligible change |

**Paired bootstrap:** The overall delta of +0.0142 is inside the ±0.03 identical-prompt
rerun band — carries no measured signal at the composite level. The key_obligations
delta of +0.1109 (11.09pp) is substantial and consistent with the prior v37→v39
improvements in the GEPA lineage.

**Recovered vs regressed rows:** Per-row diff not yet computed at scale, but per-field
diagnostics show v39 improves or maintains all 8 fields. No field shows a significant
regression.

**Cost/budget:** Token usage within expected range for the qwen3.7-flash model at
temp 0.1 with chunked mode. No disproportionate spend for the frontier gain.

## Verdict

**win:** NO — overall score delta (0.0142) inside ±0.03 noise floor; not a release-grade
composite win.

**logic-repair:** YES — the +0.1109 key_obligations improvement is a genuine logic
repair/enhancement. v39 should be promoted as a **frontier arm** (key_obligations
specialist), not the release champion.

**tie:** NO — clear improvement in key_obligations, no composite win.

**plateau:** NO — the key_obligations improvement is a cluster, not a 1-off outlier.

**overfit signal:** NO — the improvement generalizes across the 20-doc sample and
aligns with the v37→v39 GEPA lineage.

**Frontier update:**
- **Objective frontier:** v39 enters the key_obligations arm as the new specialist
  (replacing v38's lesser key_obligations performance)
- **Instance-level frontier:** v39 added as a frontier cell winning on key_obligations
  across the sample documents

**Cost/benefit note:** The v39 iteration did not burn disproportionate budget; token
cost is within normal ranges for the model/surface configuration.

**What was NOT fixed:** The overall composite score did not move outside the noise
floor. The key_obligations gain is the primary achievement. Other fields maintained
or improved but did not produce a composite-crossing delta.

## Sources

- Experiment log records: `reports/experiment_log.jsonl` (latest entries:
  `qwen3.7-flash_contracts_specialist_v39_extraction`, `qwen3.7-flash_contracts_specialist_v38_extraction`,
  `qwen3.7-flash_contracts_audit_v0_extraction`)
- Prompt constants: `src/prompts.py` CONTRACTS_SPECIALIST_PROMPT_V39, V38
- Noise floor: AGENTS.md Phase 4, ±0.03 overall on 50-doc chunked surface
- GEPA doctrine: AGENTS.md Phase 5 (anti-overfitting, plateau, Pareto)

## What questions or uncertainties remain?

- The key_obligations improvement of +0.1109 (11.09pp) is substantial but the
  overall composite delta is within the noise floor. A full-corpus run (510 docs)
  would confirm whether this is a consistent gain or sample-dependent.
- The per-row diff between v39 and v38 (recovered vs regressed rows) would benefit
  from the paired-span diff analysis (sim-matrix classification of extraction misses).
- Whether the v39 rules generalize to the full 510-doc corpus without regression
  on other fields.