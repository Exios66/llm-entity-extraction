# ContractEval mapping-scorer benchmark

Pooled over the CUAD YES/NO obligation categories (32 per document) on stored full-corpus extraction runs, using the ContractEval rubric (arXiv 2508.03080): TP = every GT label span verbatim-contained in the synthesized per-category answer; Jaccard over positive-label pairs; false-'no related clause' rate over positive-label pairs.

| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | no-rel | false-nr |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.7-flash v32 | 15968 | 3505 | 0.800 | 1.000 | 0.089 | 0.164 | 0.109 | 0.215 | 0.928 | 0.670 |
| qwen3.7-flash v31 | 16096 | 3556 | 0.799 | 1.000 | 0.090 | 0.166 | 0.110 | 0.214 | 0.929 | 0.680 |
| llama-4-scout v31 | 16256 | 3578 | 0.784 | 1.000 | 0.017 | 0.034 | 0.022 | 0.045 | 0.986 | 0.934 |

ContractEval Table III reference (F1/F2/Jaccard/false-nr):

| Model | F1 | F2 | Jacc | false-nr |
|---|---|---|---|---|
| gpt-4.1 | 0.641 | 0.672 | 0.472 | 0.071 |
| gpt-4.1-mini | 0.644 | 0.678 | 0.435 | 0.072 |
| claude-sonnet-4 | 0.523 | 0.578 | 0.458 | 0.025 |
| gemini-2.5-pro | 0.497 | 0.604 | 0.506 | 0.011 |
| qwen3-8b-thinking | 0.540 | 0.512 | 0.391 | 0.110 |

**Caveat:** this pipeline is a one-pass extractor — it never claims a category the GT marks absent, so Precision is structurally 1.0 and F1 tracks recall. The discriminating signals versus ContractEval are recall, F2, Jaccard, and the false-'no related clause' rate. ContractEval's false-rate denominator is its hardcoded 1,244 positive pairs; the rate above uses this benchmark's own n_pos.

## Semantic-coverage companion (contained-label lens)

Share of positive-label (doc, category) pairs whose best predicted-span containment against the GT label reaches each band. Verbatim = ContractEval's exact-substring TP; the wider bands quantify the paraphrase penalty this repo's field-type-aware scorer is designed to absorb.

| Run | n_pos | verbatim | >=0.7 | >=0.5 | >=0.3 |
|---|---|---|---|---|---|
| qwen3.7-flash v32 | 3505 | 0.092 | 0.427 | 0.584 | 0.768 |
| qwen3.7-flash v31 | 3556 | 0.092 | 0.421 | 0.574 | 0.761 |
| llama-4-scout v31 | 3578 | 0.018 | 0.093 | 0.139 | 0.293 |

## Scope notes

- Task unit: ContractEval asks one (contract, question) per category; this pipeline extracts the obligation lists in one pass, so each predicted span is mapped to the CUAD category whose label it covers (verbatim, else best containment >= 0.5). Only the 32 YES/NO obligation categories are scored (the pipeline has no per-question surface for the string-answer categories).
- Precision is structurally 1.0 (a one-pass extractor never claims a category the GT marks absent), so F1 tracks recall and is NOT directly comparable to ContractEval's precision-constrained F1.
- GT = `data/cuad/master_clauses.csv` (full clause spans per category); rows joined by aggressive filename normalization.
