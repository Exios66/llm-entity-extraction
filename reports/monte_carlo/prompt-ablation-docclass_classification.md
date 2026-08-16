# Paired-bootstrap prompt ablation (Monte Carlo gate)

_Task: `docclass_classification` · corpus-wide paired bootstrap over shared documents_

| model | prompt A | prompt B | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |
|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.7-flash | sorter_docclass_v3 | sorter_docclass_v5 | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| qwen/qwen3.7-flash | sorter_docclass_v4 | sorter_docclass_v5 | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| qwen/qwen3.7-flash | sorter_docclass_v5 | sorter_docclass_v3 | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v5 | sorter_docclass_v4 | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v5 | sorter_docclass_v6 | 30 | 0.8333 | 0.8667 | -0.0333 | [-0.1000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v6 | sorter_docclass_v5 | 30 | 0.8667 | 0.8333 | +0.0333 | [+0.0000, +0.1000] | 0.647 |
| qwen/qwen3.7-flash | sorter_docclass_v3 | sorter_docclass_v6 | 676 | 0.9926 | 0.9941 | -0.0015 | [-0.0044, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v6 | sorter_docclass_v3 | 676 | 0.9941 | 0.9926 | +0.0015 | [+0.0000, +0.0044] | 0.637 |
| qwen/qwen3.7-flash | sorter_docclass_v3 | sorter_docclass_v4 | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v4 | sorter_docclass_v3 | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v4 | sorter_docclass_v6 | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |
| qwen/qwen3.7-flash | sorter_docclass_v6 | sorter_docclass_v4 | 30 | 0.8667 | 0.8667 | +0.0000 | [+0.0000, +0.0000] | 0.000 |

Reading: `mean Δ > 0` favors A; a CI excluding zero with high `P(A beats B)` is the promotion signal (same contract as the repo's same-surface A/B runs).
