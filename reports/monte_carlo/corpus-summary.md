# Monte Carlo corpus summary

_Derived by `scripts/reporting/monte_carlo_corpus.py` from `reports/experiment_log.jsonl` + `data/manifests/*.jsonl`_

**17691 scored rows** (42 non-completed) across **59 runs**.

## Rows by task

| task | rows |
|---|---|
| subtype_classification | 16,120 |
| docclass_classification | 1,442 |
| chained_sorter_extractor | 80 |
| sorter_classification | 7 |

## Rows by model

| model | rows |
|---|---|
| qwen/qwen3.7-flash | 11,025 |
| meta-llama/llama-4-scout | 2,038 |
| deepseek/deepseek-v4-flash | 1,020 |
| openai/gpt-4.1-nano | 1,019 |
| meta-llama/llama-3.3-70b-instruct | 1,019 |
| openai/gpt-4o-mini | 510 |
| openai/gpt-5-nano | 509 |
| deepseek/deepseek-v4-pro | 509 |

## Shared-document surfaces (docs with >= 2 runs)

**1198 documents** observed by multiple runs — the paired comparison surface for prompt ablation / ensemble voting.

- docclass_classification: 676 shared docs
- subtype_classification: 509 shared docs
- chained_sorter_extractor: 10 shared docs
- sorter_classification: 3 shared docs

## Reasoning coverage

**17,640 / 17,649** completed rows carry a reasoning trace (99.9%) — the near-miss/exemplar material for the exemplar miner.
