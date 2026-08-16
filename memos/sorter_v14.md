# Sorter v14 — Marketing title-wins strengthening: logic repair, NOT a win

**Research question:** The marketing cell has been stuck at 14/17 (0.8235)
since v12 with three DETERMINISTIC fails across all runs (v9-clean, v12-orig,
v12-rerun, v13-clean): Zounds "MANUFACTURING, DESIGN AND MARKETING AGREEMENT"
→ manufacturing, PACIRA "STRATEGIC LICENSING, DISTRIBUTION AND MARKETING
AGREEMENT" → distributor, Audible "CO-BRANDING, MARKETING AND DISTRIBUTION
AGREEMENT" → co_branding — all with the model QUOTING rule 26 and then
defeating it (the rule-narrowing shape rules 28/29 fixed). Does a rule-30
strengthening (machinery re-reads / rule-9 hybrid read / first-named-family
precedence killed) resolve the cell and move the aggregate?

**Companions:** KANBAN-032 (this iteration), `memos/sorter_v13.md` (the rule-29
maintenance win — the same inversion shape), `memos/sorter_v12.md`,
`memos/sorter_v10_v11.md` (marketing title-wins origin, rules 26/27).

## Answer, Response, + Summary of Results

**Short answer: NO on the aggregate — v14 0.9371 vs v13-clean 0.9430 =
−0.0059, paired CI [−0.0177, +0.0059], P(Δ≤0)=0.8765, INSIDE the ±0.006
identical-prompt noise band and NEGATIVE in direction → v14 is a LOGIC REPAIR,
not a claimed win; v13 stays the aggregate champion.** The rule fired
correctly on 2 of its 3 deterministic targets (marketing cell 14/17 → 16/17),
but the flagged Playboy counterfactual FIRED (carve-out too narrow) and Zounds
resists even its own literal example. Same-surface full-509 A/B (fp
`c2341957…`, seed 42, temp 0.1, reasoning medium, qwen/qwen3.7-flash, Phoenix
sink, 0 errors both runs):

| Version | Strict | Marketing cell | Recovered | Regressed | Verdict |
|---|---|---|---|---|---|
| **v13 (champion, clean)** | **0.9430** | 14/17 (0.8235) | — | — | champion |
| **v14 (candidate)** | **0.9371** | **16/17 (0.9412)** | 3 | 6 | **logic repair, NOT a win** |

*(The v13 noise-floor rerun was SKIPPED per the human's token-budget
directive; the ±0.006 band on this surface was already measured twice —
v9 0.9116→0.9175, v12 0.9234→0.9293 — and v13-clean is the champion
measurement.)*

### What rule 30 DID do — the directional gain (banked)

| Doc | v13 pred | v14 pred | v14 reasoning (excerpt) |
|---|---|---|---|
| Audible "CO-BRANDING, MARKETING AND DISTRIBUTION" | co_branding | **marketing** | rule-30 fired: co-branding section does not outrank the marketing title |
| PACIRA "STRATEGIC LICENSING, DISTRIBUTION AND MARKETING" | distributor | **marketing** | rule-30 fired: rule 9's hybrid machinery read does not apply to a marketing-named title |
| Zounds "MANUFACTURING, DESIGN AND MARKETING" | manufacturing | manufacturing (STILL) | **the model quotes rule 30's literal example and re-reads the manufacturing machinery anyway** — a model-bound resistance |

The marketing cell went 14/17 → 16/17 — a +2 deterministic recovery — and the
two recovered rows cite rule 30's exact language. That directional evidence is
real and is banked for the carve-out fix (v15).

### What went wrong — two findings

1. **The flagged counterfactual FIRED (rule-driven regression):** Playboy
   "CONTENT LICENSE, MARKETING AND SALES AGREEMENT" regressed license→marketing
   (v13: license OK → v14: marketing FAIL). Rule 30's carve-out (a) cited only
   the exact phrase "Content License Agreement" with a marketing annex; the
   model did not generalize it to any **license-PRIMARY** title that co-names
   marketing/sales. The carve-out must be widened: license-primary titles keep
   license regardless of co-named marketing/sales. **This is the v15 lesson.**
2. **Zounds is a model-bound ceiling:** rule 30 contains the doc's own title as
   the leading example ("MANUFACTURING, DESIGN AND MARKETING AGREEMENT" ->
   marketing, not manufacturing) and the model still routes to manufacturing,
   reasoning "the primary function described in the recitals and detailed
   sections is the manufacturing and supply of goods". Unlike the maintenance
   docs (which quoted rule 29 correctly once added), this doc's machinery read
   is strong enough to defeat the explicit example. A v15 restatement is
   unlikely to fix it; flag as a possible model-bound 1-doc residual.

### The 4 noise regressions (not rule-30-driven)

LinkPlus (affiliate→collaboration), Liquidmetal (development→collaboration),
Ehave (reseller→license), HALITRON (sponsorship→endorsement) — all in families
rule 30 never touches. Identical-prompt reruns on this surface flip 4–6 docs
(v12-orig 39 fails vs v12-rerun 36 fails), so these sit inside the noise band.

### Interpretation

1. **The title-wins doctrine does NOT transfer to marketing as cleanly as to
   maintenance/alliance.** Rules 28/29 succeeded because the target docs' GT
   matched the title and the counterfactuals were clean. Marketing's
   counterfactual set includes license-primary hybrids (Playboy) that rule 26's
   carve-out handled but rule 30's restatement re-opened — the strengthening
   moved the machinery-read failure into a carve-out failure.
2. **The deterministic-target evidence is still worth banking:** 2/3 recovered
   with rule-30 reasoning pinned is a directional signal, and the v15 carve-out
   widening (license-PRIMARY titles exempt) directly addresses the only
   rule-driven regression.
3. **Aggregate discipline held:** a −0.0059 inside-band delta is NOT a win even
   though the target cell improved — the Pareto check (6 regressed, 1
   rule-driven) blocks release-grade. v13 stays champion.

*Sources:* `reports/experiment_log.jsonl` (v13-clean 2026-08-15, v14 2026-08-15,
both fp `c2341957…`, seed 42, temp 0.1, reasoning medium, Phoenix sink);
`src/prompts.py` SORTER_PROMPT_V14; `tests/test_prompts.py::test_sorter_v14_marketing_title_wins_strengthened`.

## What questions or uncertainties remain?

- **v15 mutation:** widen rule 30's carve-out (a) to ANY license-PRIMARY title
  ("CONTENT LICENSE, MARKETING AND SALES AGREEMENT" -> license, not marketing),
  keep rules 26/30's machinery-kill, and re-test on the full-509 surface. The
  banked directional gain (+2 marketing) + carve-out fix should flip the
  aggregate positive — but the A/B verdict depends on the noise band.
- **Zounds:** one doc resists even its literal example — candidate for the
  instance-level frontier's "model-bound residual" bucket; a v15 restatement
  may or may not catch it.
- **Outsourcing (banked from KANBAN-031):** NEXSTAR hallucination +
  ImperialGarden narrowing remain — the cell is 15/18 and NEXSTAR is the only
  deterministic family_confusion fail. The v15 slot is now contested between
  the marketing carve-out (stronger: 2 deterministic recoveries already
  measured) and the outsourcing rule-24 fix (1 deterministic + 1 variance).
