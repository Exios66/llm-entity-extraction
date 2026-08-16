# Near-miss exemplar mining (Monte Carlo selection)

_Task: `docclass_classification` · surrogate efficacy 50% · budget 12,000 chars · max 6 exemplars_

## Top confusion pairs

| expected → predicted | errors | near-miss traces |
|---|---|---|
| contract → corporate_record | 8 | 127 |
| merger_agreement → contract | 7 | 13 |
| contract → correspondence | 5 | 0 |
| contract → compliance_filing | 2 | 24 |
| merger_agreement → corporate_record | 1 | 1 |

## Selected exemplar subset (expected error-flip gain 4.0 errors)

### Pair contract → corporate_record — 127 near-miss traces, selecting 2

- **PalmerSquareCapitalBdcInc_20200116_10-12GA_EX-10.6_11949289_EX-10.6_Trademark License Agreement** (qwen/qwen3.7-flash, sorter_docclass_v3):
  `The document is explicitly titled 'TRADEMARK LICENSE AGREEMENT' and contains operative clauses granting a license to use intellectual property (trademarks). It fits the 'license' contract subtype perfectly. It is not a corporate record, merger agreement, or other category.`
- **PalmerSquareCapitalBdcInc_20200116_10-12GA_EX-10.6_11949289_EX-10.6_Trademark License Agreement** (qwen/qwen3.7-flash, sorter_docclass_v6):
  `The document is explicitly titled 'TRADEMARK LICENSE AGREEMENT' and contains operative clauses granting a license to use the Licensed Mark (Article 1). It fits the definition of a License Agreement under the contract subtypes. It is not a merger agreement, corporate record, or other class.`

### Pair merger_agreement → contract — 13 near-miss traces, selecting 2

- **contract_2_merger_agreement.txt** (qwen/qwen3.7-flash, sorter_docclass_v4):
  `The document is an 'AGREEMENT AND PLAN OF MERGER' (Rule 31). It involves a cash tender offer followed by a merger, with consideration consisting of cash ($8.10/share) and Contingent Value Rights (CVRs), which constitutes mixed consideration (cash + equity-like instruments). The CVR Agreement annexed to the document is an ancillary instrument within the M&A deal structure (Rule 36), not a separate `
- **contract_12_merger_agreement.txt** (qwen/qwen3.7-flash, sorter_docclass_v6):
  `The document is explicitly titled 'AGREEMENT AND PLAN OF MERGER' and contains standard M&A operative machinery including a Parent, Merger Sub, Company, Effective Time mechanics, representations and warranties, and termination covenants (Rule 31). The consideration section (Recitals and Section 2.01) specifies a cash tender offer at '$72.00 per share', making the subclass 'all_cash'. As it is class`

### Pair contract → compliance_filing — 24 near-miss traces, selecting 2

- **NELNETINC_04_08_2020-EX-1-JOINT FILING AGREEMENT** (qwen/qwen3.7-flash, sorter_docclass_v6):
  `The document is explicitly titled 'JOINT FILING AGREEMENT'. According to Rule 12, a Joint Filing Agreement for Schedule 13D/13G filings is classified as a contract of the joint_venture family. It is not a corporate record or compliance filing because it is an agreement between parties rather than a regulatory submission itself.`
- **SPRINGBANKPHARMACEUTICALS,INC_04_08_2020-EX-99.A-JOINT FILING AGREEMENT** (qwen/qwen3.7-flash, sorter_docclass_v6):
  `The document is explicitly titled 'JOINT FILING AGREEMENT' and concerns the joint filing of Schedule 13G under the Securities Exchange Act. Per Rule 12, SEC Joint Filing Agreements are classified as contracts of the joint_venture family. It is not a corporate record or compliance filing because it is an agreement between parties rather than a regulatory submission itself.`

### Pair merger_agreement → corporate_record — 1 near-miss traces, selecting 1

- **contract_42_merger_agreement.txt** (qwen/qwen3.7-flash, sorter_docclass_v6):
  `The document is titled 'AGREEMENT AND PLAN OF MERGER' and contains standard M&A operative machinery including a 'Merger Sub', 'Effective Time' mechanics, 'Representations and Warranties', and 'No Shop' covenants, satisfying rule 31. The consideration structure in Section 2.04 specifies an 'Exchange Ratio' based on the 'Parent Stock Price' and payment of 'Parent Common Stock', indicating an all-sto`
