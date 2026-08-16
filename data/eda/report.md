# CUAD Contracts — Full Exploratory Data Analysis

**Corpus**: theatticusproject/cuad (CUAD_v1.json) · **contracts**: 510 · **QA pairs**: 20,910 · **categories**: 41

**Text corpus**: 510 documents (of 510 contracts; 0 absent from the synced full corpus), min 645 / median 33,425 / mean 52,563 / max 338,211 chars (~8,356 tokens median by chars/4)

## 1. Corpus composition

| subtype | contracts | share |
|---|---|---|
| `maintenance` | 34 | 6.7% |
| `license` | 33 | 6.5% |
| `distributor` | 32 | 6.3% |
| `strategic_alliance` | 32 | 6.3% |
| `sponsorship` | 31 | 6.1% |
| `development` | 28 | 5.5% |
| `service` | 28 | 5.5% |
| `collaboration` | 26 | 5.1% |
| `endorsement` | 24 | 4.7% |
| `joint_venture` | 23 | 4.5% |
| `co_branding` | 22 | 4.3% |
| `hosting` | 20 | 3.9% |
| `outsourcing` | 18 | 3.5% |
| `supply` | 18 | 3.5% |
| `ip` | 17 | 3.3% |
| `manufacturing` | 17 | 3.3% |
| `marketing` | 17 | 3.3% |
| `franchise` | 15 | 2.9% |
| `agency` | 13 | 2.5% |
| `transportation` | 13 | 2.5% |
| `promotion` | 12 | 2.4% |
| `reseller` | 12 | 2.4% |
| `consulting` | 11 | 2.2% |
| `affiliate` | 10 | 2.0% |
| `non_compete_no_solicit` | 3 | 0.6% |

## 2. Filing context

| filing type | contracts |
|---|---|
| EX-10 | 385 |
| EX-99 | 48 |
| other | 33 |
| EX-4 | 19 |
| EX-1 | 13 |
| EX-2 | 5 |
| EX-7 | 3 |
| EX-9 | 1 |
| EX-13 | 1 |
| EX-16 | 1 |
| EX-6 | 1 |

## 3. Text length vs pipeline budgets

| budget | contracts over | share |
|---|---|---|
| 25k (small) | 311 | 61.0% |
| 90k (chunk window) | 88 | 17.3% |
| 128k (~32k tokens) | 49 | 9.6% |
| 256k (~64k tokens) | 7 | 1.4% |

## 4. Text length by subtype (chars)

| subtype | contracts | median | min | max |
|---|---|---|---|---|
| `agency` | 13 | 121,559 | 3,886 | 161,626 |
| `franchise` | 15 | 116,873 | 2,974 | 300,768 |
| `promotion` | 12 | 64,014 | 10,553 | 175,580 |
| `ip` | 16 | 56,683 | 5,046 | 155,463 |
| `transportation` | 12 | 50,613 | 6,088 | 229,670 |
| `collaboration` | 26 | 50,175 | 2,811 | 335,282 |
| `supply` | 21 | 49,915 | 5,713 | 188,674 |
| `outsourcing` | 18 | 49,361 | 1,952 | 338,211 |
| `co_branding` | 23 | 47,639 | 857 | 114,759 |
| `development` | 30 | 45,029 | 6,390 | 291,873 |
| `strategic_alliance` | 32 | 42,737 | 5,712 | 122,054 |
| `manufacturing` | 14 | 41,030 | 1,742 | 225,094 |
| `marketing` | 18 | 39,906 | 3,558 | 221,382 |
| `reseller` | 12 | 38,873 | 2,935 | 117,478 |
| `hosting` | 20 | 36,481 | 1,660 | 161,066 |
| `distributor` | 31 | 36,275 | 6,320 | 175,770 |
| `maintenance` | 34 | 32,920 | 1,707 | 233,248 |
| `affiliate` | 10 | 26,565 | 14,083 | 109,014 |
| `sponsorship` | 30 | 26,337 | 4,066 | 96,662 |
| `license` | 31 | 25,060 | 1,902 | 159,488 |
| `endorsement` | 24 | 22,068 | 3,456 | 68,204 |
| `service` | 27 | 20,983 | 3,860 | 289,615 |
| `consulting` | 11 | 20,805 | 12,020 | 33,425 |
| `joint_venture` | 23 | 3,971 | 645 | 95,181 |

## 5. Category presence (annotator YES rates)

| category | docs YES | rate | answer spans |
|---|---|---|---|
| Document Name | 510 | 100.0% | 521 |
| Parties | 509 | 99.8% | 2554 |
| Agreement Date | 470 | 92.2% | 476 |
| Governing Law | 437 | 85.7% | 464 |
| Expiration Date | 413 | 81.0% | 467 |
| Effective Date | 390 | 76.5% | 447 |
| Anti-Assignment | 374 | 73.3% | 654 |
| Cap On Liability | 275 | 53.9% | 672 |
| License Grant | 255 | 50.0% | 777 |
| Audit Rights | 214 | 42.0% | 643 |
| Termination For Convenience | 183 | 35.9% | 246 |
| Post-Termination Services | 182 | 35.7% | 450 |
| Exclusivity | 180 | 35.3% | 410 |
| Renewal Term | 176 | 34.5% | 210 |
| Revenue/Profit Sharing | 166 | 32.5% | 418 |
| Insurance | 166 | 32.5% | 560 |
| Minimum Commitment | 165 | 32.4% | 424 |
| Non-Transferable License | 138 | 27.1% | 298 |
| Ip Ownership Assignment | 124 | 24.3% | 318 |
| Change Of Control | 121 | 23.7% | 253 |
| Non-Compete | 119 | 23.3% | 259 |
| Notice Period To Terminate Renewal | 111 | 21.8% | 122 |
| Uncapped Liability | 111 | 21.8% | 167 |
| Covenant Not To Sue | 100 | 19.6% | 173 |
| Rofr/Rofo/Rofn | 85 | 16.7% | 367 |
| Volume Restriction | 82 | 16.1% | 171 |
| Competitive Restriction Exception | 76 | 14.9% | 125 |
| Warranty Duration | 75 | 14.7% | 176 |
| Irrevocable Or Perpetual License | 70 | 13.7% | 165 |
| Liquidated Damages | 61 | 12.0% | 121 |
| No-Solicit Of Employees | 59 | 11.6% | 91 |
| Affiliate License-Licensee | 59 | 11.6% | 115 |
| Joint Ip Ownership | 46 | 9.0% | 115 |
| Non-Disparagement | 38 | 7.5% | 65 |
| No-Solicit Of Customers | 34 | 6.7% | 58 |
| Third Party Beneficiary | 32 | 6.3% | 39 |
| Most Favored Nation | 28 | 5.5% | 38 |
| Affiliate License-Licensor | 23 | 4.5% | 69 |
| Unlimited/All-You-Can-Eat-License | 17 | 3.3% | 32 |
| Price Restrictions | 15 | 2.9% | 27 |
| Source Code Escrow | 13 | 2.5% | 66 |

## 6. Restriction-family span load per contract (key_obligations scope)

The extractor's ``key_obligations`` GT scope covers 31 of the 41 categories (the restriction/covenant families).

| metric | all categories | restriction families |
|---|---|---|
| mean spans/doc | 27.1 | 16.0 |
| median spans/doc | 22 | 11 |
| max spans/doc | 97 | 85 |
| docs with 0 spans | 0 | 49 |

## 7. Restriction-family co-occurrence highlights

Share = fraction of the less-common category's docs that also carry the other category (co-occurring docs / smaller YES count).

| category pair | share | co-occurring docs |
|---|---|---|
| Anti-Assignment + Change Of Control | 98% | 119 |
| Anti-Assignment + Most Favored Nation | 96% | 27 |
| Anti-Assignment + Competitive Restriction Exception | 93% | 71 |
| Anti-Assignment + Rofr/Rofo/Rofn | 92% | 78 |
| Anti-Assignment + Non-Compete | 91% | 108 |
| Anti-Assignment + Non-Disparagement | 89% | 34 |
| Anti-Assignment + No-Solicit Of Customers | 88% | 30 |
| Anti-Assignment + No-Solicit Of Employees | 88% | 52 |
| Anti-Assignment + Exclusivity | 87% | 156 |
| Competitive Restriction Exception + Exclusivity | 75% | 57 |

## 8. Data-quality markers

- Titles carrying redaction markers (`[***]`-style): 1
- Text bodies carrying redaction markers: 131 docs, 17013 markers total
- Zero-span docs (no labeled category at all): 0
- Figures: `figures/01`–`10` (subtype distribution, text lengths, category YES rates, category span load, spans/doc, filing types, subtype lengths, restriction co-occurrence, length budgets, annotation density)

