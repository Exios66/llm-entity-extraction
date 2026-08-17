# Monte Carlo selection in the GEPA loop — champion-contender layer + half-corpus effectiveness pilot

**Research question:** Can the KANBAN-048 Monte Carlo suite become a formal
GEPA selection layer — a corpus-wide **champion-contender step** that
complements same-surface A/B — and is it sample-efficient enough to trust
before full adoption? Specifically: does a seeded **half-corpus sample**
of the shared-document surface recover the same champion the full corpus
selects, and how does the paired-bootstrap P(win) separation scale with
document count?

**Companions:** KANBAN-049 board card, issue #17 (FEATURE: MONTE CARLO
SIMULATIONS IN LINE WITH RVL-CDIP CLASSIFIER),
`scripts/reporting/monte_carlo_gepa.py`, outputs in
`reports/monte_carlo/gepa-champion-contender-*.md`, the corpus built by
`monte_carlo_corpus.py` (`reports/monte_carlo/corpus.jsonl`, gitignored),
`memos/monte_carlo_robustness.md` (KANBAN-048).

## Answer, Response, + Summary of Results

**Short answer:** Yes — the MC selection layer works and is sample-efficient.
On the **subtype surface** the full-corpus paired-bootstrap selection names
`sorter_v15` (0.9506 on its own docs, tied with v13 at 7 pairwise wins,
tiebreak by aggregate accuracy), and a seeded **50% sample (254 shared docs)
recovers the same champion**; the 25% sample (127 docs) collapses to a
plateau, placing the sample-efficiency boundary between 25% and 50%. On the
**docclass surface** the selection correctly reports a **plateau** — the
v6-vs-v3 full-676 delta (+0.0015, CI [+0.0000, +0.0044], P(win)=0.637) never
clears the noise-floor gate (CI excludes zero AND P(win) ≥ 0.9), matching the
same-surface A/B verdict that v6's aggregate gain is inside noise. **The
pilot validates full adoption**: the MC selection layer becomes a standard
GEPA gate, with the 25%→plateau result as the documented floor for when the
selection cannot discriminate.

## Results

### 1. The selection layer (`monte_carlo_gepa.py`)

For every ordered prompt-version pair on a model, per-document deltas
`correct(A) − correct(B)` over the SHARED-document surface are resampled
with replacement (n_boot 2000, seed 42) → mean Δ, 95% CI, P(A beats B).
A version *beats* a peer when the CI excludes zero AND P(win) ≥ 0.9 (the
GEPA noise-floor contract). The **MC champion contender** is the version with
the most wins (ties broken by aggregate accuracy on its own docs); when no
version beats any peer the surface is a **plateau** — no measurable champion.
The layer then adds **committee-voting robustness @ K** for the contender and
a **document-count sweep** (25/50/75/100% of shared docs) for the
effectiveness pilot.

### 2. Subtype surface (qwen3.7-flash, 507 shared docs)

| Selection | Contender | Wins | Own-docs accuracy |
|---|---|---|---|
| Full corpus | `sorter_v15` | 7 (tied with v13) | 0.9506 |
| Half-corpus (254 docs, seed 42) | `sorter_v15` | 6 | — |
| 25% sample (127 docs) | **plateau** | — | — |

**Champion recovered by the half-corpus sample: YES.** The strongest-pair
separation scales cleanly with document count:

| fraction | n docs | mean Δ (strongest pair) | P(win) | 95% CI |
|---|---|---|---|---|
| 25% | 127 | −0.0702 (v3→v8) | 0.021 | [−0.1579, 0.0] |
| 50% | 254 | −0.129 (v3→v10) | 0.000 | [−0.2097, −0.0484] |
| 75% | 380 | −0.1383 (v3→v10) | 0.000 | [−0.2128, −0.0745] |
| 100% | 507 | −0.1406 (v3→v10) | 0.000 | [−0.2109, −0.0781] |

The mean Δ converges toward its full-corpus value by 50%, and the CI stops
touching zero at 50% (it touches zero at 25% — the plateau). The early
lineage separation (v3 vs the v10+ family) is large and stable; the selection
among the modern frontier (v9..v15) is decided at 7 wins each for v13/v15.

### 3. Docclass surface (qwen3.7-flash, 676 shared docs)

| Selection | Contender | Detail |
|---|---|---|
| Full corpus | **plateau** | no version beats another outside the CI |
| Half-corpus (338 docs, seed 42) | **plateau** | N/A (no champion) |
| Sweep 25/50/75/100% | **plateau** | — |

The closest call is v6 vs v3 on the full 676: +0.0015 with CI
[+0.0000, +0.0044] and P(win)=0.637 — the CI lower bound is exactly zero, so
the noise-floor contract refuses to crown v6, correctly reproducing the
same-surface A/B conclusion (v6 +0.0030 aggregate, inside the merged-surface
noise floor ≈ 0.000). The diag-30 slice comparisons (v3/v4/v5/v6) all sit
inside the CI as well.

### 4. The relationship to same-surface A/B

The MC champion contender (`sorter_v15`) is selected on **corpus-wide paired
evidence** — every run's shared docs, not one A/B sample — so it can differ
from the A/B-surface crown (v13 stays the same-surface aggregate champion
per `memos/sorter_v15.md`; v15's +0.0020 there was inside the ±0.006 band).
The two layers are complementary: same-surface A/B measures the controlled
delta on one surface; the MC layer aggregates the same evidence across every
paired run and gates on the noise floor. When they disagree, the disagreement
itself is the signal (a version whose corpus-wide wins exceed its A/B delta is
winning on more docs than the A/B surface sampled).

## Interpretation

1. **Half the shared surface is enough on subtype.** 254 shared docs recover
   the full-corpus champion; the boundary for reliable discrimination sits
   between 25% (127 docs → plateau) and 50%. Adoption rule: run the MC
   selection layer at full corpus when ≥ ~250 shared docs exist; use the 25%
   floor as the documented lower bound where the selection can no longer
   separate champions.
2. **The noise-floor gate is doing its job on docclass.** The v6-vs-v3 delta
   at full 676 is +0.0015 with the CI touching zero — refusing to crown v6 is
   the correct behavior, not a failure of the layer. The MC layer protects
   the loop from promoting noise-floor deltas.
3. **P(win) separation is the sample-efficiency metric.** The strongest-pair
   mean Δ converges monotonically toward the full-corpus value as n grows,
   and the CI stops touching zero at the same 50% point where the champion
   emerges — the two signals agree.
4. **The tiebreak matters.** v13 and v15 each win 7 pairwise comparisons; the
   tiebreak (aggregate accuracy on own docs) picks v15 (0.9506). The two are
   effectively co-champions on the corpus; the MC layer's pick is a
   recommendation, and the same-surface A/B remains the controlled
   confirmation step before promotion.
5. **Zero-spend.** The entire layer consumes the already-scored corpus; the
   only spend in the loop is the same-surface A/B that produces the candidate
   versions it selects among.

*Sources:* `scripts/reporting/monte_carlo_gepa.py`,
`reports/monte_carlo/gepa-champion-contender-subtype_classification.md`,
`reports/monte_carlo/gepa-champion-contender-subtype_classification-sample50%.md`,
`reports/monte_carlo/gepa-champion-contender-docclass_classification-sample50%.md`,
`src/monte_carlo.py` (`paired_delta_bootstrap`, `draw_committee`),
`memos/sorter_v15.md`, `memos/monte_carlo_robustness.md`.

## What questions or uncertainties remain?

- **Cross-model generalization:** the pilot is qwen3.7-flash only. The
  sample-efficiency boundary (25%→plateau / 50%→champion) should be re-checked
  on the deepseek-v4-pro sweep before the layer is trusted for model-choice
  decisions, not just prompt-choice.
- **The v13/v15 co-champion case:** the 7-win tie is resolved by aggregate
  accuracy; a paired bootstrap between v13 and v15 specifically (not just vs
  the older lineage) was not isolated — worth a dedicated pair check before
  any promotion decision uses the MC pick alone.
- **Docclass discrimination power:** with only 4 versions and most pairs
  landing inside the CI, the layer cannot yet separate docclass versions — a
  larger docclass lineage (or the vision arm) would give the sweep real
  signal.
- **Corpus provenance:** `corpus.jsonl` is gitignored (derived from the
  experiment log + manifests); the committed reports are the audit record —
  regenerating them requires a re-derivation from the current log state.