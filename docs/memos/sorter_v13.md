# Sorter v13 — Maintenance title-wins: the rule-13 inversion cluster, aggregate WIN

**Research question:** KANBAN-023's close-out banked the maintenance cluster
(4 fails @509, rule-13 inversion shape). v12@509 left the maintenance cell at
30/34 (0.8824) — SUNTRONCORP/WELLSFARGO/PRIMEENERGY routed to `other`,
AtnInternational to `service`, with the model quoting rule 13 BACKWARDS. Does
a MAINTENANCE TITLE WINS rule (v13 = v12 + rule 29) resolve the cell, and does
it move the aggregate outside the noise band?

**Companions:** KANBAN-031 (this iteration), `memos/sorter_v12.md`
(the strategic_alliance title-wins predecessor — the rule-28 fix that proved
the title-wins doctrine against rule-inversion failures), `memos/sorter_v10_v11.md`,
`memos/contracts_specialist_v30.md` (noise-floor methodology).

## Answer, Response, + Summary of Results

**Short answer: YES on both counts — the maintenance cell goes 30/34 → 34/34
(1.0) with all 4 failures deterministically recovered and rule-29 reasoning
pinned, and the aggregate moves OUTSIDE the identical-prompt noise band
(paired +0.0137, CI [+0.0020, +0.0255], P(Δ≤0)=0.0090) — v13 is the new
aggregate sorter champion.** Same-surface full-509 A/B
(fp `c2341957…`, seed 42, temp 0.1, reasoning medium, qwen/qwen3.7-flash):

| Version | Strict | Equiv | Scored | Verdict |
|---|---|---|---|---|
| v12 (original, langfuse sink) | 0.9234 (470/509) | 0.9312 | 509/509, 0 err | — |
| **v12 rerun (noise-floor control, Phoenix sink)** | **0.9293 (473/509)** | 0.9352 | 509/509, 0 err | identical-prompt band ±0.0059 |
| **v13 (candidate, clean)** | **0.9430 (480/509)** | 0.9470 | 509/509, 0 err | **aggregate win** |

*(The FIRST v13 run — `…_langfuse` with `subtype_v13_509.jsonl` — was
DEGRADED: 93/509 rows defaulted to `correspondence` by the runner's
except-clause on `Connection error` (OpenRouter transient), producing a
misleading 0.7741. The manifest marks error-defaulted rows "completed", so
resume cannot recover them; replaced by a CLEAN rerun with a fresh manifest
`subtype_v13_509_clean.jsonl` — the same lesson as KANBAN-029's v32 run. The
degraded run stays in the append-only log, superseded by the clean one.)

### The paired A/B (509-row intersection, all rows both-ok)

| Metric | v12 rerun | v13 clean | Δ |
|---|---|---|---|
| strict accuracy | 0.9293 (473/509) | 0.9430 (480/509) | **+0.0137** |
| maintenance cell | 30/34 (0.8824) | **34/34 (1.0)** | +4 |
| recovered rows | — | 8 (incl. all 4 target) | — |
| regressed rows | — | 1 (ImperialGarden, see below) | −1 |
| paired bootstrap 95% CI | — | — | **[+0.0020, +0.0255]** |
| P(Δ≤0) | — | — | **0.0090** |

### The 4 recovered maintenance rows (target cluster, all deterministic)

| Doc | v12 pred | v13 pred | v13 reasoning (excerpt) |
|---|---|---|---|
| SUNTRONCORP `MAINTENANCE AGREEMENT` (capital-contribution covenants) | other | **maintenance** | "Per Rule 29 ('MAINTENANCE TITLE WINS'), an agreement titled 'Maintenance Agreement' that involves financial maintenance obligations (such as capital contributions to maintain liquidity…)" |
| WELLSFARGO `Yield Maintenance Agreement` (ISDA cap confirmation) | other | **maintenance** | "an agreement whose title names maintenance is classified as 'maintenance' even when its operative machinery reads as financial (such as yield-maintenance confirmations under an ISDA master agreement)" |
| PRIMEENERGY `COMPLETION AND LIQUIDITY MAINTENANCE AGREEMENT` | other | **maintenance** | "Per Rule 29, agreements titled 'Maintenance' (including 'Completion and Liquidity Maintenance') are classified…" |
| AtnInternational `Network Build and Maintenance Agreement` (MSA) | service | **maintenance** | "an agreement whose title names maintenance is classified as maintenance even when it includes build/construction obligations" |

The v9-clean rerun also failed SUNTRONCORP/WELLSFARGO/AtnInternational →
3/4 target rows deterministic across three runs; PRIMEENERGY flipped in v12
(same inversion quote) and is recovered here. Control rows
VARIABLESEPARATEACCOUNT + SECURIAN (capital / net-investment maintenance)
passed in every run by quoting rule 13 correctly — the mechanism is model
instability on the trailing financial-sense clause, not a missing rule.

### The 1 regression — a pre-existing outsourcing variance flip, NOT rule 29

ImperialGarden `Outsourcing Contract` (architectural services) → service.
Per-run status: **correct** in v9-clean and the v12-Phoenix rerun; **wrong**
in v12-original, v13-degraded, v13-clean. Rule 29 does not touch the
outsourcing cell (maintenance cell: 0 regressions). This is rule 24's
narrowing shape (model reads "outsourcing = manufacturing/BPO only" and
routes professional services to `service`) — the **banked v14 lesson**
(alongside NEXSTAR's "outsourcing not in the list" hallucination and Paratek's
rule-24 doubt).

### Cost

v13 clean: 509 rows, 0 errors, full-509 surface (~$0.5 at flash pricing,
same order as the v12 control). Both runs used the **Phoenix tracing sink**
(`tracing_backend: phoenix` in the experiment log — the runner now selects
`PhoenixTracer` when `PHOENIX_TRACING=enabled`), verifying the new observability
path end-to-end on a production-scale run.

### Interpretation

1. **The title-wins doctrine generalizes to a fourth family.** Rules 23/24/26
   (promotion/outsourcing/marketing) and 28 (alliance) all beat their
   machinery; rule 29 extends it to maintenance and kills the rule-13
   inversion — the same failure shape (model quoting a rule's trailing clause
   backwards) rule 28 fixed for collaboration. The maintenance cell is now the
   second title-wins cell at 1.0 (with promotion).
2. **The aggregate win is real, not a sample artifact.** +0.0137 with CI
   [+0.0020, +0.0255] and P=0.0090 vs a measured ±0.0059 identical-prompt
   band — outside the band on the 509-doc surface, and the recovery set is
   the diagnosed target cluster (4/4), not 3 easy docs.
3. **No new regression pattern.** The single regression is a pre-existing
   outsourcing-cell variance flip (rule 24), already unstable across runs
   before v13; rule 29 contributed zero maintenance regressions.
4. **Runner degradation discipline held.** The first v13 run's 93 connection
   errors were caught and re-run clean with a fresh manifest before any
   claim — the KANBAN-029 survivorship-bias lesson applied.

*Sources:* `reports/experiment_log.jsonl` (v12 original 2026-08-15 22:19,
v12 rerun phoenix 22:2x, v13 degraded 22:2x, v13 clean 22:3x; all fp
`c2341957…`, seed 42, temp 0.1, reasoning medium); `src/prompts.py`
SORTER_PROMPT_V13; `tests/test_prompts.py::test_sorter_v13_maintenance_title_wins`.

## What questions or uncertainties remain?

- **ImperialGarden + NEXSTAR + Paratek: the outsourcing cell (14/18 @ v12,
  ~0.78) is the next banked arm.** Rule 24 exists but the model narrows it
  ("outsourcing = manufacturing/BPO only") and NEXSTAR hallucinated that the
  `outsourcing` key is absent from the option list (it IS in the enum —
  verified). A v14 rule-24 strengthening (title-wins mirror + "outsourcing IS
  a valid key") targets 3–4 docs; the cell has fluctuated 16/18 ↔ 14/18
  across runs, so a cluster rule needs the full-509 surface again.
- **Other v12 fail families worth a later arm:** development (7 fails,
  heterogeneous — risky single rule), marketing (3), supply (3), sponsorship
  (2).
- **Phoenix sink noise:** the runner's Phoenix path is verified, but the
  LangSmith sidecar still 429s on the tenant quota (non-fatal; spans land in
  Phoenix/experiment log regardless).
