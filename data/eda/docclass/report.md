# Merged hierarchical doc-class surface (676 rows)

_Emitted by `scripts/eda/explore_pipeline_sources.py --source docclass`_
_Note: Source: merged doc-class surface (CUAD 509 + MAUD 152 + S-1 15, fp 5602b71f)_

**676 rows** (`data/datasets/docclass_merged.jsonl`)

## Composition by source

| source | rows |
|---|---|
| mailroom-cuad-contracts-full | 509 |
| data/maud/contracts.jsonl | 152 |
| data/s1_corporate_records/corporate-records.jsonl | 15 |

## Doc class (primary dimension)

| doc_type | rows | share |
|---|---|---|
| contract | 509 | 75.3% |
| merger_agreement | 152 | 22.5% |
| corporate_record | 15 | 2.2% |

## Subclass (second dimension)

Rows WITH subclass GT: **167** · without: **509** (unscored on the subclass metric) · GT-`other` gap cluster: **57**.

| subclass | rows |
|---|---|
| None | 509 |
| all_cash | 57 |
| other | 57 |
| all_stock | 24 |
| mixed_cash_stock | 13 |
| articles_of_incorporation | 8 |
| rights_instrument | 6 |
| mixed_cash_stock_election | 1 |
| bylaws | 1 |

## Text size by source

| source | n | median chars | max chars | over 90k |
|---|---|---|---|---|
| mailroom-cuad-contracts-full | 509 | 32,861 | 338,211 | 87 |
| data/maud/contracts.jsonl | 152 | 338,224 | 1,008,540 | 152 |
| data/s1_corporate_records/corporate-records.jsonl | 15 | 34,099 | 93,296 | 2 |

## CUAD category metadata (contract rows)

| category | docs |
|---|---|
| Maintenance | 34 |
| License_Agreements | 33 |
| Distributor | 32 |
| Strategic Alliance | 32 |
| Sponsorship | 31 |
| Service | 28 |
| Development | 28 |
| Collaboration | 26 |
| Co_Branding | 22 |
| Hosting | 20 |
| Outsourcing | 18 |
| Supply | 18 |
| Manufacturing | 17 |
| IP | 17 |
| Marketing | 17 |
| Franchise | 15 |
| Endorsement | 15 |
| Joint Venture _ Filing | 14 |
| Agency Agreements | 13 |
| Transportation | 13 |
| Reseller | 12 |
| Promotion | 12 |
| Consulting Agreements | 11 |
| Joint Venture | 9 |
| Endorsement Agreement | 9 |
| Affiliate_Agreements | 9 |
| Non_Compete_Non_Solicit | 3 |
| Affiliate Agreement | 1 |
