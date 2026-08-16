# Confidence-gated escalation — accuracy vs cost (Monte Carlo)

_Task: `docclass_classification` · escalated model accuracy parameterized (sensitivity ±5 pp)_

| alpha | accuracy | band (low/high) | cost multiplier | n escalated |
|---|---|---|---|---|
| 0.00 | 0.9928 | [0.9928, 0.9928] | 1.00x | 0 |
| 0.05 | 0.9881 | [0.9856, 0.9906] | 1.10x | 34 |
| 0.10 | 0.9835 | [0.9785, 0.9885] | 1.20x | 68 |
| 0.15 | 0.9788 | [0.9713, 0.9863] | 1.30x | 101 |
| 0.20 | 0.9742 | [0.9642, 0.9842] | 1.40x | 135 |
| 0.25 | 0.9696 | [0.9571, 0.9821] | 1.50x | 169 |
| 0.30 | 0.9649 | [0.9499, 0.9799] | 1.60x | 203 |
| 0.40 | 0.9557 | [0.9357, 0.9757] | 1.80x | 270 |
| 0.50 | 0.9464 | [0.9214, 0.9714] | 2.00x | 338 |

The Pareto point should be chosen from this table, not extrapolated — the low-confidence tail is heterogeneous (near-miss/uncertainty-flagged single-observation docs).
