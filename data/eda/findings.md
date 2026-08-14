# EDA Findings — CUAD Contracts

## Key findings

1. **The corpus is obligation-rich and near-universally labeled**: the five most-labeled categories are `Document Name` (100%), `Parties` (100%), `Agreement Date` (92%), `Governing Law` (86%), `Expiration Date` (81%), `Effective Date` (76%) — every contract carries multiple review-relevant clauses (zero docs have no labeled category).
2. **Span load is right-skewed**: mean 27.1 spans/doc (all 41 categories), median 22, max 97 — a small set of dense agreements carries most of the labeling volume.
3. **Restriction families carry the extractor's ``key_obligations`` GT scope (31 of 41 categories)**: they average 16.0 spans/doc (median 11, max 85), and 49 of 510 contracts carry none — a null-expectation baseline the extractor must survive.
4. **Text length spans 645–338,211 chars (median 33,425, mean 52,563)** — 17% of contracts exceed the 90k-char chunk window and 10% exceed a 32k-token context, which is why the chunked/head+tail-truncated extraction architecture exists.
5. **The corpus is SEC-exhibit-centric**: 477 of 510 titles are SEC exhibit tags (top families: `EX-10` 385, `EX-99` 48, `EX-4` 19) — extraction must tolerate exhibit wrappers and redaction markers (131 docs carry `[***]`-style markers in their text).
6. **Restriction clauses co-occur strongly**: top pairwise shares — Anti-Assignment+Change Of Control 98%; Anti-Assignment+Most Favored Nation 96%; Anti-Assignment+Competitive Restriction Exception 93%.

## Figures

- `01_subtype_distribution.png`
- `02_text_length_hist.png`
- `03_category_yes_rates.png`
- `04_category_spans.png`
- `05_spans_per_doc.png`
- `06_filing_types.png`
- `07_subtype_lengths.png`
- `08_restriction_cooccurrence.png`
- `09_length_budgets.png`
- `10_density_vs_length.png`
