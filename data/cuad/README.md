# `data/cuad/` — curated CUAD master ground truth

**Status:** tracked (committed)

The Atticus Project CUAD v1 corpus supplies clause-level QA labels; this
directory holds the **normalized master answer table** used by extraction
diagnostics (date/duration/money MAE, R² pair counts) when raw clause spans
are ambiguous.

## Files

| File | Rows | Purpose |
|---|---|---|
| `master_clauses.csv` | 510 contracts × 40 `-Answer` columns | Per-category normalized answers ("5/8/14", "2 years", …) preferred over raw clause text |

## Loader

`src/master_labels.py` resolves the CSV in this order:

1. `MASTER_LABELS_CSV` env var (if set)
2. `data/cuad/master_clauses.csv` (repo-local default)
3. `../llm-mailroom/data/cuad/master_clauses.csv` (sibling fallback)

Eval runners accept `--master-labels` to override the path.

## Related paths

- Full PDF corpus + `CUAD_v1.json`: [`data/cuad_pdfs/`](../cuad_pdfs/README.md) (gitignored, downloaded)
- EDA over the synced corpus: [`data/eda/`](../eda/README.md)
- Braintrust dataset: `mailroom-cuad-contracts` / `mailroom-cuad-contracts-full`

## License

CUAD v1 — CC BY 4.0, The Atticus Project.
