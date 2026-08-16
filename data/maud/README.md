# `data/maud/` — MAUD v1 merger-agreement local dumps

**Status:** gitignored (local only)

Merger Agreement Understanding Dataset (MAUD) — 152 merger agreements plus the
per-question expert-GT suite — mirrored to local JSONL dumps. These dumps are
the reliable eval path while Braintrust row uploads remain org-capped
(KANBAN-033).

## Contents

| Path | What it holds |
|---|---|
| `contracts.jsonl` | 152 merger agreements, GT `doc_type: merger_agreement` + consideration-type subclass |
| `classification.jsonl` | 25,827 per-question rows (22 question families / 7 categories) |

## Populate

```bash
python scripts/datasets/stream_maud_to_bt.py --local-dump data/maud/
```

## Use

The hierarchical doc-class eval consumes the contracts dump directly:

```bash
python scripts/eval/run_langfuse_docclass_eval.py \
    --local-dumps data/maud/contracts.jsonl --stratified 120 --seed 42
```

Mirror into Langfuse datasets with
`scripts/eval/sync_langfuse_datasets.py --maud --maud-dir data/maud`.

## Related paths

- S-1 corporate-record dumps: [`data/s1_corporate_records/`](../s1_corporate_records/README.md)
- Source: MAUD v1 — CC BY 4.0 (Zenodo `maud_v1.zip` / HF `theatticusproject/maud`).
