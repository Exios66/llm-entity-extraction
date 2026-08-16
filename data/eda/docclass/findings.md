# Merged doc-class findings (condensed)

- 676 rows: mailroom-cuad-contracts-full 509, data/maud/contracts.jsonl 152, data/s1_corporate_records/corporate-records.jsonl 15.
- Subclass GT coverage: 167/676 rows scored (509 unscored); **57 GT-`other` rows** — the dominant driver of the 56/69 full-676 subclass misses (the model reads an explicit consideration where MAUD GT falls back to `other`).
- Doc-class balance: contract 509 (75%), merger_agreement 152 (22%), corporate_record 15 (2%).
- Truncation regime is source-bound: data/maud/contracts.jsonl has the most over-90k docs (152/152) — chunking/head+tail is required there.
