# Prompt ablation — per-class deltas (worst/strongest movers)

_Task: `subtype_classification` — per-class paired deltas for the top pairs_

## sorter_v3 vs sorter_v10 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| maintenance | -0.8750 | 0.000 | 8 |
| marketing | -0.5000 | 0.000 | 8 |
| collaboration | -0.3333 | 0.000 | 6 |
| promotion | -0.1667 | 0.000 | 6 |
| ip | -0.1667 | 0.000 | 6 |
| reseller | -0.1429 | 0.000 | 7 |
| affiliate | -0.1250 | 0.000 | 8 |
| consulting | +0.0000 | 0.000 | 8 |
| franchise | +0.0000 | 0.000 | 7 |
| agency | +0.0000 | 0.000 | 5 |
| transportation | +0.0000 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 7 |

## sorter_v3 vs sorter_v11 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| maintenance | -0.8750 | 0.000 | 8 |
| marketing | -0.5000 | 0.000 | 8 |
| collaboration | -0.3333 | 0.000 | 6 |
| promotion | -0.1667 | 0.000 | 6 |
| ip | -0.1667 | 0.000 | 6 |
| affiliate | -0.1250 | 0.000 | 8 |
| reseller | +0.0000 | 0.000 | 7 |
| consulting | +0.0000 | 0.000 | 8 |
| franchise | +0.0000 | 0.000 | 7 |
| agency | +0.0000 | 0.000 | 5 |
| transportation | +0.0000 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 7 |

## sorter_v10 vs sorter_v3 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| consulting | +0.0000 | 0.000 | 8 |
| franchise | +0.0000 | 0.000 | 7 |
| agency | +0.0000 | 0.000 | 5 |
| transportation | +0.0000 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 7 |
| affiliate | +0.1250 | 0.639 | 8 |
| reseller | +0.1429 | 0.680 | 7 |
| promotion | +0.1667 | 0.664 | 6 |
| ip | +0.1667 | 0.675 | 6 |
| collaboration | +0.3333 | 0.920 | 6 |
| marketing | +0.5000 | 0.995 | 8 |
| maintenance | +0.8750 | 1.000 | 8 |

## sorter_v11 vs sorter_v3 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| reseller | +0.0000 | 0.000 | 7 |
| consulting | +0.0000 | 0.000 | 8 |
| franchise | +0.0000 | 0.000 | 7 |
| agency | +0.0000 | 0.000 | 5 |
| transportation | +0.0000 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 7 |
| affiliate | +0.1250 | 0.669 | 8 |
| promotion | +0.1667 | 0.664 | 6 |
| ip | +0.1667 | 0.675 | 6 |
| collaboration | +0.3333 | 0.920 | 6 |
| marketing | +0.5000 | 0.995 | 8 |
| maintenance | +0.8750 | 1.000 | 8 |

## sorter_v3 vs sorter_v15 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| maintenance | -0.7273 | 0.000 | 11 |
| marketing | -0.6667 | 0.000 | 9 |
| hosting | -0.3333 | 0.000 | 9 |
| promotion | -0.2500 | 0.000 | 8 |
| affiliate | -0.2500 | 0.000 | 8 |
| collaboration | -0.2000 | 0.000 | 10 |
| ip | -0.1250 | 0.000 | 8 |
| outsourcing | -0.1250 | 0.000 | 8 |
| reseller | -0.1111 | 0.000 | 9 |
| strategic_alliance | -0.1111 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 12 |
| joint_venture | +0.0000 | 0.000 | 5 |
| consulting | +0.0000 | 0.000 | 9 |
| franchise | +0.0000 | 0.000 | 9 |
| agency | +0.0000 | 0.000 | 7 |
| transportation | +0.0000 | 0.000 | 10 |
| supply | +0.0000 | 0.000 | 9 |
| license | +0.0000 | 0.000 | 9 |
| manufacturing | +0.0000 | 0.000 | 8 |
| service | +0.0000 | 0.000 | 9 |
| distributor | +0.0000 | 0.000 | 8 |
| endorsement | +0.0000 | 0.000 | 9 |
| development | +0.0000 | 0.430 | 9 |
| sponsorship | +0.1111 | 0.666 | 9 |

## sorter_v15 vs sorter_v3 (qwen/qwen3.7-flash)

| class | mean Δ | P(A beats B) | n docs |
|---|---|---|---|
| sponsorship | -0.1111 | 0.000 | 9 |
| co_branding | +0.0000 | 0.000 | 12 |
| joint_venture | +0.0000 | 0.000 | 5 |
| consulting | +0.0000 | 0.000 | 9 |
| franchise | +0.0000 | 0.000 | 9 |
| agency | +0.0000 | 0.000 | 7 |
| transportation | +0.0000 | 0.000 | 10 |
| supply | +0.0000 | 0.000 | 9 |
| license | +0.0000 | 0.000 | 9 |
| manufacturing | +0.0000 | 0.000 | 8 |
| service | +0.0000 | 0.000 | 9 |
| distributor | +0.0000 | 0.000 | 8 |
| endorsement | +0.0000 | 0.000 | 9 |
| development | +0.0000 | 0.375 | 9 |
| reseller | +0.1111 | 0.634 | 9 |
| strategic_alliance | +0.1111 | 0.666 | 9 |
| ip | +0.1250 | 0.651 | 8 |
| outsourcing | +0.1250 | 0.651 | 8 |
| collaboration | +0.2000 | 0.901 | 10 |
| promotion | +0.2500 | 0.909 | 8 |
| affiliate | +0.2500 | 0.902 | 8 |
| hosting | +0.3333 | 0.972 | 9 |
| marketing | +0.6667 | 1.000 | 9 |
| maintenance | +0.7273 | 1.000 | 11 |
