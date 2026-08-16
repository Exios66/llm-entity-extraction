# Near-miss exemplar mining (Monte Carlo selection)

_Task: `subtype_classification` · surrogate efficacy 50% · budget 12,000 chars · max 6 exemplars_

## Top confusion pairs

| expected → predicted | errors | near-miss traces |
|---|---|---|
| maintenance → license | 67 | 268 |
| license → other | 53 | 0 |
| development → license | 50 | 212 |
| supply → distributor | 48 | 2 |
| development → collaboration | 47 | 66 |
| collaboration → joint_venture | 46 | 86 |
| joint_venture → other | 44 | 0 |
| agency → other | 44 | 0 |
| service → other | 43 | 0 |
| franchise → non_compete_no_solicit | 41 | 0 |
| marketing → other | 40 | 0 |
| marketing → manufacturing | 35 | 10 |

## Selected exemplar subset (expected error-flip gain 25.0 errors)

### Pair development → license — 212 near-miss traces, selecting 2

- **BIOAMBERINC_04_10_2013-EX-10.34-DEVELOPMENT AGREEMENT (1)** (openai/gpt-5-nano, sorter_v13):
  `Document is titled 'DEVELOPMENT AGREEMENT' and outlines a Work Plan, Milestones, fees, and development activities (Sections 1, 2, 3), plus IP and transfer provisions (Sections 5-7). These features identify it as a Development contract (not solely license/marketing, etc.).`
- **WARNERCHILCOTTPLC_12_31_2003-EX-4.36-DEVELOPMENT AGREEMENT** (openai/gpt-5-nano, sorter_v13):
  `The document is titled Development Agreement and the operative provisions center on development work, development costs, regulatory filings, and a development plan (Appendix I). These features align with the Development contract subtype rather than other families (no dominant license, marketing, outsourcing, etc.).`

### Pair development → collaboration — 66 near-miss traces, selecting 2

- **LiquidmetalTechnologiesInc_20200205_8-K_EX-10.1_11968198_EX-10.1_Development Agreement** (openai/gpt-4o-mini, sorter_v13):
  `The document is titled 'BUSINESS DEVELOPMENT AGREEMENT' and contains extensive provisions related to the development and commercialization of amorphous alloys and technologies. The operative clauses focus on collaboration, product development, and the licensing of equipment and intellectual property, which aligns closely with the characteristics of a development agreement.`
- **FuelcellEnergyInc_20191106_8-K_EX-10.1_11868007_EX-10.1_Development Agreement** (qwen/qwen3.7-flash, sorter_v14):
  `The document is explicitly titled 'JOINT DEVELOPMENT AGREEMENT'. The operative clauses establish a collaborative research and development program for Molten Carbonate Fuel Cells, including a Steering Committee for governance, specific Project Descriptions with milestones, and IP ownership/licensing structures typical of R&D collaborations. This fits the 'development' family perfectly.`

### Pair co_branding → endorsement — 13 near-miss traces, selecting 2

- **PcquoteComInc_19990721_S-1A_EX-10.11_6377149_EX-10.11_Co-Branding Agreement2** (qwen/qwen3.7-flash, sorter_v11):
  `The document is explicitly titled 'AMENDMENT TO SECTION 2, PART B OF THE CO-BRANDING AGREEMENT'. It modifies an existing agreement between PC Quote, Inc. and A.B. Watley, Inc. According to Rule 6, endorsement riders attached to other agreements are endorsements, but this is a direct amendment to the core co-branding agreement itself. The title clearly identifies the family as co_branding.`
- **PcquoteComInc_19990721_S-1A_EX-10.11_6377149_EX-10.11_Co-Branding Agreement3** (qwen/qwen3.7-flash, sorter_v15):
  `The document is explicitly titled 'SECOND AMENDMENT TO CO-BRANDING AGREEMENT' and amends a prior 'Co-Branding Agreement'. Under rule 6, endorsement riders attached to other agreements are endorsements, but this is an amendment to the co-branding agreement itself, not a rider. The title clearly names the family 'co_branding', which takes precedence. It is a formal agreement between parties.`

### Pair marketing → joint_venture — 23 near-miss traces, selecting 2

- **Loop Industries, Inc. - Marketing Agreement** (deepseek/deepseek-v4-pro, sorter_v13):
  `The document is titled 'Marketing Agreement' and its operative clauses establish a framework for Loop to market and sell Loop-branded products and assign the resulting sales contracts to the Joint Venture Company for fulfillment. The core is marketing and sales, consistent with the marketing subtype.`
- **Loop Industries, Inc. - Marketing Agreement** (qwen/qwen3.7-flash, sorter_v3):
  `The document is explicitly titled 'Marketing Agreement' and its operative provisions govern marketing and sales mechanics, including branding standards, exclusivity/marketing restrictions, and the assignment of customer sales contracts to the joint venture for manufacturing and fulfillment. The structure and substantive clauses align directly with a marketing agreement framework.`

### Pair promotion → distributor — 19 near-miss traces, selecting 2

- **WHITESMOKE,INC_11_08_2011-EX-10.26-PROMOTION AND DISTRIBUTION AGREEMENT** (deepseek/deepseek-v4-pro, sorter_v13):
  `The document is titled 'PROMOTION AND DISTRIBUTION AGREEMENT'. Per rule 23, promotion title wins over distributor, so it is classified as promotion. The agreement involves bundling and distributing Google products, but the title names promotion, making promotion the primary family. Runner-up family: distributor.`
- **CYBERIANOUTPOSTINC_07_09_1998-EX-10.13-PROMOTION AGREEMENT** (deepseek/deepseek-v4-pro, sorter_v13):
  `The document is titled 'PROMOTION AGREEMENT' and its operative clauses describe CNET providing various online and television promotions (TV spots, banners, retail links) to the Company in exchange for fees and a share of CNET Sales. Under Rule 23, a promotion title wins over any marketing or distribution machinery present, so this is a promotion agreement, not marketing or distributor.`

### Pair service → sponsorship — 1 near-miss traces, selecting 1

- **RISEEDUCATIONCAYMANLTD_04_17_2020-EX-4.23-SERVICE AGREEMENT** (qwen/qwen3.7-flash, sorter_v8):
  `The document is explicitly titled 'SERVICE AGREEMENT' and defines the relationship as a 'Service Provider' providing various operational support services (academic, enrollment, HR, etc.) to a 'Service Recipient'. The operative clauses focus on the provision of these professional/support services rather than the sale of goods (supply/manufacturing), development of new IP (development), or specific `
