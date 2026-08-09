# Extraction scoring report — extract_v2.jsonl

Rows: 6 completed

## Per-field content scores (mean over scored rows)

| field | n | mean |
|-------|---|------|
| overall | 6 | 0.6207 |
| field_presence | 6 | 0.9444 |
| schema_valid | 6 | 1.0 |
| effective_date | 6 | 0.5509 |
| governing_law | 6 | 1.0 |
| key_obligations | 6 | 0.3011 |
| parties | 6 | 0.6389 |
| renewal_terms | 2 | 0.7304 |
| term_length | 6 | 0.6664 |
| termination_clauses | 3 | 0.4445 |

## Per-document scores

| document | overall | ambiguous | field scores |
|----------|---------|-----------|--------------|
| document_2 | 0.5075 | parties,term_length,termination_clauses | effective_date=0.000; governing_law=1.000; key_obligations=0.222; parties=0.500; term_length=0.656; termination_clauses=0.667 |
| document_1 | 0.6637 | effective_date,key_obligations,parties,renewal_terms | effective_date=0.617; governing_law=1.000; key_obligations=0.500; parties=0.667; renewal_terms=0.723; term_length=0.475 |
| document_3 | 0.7495 | parties,term_length,termination_clauses | effective_date=1.000; governing_law=1.000; key_obligations=0.353; parties=0.667; term_length=0.811; termination_clauses=0.667 |
| document_4 | 0.6059 | effective_date,parties,term_length | effective_date=0.689; governing_law=1.000; key_obligations=0.148; parties=0.667; term_length=0.526 |
| document_6 | 0.4653 | parties | effective_date=0.000; governing_law=1.000; key_obligations=0.250; parties=0.667; term_length=0.875; termination_clauses=0.000 |
| document_5 | 0.7322 | parties,renewal_terms,term_length | effective_date=1.000; governing_law=1.000; key_obligations=0.333; parties=0.667; renewal_terms=0.737; term_length=0.656 |
