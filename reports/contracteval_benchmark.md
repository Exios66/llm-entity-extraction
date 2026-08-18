# Directly-mirrored ContractEval benchmark

Pooled over the CUAD test split (one (contract, question) call per row; faithful full-context, temp 0, max_tokens 5000) using ContractEval's EXACT rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the output; token-set Jaccard over positive pairs; false-'no related clause' rate.

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | false-nr (own) | false-nr (paper/1244) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.7-flash v0 | 4182 | 1244 | 0.681 | 0.474 | 0.666 | 0.554 | 0.616 | 0.506 | 0.029 | 0.029 |

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

## Per-category breakdown — qwen3.7-flash v0 (Fig-4 analogue)

| Category | n_pairs | n_pos | P | R | F1 | F2 | Jacc |
|---|---|---|---|---|---|---|---|
| Source Code Escrow | 102 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 0.920 |
| Document Name | 102 | 102 | 1.000 | 0.922 | 0.959 | 0.936 | 0.268 |
| Agreement Date | 102 | 93 | 0.905 | 0.925 | 0.915 | 0.921 | 0.129 |
| Parties | 102 | 102 | 1.000 | 0.833 | 0.909 | 0.862 | 0.214 |
| Governing Law | 102 | 83 | 0.972 | 0.843 | 0.903 | 0.866 | 0.831 |
| Expiration Date | 102 | 78 | 0.870 | 0.859 | 0.865 | 0.861 | 0.736 |
| No-Solicit Of Employees | 102 | 10 | 0.727 | 0.800 | 0.762 | 0.784 | 0.807 |
| Anti-Assignment | 102 | 72 | 0.855 | 0.653 | 0.740 | 0.685 | 0.709 |
| Effective Date | 102 | 70 | 0.648 | 0.843 | 0.733 | 0.795 | 0.314 |
| Insurance | 102 | 32 | 0.657 | 0.719 | 0.687 | 0.706 | 0.799 |
| Audit Rights | 102 | 38 | 0.750 | 0.553 | 0.636 | 0.583 | 0.610 |
| Rofr/Rofo/Rofn | 102 | 17 | 0.889 | 0.471 | 0.615 | 0.519 | 0.628 |
| Renewal Term | 102 | 26 | 0.465 | 0.769 | 0.580 | 0.680 | 0.738 |
| Covenant Not To Sue | 102 | 24 | 0.733 | 0.458 | 0.564 | 0.495 | 0.483 |
| Cap On Liability | 102 | 44 | 0.629 | 0.500 | 0.557 | 0.521 | 0.698 |
| License Grant | 102 | 50 | 0.600 | 0.420 | 0.494 | 0.447 | 0.596 |
| Liquidated Damages | 102 | 14 | 0.375 | 0.643 | 0.474 | 0.562 | 0.629 |
| Revenue/Profit Sharing | 102 | 35 | 0.500 | 0.429 | 0.462 | 0.441 | 0.373 |
| Termination For Convenience | 102 | 29 | 0.298 | 0.690 | 0.417 | 0.546 | 0.752 |
| Non-Compete | 102 | 23 | 0.286 | 0.522 | 0.369 | 0.448 | 0.542 |
| Exclusivity | 102 | 33 | 0.318 | 0.424 | 0.364 | 0.398 | 0.540 |
| Competitive Restriction Exception | 102 | 16 | 0.257 | 0.562 | 0.353 | 0.455 | 0.529 |
| Notice Period To Terminate Renewal | 102 | 16 | 0.222 | 0.750 | 0.343 | 0.508 | 0.908 |
| Change Of Control | 102 | 26 | 0.255 | 0.500 | 0.338 | 0.419 | 0.475 |
| Ip Ownership Assignment | 102 | 23 | 0.233 | 0.435 | 0.303 | 0.370 | 0.463 |
| Non-Disparagement | 102 | 7 | 0.231 | 0.429 | 0.300 | 0.366 | 0.615 |
| Non-Transferable License | 102 | 22 | 0.200 | 0.545 | 0.293 | 0.405 | 0.639 |
| Most Favored Nation | 102 | 3 | 0.250 | 0.333 | 0.286 | 0.312 | 0.487 |
| Irrevocable Or Perpetual License | 102 | 13 | 0.170 | 0.692 | 0.273 | 0.429 | 0.721 |
| Uncapped Liability | 102 | 13 | 0.157 | 0.846 | 0.265 | 0.451 | 0.727 |
| No-Solicit Of Customers | 102 | 7 | 0.200 | 0.286 | 0.235 | 0.263 | 0.567 |
| Post-Termination Services | 102 | 29 | 0.145 | 0.310 | 0.198 | 0.253 | 0.236 |
| Minimum Commitment | 102 | 32 | 0.263 | 0.156 | 0.196 | 0.170 | 0.287 |
| Warranty Duration | 102 | 10 | 0.125 | 0.400 | 0.191 | 0.278 | 0.533 |
| Third Party Beneficiary | 102 | 6 | 0.105 | 0.667 | 0.182 | 0.323 | 0.682 |
| Affiliate License-Licensee | 102 | 12 | 0.109 | 0.417 | 0.172 | 0.266 | 0.604 |
| Volume Restriction | 102 | 17 | 0.136 | 0.176 | 0.154 | 0.167 | 0.271 |
| Joint Ip Ownership | 102 | 7 | 0.059 | 0.429 | 0.103 | 0.190 | 0.688 |
| Unlimited/All-You-Can-Eat-License | 102 | 3 | 0.035 | 0.333 | 0.062 | 0.122 | 0.666 |
| Affiliate License-Licensor | 102 | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.404 |
| Price Restrictions | 102 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |