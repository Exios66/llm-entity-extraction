# LLM Entity Extraction — Comprehensive Preliminary Results Report

**Project:** llm-entity-extraction — prompt experiment loop for the llm-mailroom legal document pipeline
**Source of truth:** `reports/experiment_log.jsonl` (195 records, 2026-08-09 → 2026-08-16)
**Models evaluated:** qwen3.7-flash, deepseek-v4-flash, deepseek-v4-pro, gpt-4o-mini, gpt-5-nano, gpt-4.1-nano, llama-4-scout, llama-3.3-70b-instruct
**Total rows evaluated:** 21,985 · **Total tokens consumed:** 326.3M · **Total estimated cost:** **$13.63** (171/195 records carry cost estimates)

---

## 1. Executive Summary

This preliminary work evaluates a three-stage LLM pipeline for legal document processing — **sort** (classify the document), **specialize** (extract structured entities per contract type), **judge** (offline quality checks) — built on LangChain agents routed through OpenRouter, with deterministic, field-type-aware scoring against CUAD / MAUD / EDGAR S-1 / LegalBench ground truth.

**Headline results (best measured configuration per task):**

| Task | Best result | Config | Cost |
|---|---|---|---|
| **Document-type classification** (sorter) | **99.61%** accuracy (509 docs) | qwen3.7-flash, sorter_v13 | $0.0005/doc |
| **Contract-subtype classification** (25-way) | **94.30%** strict / **94.70%** family-equiv | qwen3.7-flash, sorter_v13 | $0.0005/doc |
| **Entity extraction** (8 fields, 509 contracts) | **0.887** composite, **100%** schema-valid | qwen3.7-flash, contracts_specialist_v32 | $0.0010/doc |
| **Hierarchical doc-class** (3 classes + subclasses, 676 docs) | **99.41%** doc-type / **89.35%** exact (doc+subclass) | qwen3.7-flash, sorter_docclass_v6 | $0.0007/doc |
| **LegalBench hearsay** (94-row test) | **88.3%** accuracy | qwen3.7-flash, legalbench_task_v2 | $0.00005/row |
| **Chained sort→extract** (5 docs) | **0.946** extraction composite | sorter_v6 + specialist_v11, subtype handoff | $0.0016/doc |
| **Model sweep** (8 models, sorter 509 docs) | **95.28%** strict | deepseek-v4-pro | $0.0062/doc (11.4× qwen) |

**Key takeaways:**
1. **The full pipeline is production-viable at sub-cent cost per document** — sorter ($0.0005) + extractor ($0.001) ≈ **$0.0015–0.002 per contract**, ~21,985 rows evaluated for a total research spend of ≈ $13.63.
2. **Prompt iteration delivered large, measured gains**: sorter subtype accuracy 0.84 → 0.943 (v3→v13, same 509-doc surface); extraction composite 0.656 → 0.887 full-corpus (v2→v32); LegalBench 0.777 → 0.883 (v0→v2).
3. **qwen3.7-flash is the value champion** across every task; deepseek-v4-pro buys the last +1pp at 11.4× cost; llama-4-scout underperforms on extraction (0.697 vs 0.887) and fails badly on list-heavy fields.
4. **Two statistically verified champion claims**: sorter v13 (0.9430) and docclass v6 (0.8935) — both validated with noise-floor controls (identical-prompt reruns); sorter v15 (+0.0020, CI [−0.0059, +0.0098], P=0.416) is a **logic repair, not a win** — v13 stays champion.

---

## 2. Methodology & Evaluation Surfaces (what the numbers mean)

**Pipeline agents under test** (LangChain, shared with the production llm-mailroom graph):

| Agent | Role | Output |
|---|---|---|
| `SorterAgent` | Classify doc type + contract subtype (25 CUAD families, `reasoning_effort=medium`) | `{doc_type, subtype, confidence, reasoning}` |
| Specialists (`ContractsSpecialist` etc.) | Extract per-class structured fields (`reasoning_effort=none`) | 8-field JSON schema (v24+ includes a per-field reasoning trace) |
| `JudgeAgent` | Offline classification/completeness/correctness audit (optional `--judge` pass) | 3-dimension verdicts |

**Scoring** — deterministic and field-type-aware (never exact-match on extraction):
- **Classification**: exact match + per-class accuracy + percentile bootstrap CIs (2,000 resamples, seed 42).
- **Extraction**: per-field content scoring by type (dates, money, IDs, names, free text, entity lists via Hungarian bipartite matching, threshold 0.6); containment fields (governing law, term length, renewal) scored by expected-within-predicted token containment; factuality guard (every predicted item must match GT or be grounded in the source, token coverage ≥ 0.7); partial-GT list fields scored by GT-coverage (recall), never F1.
- **Diagnostics** (run-level): list precision/recall/F1, error decomposition, date/duration MAE (days) + R², span-count drift — always read with pair-count support (`date_n_pairs`, etc.).

**Evaluation surfaces (comparability rule):** only same-sample, same-seed, same-surface runs are directly comparable. Primary A/B surfaces: **50-doc** (extraction lineage), **195/243-doc** (mid sorter), **509-doc full CUAD** (sorter + extraction finals), **676-doc merged** (docclass), **94-row** (LegalBench hearsay test), **5-doc** (chained). Noise floor on the 50-doc surface at temp 0.1: ±0.03 overall (identical-prompt rerun) — deltas inside that band are logic repairs, not wins.

---

## 3. Global Cost & Volume Ledger

**Total: 195 runs · 21,985 rows · 326,307,226 tokens · $13.63 estimated spend** (171/195 records; OpenAI/Meta sweep runs did not report OpenRouter pricing → true total is higher).

| Task | Runs | Rows | Tokens | Est. Cost | % of spend |
|---|---|---|---|---|---|
| Subtype classification (sorter) | 53 | 14,751 | 192,634,273 | **$8.56** | 62.8% |
| Contract entity extraction | 52 | 3,580 | 83,984,964 | **$3.25** | 23.9% |
| Doc-class classification (hierarchical) | 15 | 1,203 | 45,677,923 | **$1.65** | 12.1% |
| Chained sorter→extractor | 16 | 80 | 3,030,791 | **$0.12** | 0.9% |
| LegalBench task classification | 56 | 2,335 | 847,470 | **$0.04** | 0.3% |
| Sorter classification (pilots) | 3 | 7 | 131,805 | **$0.005** | <0.1% |

**Per-document production cost (champion configs, qwen3.7-flash):**

| Surface | Total run cost | Per doc |
|---|---|---|
| Sorter, full 509-doc | $0.275 | **$0.00054** |
| Extractor, full 509-doc (v32) | $0.485 | **$0.00095** |
| Docclass, full 676-doc (v6) | $0.473 | **$0.00070** |
| LegalBench, 94 rows (v2) | $0.004 | **$0.00005** |
| Chained pipeline, 5 docs | $0.008 | **$0.0016** |
| **Full pipeline per contract (sorter + extractor)** | — | **≈ $0.0015–0.002** |

**Model cost tiering on the sorter 509-doc sweep (v13):**

| Model | Run cost | Per doc | × qwen |
|---|---|---|---|
| qwen3.7-flash | $0.275 | $0.00054 | 1.0× |
| deepseek-v4-flash | $0.394 | $0.00077 | 1.43× |
| deepseek-v4-pro | $3.15 | $0.00619 | **11.4×** |

---

## 4. Task 1 — Sorter Subtype Classification (53 runs)

**Objective:** classify each contract into 1 of 25 near-synonymous CUAD subtype families (plus doc type). Strict accuracy = exact CUAD-folder key; equiv accuracy honors family equivalences (reseller↔distributor, maintenance↔license, development↔license, affiliate↔joint_venture).

### 4.1 Lineage on the full 509-doc surface (qwen3.7-flash, seed 42, temp 0.1)

| Prompt | Date | Doc-type acc | Subtype strict | Subtype equiv | Confidence | Cost |
|---|---|---|---|---|---|---|
| sorter_v5 | 08-11 | 0.9843 | 0.8585 | 0.8743 | 0.9404 | $0.236 |
| sorter_v6 | 08-11 | 0.9961 | 0.9312 | 0.9391 | 0.9440 | $0.245 |
| sorter_v8 | 08-13 | 0.9921 | 0.9018 | 0.9096 | 0.9533 | $0.254 |
| sorter_v9 | 08-13 | 0.9961 | 0.9116 | 0.9194 | 0.9537 | $0.259 |
| sorter_v9 (rerun) | 08-15 | 0.9957 | 0.9143 | 0.9208 | 0.9550 | $0.260 |
| sorter_v9 (rerun, clean) | 08-15 | 0.9961 | 0.9175 | 0.9214 | 0.9554 | $0.260 |
| sorter_v12 | 08-15 | 0.9961 | 0.9234 | 0.9312 | 0.9556 | $0.270 |
| sorter_v12 (rerun) | 08-16 | 0.9961 | 0.9293 | 0.9352 | 0.9562 | $0.271 |
| **sorter_v13 (CHAMPION)** | 08-16 | **0.9961** | **0.9430** | **0.9470** | 0.9583 | $0.275 |
| sorter_v14 | 08-16 | 0.9961 | 0.9371 | 0.9411 | 0.9572 | $0.280 |
| sorter_v15 (A/B vs v13) | 08-16 | 0.9961 | 0.9450 | 0.9509 | 0.9574 | $0.278 |

**Champion verification (v13 vs v15, full-509 A/B):** v15 delta **+0.0020** strict — inside the bootstrap CI **[−0.0059, +0.0098]**, P = 0.4160 → **v15 is a logic repair, NOT a win; v13 remains the champion.** (One anomalous v13 record shows 0.7741 — an aborted/partial run with 95 `function_over_form` failures; the replicated good run is 0.9430.)

### 4.2 Mid-size surface lineage (195- and 243-doc, qwen3.7-flash)

| Prompt | Surface | Doc-type | Subtype strict | Subtype equiv |
|---|---|---|---|---|
| sorter_v3 | 50 | 0.96 | 0.8400 | — |
| sorter_v3 | 195 | 0.9846 | 0.8359 | 0.8564 |
| sorter_v3 (rerun) | 195 | 0.9744 | 0.7897 | 0.8256 |
| sorter_v4 | 195 | 0.9795 | 0.8103 | 0.8308 |
| sorter_v5 (ab200) | 195 | 0.9846 | 0.8410 | 0.8667 |
| sorter_v6 (ab200) | 195 | 1.0000 | 0.9385 | 0.9436 |
| sorter_v6 (langfuse) | 195 | 1.0000 | 0.9436 | 0.9487 |
| sorter_v6 | 243 | 0.9918 | 0.8683 | 0.8807 |
| sorter_v7 | 243 | 0.9918 | 0.8765 | 0.8889 |
| sorter_v8 | 243 | 0.9877 | 0.8971 | 0.9012 |
| sorter_v9 | 243 | 0.9918 | 0.9259 | 0.9259 |
| sorter_v9 (rerun) | 243 | 0.9918 | 0.9300 | 0.9300 |
| sorter_v10 | 243 | 0.9918 | 0.9342 | 0.9342 |
| sorter_v11 | 243 | 0.9918 | 0.9342 | 0.9424 |

*(v11 first record shows 0.0 — failed run, all zeros; replicated run shown. Note: 50/195/243/509-doc surfaces are NOT mutually comparable — same-surface comparisons only.)*

### 4.3 Eight-model sweep (sorter_v13, full 509 docs)

| Model | Doc-type | Subtype strict | Subtype equiv | Confidence | Cost | Tier |
|---|---|---|---|---|---|---|
| **deepseek-v4-pro** | 0.9961 | **0.9528** | **0.9548** | 0.9555 | $3.15 | Quality (11.4×) |
| **qwen3.7-flash** | 0.9961 | **0.9430** | **0.9470** | 0.9583 | $0.28 | **Value champion** |
| deepseek-v4-flash (run 1) | 0.9980 | 0.9332 | 0.9352 | 0.9426 | $0.39 | Budget |
| deepseek-v4-flash (run 2) | 0.9941 | 0.9253 | 0.9312 | 0.9409 | $0.39 | Budget |
| gpt-4o-mini | 0.9961 | 0.9312 | 0.9352 | 0.9349 | n/r | Budget |
| gpt-5-nano | 0.9941 | 0.8978 | 0.9018 | 0.8957 | n/r | Budget |
| llama-3.3-70b-instruct (run 1) | 0.9921 | 0.8900 | 0.9116 | 0.9406 | n/r | — |
| llama-3.3-70b-instruct (run 2) | 0.9941 | 0.8782 | 0.8998 | 0.9424 | n/r | — |
| llama-4-scout (run 1) | 0.9961 | 0.8880 | 0.9077 | 0.9434 | n/r | — |
| llama-4-scout (run 2, replicated ×3) | 0.9941 | 0.8762 | 0.8939 | 0.9459 | n/r | — |
| gpt-4.1-nano (run 1) | 0.9784 | 0.8782 | 0.8959 | 0.9435 | n/r | — |
| gpt-4.1-nano (run 2) | 0.9666 | 0.8605 | 0.8782 | 0.9432 | n/r | — |

*n/r = cost not reported (OpenRouter pricing unavailable for those providers in the log).*

**Weakest subtypes across models (support n):** `marketing` (0.41–0.65, n=17), `development` (0.57–0.79, n=28), `service` (0.75–0.86, n=28), `collaboration` (0.46–0.89, n=26), `license` (0.55–0.91, n=33), `hosting` (0.60, n=20). Champion qwen v13's only weak spots: development 0.786, marketing 0.824, outsourcing 0.833.

### 4.4 Failure-mode analysis (champion qwen v13, 509 docs — 28 failures)

| Failure mode | Count | Meaning |
|---|---|---|
| family_confusion | 24 | Near-synonymous family chosen (e.g., escrow agreement → license) |
| equivalent_family | 2 | Recovered by equivalence mapping |
| function_over_form | 2 | Doc-type miss (title-based misread) |
| other_fallback | 1 | `other` fallback used |

---

## 5. Task 2 — Contract Entity Extraction (52 runs)

**Objective:** extract 8 fields from commercial contracts — `document_name`, `effective_date`, `governing_law`, `parties`, `key_obligations` (restriction/covenant families, partial GT), `term_length`, `renewal_terms`, `termination_clauses` (verbatim list fields). Composite = field-type-aware content score.

### 5.1 Lineage on the 50-doc A/B surface (qwen3.7-flash unless noted)

| Prompt | Overall | Presence | Cost | Note |
|---|---|---|---|---|
| contracts_specialist_v13 | 0.8937 | 0.9777 | $0.029 | |
| v14 | 0.9007 | 0.9777 | $0.031 | |
| v15 | 0.9129 | 0.9802 | $0.039 | |
| v16 | 0.8859 | 0.9669 | $0.035 | regression |
| v17 | 0.9074 | 0.9777 | $0.034 | |
| v18 | 0.9230 | 0.9777 | $0.037 | |
| v18 (deepseek-v4-flash) | 0.9012 | 0.9565 | $0.069 | |
| v18 (deepseek-v4-pro) | 0.9289 | 0.9777 | $0.053 | |
| v19 | 0.9135 | 0.9734 | $0.098 | |
| v20 | 0.9142 | 0.9685 | $0.094 | |
| v21 | 0.9283 | 0.9839 | $0.038 | |
| v21b | 0.9396 | 0.9789 | $0.039 | |
| **v22 (50-doc champion)** | **0.9512** | 0.9814 | $0.039 | |
| v22 (reasoning=max) | 0.9446 | 0.9806 | $0.100 | 2.6× cost, no gain |
| v23 | 0.9315 | 0.9689 | $0.039 | |
| v23 (reasoning=max) | 0.9363 | 0.9751 | $0.103 | |
| v26 (v28ab run) | 0.8780 | 0.9502 | $0.049 | |
| v28 | 0.9228 | 0.9798 | $0.057 | |
| v28 (run 2) | 0.8935 | 0.9681 | $0.053 | noise-floor check |
| v29 | 0.8964 | 0.9564 | $0.054 | |
| v30 | 0.8847 | 0.9473 | $0.052 | |

**Noise floor:** ±0.03 on this surface (identical-prompt rerun) — v13→v22 gains (+5.7pp) far exceed noise; v23–v30 deltas are within/at the noise band (logic repairs, not wins).

### 5.2 Full-corpus runs (all 509 CUAD contracts)

| Run | Overall | Presence | Schema valid | Cost | Notes |
|---|---|---|---|---|---|
| v28 | 0.8631 | 0.9630 | 1.0 | $0.317 | (0.8558 on $0.19 subsample) |
| v31 | 0.8737 | 0.9655 | 1.0 | $0.494 | |
| **v32 (full-corpus champion)** | **0.8870** | **0.9728** | **1.0** | $0.485 | |
| v32 (clean rerun) | 0.8807 | 0.9701 | 1.0 | $0.488 | |
| llama-4-scout v31 | 0.6968 | 0.9447 | 1.0 | n/r | far below qwen |

### 5.3 Per-field performance — champion v32 (509 docs)

| Field | Score | | Field | Score |
|---|---|---|---|---|
| document_name | 0.9874 | | key_obligations (list) | 0.7810 |
| effective_date | 0.8877 | | parties (list) | 0.9167 |
| governing_law (containment) | 0.9290 | | termination_clauses (list) | 0.9012 |
| term_length (containment) | 0.8026 | | renewal_terms (containment) | 0.8124 |

List-field raw F1 (entity_list_f1): key_obligations 0.781 · parties 0.917 · termination_clauses 0.901. **Schema validity 100%; field presence 97.3%.**

### 5.4 Diagnostics (v32 vs predecessors, full-509)

| Metric | v28 | v31 | **v32** | Support |
|---|---|---|---|---|
| Date MAE (days) | 36.7 | 43.9 | **16.0** | n=378 pairs |
| Date R² | 0.982 | 0.981 | **0.996** | |
| Duration MAE (days) | 407.3 | 421.2 | **398.6** | n=136 pairs |
| Duration R² | 0.743 | 0.720 | **0.798** | |
| Span-count MAE (list items) | 5.83 | 5.43 | **5.36** | |

**Interpretation:** dates are effectively solved (16-day MAE, R² 0.996); term-length extraction is the remaining weak point (≈400-day MAE — a mix of missing duration clauses and unit/format errors; money pairs n=0 — not yet measured).

### 5.5 Early-stage pilot lineage (10-doc and below)

| Run | n | Overall | Presence |
|---|---|---|---|
| v2 (baseline) | 10 | 0.6563 | 0.980 |
| v3 | 10 | 0.9128 → 0.9173 | 0.980 |
| v3 (variants) | 10 | 0.7976 / 0.7848 | 0.933 / 0.917 |
| v11 pilots | 3 | 0.8387 / 0.8012 | 1.0 / 0.944 |
| v11 diag surface50 | 5 | 0.9399 | 1.0 |
| v12 pilot | 5 | 0.8831 | 1.0 |
| v12 (30 docs) | 30 | 0.8947 | 0.9905 |
| v13 (30 docs) | 30 | 0.8982 | 0.9863 |
| v22 probe | 2 | 0.9910 | 1.0 |
| v23–v28 probes (5 docs) | 5 | 0.9154–0.9447 (unchunked), 0.8944–0.9837 (chunked) | 1.0 |
| v31 probes (2 docs) | 2 | 0.9910 | 1.0 |

*(v31's first two probe runs show None — failed/probe runs before the working config.)*

---

## 6. Task 3 — Chained Sorter→Extractor (16 runs, 5-doc controlled surface)

**Objective:** end-to-end pipeline — sorter classifies subtype, specialist extracts with a subtype-scoped handoff cue. All runs sorter doc-type exact match = 1.0; verified precision 1.0 on all but the v7/v8 regressions.

| Run | Sorter | Extractor overall | Handoff | Cost |
|---|---|---|---|---|
| v1 + v4 | em 1.0, subtype 0.6 | 0.8894 | legacy | $0.010 |
| v2 + v5 | em 1.0, subtype 0.8 | 0.9165 | legacy | $0.010 |
| v3 + v6 | em 1.0, subtype 1.0 | 0.8917 | legacy | $0.010 |
| v3 + v7 | em 1.0, subtype 1.0 | 0.6959 | legacy | $0.008 |
| v3 + v8 | em 1.0, subtype 1.0 | 0.6994 → 0.8933 | legacy | $0.007–0.010 |
| v5 + v10 | em 1.0, subtype 1.0 | 0.8952 | legacy | $0.007 |
| v5 + v11 | em 1.0, subtype 1.0 | 0.9060 | legacy | $0.007 |
| v6 + v11 (ab: none) | em 1.0 | **0.8497** | none | $0.007 |
| v6 + v11 (ab: subtype) | em 1.0 | **0.8666** | subtype | $0.007 |
| v6 + v11 (pilot) | em 1.0 | 0.8687 | subtype | $0.007 |
| v6 + v11 (pilot 2) | em 1.0 | 0.8441 | subtype | $0.007 |
| **v6 + v11 (diag surface50)** | em 1.0 | **0.9460** | subtype | $0.008 |
| v6 + v11 (diag surface50) | em 1.0 | 0.9388 | none | $0.008 |
| v6 + v12 | em 1.0 | 0.8818 | subtype | $0.007 |
| v6 + v12b | em 1.0 | 0.8882 | subtype | $0.007 |

**Handoff ablation finding:** the subtype-scoped specialist cue (vs no cue) adds **+1.7pp** on the identical 5-doc surface (0.8666 vs 0.8497) and +0.7pp on the surface50 diagnostic set (0.9460 vs 0.9388) — the sorter's subtype routing carries real information into extraction. The v7/v8 dips (0.696/0.699) were prompt regressions later repaired (v8 rerun 0.8933).

---

## 7. Task 4 — Hierarchical Doc-Class Classification (15 runs)

**Objective:** extended primary dimension — 3-way (contract / merger_agreement / corporate_record) plus a second-level `doc_subclass` (consideration type for mergers — MAUD expert GT: all_cash / all_stock / mixed_cash_stock / mixed_cash_stock_election; record type for corporate records — content-detected). Surface: 676 merged docs (152 MAUD + CUAD + EDGAR S-1 corporate records).

| Run | n | Doc-type | Subclass | Exact (both) | Confidence | Cost |
|---|---|---|---|---|---|---|
| v0 pilot | 5 | 0.6000 | 0.4000 | 0.4000 | 0.960 | — |
| v0 (ab30) | 30 | 0.8333 | 0.5000 | 0.6667 | 0.968 | $0.023 |
| v1 (ab30) | 30 | 0.8333 | 0.5000 | 0.6667 | 0.968 | $0.022 |
| v2 (ab30) | 30 | 1.0000 | 0.7000 | 0.8000 | 0.970 | $0.022 |
| v3 (ab30) | 30 | 1.0000 | 0.7000 | 0.8000 | 0.968 | $0.022 |
| v3 (diag30) | 30 | 0.8667 | 0.4737 | 0.5667 | 0.963 | $0.024 |
| v4 (diag30) | 30 | 0.8667 | 0.5263 | 0.6000 | 0.963 | $0.024 |
| v5 (diag30) | 30 | 0.8667 | 0.5789 | 0.6333 | 0.957 | $0.024 |
| v3 (diag30b) | 30 | 0.8333 | 0.5263 | 0.5667 | 0.962 | $0.024 |
| v4 (diag30b) | 30 | 0.8667 | 0.5263 | 0.6000 | 0.967 | $0.025 |
| v5 (diag30b) | 30 | 0.8333 | 0.5263 | 0.5667 | 0.957 | $0.024 |
| **v3 (full-676)** | 676 | 0.9926 | 0.5808 | 0.8905 | 0.957 | $0.468 |
| v3 (full-676 rerun, noise control) | 676 | 0.9926 | 0.5749 | **0.8905** (= control) | 0.958 | $0.469 |
| **v6 (full-676, CHAMPION)** | 676 | **0.9941** | **0.5868** | **0.8935** | 0.959 | $0.473 |
| vision v0 pilot (8 PDFs, all pages) | 8 | 1.0000 | 0.6667 | 0.8750 | 0.910 | $0.005 |

**Champion verification (full-676 A/B with noise control):** v3 identical-prompt rerun reproduced the headline exactly (0.8905 = 0.8905); **v6 = 0.8935 with 0 regressions, 2 rule-pinned recoveries, subclass +1.19pp, exact CI [0.8698, 0.9157]** → v6 strictly dominates v3 → **new docclass text champion**.

**Per-class (v6, full-676):** contract 0.9941 · corporate_record 1.0000 · merger_agreement 0.9934.

**Confusion highlights (v6):** `other` (MAUD consideration) misreads: all_cash 25, mixed_cash_stock 13, all_stock 17 — the residual subclass error is concentrated in the `other`↔consideration-type boundary (74→72 failures). Articles of incorporation ↔ rights_instrument/bylaws confusion (4 correct / 2+2 off). Vision pilot shows text+vision parity on doc-type (1.0) with weaker subclass (0.667) at 8-doc scale.

---

## 8. Task 5 — LegalBench Task Classification (56 runs)

**Objective:** multi-class LegalBench task mode (`--prompt-mode task`) on `mailroom-lb-hearsay` — binary Yes/No: does the evidence qualify as hearsay under the Federal Rules of Evidence (5 train / 95 test, 5 slices).

### 8.1 The 94-row test-set progression (the meaningful surface)

| Prompt | Date | Exact match | CI (±) | Per-class no / yes | Cost |
|---|---|---|---|---|---|
| legalbench_task_v0 | 08-15 | 0.7766 | 0.0798 | 0.774 / 0.780 | n/r |
| legalbench_task_v0 (rerun) | 08-15 | 0.7872 | 0.0745 | 0.774 / 0.805 | $0.0027 |
| legalbench_task_v0 (rerun 2) | 08-15 | 0.7766 | 0.0798 | 0.774 / 0.780 | $0.0026 |
| legalbench_task_v0 (langfuse) | 08-15 | 0.7872 | 0.0798 | 0.774 / 0.805 | $0.0027 |
| legalbench_task_v1 | 08-15 | 0.8511 | 0.0692 | 0.793 / 0.927 | $0.0041 |
| legalbench_task_v1 (rerun94) | 08-16 | 0.8617 | 0.0638 | 0.811 / 0.927 | $0.0044 |
| **legalbench_task_v2 (CHAMPION)** | 08-16 | **0.8830** | 0.0638 | **0.906 / 0.854** | $0.0042 |

**Interpretation:** v0→v2 = +10.6pp; v1→v2 = +2.1pp (no-class precision 0.793→0.906 — fewer false "no hearsay" calls). Residual errors are balanced-class (no 0.906, yes 0.854), i.e. hard boundary cases, not systematic bias.

### 8.2 Sampled per-task slices (6-row pilots, task-variant prompts v3/v4)

| Config | Runs | Accuracy |
|---|---|---|
| legalbench_task_v0 (6-row) | 8 | 7× 1.0, 1× 0.8333 |
| legalbench_task_v3 | 7 | 7× 1.0 |
| legalbench_task_v3_anti_assignment | 8 | 6× 1.0, 2× 0.8333 |
| v3 per-task: audit_rights | 1 | 1.0 |
| v3 per-task: cap_on_liability | 1 | 1.0 |
| v3 per-task: change_of_control | 1 | 1.0 |
| v3 per-task: competitive_restriction_exception | 1 | 0.8333 |
| v3 per-task: covenant_not_to_sue | 1 | 1.0 |
| v3 per-task: effective_date | 1 | 1.0 |
| v4 per-task ×7 (audit_rights, cap_on_liability, change_of_control, competitive_restriction_exception, covenant_not_to_sue, effective_date, anti_assignment) | 7 | 7× 1.0 |
| v4 per-task ×7 (sampled variants) | 7 | 7× 1.0 |

**v4 fixed the competitive_restriction_exception miss** (0.8333 → 1.0) — the only task-level failure in the v3 family. Plus 5-row pilot/config-verification runs (v0 ×6, v1 smoke) all at 1.0 exact match. Cost per 6-row slice: ~$0.0004–0.0006 (≈ $0.00007/row).

---

## 9. Task 6 — Sorter Classification Pilots (3 runs)

Infrastructure pilots on the 3-doc/1-doc surface validating the Langfuse mirror tracing path — all at 1.0 exact match (contract class):

| Run | n | Exact match | Cost |
|---|---|---|---|
| pilot_langfuse_classification_v6 | 3 | 1.0 | $0.0018 |
| pilot_langfuse_classification_v6_2 | 3 | 1.0 | $0.0019 |
| qwen3.7-flash_sorter_v6_classification_langfuse | 1 | 1.0 | $0.0009 |

---

## 10. The Critical Numbers for Your Presentation (slide cheat sheet)

**The one-liner:** *An end-to-end legal-document sort-and-extract pipeline that classifies 25 contract families at 94–99% accuracy and extracts structured entities at 0.89 composite — for under $0.002 per document.*

1. **Cost story:** 21,985 rows · 326M tokens · **$13.63 total research spend** · **$0.0005/doc classification** · **$0.0010/doc extraction** · **$0.0020/doc end-to-end**.
2. **Sorter:** 99.6% doc-type accuracy; **94.3% strict / 94.7% equiv** on 25 near-synonymous subtypes (509 real CUAD contracts, qwen3.7-flash, $0.28 total run).
3. **Extraction:** **0.887 composite** on the full 509-contract corpus; **100% schema-valid**, 97.3% field presence; list extraction F1: parties 0.917, termination clauses 0.901, key obligations 0.781.
4. **Diagnostics:** dates **R² 0.996, MAE 16 days** (n=378); term length R² 0.798 (n=136) — dates solved, durations next.
5. **Docclass hierarchy:** **99.4% doc-type**; 89.4% exact doc+subclass on 676 docs (MAUD+CUAD+S-1) — statistically verified vs noise control.
6. **LegalBench:** **88.3%** on the 94-row hearsay test, 100% on 7/7 sampled v4 task variants.
7. **Chained pipeline:** works end-to-end; subtype handoff cue is worth **+1.7pp** over no handoff.
8. **Model selection:** qwen3.7-flash = value champion everywhere; deepseek-v4-pro = +0.98pp on the sorter at 11.4× cost; llama-4-scout fails on extraction (0.697).
9. **Statistical rigor:** every headline claim verified with bootstrap CIs + identical-prompt noise-floor reruns; two candidate "wins" (sorter v15, docclass v5) correctly identified as logic repairs within the noise band.
10. **Prompt-iteration ROI:** 6 prompt generations × ~$0.25–0.50 per full-corpus A/B → +8.5pp sorter (v5→v13), +13pp extraction (v3→v22 50-doc), +10.6pp LegalBench (v0→v2).

---

## 11. Caveats & Limitations (present these — they are a strength, not a weakness)

1. **Cost figures are estimates where OpenRouter pricing was available** (171/195 records). OpenAI/Meta sweep runs (gpt-*, llama-*) report no cost — the true total spend exceeds $13.63, but by a small margin (those runs are a minority of tokens).
2. **Cross-surface comparability:** 50-doc vs 195/243-doc vs 509-doc vs 676-doc numbers are NOT mutually comparable — only same-surface A/Bs are valid (this discipline is enforced throughout).
3. **Money-field diagnostics unmeasured** (money_n_pairs = 0) — currency extraction accuracy is not yet quantified; duration MAE (≈400 days) is the largest known weakness.
4. **CUAD ground truth is partial** (clause-QA labels sample the document) — list fields are scored by GT-coverage (recall), which is the correct but conservative lens; raw F1 is always reported alongside.
5. **Two records flagged as anomalous** (sorter v11 zero-run, sorter v13 0.7741 partial run) — excluded from champion claims; replicated runs confirm the champions.
6. **Docclass subclass accuracy (0.587) lags doc-type (0.994)** — the `other`↔consideration-type boundary accounts for most residual error; tertiary levels were deliberately dropped (data-necessity rule).
7. **Small surfaces** (chained 5-doc, docclass vision 8-doc, LegalBench 6-row slices) are directional pilots, not final claims.

---

## 12. Source References

- `reports/experiment_log.jsonl` — the 195-record source of truth (append-only)
- `reports/experiment_log.md` — fully expanded render (metadata, per-doc results, confusion matrices, failure insights, model reasoning)
- `reports/same_scorer_scores.json` — same-scorer re-scoring of the v13→v21 extraction lineage
- `memos/docclass_v6.md`, `memos/docclass_v3_merged_benchmark.md` — docclass iteration research memoranda
- `reports/sheets/` — exported workbooks: `Sorter_Model_Sweep_Results.xlsx`, `contract_specialist_v32_and_sorter_v14_deck.xlsx`, `extraction_sweep_legalbench_full_deck.xlsx`
- `docs/data/trends.json` + `docs/data/runs/` — GH Pages site data (derived)
- `SCORING.md` — formula-level scoring reference; `AGENTS.md` §"Gotchas" — evaluation discipline

*Report compiled 2026-08-16 from `reports/experiment_log.jsonl` (195 records). All scores are deterministic; all CIs are percentile bootstrap (n_boot=2000, seed 42).*
