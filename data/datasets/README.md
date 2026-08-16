# `data/datasets/` — merged corpus artifacts

**Status:** gitignored (local only, regenerable)

The merged docclass corpus: every document the hierarchical sorter eval
(KANBAN-033) classifies, in ONE dataset. Rebuild it with
`scripts/datasets/build_docclass_merged.py`:

```bash
python scripts/datasets/build_docclass_merged.py --dry-run   # load + count + fingerprint
python scripts/datasets/build_docclass_merged.py             # write docclass_merged.jsonl
```

## Contents

| File | Rows | Sources |
|---|---|---|
| `docclass_merged.jsonl` | 676 (509 contract + 152 merger_agreement + 15 corporate_record) | `mailroom-cuad-contracts-full` (Braintrust) + `data/maud/contracts.jsonl` + `data/s1_corporate_records/corporate-records.jsonl` |

Row shape (the flat streamer-dump shape the docclass eval runner reads via
`--local-dumps`): `{filename, doc_text, prompt, expected,
expected_subclass, metadata}` — `expected` is the doc_type key,
`expected_subclass` the second-level key (None for contract rows: CUAD
subtype scoring is the shared subtype surface's job).

## Consumers

- `scripts/eval/run_langfuse_docclass_eval.py --local-dumps data/datasets/docclass_merged.jsonl`
  — one-file A/B surface for the docclass sorter iterations.
- `scripts/eval/sync_langfuse_datasets.py --docclass` — Langfuse mirror as a
  single `mailroom-docclass` dataset (llm-dojo).

The dump is deterministically ordered (corpus, then filename), so its
`dataset_fingerprint` is reproducible across rebuilds — the same-surface
contract holds for any sample drawn from it.
