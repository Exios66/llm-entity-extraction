# GEPA champion contender — Monte Carlo selection

_Task: `docclass_classification` · model `qwen/qwen3.7-flash` · paired-bootstrap ablation over the shared-document surface (n_boot=2000, seed 42, min_shared=20)_

## Full-corpus selection

**Plateau** — no prompt version beats another outside the CI on the shared surface (versions: sorter_docclass_v3, sorter_docclass_v4, sorter_docclass_v5, sorter_docclass_v6).
### Decisive pairwise statistics (strongest pairs)

| pair (A → B) | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |
|---|---|---|---|---|---|---|
| `sorter_docclass_v3` → `sorter_docclass_v5` | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| `sorter_docclass_v4` → `sorter_docclass_v5` | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| `sorter_docclass_v5` → `sorter_docclass_v3` | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| `sorter_docclass_v5` → `sorter_docclass_v4` | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| `sorter_docclass_v5` → `sorter_docclass_v6` | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| `sorter_docclass_v6` → `sorter_docclass_v5` | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| `sorter_docclass_v3` → `sorter_docclass_v6` | 676 | 0.9926 | 0.9941 | -0.0015 | [-0.0044, +0.0000] | 0.000 |
| `sorter_docclass_v6` → `sorter_docclass_v3` | 676 | 0.9941 | 0.9926 | +0.0015 | [+0.0000, +0.0044] | 0.637 |
| `sorter_docclass_v3` → `sorter_docclass_v4` | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| `sorter_docclass_v4` → `sorter_docclass_v3` | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| `sorter_docclass_v4` → `sorter_docclass_v6` | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| `sorter_docclass_v6` → `sorter_docclass_v4` | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |

## Half-corpus pilot (fraction 0.5, seed 42)

- shared docs available: **676**
- sampled selection: **plateau** (no measurable champion on the sample)
- **champion recovered by the half-corpus sample: N/A (plateau)**

## Document-count sweep (P(win) separation vs sample size)

| fraction | n docs | contender | strongest pair | mean Δ | P(win) | 95% CI |
|---|---|---|---|---|---|---|
| 25% | 169 | plateau | sorter_docclass_v3 → sorter_docclass_v6 | 0.0 | 0.0 | [0.0, 0.0] |
| 50% | 338 | plateau | sorter_docclass_v3 → sorter_docclass_v6 | 0.0 | 0.0 | [0.0, 0.0] |
| 75% | 507 | plateau | sorter_docclass_v3 → sorter_docclass_v6 | 0.0 | 0.0 | [0.0, 0.0] |
| 100% | 676 | plateau | sorter_docclass_v3 → sorter_docclass_v5 | 0.0333 | 0.6475 | [0.0, 0.1] |

Reading: the `P(win)`/CI columns show how cleanly the strongest pair separates at each sample size — the effectiveness (sample-efficiency) evidence for adopting the MC selection layer in the GEPA loop.
