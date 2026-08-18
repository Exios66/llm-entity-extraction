# `data/contracteval/` — ContractEval (arXiv 2508.03080) CUAD test split

**Status:** derived corpora gitignored (local only, regenerable); the curated
reference files are committed.

Directly-mirrored task data for the ContractEval benchmark — the CUAD **test
split** as used by the paper and `github.com/olivialiu121/ContractEval`: one
LLM call per (contract, question) pair, full-contract context, "extract exact
sentences or `No related clause.`".

## Contents

| Pattern | What it holds | Tracked? |
|---|---|---|
| `contracteval_test.jsonl` | 4,182 (contract, question) pairs `{id, title, category, question, label_spans, n_labels}` (compact — no context duplication) | gitignored |
| `contracteval_contracts.jsonl` | 102 contracts `{title, context}` (FULL text, 645–300,768 chars) | gitignored |
| `questions.json` | 41 `{category: question}` — the curated category→question table | committed |
| `testset_summary.json` | counts, positive/negative, fingerprint, fidelity note | committed |
| `_cache/` | downloaded `cuad-data.zip` + extraction | gitignored |

## Populate

```bash
python scripts/datasets/build_contracteval_testset.py --dry-run   # preview
python scripts/datasets/build_contracteval_testset.py             # full build
```

The authoritative source is the SQuAD-style `test.json` inside the Atticus
CUAD `data.zip` (https://github.com/TheAtticusProject/cuad/raw/main/data.zip) —
the exact file the HuggingFace `theatticusproject/cuad-qa` loader downloads for
its `test` split (this repo does not depend on the `datasets` package).

## Fidelity

- 102 contracts × 41 categories = 4,182 pairs; **positives = 1,244** — exactly
  the hardcoded denominator in ContractEval's `Evaluation.py` (the false-"no
  related clause" rate is reported over those 1,244 positives).
- The paper reports 4,128 total — a 54-negative-row-smaller snapshot of the
  same `test.json`; the positive set is identical, so F1/F2/Jaccard/false-nr
  are directly comparable.
- Contexts are the FULL contracts (fed whole in one call — the eval runner
  disables the repo's input cap for this task).

## Use

```bash
python scripts/eval/run_langfuse_contracteval_eval.py \
    --task-dataset data/contracteval/contracteval_test.jsonl \
    --contracts data/contracteval/contracteval_contracts.jsonl \
    --prompt-version contracteval_v0 --model qwen3.7-flash --sample 50 --seed 42
```
