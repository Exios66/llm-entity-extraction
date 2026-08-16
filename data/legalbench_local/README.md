# `data/legalbench_local/` — LegalBench task local mirrors

**Status:** gitignored (local only)

Per-task LegalBench train/test JSONL mirrors written by the streamer's
`--local-dump` flag — the offline eval path for binary/Yes-No tasks (e.g.
`hearsay`) when Braintrust dataset-row uploads are unavailable.

## Contents

| Pattern | What it holds |
|---|---|
| `<task>.jsonl` | Train-split records (filled few-shot prompt, doc_text, metadata) |
| `<task>-test.jsonl` | Test-split records |

## Populate

```bash
python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks hearsay --local-dump data/legalbench_local/
```

## Use

The eval runners read the test dump directly:

```bash
python scripts/eval/run_langfuse_classification_eval.py \
    --task-dataset data/legalbench_local/hearsay-test.jsonl --prompt-mode task
```

## Related paths

- Streamer: `scripts/datasets/stream_legalbench_tasks_to_bt.py`
- Braintrust twin datasets: `mailroom-lb-<task>` / `mailroom-lb-<task>-test`
- Source: LegalBench (`nguha/legalbench`), CC BY 4.0.
