# Sorter v12 — Strategic-alliance title-wins: the first banked KANBAN-013 cluster

**Research question:** KANBAN-013's close-out banked the strategic_alliance
cluster (5 fails @509, all family_confusion) for a dedicated arm. Does a
STRATEGIC ALLIANCE TITLE WINS rule (v12 = v11 + rule 28) resolve that cluster
on the full-509 surface, and does it move the aggregate outside the noise
band?

**Companions:** KANBAN-023 (this iteration), `memos/sorter_v10_v11.md`
(the banked-cluster origin), `memos/contracts_specialist_v30.md` (noise-floor
methodology).

## Answer, Response, + Summary of Results

**Short answer: the cluster IS resolved — 3 of the 4 strategic_alliance
failures on the clean v9 control are deterministically recovered with rule-28
reasoning pinned (Intricon remains) — but the aggregate delta is inside the
noise band, so v12 ships as a LOGIC REPAIR / strategic_alliance
field-specialist, NOT an aggregate champion.** Same-surface full-509 A/B
(fp `c2341957…`, seed 42, temp 0.1, reasoning medium, qwen/qwen3.7-flash):

| Version | Strict | Equiv | Scored | Verdict |
|---|---|---|---|---|
| v9 (orig benchmark, 2026-08-13) | 0.9116 (464/509) | 0.9194 | 509/509, 0 err | — |
| **v9 clean rerun (noise-floor control)** | **0.9175 (467/509)** | 0.9214 | 509/509, 0 err | identical-prompt band |
| **v12 (candidate)** | **0.9234 (470/509)** | 0.9312 | 509/509, 0 err | **logic repair** |

*(The FIRST v9 @509 rerun — `…_rerun_509` — was DEGRADED: 42 transient
`generator didn't stop after throw()` errors left 467/509 scored (0.9143 on
the subset); it was replaced by a clean rerun `…_rerun_509_clean` as the
control.)*

### The A/B (paired, n=509)

- **Noise floor** (v9-orig vs v9-clean, identical prompt): delta **+0.0059**,
  paired 95% CI **[−0.0039, +0.0157]**, P(Δ≤0)=0.165.
- **Candidate** (v12 vs v9-clean): delta **+0.0059**, paired CI
  **[−0.0098, +0.0216]**, P(Δ≤0)=0.251 — **inside the band**, same magnitude
  as the identical-prompt rerun movement.
- Recovered 9 / regressed 6 (net +3 docs).

### strategic_alliance cell (the rule's target)

| Run | Cell | Fails |
|---|---|---|
| v9-clean | 28/32 (0.875) | Iovance→collaboration, Intricon→license, Giggles→consulting, Adaptimmune→collaboration |
| **v12** | **31/32 (0.9688)** | **Intricon→license only** |

The 3 recoveries (Iovance, Giggles, Adaptimmune) are **deterministic and
rule-28-driven** — each v12 reasoning block explicitly cites rule 28
(*"According to Rule 28 ('STRATEGIC ALLIANCE TITLE WINS'), an agreement whose
title names the alliance family is classified as strategic_alliance, even when
its operative…"*). **Intricon remains → license**: rule 28's text explicitly
carves out *"granting a technology license with royalty payments ->
strategic_alliance, not license"*, but the model still read the license
substance (conf 0.95) — a 1-off residual, banked not ruled (anti-overfit
doctrine).

### Recovered (9) vs regressed (6) — attribution

**Recovered:** 3× strategic_alliance (rule 28, deterministic) + 4× marketing
(Monsanto, Principal, Todos, Vertex — v10/v11's already-shipped marketing
rules, not rule 28) + STWResources (collaboration, rule-21 territory) +
Dynamex (transportation carve-out). All 4 marketing recoveries were already
deterministic v10/v11 wins carried into v12.

**Regressed (6) — NONE are strategic_alliance docs and NONE are rule-28
driven** (every v12 reasoning block argues from pre-existing Rule 9/13/24
machinery): Ehave (reseller→distributor, **equiv-recovered** via
reseller↔distributor), LinkPlus (affiliate→joint_venture, **equiv-recovered**
via affiliate↔JV — the known R27-wording regression from KANBAN-013), 2×
outsourcing→{service, manufacturing} (ImperialGarden — already wrong in v9-orig;
Paratek — Rule-24 title-vs-machinery boundary), Liquidmetal
(development→manufacturing, Rule-9 hybrid), PRIMEENERGY (maintenance→other,
Rule-13 financial-maintenance — already wrong in the degraded rerun). 2 of the
6 were already unstable across v9 runs; the strict-only losses are the known
hybrid-boundary cells, not a new regression pattern.

### Frontier (sorter) after this iteration

| Cell | Version | Same-surface score | Status |
|---|---|---|---|
| Accuracy champion | sorter_v9 | 0.9116 @509 (rerun 0.9175) | holds — v12 aggregate inside the band |
| Cost champion | sorter_v9 | — | no cheaper arm exists |
| Logic-repair arm | v12 | +0.0059 @509 (inside band) | ships; aggregate unmeasured |
| Field specialist (strategic_alliance) | v12 | cell 28/32 → 31/32 deterministic | A/B completes the arm |

### Interpretation

1. **The cluster read from KANBAN-013 transferred.** All five v9 fails were
   alliance-titled, family_confusion, with the counterfactual 0-risk (32/32
   alliance-titled docs GT strategic_alliance). Rule 28 fired on 3/4 clean
   control fails as designed; the mechanism (title-wins beating machinery) is
   the same validated doctrine as R23/24/26.
2. **Aggregate inside the band despite the cell win.** +0.0059 @509 equals the
   identical-prompt rerun movement — the 509 surface cannot resolve a 3-doc
   rule delta against a ~±0.006 band any better than the 243 surface resolved
   v10/v11. The honest verdict is logic repair with a real cell effect.
3. **Rule-28's license carve-out missed Intricon** — a genuinely hard doc
   (the operative section IS a full license grant, conf 0.95). One doc = not
   rule material; banked for a future multi-rule or re-baseline.
4. **No rule-28 regression pattern.** The 6 regressed rows all argue from
   pre-existing Rule 9/13/24 machinery and 2 are equiv-recovered; the strict
   losses are the known hybrid-boundary cells, unchanged in shape.
5. **Cost is flat** (+3.8% tokens: 7,242,673 vs 6,872,876 — the ~700-char rule
   28 block; ~$0.270 vs $0.260) — no Pareto concern.

*Sources:* `reports/experiment_log.jsonl` records
`qwen3.7-flash_sorter_v9_subtype_langfuse` (2026-08-13),
`qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509` (degraded — discarded as
control), `qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509_clean` (noise
floor), `qwen3.7-flash_sorter_v12_subtype_langfuse` + `…_pilot` (2026-08-15);
per-row reasoning in each record's `results`.
