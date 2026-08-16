# Confidence-gated escalation — accuracy vs cost (Monte Carlo)

_Task: `subtype_classification` · escalated model accuracy parameterized (sensitivity ±5 pp)_

| alpha | accuracy | band (low/high) | cost multiplier | n escalated |
|---|---|---|---|---|
| 0.00 | 0.9209 | [0.9209, 0.9209] | 1.00x | 0 |
| 0.05 | 0.9224 | [0.9199, 0.9249] | 1.10x | 25 |
| 0.10 | 0.9238 | [0.9188, 0.9288] | 1.20x | 51 |
| 0.15 | 0.9253 | [0.9178, 0.9328] | 1.30x | 76 |
| 0.20 | 0.9267 | [0.9167, 0.9367] | 1.40x | 102 |
| 0.25 | 0.9282 | [0.9157, 0.9407] | 1.50x | 127 |
| 0.30 | 0.9296 | [0.9146, 0.9446] | 1.60x | 152 |
| 0.40 | 0.9326 | [0.9126, 0.9526] | 1.80x | 203 |
| 0.50 | 0.9355 | [0.9105, 0.9605] | 2.00x | 254 |

The Pareto point should be chosen from this table, not extrapolated — the low-confidence tail is heterogeneous (near-miss/uncertainty-flagged single-observation docs).
