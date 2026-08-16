# Ensemble voting + confidence-gated escalation (Monte Carlo)

_Task: `subtype_classification` · corpus: `reports/monte_carlo/corpus.jsonl`_

**508 documents** with observations (multi-run docs: 508).

## Accuracy(K) — committee majority voting

| K | accuracy | 95% CI |
|---|---|---|
| 1 | 0.9209 | [0.9041, 0.9369] |
| 2 | 0.9212 | [0.9042, 0.9372] |
| 3 | 0.9362 | [0.9190, 0.9518] |
| 5 | 0.9426 | [0.9254, 0.9584] |
| 7 | 0.9451 | [0.9280, 0.9612] |
| 10 | 0.9472 | [0.9300, 0.9634] |
| 15 | 0.9498 | [0.9322, 0.9661] |
| 25 | 0.9513 | [0.9338, 0.9676] |

## Per-class accuracy at K (worst 10)

| class | K=1 | K=3 | K=10 | n docs |
|---|---|---|---|---|
| marketing | 0.690 | 0.703 | 0.715 | 17 |
| development | 0.781 | 0.807 | 0.824 | 28 |
| collaboration | 0.853 | 0.900 | 0.932 | 26 |
| service | 0.858 | 0.860 | 0.860 | 28 |
| hosting | 0.877 | 0.916 | 0.944 | 20 |
| reseller | 0.890 | 0.900 | 0.899 | 12 |
| supply | 0.896 | 0.899 | 0.902 | 18 |
| affiliate | 0.899 | 0.935 | 0.969 | 10 |
| maintenance | 0.915 | 0.948 | 0.975 | 34 |
| promotion | 0.916 | 0.960 | 0.989 | 12 |

## Confidence heuristic (n=508)

- median 0.919 · mean 0.854 · below 0.5: 15 docs
