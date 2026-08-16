# Paired-bootstrap prompt ablation (Monte Carlo gate)

_Task: `subtype_classification` · corpus-wide paired bootstrap over shared documents_

| model | prompt A | prompt B | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |
|---|---|---|---|---|---|---|---|---|
| qwen/qwen3.7-flash | sorter_v3 | sorter_v10 | 128 | 0.7969 | 0.9375 | -0.1406 | [-0.2109, -0.0781] | 0.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v11 | 128 | 0.7969 | 0.9375 | -0.1406 | [-0.2109, -0.0859] | 0.000 |
| qwen/qwen3.7-flash | sorter_v10 | sorter_v3 | 128 | 0.9375 | 0.7969 | +0.1406 | [+0.0781, +0.2109] | 1.000 |
| qwen/qwen3.7-flash | sorter_v11 | sorter_v3 | 128 | 0.9375 | 0.7969 | +0.1406 | [+0.0859, +0.2109] | 1.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v15 | 214 | 0.8318 | 0.9533 | -0.1215 | [-0.1729, -0.0701] | 0.000 |
| qwen/qwen3.7-flash | sorter_v15 | sorter_v3 | 214 | 0.9533 | 0.8318 | +0.1215 | [+0.0701, +0.1729] | 1.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v10 | 117 | 0.8120 | 0.9316 | -0.1197 | [-0.1880, -0.0513] | 0.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v11 | 117 | 0.8120 | 0.9316 | -0.1197 | [-0.1795, -0.0598] | 0.000 |
| qwen/qwen3.7-flash | sorter_v10 | sorter_v4 | 117 | 0.9316 | 0.8120 | +0.1197 | [+0.0513, +0.1880] | 1.000 |
| qwen/qwen3.7-flash | sorter_v11 | sorter_v4 | 117 | 0.9316 | 0.8120 | +0.1197 | [+0.0598, +0.1795] | 1.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v12 | 214 | 0.8318 | 0.9393 | -0.1075 | [-0.1589, -0.0607] | 0.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v13 | 214 | 0.8318 | 0.9393 | -0.1075 | [-0.1589, -0.0607] | 0.000 |
| qwen/qwen3.7-flash | sorter_v12 | sorter_v3 | 214 | 0.9393 | 0.8318 | +0.1075 | [+0.0607, +0.1589] | 1.000 |
| qwen/qwen3.7-flash | sorter_v13 | sorter_v3 | 214 | 0.9393 | 0.8318 | +0.1075 | [+0.0607, +0.1589] | 1.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v14 | 214 | 0.8318 | 0.9346 | -0.1028 | [-0.1542, -0.0561] | 0.000 |
| qwen/qwen3.7-flash | sorter_v14 | sorter_v3 | 214 | 0.9346 | 0.8318 | +0.1028 | [+0.0561, +0.1542] | 1.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v15 | 186 | 0.8495 | 0.9516 | -0.1022 | [-0.1613, -0.0430] | 0.000 |
| qwen/qwen3.7-flash | sorter_v15 | sorter_v4 | 186 | 0.9516 | 0.8495 | +0.1022 | [+0.0430, +0.1613] | 1.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v9 | 214 | 0.8318 | 0.9299 | -0.0981 | [-0.1449, -0.0514] | 0.000 |
| qwen/qwen3.7-flash | sorter_v9 | sorter_v3 | 214 | 0.9299 | 0.8318 | +0.0981 | [+0.0514, +0.1449] | 1.000 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v7 | 128 | 0.7969 | 0.8906 | -0.0938 | [-0.1484, -0.0469] | 0.000 |
| qwen/qwen3.7-flash | sorter_v7 | sorter_v3 | 128 | 0.8906 | 0.7969 | +0.0938 | [+0.0469, +0.1484] | 1.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v12 | 186 | 0.8495 | 0.9355 | -0.0860 | [-0.1452, -0.0269] | 0.001 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v13 | 186 | 0.8495 | 0.9355 | -0.0860 | [-0.1452, -0.0269] | 0.001 |
| qwen/qwen3.7-flash | sorter_v12 | sorter_v4 | 186 | 0.9355 | 0.8495 | +0.0860 | [+0.0269, +0.1452] | 0.999 |
| qwen/qwen3.7-flash | sorter_v13 | sorter_v4 | 186 | 0.9355 | 0.8495 | +0.0860 | [+0.0269, +0.1452] | 0.999 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v8 | 214 | 0.8318 | 0.9159 | -0.0841 | [-0.1262, -0.0421] | 0.000 |
| qwen/qwen3.7-flash | sorter_v8 | sorter_v3 | 214 | 0.9159 | 0.8318 | +0.0841 | [+0.0421, +0.1262] | 1.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v14 | 186 | 0.8495 | 0.9301 | -0.0806 | [-0.1344, -0.0269] | 0.002 |
| qwen/qwen3.7-flash | sorter_v14 | sorter_v4 | 186 | 0.9301 | 0.8495 | +0.0806 | [+0.0269, +0.1344] | 0.997 |
| qwen/qwen3.7-flash | sorter_v3 | sorter_v6 | 215 | 0.8326 | 0.9116 | -0.0791 | [-0.1256, -0.0372] | 0.000 |
| qwen/qwen3.7-flash | sorter_v6 | sorter_v3 | 215 | 0.9116 | 0.8326 | +0.0791 | [+0.0372, +0.1256] | 1.000 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v7 | 117 | 0.8120 | 0.8889 | -0.0769 | [-0.1453, -0.0085] | 0.009 |
| qwen/qwen3.7-flash | sorter_v7 | sorter_v4 | 117 | 0.8889 | 0.8120 | +0.0769 | [+0.0085, +0.1453] | 0.982 |
| qwen/qwen3.7-flash | sorter_v4 | sorter_v9 | 186 | 0.8495 | 0.9247 | -0.0753 | [-0.1344, -0.0161] | 0.003 |
| qwen/qwen3.7-flash | sorter_v9 | sorter_v4 | 186 | 0.9247 | 0.8495 | +0.0753 | [+0.0161, +0.1344] | 0.995 |
| qwen/qwen3.7-flash | sorter_v7 | sorter_v15 | 240 | 0.8875 | 0.9625 | -0.0750 | [-0.1083, -0.0417] | 0.000 |
| qwen/qwen3.7-flash | sorter_v15 | sorter_v7 | 240 | 0.9625 | 0.8875 | +0.0750 | [+0.0458, +0.1083] | 1.000 |
| qwen/qwen3.7-flash | sorter_v7 | sorter_v13 | 240 | 0.8875 | 0.9583 | -0.0708 | [-0.1042, -0.0375] | 0.000 |
| qwen/qwen3.7-flash | sorter_v13 | sorter_v7 | 240 | 0.9583 | 0.8875 | +0.0708 | [+0.0375, +0.1042] | 1.000 |

Reading: `mean Δ > 0` favors A; a CI excluding zero with high `P(A beats B)` is the promotion signal (same contract as the repo's same-surface A/B runs).
