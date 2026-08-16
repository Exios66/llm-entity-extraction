# Monte Carlo robustness of the sorter/docclass surfaces

**Research question:** What do zero-spend what-if simulations over the joint
reasoning corpus (17,691 scored rows across 195 experiment-log records +
manifests) say about the levers available to this pipeline — committee voting,
confidence-gated escalation, prompt-version promotion, retry/fallback
reliability, and few-shot exemplar recovery?

**Companions:** KANBAN-048 board card + Archive, issue #17 (FEATURE: MONTE
CARLO SIMULATIONS IN LINE WITH RVL-CDIP CLASSIFIER), the RVL-CDIP-classifier
`monte_carlo_*` suite it ports, `src/monte_carlo.py`,
`scripts/reporting/monte_carlo_*.py`, outputs in `reports/monte_carlo/`.

## Answer, Response, + Summary of Results

**Short answer:** The simulation suite ports cleanly onto this repo's corpus
(no Braintrust backfill needed — reasoning is already local). The headline
findings mirror the RVL-CDIP manuscript's structure but with this repo's
numbers: **committee voting is a weak lever** (subtype 0.9209 → 0.9513 at
K=25, ~4x cost; doc_type is saturated at 0.9928 and gains nothing),
**confidence-gated escalation is a small, surface-dependent lever** (+0.44 pp
at alpha 0.15 on the subtype surface; it *hurts* on the doc_type surface where
the baseline already exceeds the escalated-model assumption), **the retry/
fallback pipeline is already failure-proof at scale** (0.24% observed failure
rate; ~0.004% with the fallback pass), **prompt progress is quantified and
statistically solid for the early lineage** (v3→v10/v11 +14.1 pp, P(win)=1.000
on 128 shared docs) **but the newest docclass steps remain unproven on shared
slices**, and **targeted exemplars could recover ~4% of the subtype error
pool** (6 pairs selected, development→license first with +25.0 expected error
flips).

## Results

### 1. The joint corpus (`monte_carlo_corpus.py`)

17,691 scored rows: subtype_classification 16,162 · docclass_classification
1,442 · chained_sorter_extractor 80 · sorter_classification 7. 17,640 rows
(99.7%) carry a reasoning trace; 42 rows are non-completed. Prompt versions
resolve from manifest headers (subtype rows split across the sorter_v3→v13
lineage + the 8-model sweep; docclass rows across v3/v4/v5/v6). 508 subtype
docs + 676 docclass docs are observed by multiple runs — the paired-comparison
surface.

### 2. Ensemble voting (`monte_carlo_ensemble.py`)

| Surface | K=1 | K=3 | K=10 | K=25 | ceiling gain |
|---|---|---|---|---|---|
| subtype (508 docs) | 0.9209 | 0.9362 | 0.9472 | 0.9513 | +3.0 pp at ~4-25x cost |
| docclass (676 docs) | 0.9928 | 0.9929 | 0.9929 | — | ~0 (saturated) |

The doc_type dimension is already at its committee ceiling; the subtype
surface has ~3 pp of committee headroom at 10-25x cost — the variance budget
lives in prompt quality, not sampling noise (same conclusion as the RVL-CDIP
manuscript).

### 3. Confidence-gated escalation (`monte_carlo_ensemble.py`)

With the escalated model at the measured deepseek-v4-pro level (0.95):

| alpha (subtype) | accuracy | cost | alpha (docclass) | accuracy | cost |
|---|---|---|---|---|---|
| 0.00 | 0.9209 | 1.0x | 0.00 | 0.9928 | 1.0x |
| 0.15 | 0.9253 | 1.3x | 0.15 | 0.9788 | 1.3x |
| 0.50 | 0.9355 | 2.0x | 0.50 | 0.9464 | 2.0x |

Escalation pays only where the baseline is below the escalated model: +0.44 pp
at alpha 0.15 on subtype, but it **loses** on doc_type (baseline 0.9928 >
0.95). The 76 lowest-confidence subtype docs (alpha 0.15) carry a simulated
tail accuracy of 0.6392 — the verification recipe (`monte_carlo_verify.py`)
targets exactly this tail.

### 4. Paired-bootstrap prompt ablation (`monte_carlo_prompt_ablation.py`)

156 subtype + 12 docclass (model, A, B) pairs evaluated on shared docs. The
early lineage is statistically decisive: **sorter_v10/v11 beat v3 by +14.1 pp
(P(win)=1.000, n=128 shared)**; **v15 beats v3 by +12.2 pp (P(win)=1.000,
n=214)**. On the docclass diag-30 surface, **v5 loses to v3/v4/v6 (−3.3 pp,
P(win)=0.000 for v5's direction)** — corpus-wide confirmation of the
diagnostic A/B that dropped the v5 arm; the v3↔v6 delta on the 30-doc surface
stays inside the noise band (P(win)=0.647), so the v6 promotion rests on the
full-676 run, not this shared slice.

### 5. Failure pipeline (`monte_carlo_failures.py`)

Observed single-attempt failure rate 0.2374% (42/17,691), length-limit
pressure 0.006%. Simulated: max_tries=1 + fallback → 0.004%; max_tries=1
without fallback → 0.202% — **the fallback pass is the failure lever** (same
shape as the RVL-CDIP finding, at a much smaller absolute surface). At 320K
docs the current config expects ~0 failures; tail risk P(>1%) = 0.

### 6. Exemplar mining (`monte_carlo_exemplars.py`)

Near-miss traces are abundant (correct reasoning naming the decoy): 268 for
maintenance→license, 212 for development→license, 86 for
collaboration→joint_venture. Monte Carlo selection under a 12k-char budget
picks 6 subtype pairs (~+25.0 expected error flips from development→license,
+23.5 from development→collaboration) and 4 docclass pairs
(contract→corporate_record first, +4.0). Ready-to-paste appendices:
`reports/monte_carlo/exemplar-appendix-{task}.md` — direct input for the next
sorter/docclass prompt iteration.

## Interpretation

1. **The suite is corpus-driven and cheap** — every scenario re-runs in
   seconds on the local corpus with zero model spend; the only spend path is
   the optional `--run-eval` verification recipe.
2. **The levers rank the same as RVL-CDIP**: committee voting ≈ weak, escalation
   = surface-dependent, fallback = reliability lever, prompt progress = the
   real variance budget, exemplars = targeted error recovery.
3. **Doc_type is done** (0.9928, no committee/escalation headroom); the subtype
   surface still has committee headroom (~3 pp) and a 4%-of-errors exemplar
   recovery pool.

*Sources:* `reports/experiment_log.jsonl`, `data/manifests/*.jsonl`,
`src/monte_carlo.py`, `scripts/reporting/monte_carlo_{corpus,ensemble,
prompt_ablation,failures,exemplars,verify}.py`, outputs under
`reports/monte_carlo/`, RVL-CDIP-classifier `scripts/braintrust/monte_carlo_*`
(ported per issue #17).

## What questions or uncertainties remain?

- **Verification evals**: the simulated tail accuracy (0.6392) and the
  exemplar error-flip gains are untested against real runs — run
  `monte_carlo_verify.py --run-eval` (the only spend) and compare measured vs
  simulated on the same docs.
- **The exemplar appendix has not been tried in a prompt** — the next
  sorter/docclass iteration should A/B the exemplar-appended prompt on the
  targeted confusion-pair slice.
- **Extraction-task Monte Carlo** (field-level ensemble/ablation) is a natural
  extension; the classification-focused scenarios do not touch it.
