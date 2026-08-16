# MAUD findings (condensed)

- Consideration GT balance over 152 contracts: all_cash 57 (38%), other 57 (38%), all_stock 24 (16%), mixed_cash_stock 13 (9%), mixed_cash_stock_election 1 (1%) — `other` (57) is the GT-gap bucket the subclass metric loses on.
- Heaviest MAUD category by labels: **Deal Protection and Related Provisions** (7,935/22,903).
- Largest question family: **MAE Definition** (8,548 rows).
- MAUD contracts are large (median 338,224 chars, 152/152 over the 90k chunk window) — the docclass vision/truncation arm must chunk or head+tail these.
- 0 contracts carry `[***]` redaction markers.
