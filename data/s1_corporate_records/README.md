# `data/s1_corporate_records/` — EDGAR S-1 corporate-record exhibits

**Status:** gitignored (local only)

SEC EDGAR S-1 filing exhibits of the corporate-record kind (certificate of
formation/incorporation, bylaws, powers of attorney, etc.) pulled to a local
JSONL dump for the hierarchical doc-class eval's `corporate_record` class
(KANBAN-033).

## Contents

| Path | What it holds |
|---|---|
| `corporate-records.jsonl` | One row per exhibit: `doc_text`, GT `doc_type: corporate_record` + content-detected record-type subclass, exhibit-code metadata |

## Populate

```bash
python scripts/datasets/stream_s1_exhibits.py --max-filings 40 --local-dump data/s1_corporate_records/
```

The streamer fetches via EDGAR full-text search → filing index → exhibit text.

## Use

```bash
python scripts/eval/run_langfuse_docclass_eval.py \
    --local-dumps data/s1_corporate_records/corporate-records.jsonl --stratified 120 --seed 42
```

Mirror into Langfuse datasets with
`scripts/eval/sync_langfuse_datasets.py --s1 --s1-dir data/s1_corporate_records`.

## Related paths

- MAUD merger agreements: [`data/maud/`](../maud/README.md)
- Source: SEC EDGAR public filings.
