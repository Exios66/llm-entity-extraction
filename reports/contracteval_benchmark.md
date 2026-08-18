# Directly-mirrored ContractEval benchmark

Pooled over the CUAD test split (one (contract, question) call per row; faithful full-context, temp 0, max_tokens 5000) using ContractEval's EXACT rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the output; token-set Jaccard over positive pairs; false-'no related clause' rate.

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr (own) | false-nr (paper/1244) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.7-flash v2 | 4182 | 1244 | 0.700 | 0.497 | 0.580 | 0.535 | 0.561 | 0.648 | 0.043 | 0.043 |
| qwen3.7-flash v1 | 4182 | 1244 | 0.696 | 0.490 | 0.602 | 0.541 | 0.576 | 0.608 | 0.045 | 0.045 |
| qwen3.7-flash v0 | 4182 | 1244 | 0.681 | 0.474 | 0.666 | 0.554 | 0.616 | 0.506 | 0.029 | 0.029 |
| qwen3.7-flash v0 | 100 | 35 | 0.550 | 0.396 | 0.543 | 0.458 | 0.505 | 0.343 | 0.114 | 0.003 |

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

## Per-category breakdown — qwen3.7-flash v2 (Fig-4 analogue)

| Category | n_pairs | n_pos | P | R | F1 | F2 | Jacc |
|---|---|---|---|---|---|---|---|
| Agreement Date | 102 | 93 | 0.902 | 0.892 | 0.897 | 0.894 | 0.633 |
| Document Name | 102 | 102 | 1.000 | 0.804 | 0.891 | 0.837 | 0.817 |
| Parties | 102 | 102 | 1.000 | 0.794 | 0.885 | 0.828 | 0.295 |
| Governing Law | 102 | 83 | 0.970 | 0.771 | 0.859 | 0.804 | 0.917 |
| Anti-Assignment | 102 | 72 | 0.915 | 0.597 | 0.723 | 0.642 | 0.788 |
| Insurance | 102 | 32 | 0.719 | 0.719 | 0.719 | 0.719 | 0.831 |
| Expiration Date | 102 | 78 | 0.842 | 0.615 | 0.711 | 0.650 | 0.758 |
| No-Solicit Of Employees | 102 | 10 | 0.750 | 0.600 | 0.667 | 0.625 | 0.866 |
| Effective Date | 102 | 70 | 0.608 | 0.686 | 0.644 | 0.668 | 0.699 |
| Audit Rights | 102 | 38 | 0.783 | 0.474 | 0.590 | 0.514 | 0.665 |
| Renewal Term | 102 | 26 | 0.475 | 0.731 | 0.576 | 0.660 | 0.848 |
| Liquidated Damages | 102 | 14 | 0.471 | 0.571 | 0.516 | 0.548 | 0.585 |
| Covenant Not To Sue | 102 | 24 | 0.818 | 0.375 | 0.514 | 0.421 | 0.565 |
| Cap On Liability | 102 | 44 | 0.643 | 0.409 | 0.500 | 0.441 | 0.672 |
| Termination For Convenience | 102 | 29 | 0.346 | 0.621 | 0.444 | 0.536 | 0.800 |
| Non-Compete | 102 | 23 | 0.351 | 0.565 | 0.433 | 0.504 | 0.580 |
| License Grant | 102 | 50 | 0.586 | 0.340 | 0.430 | 0.371 | 0.673 |
| Revenue/Profit Sharing | 102 | 35 | 0.500 | 0.371 | 0.426 | 0.392 | 0.537 |
| Change Of Control | 102 | 26 | 0.325 | 0.500 | 0.394 | 0.451 | 0.647 |
| No-Solicit Of Customers | 102 | 7 | 0.500 | 0.286 | 0.364 | 0.312 | 0.784 |
| Non-Disparagement | 102 | 7 | 0.300 | 0.429 | 0.353 | 0.395 | 0.577 |
| Notice Period To Terminate Renewal | 102 | 16 | 0.233 | 0.625 | 0.339 | 0.467 | 0.804 |
| Uncapped Liability | 102 | 13 | 0.211 | 0.846 | 0.339 | 0.529 | 0.830 |
| Most Favored Nation | 102 | 3 | 0.333 | 0.333 | 0.333 | 0.333 | 0.487 |
| Competitive Restriction Exception | 102 | 16 | 0.250 | 0.438 | 0.318 | 0.380 | 0.580 |
| Exclusivity | 102 | 33 | 0.289 | 0.333 | 0.310 | 0.324 | 0.515 |
| Rofr/Rofo/Rofn | 102 | 17 | 0.600 | 0.176 | 0.273 | 0.205 | 0.512 |
| Irrevocable Or Perpetual License | 102 | 13 | 0.152 | 0.538 | 0.237 | 0.357 | 0.704 |
| Post-Termination Services | 102 | 29 | 0.172 | 0.345 | 0.230 | 0.287 | 0.329 |
| Ip Ownership Assignment | 102 | 23 | 0.179 | 0.304 | 0.226 | 0.267 | 0.448 |
| Non-Transferable License | 102 | 22 | 0.160 | 0.364 | 0.222 | 0.290 | 0.686 |
| Affiliate License-Licensee | 102 | 12 | 0.135 | 0.417 | 0.204 | 0.294 | 0.688 |
| Unlimited/All-You-Can-Eat-License | 102 | 3 | 0.100 | 0.667 | 0.174 | 0.312 | 0.821 |
| Third Party Beneficiary | 102 | 6 | 0.088 | 0.500 | 0.150 | 0.259 | 0.664 |
| Minimum Commitment | 102 | 32 | 0.273 | 0.094 | 0.140 | 0.108 | 0.300 |
| Warranty Duration | 102 | 10 | 0.095 | 0.200 | 0.129 | 0.164 | 0.379 |
| Affiliate License-Licensor | 102 | 6 | 0.056 | 0.167 | 0.083 | 0.119 | 0.536 |
| Volume Restriction | 102 | 17 | 0.071 | 0.059 | 0.065 | 0.061 | 0.158 |
| Joint Ip Ownership | 102 | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.700 |
| Price Restrictions | 102 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Source Code Escrow | 102 | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.641 |