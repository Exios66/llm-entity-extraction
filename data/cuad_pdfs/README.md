# `data/cuad_pdfs/` — local CUAD v1 PDF corpus

**Status:** gitignored (local only)

The full CUAD v1 contract corpus — ~510 PDFs plus the `CUAD_v1.json`
clause-QA dump — held locally for text/vision evals and EDA without touching
the Hugging Face mirror each run.

## Contents

| Path | What it holds |
|---|---|
| `CUAD_v1.json` | CUAD clause-QA labels (questions/answers/context) |
| `CUAD_v1/full_contract_pdf/…` | The PDF tree (`Part_II/<Category>/…`) |

## Populate

```bash
python scripts/datasets/download_cuad_pdfs.py --out-dir data/cuad_pdfs
```

The corpus is also streamed to Braintrust as `mailroom-cuad-contracts`
(`scripts/datasets/stream_cuad_to_bt.py`) and mirrored into Langfuse
(`scripts/eval/sync_langfuse_datasets.py --cuad --cuad-dir data/cuad_pdfs`).

## Related paths

- Curated master answers: [`data/cuad/`](../cuad/README.md)
- EDA over this corpus: [`data/eda/`](../eda/README.md)
- License: CUAD v1 — CC BY 4.0, The Atticus Project.
