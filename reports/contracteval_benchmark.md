# Directly-mirrored ContractEval benchmark

Pooled over the CUAD test split (one (contract, question) call per row; faithful full-context, temp 0, max_tokens 5000) using ContractEval's EXACT rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the output; token-set Jaccard over positive pairs; false-'no related clause' rate.

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr (own) | false-nr (paper/1244) |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-4.1-mini v1 | 4182 | 1244 | 0.790 | 0.638 | 0.675 | 0.656 | 0.667 | 0.467 | 0.084 | 0.084 |
| qwen3.7-flash v3 | 4182 | 1244 | 0.685 | 0.478 | 0.661 | 0.555 | 0.614 | 0.526 | 0.037 | 0.037 |
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

## Per-category breakdown — gpt-4.1-mini v1 (Fig-4 analogue)

| Category | n_pairs | n_pos | P | R | F1 | F2 | Jacc |
|---|---|---|---|---|---|---|---|
| Governing Law | 102 | 83 | 0.987 | 0.904 | 0.943 | 0.919 | 0.722 |
| Parties | 102 | 102 | 1.000 | 0.882 | 0.938 | 0.904 | 0.194 |
| Agreement Date | 102 | 93 | 0.926 | 0.946 | 0.936 | 0.942 | 0.149 |
| Document Name | 102 | 102 | 1.000 | 0.784 | 0.879 | 0.820 | 0.488 |
| Expiration Date | 102 | 78 | 0.887 | 0.808 | 0.846 | 0.823 | 0.748 |
| Anti-Assignment | 102 | 72 | 0.962 | 0.708 | 0.816 | 0.748 | 0.689 |
| Renewal Term | 102 | 26 | 0.619 | 1.000 | 0.765 | 0.890 | 0.735 |
| Effective Date | 102 | 70 | 0.655 | 0.814 | 0.726 | 0.777 | 0.290 |
| No-Solicit Of Employees | 102 | 10 | 0.700 | 0.700 | 0.700 | 0.700 | 0.777 |
| Change Of Control | 102 | 26 | 0.739 | 0.654 | 0.694 | 0.669 | 0.472 |
| Audit Rights | 102 | 38 | 0.875 | 0.553 | 0.677 | 0.597 | 0.526 |
| Revenue/Profit Sharing | 102 | 35 | 0.778 | 0.600 | 0.677 | 0.629 | 0.252 |
| Insurance | 102 | 32 | 0.677 | 0.656 | 0.667 | 0.660 | 0.778 |
| Liquidated Damages | 102 | 14 | 0.800 | 0.571 | 0.667 | 0.606 | 0.425 |
| License Grant | 102 | 50 | 0.885 | 0.460 | 0.605 | 0.509 | 0.470 |
| Competitive Restriction Exception | 102 | 16 | 0.500 | 0.750 | 0.600 | 0.682 | 0.510 |
| Irrevocable Or Perpetual License | 102 | 13 | 0.533 | 0.615 | 0.571 | 0.597 | 0.678 |
| Affiliate License-Licensee | 102 | 12 | 0.471 | 0.667 | 0.552 | 0.615 | 0.531 |
| Covenant Not To Sue | 102 | 24 | 1.000 | 0.375 | 0.545 | 0.429 | 0.384 |
| Unlimited/All-You-Can-Eat-License | 102 | 3 | 0.375 | 1.000 | 0.545 | 0.750 | 0.705 |
| Termination For Convenience | 102 | 29 | 0.423 | 0.759 | 0.543 | 0.655 | 0.696 |
| Non-Compete | 102 | 23 | 0.500 | 0.522 | 0.511 | 0.517 | 0.514 |
| Most Favored Nation | 102 | 3 | 1.000 | 0.333 | 0.500 | 0.385 | 0.195 |
| No-Solicit Of Customers | 102 | 7 | 0.444 | 0.571 | 0.500 | 0.540 | 0.603 |
| Non-Disparagement | 102 | 7 | 0.500 | 0.429 | 0.462 | 0.441 | 0.417 |
| Uncapped Liability | 102 | 13 | 0.293 | 0.923 | 0.444 | 0.645 | 0.554 |
| Cap On Liability | 102 | 44 | 0.923 | 0.273 | 0.421 | 0.318 | 0.440 |
| Exclusivity | 102 | 33 | 0.448 | 0.394 | 0.419 | 0.404 | 0.428 |
| Affiliate License-Licensor | 102 | 6 | 0.333 | 0.500 | 0.400 | 0.455 | 0.541 |
| Joint Ip Ownership | 102 | 7 | 0.278 | 0.714 | 0.400 | 0.543 | 0.562 |
| Minimum Commitment | 102 | 32 | 0.692 | 0.281 | 0.400 | 0.319 | 0.273 |
| Ip Ownership Assignment | 102 | 23 | 0.333 | 0.478 | 0.393 | 0.440 | 0.442 |
| Rofr/Rofo/Rofn | 102 | 17 | 1.000 | 0.235 | 0.381 | 0.278 | 0.360 |
| Notice Period To Terminate Renewal | 102 | 16 | 0.222 | 0.875 | 0.354 | 0.551 | 0.800 |
| Post-Termination Services | 102 | 29 | 0.226 | 0.414 | 0.293 | 0.355 | 0.298 |
| Warranty Duration | 102 | 10 | 0.214 | 0.300 | 0.250 | 0.278 | 0.347 |
| Non-Transferable License | 102 | 22 | 0.173 | 0.409 | 0.243 | 0.321 | 0.471 |
| Third Party Beneficiary | 102 | 6 | 0.103 | 0.500 | 0.171 | 0.283 | 0.508 |
| Price Restrictions | 102 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Source Code Escrow | 102 | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.911 |
| Volume Restriction | 102 | 17 | 0.000 | 0.000 | 0.000 | 0.000 | 0.057 |