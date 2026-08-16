# Ensemble voting + confidence-gated escalation (Monte Carlo)

_Task: `docclass_classification` · corpus: `reports/monte_carlo/corpus.jsonl`_

**676 documents** with observations (multi-run docs: 676).

## Accuracy(K) — committee majority voting

| K | accuracy | 95% CI |
|---|---|---|
| 1 | 0.9928 | [0.9861, 0.9979] |
| 3 | 0.9929 | [0.9862, 0.9981] |
| 5 | 0.9930 | [0.9863, 0.9984] |
| 10 | 0.9929 | [0.9862, 0.9984] |

## Per-class accuracy at K (worst 10)

| class | K=1 | K=3 | K=10 | n docs |
|---|---|---|---|---|
| merger_agreement | 0.987 | 0.988 | 0.988 | 152 |
| contract | 0.994 | 0.994 | 0.994 | 509 |
| corporate_record | 1.000 | 1.000 | 1.000 | 15 |

## Confidence heuristic (n=676)

- median 0.940 · mean 0.947 · below 0.5: 2 docs
