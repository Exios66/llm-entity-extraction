# Monte Carlo verification recipe (spend-minimal)

_Task: `docclass_classification` · dry-run: True (no credits spent unless `--run-eval`)_

## 1. Escalation tail (101 lowest-confidence docs, alpha 15%)

- **Simulated tail accuracy: 0.9614** (mean of the per-doc empirical p_correct) — compare with the measured accuracy of the command below.
- Filenames: `reports/monte_carlo/escalation_candidates-docclass_classification.txt`

```bash
python scripts/eval/run_langfuse_docclass_eval.py --local-dumps data/datasets/docclass_merged.jsonl --sample 101 --seed 42 --sorter-prompt-version sorter_v13 --manifest data/manifests/verify_docclass_classification_tail.jsonl --dry-run
```

## 2. Top-confusion-pair slice (661 docs)

```bash
python scripts/eval/run_langfuse_docclass_eval.py --local-dumps data/datasets/docclass_merged.jsonl --sample 60 --seed 42 --sorter-prompt-version sorter_v13 --manifest data/manifests/verify_docclass_classification_confusion.jsonl --dry-run
```

Compare the measured accuracy on the slice against the simulator's K=1 expectation (the empirical distribution of the same docs); `--run-eval` executes only the first command (base config).
