# LegalBench tasks (hearsay + CUAD subtasks)

_Emitted by `scripts/eda/explore_pipeline_sources.py --source legalbench`_
_Note: Source: LegalBench (Neel Guha et al.) — hearsay + CUAD clause subtasks, CC BY 4.0_

**9 files** / **141 rows** under `data/legalbench_local/`

| task | rows | type | answers | slices | median chars |
|---|---|---|---|---|---|
| cuad_anti-assignment | 6 | Binary classification | Yes 3, No 3 | ? | 278 |
| cuad_audit_rights | 6 | Binary classification | Yes 3, No 3 | ? | 391 |
| cuad_cap_on_liability | 6 | Binary classification | Yes 3, No 3 | ? | 420 |
| cuad_change_of_control | 6 | Binary classification | Yes 3, No 3 | ? | 288 |
| cuad_competitive_restriction_exception | 6 | Binary classification | Yes 3, No 3 | ? | 298 |
| cuad_covenant_not_to_sue | 6 | Binary classification | Yes 3, No 3 | ? | 372 |
| cuad_effective_date | 6 | Binary classification | Yes 3, No 3 | ? | 218 |
| hearsay-test | 94 | Binary classification | No 53, Yes 41 | Standard hearsay, Not introduced to prove truth, Non-assertive conduct, Statement made in-court, Non-verbal hearsay | 133 |
| hearsay | 5 | Binary classification | No 3, Yes 2 | Non-assertive conduct, Standard hearsay, Not introduced to prove truth, Statement made in-court, Non-verbal hearsay | 122 |

## Hearsay split

- **hearsay-test**: 94 rows, No 53 (56%), Yes 41 (44%) — slices: Standard hearsay, Not introduced to prove truth, Non-assertive conduct, Statement made in-court, Non-verbal hearsay
- **hearsay**: 5 rows, No 3 (60%), Yes 2 (40%) — slices: Non-assertive conduct, Standard hearsay, Not introduced to prove truth, Statement made in-court, Non-verbal hearsay
