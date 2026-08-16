# Monte Carlo verification recipe (spend-minimal)

_Task: `subtype_classification` · dry-run: True (no credits spent unless `--run-eval`)_

## 1. Escalation tail (76 lowest-confidence docs, alpha 15%)

- **Simulated tail accuracy: 0.6392** (mean of the per-doc empirical p_correct) — compare with the measured accuracy of the command below.
- Filenames: `reports/monte_carlo/escalation_candidates-subtype_classification.txt`

```bash
python scripts/eval/run_langfuse_subtype_eval.py --dataset mailroom-cuad-contracts-full --sample 76 --seed 42 --sorter-prompt-version sorter_v13 --manifest data/manifests/verify_subtype_classification_tail.jsonl --dry-run
```

## 2. Top-confusion-pair slice (113 docs)

```bash
python scripts/eval/run_langfuse_subtype_eval.py --dataset mailroom-cuad-contracts-full --sample 60 --seed 42 --sorter-prompt-version sorter_v13 --manifest data/manifests/verify_subtype_classification_confusion.jsonl --dry-run
```

Compare the measured accuracy on the slice against the simulator's K=1 expectation (the empirical distribution of the same docs); `--run-eval` executes only the first command (base config).
