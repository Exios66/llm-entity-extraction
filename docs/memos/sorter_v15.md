# Sorter v15 — License-primary title-wins: logic repair, NOT a win

**Research question:** Rule 26's carve-out (a) protected only the exact phrase
"Content License Agreement", and the v14 marketing-strengthening re-opened the
license-primary counterfactual (Playboy "CONTENT LICENSE, MARKETING AND SALES
AGREEMENT" regressed license→marketing). Cross-model failure traces on the SAME
`sorter_v13` prompt (full-509, seed 42, temp 0.1, reasoning medium — qwen3.7-flash
champion 0.9430, gpt-5-nano 0.8978, gpt-4.1-nano 0.8782, llama-4-scout 0.8880,
deepseek-v4-flash 0.9332) show a universal license-primary cluster: "Content
License Agreement" titles mis-routed to `other`/`ip`/`marketing`/`manufacturing`/
`joint_venture`. Does widening carve-out (a) to ANY license-PRIMARY title (rule
31) fix the cluster and move the aggregate?

**Companions:** KANBAN-038 (this iteration), `memos/sorter_v14.md` (the banked
carve-out-widening lesson), `memos/sorter_v13.md` (the rule-29 maintenance win),
`memos/sorter_v12.md`.

## Answer, Response, + Summary of Results

**Short answer: NO on the aggregate — v15 0.9450 vs v13-clean 0.9430 =
+0.0020, paired bootstrap 95% CI [−0.0059, +0.0098], P(Δ≤0)=0.4160, INSIDE the
±0.006 identical-prompt noise band → v15 is a LOGIC REPAIR, not a claimed win;
v13 stays the aggregate champion.** Rule 31 fired correctly on its single
champion-surface deterministic target (PACIRA, named verbatim in the carve-out),
but the license-primary cluster that motivated the rule was already ~handled on
the champion surface — the one remaining "Content License Agreement" fail
(LejuHoldings) is a GT-labeling artifact, not a genuine license-primary
mis-route. Same-surface full-509 A/B (seed 42, temp 0.1, reasoning medium,
qwen/qwen3.7-flash, Phoenix sink, 0 errors both runs):

| Version | Strict | Equiv | Fails | Recovered | Regressed | Verdict |
|---|---|---|---|---|---|---|
| **v13 (champion, clean)** | **0.9430** | 0.9470 | 29 | — | — | champion |
| **v15 (candidate)** | **0.9450** | 0.9509 | 28 | 3 | 2 | **logic repair, NOT a win** |

### What rule 31 DID do — the directional gain (banked)

| Doc | v13 pred | v15 pred | v15 reasoning (excerpt) |
|---|---|---|---|
| PACIRA "STRATEGIC LICENSING, DISTRIBUTION AND MARKETING" | distributor | **marketing** | rule 31's carve-out re-states rule 26 with PACIRA's exact shape: licensing is merely co-named, marketing is the primary family |
| NEXSTAR "OUTSOURCING AGREEMENT" | service | **outsourcing** | rule-24 variance flip (not rule 31 — the model quotes rule 24) |
| ImperialGarden "Outsourcing Contract" | service | **outsourcing** | rule-24 variance flip (pre-existing, flagged in the v13 memo) |

PACIRA was a DETERMINISTIC cross-model fail (champion → distributor, gpt-5-nano
→ license, gpt-4.1-nano → strategic_alliance, llama-4-scout → license), so its
recovery is a real, rule-31-driven win — the carve-out names the doc's shape
directly. NEXSTAR and ImperialGarden are rule-24 outsourcing variance flips that
rule 31 never touches (the v13 memo already flagged ImperialGarden as such).

### What went wrong — two findings

1. **The rule's motivating target was already ~fixed on the champion.** The
   license-primary cluster is a WEAK-MODEL problem, not a champion problem: the
   champion v13-clean only fails ONE "Content License Agreement" doc —
   LejuHoldings "Content License Agreement2" → `other`. That exhibit's actual
   title is **"Mutual Termination Agreement"** (it terminates a prior license);
   the CUAD folder labels it "license", but the document content genuinely
   matches no family, so rule 8 routes it to `other` and rule 31 cannot
   legitimately override that. **Rule 31 is correct to leave it; the GT label
   is the artifact.**
2. **The regressions are rule-24/rule-19 variance, not rule 31.** Paratek
   ("Outsourcing Agreement" with a manufacturing-services core) flipped
   outsourcing→manufacturing — the same rule-24 machinery-read variance that
   NEXSTAR/ImperialGarden flip on the other side. Artara ("Sponsored Research
   and License Agreement") moved license→development, which is the rules 19/21
   license+development carve-out working AS DESIGNED and is equiv-recovered
   (license↔development is an equivalence family).

### Interpretation

1. **The title-wins doctrine is now over-applied at the margins.** Rules
   23/24/26/28/29/31 together pin every "X-TITLE WINS" shape, but the marginal
   variance (rule-24 outsourcing flips, rule-19/21 development reads) now
   dominates the failure set — the champion's remaining 22+ family_confusion
   fails are in development (6), service (4), sponsorship/supply (5), and the
   single-doc universal families (franchise/co_branding/distributor/hosting/
   agency), not license-primary.
2. **The directional evidence is banked, not claimed:** PACIRA is recovered by
   name (a real +1 on a deterministic cross-model fail), but the aggregate delta
   (+0.0020) is inside the ±0.006 band, so v15 joins the frontier as a
   license-primary field specialist, not a champion.
3. **Follow-on clusters are the real remaining headroom** — development (6
   champion fails: Ritter/RevolutionMedicines/EmeraldHealth/ElPolloLoco/
   ArcaUsTreasury/Eton), service (4: IntegrityFunds/GpaqAcquisition/KUBIENT/
   FEDERATED), and cooperation→collaboration (CHINARECYCLING on the champion;
   10+ docs in the weaker models) are each larger than the license-primary
   cluster ever was. These are the candidate v16 slots.

*Sources:* `reports/experiment_log.jsonl` (v13-clean 2026-08-16 03:56, v15
2026-08-16 07:0x, both fp `c2341957…`, seed 42, temp 0.1, reasoning medium,
Phoenix sink); `src/prompts.py` `SORTER_PROMPT_V15`; `tests/test_prompts.py::
test_sorter_v15_license_primary_title_wins`; cross-model sweeps gpt-5-nano /
gpt-4.1-nano / llama-4-scout / deepseek-v4-flash on `sorter_v13`.

## What questions or uncertainties remain?

- **v16 candidates:** development (6 champion fails — the largest single
  cluster), service (4), and cooperation→collaboration (cross-model huge) each
  outrank license-primary. The next slot should target ONE of these with the
  same cross-model cluster discipline.
- **The GT-labeling artifact:** LejuHoldings "Content License Agreement2" (a
  Mutual Termination Agreement) will never resolve under rule 31 — either the
  GT folder is corrected or it is accepted as a permanent 1-doc residual.
- **Zounds** remains model-bound (unresolved since v14) — a marketing-titled
  doc the model routes to manufacturing despite rule 26/30 naming its literal
  title.
