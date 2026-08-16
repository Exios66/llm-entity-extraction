# Ready-to-paste exemplar appendix (next prompt version)


_Paste the disambiguation examples below into the prompt's few-shot section (or the rule exemplar list). Each shows a correct classification that explicitly rejects the decoy label of a confusion pair._

## contract (decoy: corporate_record)

**Example — PalmerSquareCapitalBdcInc_20200116_10-12GA_EX-10.6_11949289_EX-10.6_Trademark License Agreement**

> The document is explicitly titled 'TRADEMARK LICENSE AGREEMENT' and contains operative clauses granting a license to use intellectual property (trademarks). It fits the 'license' contract subtype perfectly. It is not a corporate record, merger agreement, or other category.

**Example — PalmerSquareCapitalBdcInc_20200116_10-12GA_EX-10.6_11949289_EX-10.6_Trademark License Agreement**

> The document is explicitly titled 'TRADEMARK LICENSE AGREEMENT' and contains operative clauses granting a license to use the Licensed Mark (Article 1). It fits the definition of a License Agreement under the contract subtypes. It is not a merger agreement, corporate record, or other class.

## merger_agreement (decoy: contract)

**Example — contract_2_merger_agreement.txt**

> The document is an 'AGREEMENT AND PLAN OF MERGER' (Rule 31). It involves a cash tender offer followed by a merger, with consideration consisting of cash ($8.10/share) and Contingent Value Rights (CVRs), which constitutes mixed consideration (cash + equity-like instruments). The CVR Agreement annexed to the document is an ancillary instrument within the M&A deal structure (Rule 36), not a separate contract type.

**Example — contract_12_merger_agreement.txt**

> The document is explicitly titled 'AGREEMENT AND PLAN OF MERGER' and contains standard M&A operative machinery including a Parent, Merger Sub, Company, Effective Time mechanics, representations and warranties, and termination covenants (Rule 31). The consideration section (Recitals and Section 2.01) specifies a cash tender offer at '$72.00 per share', making the subclass 'all_cash'. As it is classified as merger_agreement, contract_subtype is null.

## contract (decoy: compliance_filing)

**Example — NELNETINC_04_08_2020-EX-1-JOINT FILING AGREEMENT**

> The document is explicitly titled 'JOINT FILING AGREEMENT'. According to Rule 12, a Joint Filing Agreement for Schedule 13D/13G filings is classified as a contract of the joint_venture family. It is not a corporate record or compliance filing because it is an agreement between parties rather than a regulatory submission itself.

**Example — SPRINGBANKPHARMACEUTICALS,INC_04_08_2020-EX-99.A-JOINT FILING AGREEMENT**

> The document is explicitly titled 'JOINT FILING AGREEMENT' and concerns the joint filing of Schedule 13G under the Securities Exchange Act. Per Rule 12, SEC Joint Filing Agreements are classified as contracts of the joint_venture family. It is not a corporate record or compliance filing because it is an agreement between parties rather than a regulatory submission itself.

## merger_agreement (decoy: corporate_record)

**Example — contract_42_merger_agreement.txt**

> The document is titled 'AGREEMENT AND PLAN OF MERGER' and contains standard M&A operative machinery including a 'Merger Sub', 'Effective Time' mechanics, 'Representations and Warranties', and 'No Shop' covenants, satisfying rule 31. The consideration structure in Section 2.04 specifies an 'Exchange Ratio' based on the 'Parent Stock Price' and payment of 'Parent Common Stock', indicating an all-stock transaction (rule 33). Although Exhibits A and B contain corporate records (Certificate of Incorporation and Bylaws), rule 34 dictates that embedded records do not change the parent class of the merger agreement.
