# GEPA champion contender — Monte Carlo selection

_Task: `subtype_classification` · model `qwen/qwen3.7-flash` · paired-bootstrap ablation over the shared-document surface (n_boot=2000, seed 42, min_shared=20)_

## Full-corpus selection

**MC champion contender: `sorter_v15`** (accuracy 0.9506 on its own docs, beats 7 peer(s)).

### Pairwise wins (CI excludes zero + P(win) >= 0.9)

- `sorter_v13`: **7** wins
- `sorter_v15`: **7** wins
- `sorter_v10`: **6** wins
- `sorter_v11`: **6** wins
- `sorter_v12`: **6** wins
- `sorter_v14`: **6** wins
- `sorter_v9`: **3** wins
- `sorter_v7`: **2** wins
- `sorter_v8`: **2** wins
- `sorter_v5`: **1** wins
- `sorter_v6`: **1** wins

### Decisive pairwise statistics (strongest pairs)

| pair (A → B) | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |
|---|---|---|---|---|---|---|
| `sorter_v3` → `sorter_v10` | 128 | 0.7969 | 0.9375 | -0.1406 | [-0.2109, -0.0781] | 0.000 |
| `sorter_v3` → `sorter_v11` | 128 | 0.7969 | 0.9375 | -0.1406 | [-0.2109, -0.0859] | 0.000 |
| `sorter_v10` → `sorter_v3` | 128 | 0.9375 | 0.7969 | +0.1406 | [+0.0781, +0.2109] | 1.000 |
| `sorter_v11` → `sorter_v3` | 128 | 0.9375 | 0.7969 | +0.1406 | [+0.0859, +0.2109] | 1.000 |
| `sorter_v3` → `sorter_v15` | 214 | 0.8318 | 0.9533 | -0.1215 | [-0.1729, -0.0701] | 0.000 |
| `sorter_v15` → `sorter_v3` | 214 | 0.9533 | 0.8318 | +0.1215 | [+0.0701, +0.1729] | 1.000 |
| `sorter_v4` → `sorter_v10` | 117 | 0.8120 | 0.9316 | -0.1197 | [-0.1880, -0.0513] | 0.000 |
| `sorter_v4` → `sorter_v11` | 117 | 0.8120 | 0.9316 | -0.1197 | [-0.1795, -0.0598] | 0.000 |
| `sorter_v10` → `sorter_v4` | 117 | 0.9316 | 0.8120 | +0.1197 | [+0.0513, +0.1880] | 1.000 |
| `sorter_v11` → `sorter_v4` | 117 | 0.9316 | 0.8120 | +0.1197 | [+0.0598, +0.1795] | 1.000 |
| `sorter_v3` → `sorter_v12` | 214 | 0.8318 | 0.9393 | -0.1075 | [-0.1589, -0.0607] | 0.000 |
| `sorter_v3` → `sorter_v13` | 214 | 0.8318 | 0.9393 | -0.1075 | [-0.1589, -0.0607] | 0.000 |

## Half-corpus pilot (fraction 0.5, seed 42)

- shared docs available: **507**
- sampled selection: **`sorter_v15`** (beats 6 peer(s))
- **champion recovered by the half-corpus sample: YES**

## Document-count sweep (P(win) separation vs sample size)

| fraction | n docs | contender | strongest pair | mean Δ | P(win) | 95% CI |
|---|---|---|---|---|---|---|
| 25% | 127 | plateau | sorter_v3 → sorter_v8 | -0.0702 | 0.021 | [-0.1579, 0.0] |
| 50% | 254 | sorter_v15 | sorter_v3 → sorter_v10 | -0.129 | 0.0 | [-0.2097, -0.0484] |
| 75% | 380 | sorter_v15 | sorter_v3 → sorter_v10 | -0.1383 | 0.0 | [-0.2128, -0.0745] |
| 100% | 507 | sorter_v15 | sorter_v3 → sorter_v10 | -0.1406 | 0.0 | [-0.2109, -0.0781] |

Reading: the `P(win)`/CI columns show how cleanly the strongest pair separates at each sample size — the effectiveness (sample-efficiency) evidence for adopting the MC selection layer in the GEPA loop.
