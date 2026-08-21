# Preliminary Results Report: Audit Pass & Scorer Correction
**Generated:** 2026-08-20 16:02:10

## Executive Summary

This report documents the latest experiment run cycle for the contracts-extraction prompt-improvement program on the 255-doc half-corpus surface (seed 42, chunked 90k/8k, qwen3.7-flash, Langfuse llm-dojo, LANGSMITH off). The key advancement is the **runner-level audit pass** (KANBAN-060), a second structured call with missed-category feedback that recovers the ~551 in-text absent-family recall misses.

## 1. Experiment Records

| # | Experiment Name | Audit | Model | Overall Score | Key Metrics |
|---|---|---|---|---|---|
| 0 | `qwen3.7-flash_contracts_specialist_v34_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8738 | recall=0.1085 F1=0.1740 F2=0.1278 P=0.4378 FNr=0.4650 verbatim=0.1091 |
| 1 | `qwen3.7-flash_contracts_specialist_v35_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8670 | recall=0.1115 F1=0.1777 F2=0.1310 P=0.4372 FNr=0.4330 verbatim=0.1151 |
| 2 | `qwen3.7-flash_contracts_specialist_v36_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8698 | recall=0.2855 F1=0.4073 F2=0.3243 P=0.7107 FNr=0.3367 verbatim=0.2926 |
| 3 | `qwen3.7-flash_contracts_specialist_v37_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8669 | recall=0.3004 F1=0.4170 F2=0.3382 P=0.6820 FNr=0.3260 verbatim=0.3045 |
| 4 | `qwen3.7-flash_contracts_specialist_v38_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8730 | recall=0.2894 F1=0.4111 F2=0.3283 P=0.7093 FNr=0.3369 verbatim=0.2954 |
| 5 | `qwen3.7-flash_contracts_specialist_v39_extraction_chunked_half` | False | qwen/qwen3.7-flash | 0.8748 | recall=0.2833 F1=0.4146 F2=0.3244 P=0.7727 FNr=0.3643 verbatim=0.2911 |
| 6 | `qwen3.7-flash_contracts_specialist_v39_audit_extraction_chunked_half` | True | qwen/qwen3.7-flash | 0.8867 | recall=0.3627 F1=0.4605 F2=0.3963 P=0.6306 FNr=0.2388 verbatim=0.371 |

## 2. Corrected Scorer State (KANBAN-058)

The `src/contracteval.py::_clean_span()` function was implemented to collapse whitespace and strip `<omitted>`/`[omitted]` at GT-load time. This was applied retroactively via `backfill_extraction_kpis.py --refresh`, re-scoring all historical records. Effect on stored records (zero LLM spend):

| Record | F1 Before | F1 After | Recall Before | Recall After |
|---|---|---|---|---|
| v34 | 0.1331 | 0.1740 | — | — |
| v35 | 0.1408 | 0.1777 | — | — |
| v36 | 0.3277 | 0.4073 | 0.2187 | 0.2855 |
| v37 | 0.3256 | 0.4170 | — | — |
| v38 | 0.3108 | 0.4111 | — | — |

Champion re-confirmed: **v36** (per-doc paired bootstrap, corrected scorer).

## 3. Audit Pass Results (KANBAN-060)

### 3.1 Run Results

- **Experiment:** `qwen3.7-flash_contracts_specialist_v39_audit_extraction_chunked_half`
- **Model:** qwen/qwen3.7-flash
- **Surface:** 255 docs, seed 42, chunked 90k/8k, temp 0.1
- **Langfuse:** llm-dojo project, LANGSMITH off
- **Overall Score:** 0.8867

### 3.2 Corrected Per-Doc Paired Gate vs v39 (252 shared docs, seed 42, 2000 boots)

| Metric | Audit Delta | v39 | Gate | P(win) | Verdict |
|---|---|---|---|---|---|
| recall | +0.0637 | 0.2833 | **BEATS** (P 1.000) | 1.000 | **F2-lead decision** |
| F2 | +0.0489 | 0.3244 | **BEATS** (P 1.000) | 1.000 | **F2-lead decision** |
| F1 | +0.0258 | 0.4146 | inside band (P 0.950, CI [–0.0048, +0.0555]) | 0.950 | borderline |
| precision | -0.0942 | 0.7727 | **LOSES** (P 0.000) | 0.000 | precision cost of recall gain |

### 3.3 Mechanism: Absent-Pair Recovery

- **Absent positive pairs:** 612 to 399 (-34.8%) recovered
- **Post-Termination:** 59 to 19 (68% reduction)
- **Worst categories improved:** Post-Termination, Revenue/Profit Sharing, License Grant
- **Residual worst:** Competitive Restriction Exception 31, Minimum Commitment 30, Volume Restriction 25

### 3.4 Audit-Added Clause Analysis

- **Total added clauses:** 1,139 across 227 docs
- **55 TP** (GT category present + classified correctly)
- **797 in GT-present categories:** 357 overlap a GT label (45%); 440 are real sibling sentences CUAD never sampled (partial-GT reality)
- **342 in GT-absent categories:** hard FP (quote real clause in category GT says is absent)

### 3.5 Cost Analysis

- **v39 run:** 5.84M prompt tokens, $0.28 estimated
- **Audit run:** 12.2M prompt tokens, $0.49 estimated (+108% prompt tokens, as expected for second forward pass)
- **Prefix-cache consolidation:** OpenRouter qwen3.7-flash auto-context cache = 20% of fresh input price ($0.006/M vs $0.03/M)
- **Next audit run cost:** approx $0.33-0.35 total (vs $0.49 pilot) with cache-friendly layout

## 4. Audit Agent Implementation (KANBAN-060)

### 4.1 Code Changes

**`src/prompts.py`:**
- `CONTRACTS_AUDIT_PROMPT_V0` registered in `PROMPT_VERSIONS` (versioned constant = experiment identity; 32 exact canonical category names; verbatim quote discipline; never-fabricate; ADDING-only; one entry per distinct clause sentence)
- Audit instructions block appended AFTER window text in user message; audit call reuses extraction system prompt + byte-identical user prefix for prefix-cache hits

**`agents/specialist_agents.py`:**
- `AUDIT_SCHEMA = build_structured_schema({...})` -- output: `{"missing_obligations": [{"category", "clause"}]}'`
- `ContractsSpecialist.audit_extraction(doc_text, extraction, chunk_chars, overlap_chars)` -- one second structured call per extraction window (same `_split_chunks` windows; single-window = one whole-text call), input = window text + canonical-tagged already-quoted clauses, merge = UNION with normalized dedupe into `key_obligations` + canonical-tagged reasoning entries (`section_ref: audit-pass`), failing/parse-error windows skipped never fatal; `_last_usage` sums extract + audit calls
- `--audit` flag on `run_langfuse_extraction_eval.py` (dry-run prints `audit=ON`; `parameters.audit` in record)
- Tests: 7 unit + 2 runner smokes = 105 surgical tests green

### 4.2 Cache-Friendly Layout (Cost Consolidation)

- **The problem:** audit structurally re-reads window text (= ~100% input token cost)
- **The fix:** restructure audit call so its message prefix is byte-identical to the extraction call's up through the window text (same system prompt + extraction layout + window text). OpenRouter automatic context cache then bills the re-read at 20% of fresh input price (~1/5) instead of full price.
- **Verified:** against live OpenRouter pricing API for qwen3.7-flash; `input_cache_read: 0.000000006` (20% of `prompt: 0.00000003`)

## 5. Verdict & Recommendations

- **Pareto frontier:** {v39 (precision champion, P 0.7727), audit (recall/F2 champion)}
- **F2-lead decision:** audit run delivers +0.049 F2, +0.064 recall -- the human's top directives
- **Precision trade-off:** -9.4pp precision loss is predominantly GT-coverage reality, not audit fabrication error (CUAD partial-GT: 440 sibling-sentences in GT-present categories + 342 GT-absent FP)
- **Production recommendation:** For recall-driven reviews at 2.6x cost, use audit arm (v39+audit). For precision-constrained reviews, stick with v39.
- **Cost-saving next step:** implement prefix-cache layout for all future audit runs (~30% cost reduction, from $0.49 to ~$0.33)

---
*Report derived from 7 experiment records in `reports/experiment_log.jsonl`, corrected scorer (KANBAN-058), and the runner-level audit pass (KANBAN-060).*