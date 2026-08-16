# MAUD — merger-agreement corpus + per-question classification suite

_Emitted by `scripts/eda/explore_pipeline_sources.py --source maud`_
_Note: Source: MAUD — Merger Agreement Understanding Dataset (Gebre et al., COLING 2025), CC BY 4.0 · Zenodo maud_v1_

**Contracts**: 152 merger agreements (`data/maud/contracts.jsonl`)
**Per-question rows**: 25,827 (`data/maud/classification.jsonl`)

## Contract text size

152 docs · 54,141,502 chars total
  size: min 105,682 / p25 300,521 / median 338,224 / p75 390,026 / max 1,008,540 chars
  median 52,119 words (≈84,556 tokens at 4 ch/tok)
  docs over 90k chars (chunk window): 152 · over 16k (single-pass limit): 152
  docs with [***] redaction markers: 0

## Consideration-type subclass (expert GT)

| subclass | contracts | share |
|---|---|---|
| all_cash | 57 | 37.5% |
| other | 57 | 37.5% |
| all_stock | 24 | 15.8% |
| mixed_cash_stock | 13 | 8.6% |
| mixed_cash_stock_election | 1 | 0.7% |

## MAUD category coverage (label counts over the 152 contracts)

| category | labels | share |
|---|---|---|
| Deal Protection and Related Provisions | 7,935 | 34.6% |
| Material Adverse Effect | 7,856 | 34.3% |
| Conditions to Closing | 4,805 | 21.0% |
| Operating and Efforts Covenant | 1,459 | 6.4% |
| Knowledge | 423 | 1.8% |
| Remedies | 214 | 0.9% |
| General Information | 211 | 0.9% |

Total labels across the corpus: **22,903** (median 173 per contract).

## Per-question suite (22 question families / 7 categories)

**22 tasks** across **7 categories**; train rows cover **153** distinct contracts; **11,980** rows carry a subquestion.

| category | rows |
|---|---|
| Deal Protection and Related Provisions | 9,753 |
| Material Adverse Effect | 8,548 |
| Conditions to Closing | 5,034 |
| Operating and Efforts Covenant | 1,611 |
| Knowledge | 442 |
| General Information | 225 |
| Remedies | 214 |

| task | rows |
|---|---|
| MAE Definition | 8,548 |
| Accuracy of Target R&W Closing Condition | 4,765 |
| Tail Period & Acquisition Proposal Details | 3,627 |
| Limitations on FTR Exercise | 1,110 |
| Fiduciary exception to COR covenant | 1,091 |
| Agreement provides for matching rights in connection with COR | 893 |
| Ordinary course covenant | 756 |
| Intervening Event Definition | 711 |
| Fiduciary exception:  Board determination (no-shop) | 622 |
| Superior Offer Definition | 591 |
| Negative interim operating covenant | 554 |
| Agreement provides for matching rights in connection with FTR | 490 |
| Knowledge Definition | 442 |
| General Antitrust Efforts Standard | 301 |
| No-Shop | 290 |
| Type of Consideration | 225 |
| Compliance with Covenant Closing Condition | 214 |
| Specific Performance | 214 |
| FTR Triggers | 181 |
| Breach of No Shop | 101 |
| Absence of Litigation Closing Condition | 55 |
| Breach of Meeting Covenant | 46 |

### Answer cardinality

| valid classes per row | rows |
|---|---|
| 2 | 542 |
| 3 | 515 |
| 4 | 814 |
| 5 | 617 |
| 6 | 1,587 |
| 7 | 2,137 |
| 8 | 3,854 |
| 9 | 6,081 |
| 10 | 766 |
| 11 | 2,376 |
| 12 | 1,581 |
| 14 | 176 |
| 16 | 342 |
| 17 | 340 |
| 18 | 168 |
| 29 | 856 |
| 51 | 443 |
| 52 | 215 |
| 53 | 659 |
| 54 | 220 |
| 55 | 433 |
| 56 | 221 |
| 58 | 662 |
| 59 | 222 |

### Answer balance (per task)

- **Absence of Litigation Closing Condition**: Governmental litigation only 15, Pending or threatened (without "writing" requirement) 14, Non-Governmental & governmental litigation 13, Pending or threatened in writing 8, Pending 5
- **Accuracy of Target R&W Closing Condition**: General R&Ws 568, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE 313, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee 243, All/The R&Ws accurate at MAE standard 205, Accurate in all respects with de minimis exception 179, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor 179, At Signing & At Closing 165, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor 150, Accurate in all material respects 149, Tax 148, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee 117, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee, Opinion of Financial Advisor, Other 107, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 87, General R&Ws, Fundermental/Special R&Ws 70, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement 69, General R&Ws, fundamental/Special R&Ws 66, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Opinion of Financial Advisor, Other 64, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Takeover Statutes, Rights Agreement 63, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 58, Capitalization-Other, Authority, Approval, Enforceability, Subsidiaries, Brokers' Fee 57, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 57, At Closing Only 55, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Other 54, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Other 54, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee 51, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor, Other 51, Accurate in all respects 46, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Opinion of Financial Advisor, Other 45, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee 44, Accurate at another materiality standard (e.g., hybrid standard) 42, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Opinion of Financial Advisor 42, Authority, Approval, Enforceability 41, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Opinion of Financial Advisor 38, Specified R&Ws only 37, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Other 36, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE 36, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Takeover Statutes 36, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor, Other 34, Authority, Approval, Enforceability, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 33, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor, Other 33, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes 33, Capitalization-Other, Authority, Approval, Enforceability, Subsidiaries, No MAE, Takeover Statutes, Opinion of Financial Advisor, Other 30, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee, Takeover Statutes, Other 30, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Other 30, Authority, Approval, Enforceability, Organization, Brokers' Fee 30, Authority, Approval, Enforceability, No MAE, Opinion of Financial Advisor, Other 30, General R&Ws, Capitalization R&Ws, Fundermental/Special R&Ws 28, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee, Takeover Statutes 27, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes 27, Authority, Approval, Enforceability, No MAE, Brokers' Fee 24, Authority, Approval, Enforceability, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor 24, Capitalization-Other, Authority, Enforceability, Organization, No MAE, Brokers' Fee, Opinion of Financial Advisor, No-Conflict 24, Capitalization-Other, Authority, Approval, Enforceability, Subsidiaries, No MAE, Brokers' Fee, Opinion of Financial Advisor 21, Capitalization-Other, Approval, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor, Other 21, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Opinion of Financial Advisor 21, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor, Tax 21, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Rights Agreement, Opinion of Financial Advisor 21, General R&Ws, Capitalization R&Ws 21, Capitalization-Other 18, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Takeover Statutes, Opinion of Financial Advisor, Other 18, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Opinion of Financial Advisor 18, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee, No-Conflict 18, Capitalization-Other, No MAE, Other 18, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, No-Conflict 18, General R&Ws, Specified R&Ws only 16, General R&Ws, Capitalization R&Ws, fundamental/Special R&Ws 16, Accurate in all respects with below-threshold carveout 15, Capitalization-Other, Authority, Approval, Enforceability, Subsidiaries, No MAE, Brokers' Fee, Opinion of Financial Advisor, Other 15, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, No-Conflict, Other 13, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor, Other 12, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 12, Capitalization-Other, No MAE 10, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Opinion of Financial Advisor, No-Conflict 10, Capitalization-Other, Authority, Approval, Enforceability, Organization, Other 10, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement 10, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Other 10, Capitalization-Other, Authority, Enforceability, Brokers' Fee 10, Capitalization-Other, Authority, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement 9, Capitalization-Other, Authority, Approval, Enforceability, No MAE, Brokers' Fee 9, Capitalization-Other, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Opinion of Financial Advisor, Other 9, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Other 9, Capitalization-Other, Authority, Approval, Enforceability, Organization, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor 8, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Other 8, Authority, Approval, Enforceability, Organization, Subsidiaries, No MAE, Brokers' Fee, Takeover Statutes, Other 8, Capitalization-Other, Authority, Approval, Organization, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 8, Capitalization-Other, Authority, Enforceability, Organization, Brokers' Fee, Takeover Statutes, Opinion of Financial Advisor, Other 8, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor 7, Capitalization-Other, Authority, Approval, Enforceability, Organization, No MAE, Brokers' Fee, Takeover Statutes, Rights Agreement, Opinion of Financial Advisor, No-Conflict 7, Capitalization-Other, Authority, Approval, Enforceability, Organization 6, General R&Ws, Capitalization R&Ws, Specified R&Ws only 6, Capitalization-Other, Authority, Approval, Enforceability, No MAE, Brokers' Fee, Rights Agreement, Other 5, R&Ws accurate at another materiality standard (e.g., hybrid standard) 3, All/The R&Ws accurate in all respects (repeating R&Ws) 1, Each R&W accurate at MAE standard 1, fundamental/Special R&Ws 1
- **Agreement provides for matching rights in connection with COR**: Continuous matching right 201, 2 business days or less 173, None 138, 4 business days 125, 3 business days 110, 5 business days 45, 4 calendar days 40, 3 calendar days 26, Greater than 5 business days 23, 3 days 8, > 5 business days 4
- **Agreement provides for matching rights in connection with FTR**: Continuous matching right 180, 4 business days 90, 2 business days or less 52, 3 business days 52, 5 business days 50, 4 calendar days 14, None 14, 3 calendar days 10, 5 calendar days 8, >5 business days 8, Greater than 5 business days 6, 3 days 6
- **Breach of Meeting Covenant**: Yes 30, No 16
- **Breach of No Shop**: Yes 84, No 17
- **Compliance with Covenant Closing Condition**: All Covenants 188, Each Covenant 16, Hybrid/Other Standard 10
- **FTR Triggers**: Superior Offer 173, Superior Offer, Intervening Event 8
- **Fiduciary exception to COR covenant**: Yes 170, No 165, More likely than not violate fiduciary duties 133, "Inconsistent" with fiduciary duties 125, "Reasonably likely/expected breach" of fiduciary duties 113, "Reasonably likely/expected to be inconsistent" with fiduciary duties 112, "Reasonably likely/expected violation" of fiduciary duties 92, "Breach" of fiduciary duties 71, "Violation" of fiduciary duties 63, Other specified standard 18, None 17, "Required to comply" with fiduciary duties 12
- **Fiduciary exception:  Board determination (no-shop)**: Superior Offer, or Acquisition Proposal reasonably likely/expected to result in a Superior Offer 215, None 68, "Inconsistent" with fiduciary duties 60, "Reasonably likely/expected to be inconsistent" with fiduciary duties 48, Other specified standard 43, "Breach" of fiduciary duties 36, "Reasonably likely/expected violation" of fiduciary duties 35, "Reasonably likely/expected breach" of fiduciary duties 34, Acquisition Proposal only 34, "Violation" of fiduciary duties 26, "Required to comply" with fiduciary duties 23
- **General Antitrust Efforts Standard**: Reasonable best efforts 163, Commercially reasonable efforts 126, Flat standard 12
- **Intervening Event Definition**: No 192, Yes 178, May occur or arise prior to signing 127, Known, but consequences unknown or not reasonably foreseeable, at signing 93, Not known and not reasonably foreseeable at signing 60, Must occur or arise after signing 48, Not known at signing 7, Known, but consequences unknown, at signing 6
- **Knowledge Definition**: Based on investigation or inquiry 117, Constructive knowledge 112, Actual knowledge 96, Yes 93, No 16, Based on role 8
- **Limitations on FTR Exercise**: Breach of no-shop resulting in a Superior Offer 314, Material breach of no-shop resulting in a Superior Offer 224, Material breach of no-shop 184, Any breach of no-shop 151, (Material) breach of other provisions of agreement 141, Material breach of no-shop, (Material) breach of other provisions of agreement 36, Breach of no-shop resulting in a Superior Offer, (Material) breach of other provisions of agreement 20, Other 18, Any breach of no-shop, (Material) breach of other provisions of agreement 13, Material breach of no-shop resulting in a Superior Offer, (Material) breach of other provisions of agreement 9
- **MAE Definition**: Yes 2,591, No 1,601, War or terrorism, Natural disaster 528, War or terrorism, Natural disaster, "act of God" 386, War or terrorism, Natural disaster, force majeure 371, "Resulting from", "Arising from/out of" 246, announcement, pendency, consummation 227, "Resulting from" 224, business and operation of Target, ability to consummate transaction 213, announcement, pendency 191, Applies to Target and subsidiaries "taken as a whole" 154, War or terrorism, Natural disaster, "act of God", force majeure 145, business and operation of Target 143, War or terrorism 136, announcement 131, All MAE carveouts 108, "Resulting from", "Arising from/out of", "Relating to" 104, "Would" (reasonably) be expected to 101, announcement, consummation 101, "Resulting from", "Arising from/out of", "Relating to", "Attributable to" 100, "Relating to" 87, Other forward-looking standard 68, "Could" (reasonably) be expected to 64, "Resulting from", "Arising from/out of", Relational language varies among carveouts 64, "Arising from/out of", "Relating to" 55, Natural disaster 54, "Resulting from", "Arising from/out of", "Attributable to" 52, "Resulting from", "Relating to" 44, ability to consummate transaction 43, "Resulting from", "Arising from/out of", "Relating to", Relational language varies among carveouts 41, Some MAE carveouts 33, "Resulting from", "Attributable to" 31, "Resulting from", "Arising from/out of", "Relating to", Other 28, "Arising from/out of" 22, "Would" 19, Natural disaster, "act of God" 10, "Resulting from", Other 9, "Resulting from", "Arising from/out of", "Relating to", "Attributable to", Relational language varies among carveouts 9, "Attributable to" 8, "Arising from/out of", Other 4, War or terrorism, "act of God", force majeure 2
- **Negative interim operating covenant**: Consent may not be unreasonably withheld, conditioned or delayed 207, Applies to all negative covenants 187, No 55, Yes 43, Flat consent 42, Applies only to specified negative covenants 20
- **No-Shop**: Strict liability 106, Yes 90, Reasonable standard 86, No 8
- **Ordinary course covenant**: Yes 223, Consent may not be unreasonably withheld, conditioned or delayed 200, Flat covenant (no efforts standard) 112, No 98, Commercially reasonable efforts 70, Reasonable best efforts 33, Flat consent 20
- **Specific Performance**: "entitled to" specific performance 202, "entitled to seek" specific performance 12
- **Superior Offer Definition**: Greater than 50% but not "all or substantially all" 197, 50% 165, No 143, "All or substantially all" 45, Yes 22, Less than 50% 19
- **Tail Period & Acquisition Proposal Details**: Same Acquisition Proposal - Must sign during Tail Period (no closing requirement), Different Acquisition Proposal - Must sign during Tail Period (no closing requirement) 1,325, Same Acquisition Proposal - Must sign during Tail Period and close after Tail Period, Different Acquisition Proposal - Must sign during Tail Period and close after Tail Period 507, No 226, within 12 months 197, Yes 134, “Publicly disclosed” requirement applies to Acquisition Proposal + No-Vote / MTC Failure Trigger 122, “Publicly disclosed” requirement applies to Acquisition Proposal + Breach Trigger, “Publicly disclosed” requirement applies to Acquisition Proposal + No-Vote / MTC Failure Trigger, “Publicly disclosed” requirement applies to Acquisition Proposal + Outside Date Trigger 122, within 9 months 110, Other 104, within 6 months 104, 12 months or longer 95, “Publicly disclosed” requirement applies to Acquisition Proposal + Breach Trigger, “Publicly disclosed” requirement applies to Acquisition Proposal + No-Vote / MTC Failure Trigger 89, Same Acquisition Proposal - Must sign during Tail Period and close after Tail Period 82, “Publicly disclosed” requirement applies to Acquisition Proposal + Outside Date Trigger 72, Same Acquisition Proposal - Must sign during Tail Period (no closing requirement) 71, “Publicly disclosed” requirement applies to Acquisition Proposal + No-Vote / MTC Failure Trigger, “Publicly disclosed” requirement applies to Acquisition Proposal + Outside Date Trigger 64, Same Acquisition Proposal - Must be approved or not opposed (or another similar action) during Tail Period and transaction must close after Tail Period, Different Acquisition Proposal - Must be approved or not opposed (or another similar action) during Tail Period and transaction must close after Tail Period 52, “Publicly disclosed” requirement applies to Acquisition Proposal + Breach Trigger, “Publicly disclosed” requirement applies to Acquisition Proposal + Outside Date Trigger 41, Same Acquisition Proposal - Must close during Tail Period, Different Acquisition Proposal must close during Tail Period 34, Same Acquisition Proposal - Must be approved or not opposed to (or another similar action) during Tail Period (no closing requirement), Different Acquisition Proposal - Must be approved or not opposed (or another similar action) during Tail Period (no closing requirement) 34, Same Acquisition Proposal - Must sign during Tail Period (no closing requirement), Different Acquisition Proposal - Must sign during Tail Period and close after Tail Period 27, “Publicly disclosed” requirement applies to Acquisition Proposal + Breach Trigger 15
- **Type of Consideration**: All Cash 121, All Stock 54, Mixed Cash/Stock 35, Mixed Cash/Stock: Election 15
