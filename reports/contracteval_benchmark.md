# Directly-mirrored ContractEval benchmark

Pooled over the CUAD test split (one (contract, question) call per row; faithful full-context, temp 0, max_tokens 5000) using ContractEval's EXACT rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the output; token-set Jaccard over positive pairs; false-'no related clause' rate.

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr (own) | false-nr (paper/1244) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3-8b v0 | 4182 | 1244 | 0.765 | 0.630 | 0.511 | 0.565 | 0.531 | 0.145 | 0.137 | 0.137 |

ContractEval Table III reference (F1/F2/Jaccard/false-nr, paper's own 1,244-positive denominator):

| Model | F1 | F2 | Jacc | false-nr |
|---|---|---|---|---|
| gpt-4.1 | 0.641 | 0.672 | 0.472 | 0.071 |
| gpt-4.1-mini | 0.644 | 0.678 | 0.435 | 0.072 |
| gemini-2.5-pro-preview | 0.497 | 0.604 | 0.506 | 0.011 |
| claude-sonnet-4 | 0.523 | 0.578 | 0.458 | 0.025 |
| deepseek-r1-distill-qwen-7b | 0.071 | 0.085 | 0.131 | 0.037 |
| deepseek-r1-0528-qwen3-8b | 0.475 | 0.464 | 0.404 | 0.100 |
| llama-3.1-8b-instruct | 0.392 | 0.370 | 0.300 | 0.214 |
| gemma-3-4b | 0.188 | 0.246 | 0.311 | 0.000 |
| gemma-3-12b | 0.391 | 0.421 | 0.446 | 0.045 |
| qwen3-4b | 0.411 | 0.362 | 0.337 | 0.211 |
| qwen3-4b-thinking | 0.075 | 0.055 | 0.300 | 0.198 |
| qwen3-8b-awq | 0.475 | 0.393 | 0.303 | 0.306 |
| qwen3-8b-awq-thinking | 0.187 | 0.150 | 0.374 | 0.125 |
| qwen3-8b | 0.530 | 0.453 | 0.340 | 0.248 |
| qwen3-8b-thinking | 0.540 | 0.512 | 0.391 | 0.110 |
| qwen3-8b-fp8 | 0.491 | 0.411 | 0.313 | 0.285 |
| qwen3-8b-fp8-thinking | 0.307 | 0.263 | 0.399 | 0.105 |
| qwen3-14b | 0.473 | 0.418 | 0.400 | 0.174 |
| qwen3-14b-thinking | 0.387 | 0.334 | 0.421 | 0.117 |

**Caveat:** our runs use this repo's OpenRouter models (not the paper's exact model set) — the comparison is same-shape/same-metric, not same-model. The false-nr column 'own' divides by the run's own positive count; 'paper/1244' divides by the paper's hardcoded 1,244 positives (identical on the full test set).

## Per-category breakdown — qwen3-8b v0 (Fig-4 analogue)

| Category | n_pairs | n_pos | P | R | F1 | F2 | Jacc |
|---|---|---|---|---|---|---|---|
| Document Name | 102 | 102 | 1.000 | 0.961 | 0.980 | 0.968 | 0.021 |
| Agreement Date | 102 | 93 | 0.916 | 0.935 | 0.925 | 0.931 | 0.021 |
| Parties | 102 | 102 | 1.000 | 0.706 | 0.828 | 0.750 | 0.050 |
| Governing Law | 102 | 83 | 0.966 | 0.687 | 0.803 | 0.729 | 0.167 |
| No-Solicit Of Employees | 102 | 10 | 0.857 | 0.600 | 0.706 | 0.638 | 0.291 |
| Anti-Assignment | 102 | 72 | 0.923 | 0.500 | 0.649 | 0.550 | 0.190 |
| Insurance | 102 | 32 | 0.704 | 0.594 | 0.644 | 0.613 | 0.297 |
| Effective Date | 102 | 70 | 0.622 | 0.657 | 0.639 | 0.650 | 0.052 |
| Renewal Term | 102 | 26 | 0.607 | 0.654 | 0.630 | 0.644 | 0.235 |
| Expiration Date | 102 | 78 | 0.881 | 0.474 | 0.617 | 0.523 | 0.163 |
| Termination For Convenience | 102 | 29 | 0.619 | 0.448 | 0.520 | 0.474 | 0.145 |
| Audit Rights | 102 | 38 | 0.737 | 0.368 | 0.491 | 0.409 | 0.216 |
| Non-Compete | 102 | 23 | 0.500 | 0.478 | 0.489 | 0.482 | 0.224 |
| Cap On Liability | 102 | 44 | 0.737 | 0.318 | 0.444 | 0.359 | 0.221 |
| License Grant | 102 | 50 | 0.640 | 0.320 | 0.427 | 0.356 | 0.239 |
| Change Of Control | 102 | 26 | 0.429 | 0.346 | 0.383 | 0.360 | 0.232 |
| Rofr/Rofo/Rofn | 102 | 17 | 1.000 | 0.235 | 0.381 | 0.278 | 0.219 |
| Covenant Not To Sue | 102 | 24 | 0.833 | 0.208 | 0.333 | 0.245 | 0.119 |
| Exclusivity | 102 | 33 | 0.429 | 0.273 | 0.333 | 0.294 | 0.171 |
| Liquidated Damages | 102 | 14 | 0.400 | 0.286 | 0.333 | 0.303 | 0.198 |
| Ip Ownership Assignment | 102 | 23 | 0.308 | 0.348 | 0.327 | 0.339 | 0.232 |
| Notice Period To Terminate Renewal | 102 | 16 | 0.225 | 0.562 | 0.321 | 0.433 | 0.210 |
| Revenue/Profit Sharing | 102 | 35 | 0.778 | 0.200 | 0.318 | 0.235 | 0.169 |
| Irrevocable Or Perpetual License | 102 | 13 | 0.429 | 0.231 | 0.300 | 0.254 | 0.217 |
| No-Solicit Of Customers | 102 | 7 | 0.286 | 0.286 | 0.286 | 0.286 | 0.194 |
| Non-Disparagement | 102 | 7 | 0.286 | 0.286 | 0.286 | 0.286 | 0.194 |
| Uncapped Liability | 102 | 13 | 0.200 | 0.462 | 0.279 | 0.366 | 0.196 |
| Competitive Restriction Exception | 102 | 16 | 0.227 | 0.312 | 0.263 | 0.291 | 0.185 |
| Post-Termination Services | 102 | 29 | 0.210 | 0.276 | 0.239 | 0.260 | 0.160 |
| Non-Transferable License | 102 | 22 | 0.188 | 0.273 | 0.222 | 0.250 | 0.188 |
| Joint Ip Ownership | 102 | 7 | 0.143 | 0.143 | 0.143 | 0.143 | 0.182 |
| Minimum Commitment | 102 | 32 | 0.500 | 0.062 | 0.111 | 0.076 | 0.148 |
| Third Party Beneficiary | 102 | 6 | 0.059 | 0.167 | 0.087 | 0.122 | 0.147 |
| Volume Restriction | 102 | 17 | 0.143 | 0.059 | 0.083 | 0.067 | 0.093 |
| Affiliate License-Licensee | 102 | 12 | 0.077 | 0.083 | 0.080 | 0.082 | 0.189 |
| Affiliate License-Licensor | 102 | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.139 |
| Most Favored Nation | 102 | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.109 |
| Price Restrictions | 102 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Source Code Escrow | 102 | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.467 |
| Unlimited/All-You-Can-Eat-License | 102 | 3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.148 |
| Warranty Duration | 102 | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.169 |