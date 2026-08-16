# Sorter v10/v11 — Marketing title-wins arm: the "plateau" was a cluster

**Research question:** The v9 close-out (KANBAN-012) declared ~0.93 the practical
sorter plateau on the 243-doc surface, with 18 fails read as a "1-off long tail".
Is that plateau real, or does the failure tail carry a measurable cluster the
prompt can still fix?

**Companions:** KANBAN-013 (this iteration), `V16_PROPOSITION.md` §17–18,
`docs/slides/08-problems-sorter.md`, `docs/slides/09-fixes-sorter.md`.

## Answer, Response, + Summary of Results

**Short answer: the plateau reading was wrong — the tail is dominated by one
family-level cluster.** The `marketing` cell runs at **0.5 (5/10) on the 243-doc
surface and 0.588 (7/17) on the full-509 corpus — unchanged since v6** (v8:
10/17, v9: 10/17), the lowest accuracy of any family on either surface. The
iteration shipped `sorter_v10` (rule 26 MARKETING TITLE WINS) and its over-fire
repair `sorter_v11` (rule 27 AFFILIATE IS NOT MARKETING). Measured on the same
243-doc stratified surface (fp `fb9f939d…`, seed 42, temp 0.1):

| Version | Strict | Δ vs champion rerun | Verdict |
|---|---|---|---|
| v9 (champion, orig run) | 0.9259 (225/243) | — | — |
| **v9 rerun (noise floor)** | **0.9300 (226/243)** | +0.4pp, 3 docs moved | identical-prompt band ±1 doc |
| v10 | 0.9342 (227/243) | +0.4pp, P(Δ≤0)=0.717 | **inside the noise band** — logic repair |
| **v11 (affiliate carve-out)** | **0.9342 (227/243), equiv 0.9424** | +0.4pp, P(Δ≤0)=0.710 | **inside the noise band** — logic repair; rule-driven accounting clean |

### The v10 A/B (paired, n=243)

Bootstrap 95% CI on the paired per-doc delta (2000 resamples, seed 42):
**[−0.0247, +0.0165], P(Δ≤0) = 0.717** — the candidate is unmeasurable against
the ±1-doc champion-rerun band. Recovered 4 / regressed 3:

- **Recovered (all rule-driven):** Monsanto (EXCLUSIVE AGENCY AND MARKETING →
  marketing), Principal Life (Broker Dealer Marketing and Servicing →
  marketing — rule-6 over-fire killed), Todos (MARKETING AND RESELLER →
  marketing), Dynamex (MARKETING AND TRANSPORTATION SERVICES → transportation
  via the carve-out — a doc that flip-flopped on the champion rerun, now fixed
  deterministically).
- **Regressed (2 rule-driven + 1 noise):** Cybergy and SteelVault — both
  content-titled *"Marketing Affiliate Agreement"* — the model extended rule
  26's open "alongside" list to affiliate/referral machinery; Nexstar
  (OUTSOURCING AGREEMENT → service) is champion-noise, not rule-driven (no
  marketing in title; R24 territory, wrong on this single run only).

### The v11 A/B (paired, n=243) — rule-27 boundary repair

v11 = v10 + rule 27 (AFFILIATE IS NOT MARKETING). Same-surface paired result:
**0.9342 (227/243), equiv 0.9424; delta vs the champion rerun +0.4pp,
bootstrap CI [−0.0247, +0.0165], P(Δ≤0) = 0.710 — still inside the band, but
the rule-driven accounting is now clean and deterministic:**

- All 4 v10 recoveries **held** (Monsanto, Principal, Todos, Dynamex = 1/1/1/1
  across v9-rerun → v10 → v11).
- **Cybergy and SteelVault restored to affiliate** (1→0→1) — rule 27 fired.
- The 3 remaining regressions: LinkPlus (affiliate→joint_venture) is an
  **R27-wording side-effect** (the model read the affiliate-machinery
  definition as exclusive) — **equiv-recovered** (affiliate↔joint_venture),
  documented as a 1-off long-tail residual per the anti-overfitting doctrine
  (no rule for one doc); DominiAdvisor (sponsorship→service) and Ehave
  (reseller→distributor, equiv-recovered) are champion-noise substance reads.
- Family cells at 243: **marketing 0.5 → 0.8** (Zounds/Pacira — the
  manufacturing/distribution-heavy hybrids — remain); affiliate 9/10 strict,
  **10/10 equiv**; collaboration 1.0; strategic_alliance 0.9.

### Why the counterfactual missed the affiliate docs

The reward/risk analysis for rule 26 was keyed on FILENAMES containing
"marketing" — the two affiliate regressions' filenames say "Affiliate
Agreement" while their recitals call the arrangement a marketing agreement.
Filename-keyed counterfactuals miss content-titled docs; the lesson is built
into rule 27 (boundary by machinery, not by filename).

### Cluster evidence (the reflection substrate)

| Cluster | 243 | 509 | Mechanism (model quotes) |
|---|---|---|---|
| marketing → {agency, mfg, endorsement, distributor, reseller, JV, co_branding} | 5/10 | 7/17 | operative-machinery rules (R6/R8/R16) re-classify marketing titles; "the primary legal structure is that of an agency relationship" (Monsanto); "Endorsement riders attached to insurance/annuity/other agreements ARE endorsements" (Principal, R6 over-fire); "the title includes 'Reseller'" (Todos); JV governance read on a pure Marketing Agreement (Vertex) |
| strategic_alliance → {collaboration ×2, license, consulting, service} | 1/10 | 5/32 | Rule-21 *inversion* — "Under Rule 21, collaborative governance structures (like a JSC)… classify them as 'collaboration'" (Iovance, Adaptimmune; rule 21 says the opposite) + R8 substance reads |
| collaboration (all "Cooperation Agreement"-titled) → {JV ×2, development} | 0 | 3/26 | "profit/risk sharing… fitting the 'joint_venture' family under the corpus convention" (China Recycling, SPI); "Per Rule 21, agreements with development machinery… are classified as development" (STW) |
| long tail (1-off each) | 8 | ~10 | not rule material |

### Frontier (sorter) after this iteration

| Cell | Version | Same-surface score | Status |
|---|---|---|---|
| Accuracy champion | sorter_v9 | 0.9259 @243 / 0.9116 @509 | champion holds (v10/v11 inside noise band) |
| Cost champion | sorter_v9 | — | no cheaper arm exists |
| Logic-repair arm | sorter_v10 → v11 | +0.4pp (inside band) | ships as repair; affiliate over-fire fixed by v11 |
| Field specialist (marketing) | v10/v11 (unmeasured) | marketing cell target | A/B completes the arm |

### Interpretation

1. **The plateau claim was surface-level.** Reading failure *counts* (18, 1-off)
   hid the family-level structure: 5 of the 18 v9 fails at 243 were ONE cell
   (marketing), with one mechanism (title-vs-machinery). A per-subtype
   breakdown — not the confusion matrix's row margins — is the right first
   read for the sorter.
2. **Title-wins rules are the validated doctrine** (R23 promotion, R24
   outsourcing, +2.88pp at v9): R26/R27 extend it to marketing with the
   affiliate boundary. The 4 rule-driven recoveries confirm the mechanism
   fires as designed; the 2 affiliate regressions confirm open-ended "alongside"
   lists need explicit family carve-outs.
3. **Sub-noise ≠ no signal.** The recoveries are deterministic (all 4 were
   stable v9 failures on both runs; Dynamex even flip-flopped between the two
   v9 runs). The measurement surface (243 docs) simply cannot resolve a
   one-rule delta against a 1-doc rerun band — the honest verdict is logic
   repair, and the next measurable arm is multi-rule (banked lessons:
   strategic_alliance title-wins, cooperation-title is collaboration) or the
   509-doc surface (~$0.26/run).
4. **Rule-21 inversions are a recurring failure shape** — the model's
   reasoning *cites* rule numbers while contradicting their content
   (Microgenics, El Pollo Loco, Iovance, STW). More rules saying the same
   thing will not fix it; a rule-structure change (or the family-level
   governance carve-outs of R27-style boundary rules) is the next lever.

*Sources:* `reports/experiment_log.jsonl` records
`qwen3.7-flash_sorter_v9_subtype_langfuse` (2026-08-13T05:00, 05:38),
`…_rerun` / `…_v10_subtype_langfuse` / `…_v11_subtype_langfuse` (2026-08-15);
per-row reasoning traces in each record's `results`.

## What questions or uncertainties remain?

- **v11 measurement** — the A/B on the same 243-doc surface (this card's
  closing run): does rule 27 protect Cybergy/SteelVault while the 4 recoveries
  hold? Expect 227–229/243 (still inside the band — label accordingly).
- **The 509 surface** — do R26/R27 scale? The marketing reward set is 7+Dynamex
  at 509 (vs 5 at 243); the affiliate fix protects Cybergy there too.
- **Strategic_alliance (5 fails) and cooperation-title (3 fails) clusters** —
  banked lessons for the next iteration; risk-free counterfactuals verified
  (0 risk docs at 509 for alliance-titled, 12/15 cooperation docs already
  correct).
- **Rule-21 inversion mechanism** — worth a dedicated arm: does renumbering/
  restructuring the rule block (or moving governance carve-outs to the family
  boundary rules) reduce the inversion rate, or is it reasoning-effort noise?
- **The transient 403 (weekly-limit) during the first v11 launch** — the key
  status endpoint reported $20 remaining / 0 usage while the run 403'd; the
  rerun succeeded minutes later. Worth tracking if concurrent agents share the
  account.
