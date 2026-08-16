# Prompt ablation — per-class deltas (worst/strongest movers)

_Task: `docclass_classification` — per-class paired deltas for the top pairs_

## sorter_docclass_v3 vs sorter_docclass_v5 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |
| merger_agreement | +0.0769 | 0.649 | 13 |

## sorter_docclass_v4 vs sorter_docclass_v5 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |
| merger_agreement | +0.0769 | 0.649 | 13 |

## sorter_docclass_v5 vs sorter_docclass_v3 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| merger_agreement | -0.0769 | 0.000 | 13 |
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |

## sorter_docclass_v5 vs sorter_docclass_v4 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| merger_agreement | -0.0769 | 0.000 | 13 |
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |

## sorter_docclass_v5 vs sorter_docclass_v6 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| merger_agreement | -0.0769 | 0.000 | 13 |
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |

## sorter_docclass_v6 vs sorter_docclass_v5 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| corporate_record | +0.0000 | 0.000 | 6 |
| contract | +0.0000 | 0.000 | 11 |
| merger_agreement | +0.0769 | 0.649 | 13 |
