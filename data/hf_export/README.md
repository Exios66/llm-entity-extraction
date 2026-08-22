# data/hf_export — KANBAN-069 staging

Gitignored staging area for the Braintrust → Hugging Face Hub dataset mirror.
Contents here are EPHEMERAL — regenerate anytime with:

    .venv/bin/python scripts/datasets/export_bt_to_hf.py

Per dataset `<name>` you get:

- `<name>.jsonl` — exported rows (`id`, `input`, `expected`, `metadata`,
  `tags`, `created`); CUAD page-image refs point into `<name>/images/`
- `<name>.manifest.json` — BT project/dataset ids, row count, sha256 of the
  JSONL, source streamer script, license note, export timestamp
- `<name>/images/*.png` — downloaded attachment payloads (1024x1024 grayscale
  contract pages, RVL-CDIP preprocessing shape)

`EXPORT_SUMMARY.json` records each dataset's disposition (exported /
skipped_empty / skipped_not_in_project) for the board's evidence trail.

The Hub copies live at https://huggingface.co/Lucius-Morningstar (one dataset
repo per BT dataset, provenance dataset card included). Braintrust itself is
never written by any of this — reads only.

## Live mirror state (verified 2026-08-22)

| Dataset | BT rows | HF repo | Export sha256 (first 12) |
|---|---|---|---|
| `mailroom-cuad-contracts` | 50 (+546 page PNGs under `images/`) | [mailroom-cuad-contracts](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-cuad-contracts) | `fd61aa0d88d5` |
| `mailroom-cuad-contracts-full` | 510 | [mailroom-cuad-contracts-full](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-cuad-contracts-full) | `cac0c8457e0f` |
| `mailroom-lb-hearsay` | 5 | [mailroom-lb-hearsay](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-lb-hearsay) | `7759253da9a6` |

All three verified post-upload (LFS sha256 or round-trip download hash; the
cuad-contracts repo's 596 row→`images/…` references were checked against the
Hub file list — zero missing). Honest gaps (live BT catalog):
`mailroom-maud-contracts` + `mailroom-s1-corporate-records` +
`mailroom-lb-hearsay-test` exist in Braintrust but hold zero rows; the other
streamer-default names (`mailroom-legalbench-contracts`,
`mailroom-legalbench-maud-classification`, `mailroom-maud-classification`)
were never created upstream. Populate upstream first, then re-run export +
publish.

Note on row shape: cuad-contracts rows carry downloaded payloads —
`input.image` / `input.pages[]` are `{type: image_file, file: …,
source_ref: {key, content_type}}` dicts pointing at the repo's `images/`
folder. An earlier export serialized raw `braintrust_attachment` refs; that
shape is superseded.
