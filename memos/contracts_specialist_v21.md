# Research Memo: v21 — the merge arm at reasoning=none (overall 0.9283 → 0.9396, Ediets parse error fixed, ko confound resolved)

**Research question:** v19 (worked examples + span discipline) won ko at
max reasoning but cost 2.6x and dropped a parse-error row (EdietsComInc
EX-10.4); v20 added the four field rules and won the non-obligation fields
but its ko swung −7.3pp in diffuse variance. Two questions remained: does
the merge (v19 content + v20 rules) hold both gains, and how much of the
ko numbers is the PROMPT versus the REASONING setting?

**Companions:**
[contracts_specialist_v20.md](contracts_specialist_v20.md)
· [contracts_specialist_v19.md](contracts_specialist_v19.md) ·
[model_sweep_v18.md](model_sweep_v18.md) ·
experiment log (runs 044–051, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** v21 (identical prompt text to v20, at
`reasoning_effort=none`) is the production arm: **overall 0.9396 (+1.7pp
vs v18 — best on the flash line), 50/50 rows with zero parse errors (the
Ediets failure mode is gone), verified_precision 0.997, at $0.039 — 2.6x
cheaper than the max-reasoning arms.** The confound is resolved: the v19 ko
gain was the reasoning setting, not the examples. And the analysis surfaced
two date-scorer bugs whose fixes moved effective_date 0.806 → 0.945.

### The four-arm comparison (same 50 docs, chunked, seed 42, qwen3.7-flash)

| Metric | v18 (none) | v19 (max) | v20 (max) | v21 (none) |
|---|---:|---:|---:|---:|
| overall | 0.9230 | 0.9135 | 0.9142 | **0.9396** |
| key_obligations | 0.8535 | **0.8840** | 0.8113 | 0.8168 |
| parties | 0.940 | 0.918 | **1.000** | 0.980 |
| effective_date | 0.883* | 0.865* | 0.801 | **0.945** |
| term_length | 0.979 | 0.968 | 0.966 | **0.985** |
| governing_law | 0.934 | 0.932 | 0.919 | **0.938** |
| renewal_terms | 0.841 | 0.816 | 0.861 | **0.905** |
| termination_clauses | 0.938 | 0.938 | 0.867 | 0.938 |
| document_name | 0.957 | 0.960 | 0.991 | **0.991** |
| rows ok / errors | 50/0 | 49/1 | 49/1 | **50/0** |
| verified_precision | 0.991 | 0.988 | 0.987 | **0.997** |
| cost | $0.037 | $0.098 | $0.094 | **$0.039** |

*pre-fix scorer (see below).

### Interpretation

1. **The Ediets error was a reasoning-budget failure, fixed by the setting.**
   The v19 row burned 9.8k completion tokens on 2 chunks (max reasoning)
and returned unparseable JSON (ko 0.846 → 0.000). At reasoning=none the
same prompt+doc parses cleanly (ko 0.769, overall 0.967, 1.0k completion
tokens). v21 runs 50/50; MidwestEnergy (v20's error) also recovered.
2. **The prompt-vs-reasoning confound is resolved.** At fixed reasoning=none,
   the v19/v20 prompt content scores ko 0.8385 — BELOW v18's catalog-only
0.8535. The +3.0pp v19 "gain" was the max-reasoning setting. v19's ko
crown (0.8840) is real but costs 2.6x and carries a 1/50 parse-error
risk; v21's overall is the better production trade (the field rules
+span discipline +scorer fixes recover far more than ko gives up).
3. **The date-scorer bugs (found during the v21 analysis) were the biggest
   single score lever.** The v20-era null-expectation rule (a) fired on
parseable compact dates — three perfect matches ("11/4/10" → ISO) scored
0.0 — and (b) was bypassed for null predictions (the `pred is None`
short-circuit returned 0.0 before the rule ran), leaving five
blank-template docs at 0.0 despite the model answering CORRECTLY. With
both fixed: effective_date 0.806 → 0.945 (+14pp), overall +1.1pp.
4. **All experiments now run in llm-dojo with prompts synced between
   projects.** Verified via the traces API that the project-scoped keys have
routed every run (incl. the mislabeled v21 passes) into llm-dojo; the
label default is now llm-dojo too. `sync_langfuse_prompts.py` mirrors
all 43 prompt versions into Langfuse (idempotent), ready to add the
primary project's key file for the second-project sync.

*Sources:* `reports/experiment_log.jsonl` (runs 044–051, task
`contract_entity_extraction`) · `V16_PROPOSITION.md` §10–12 ·
`SCORING.md` §3 (null-expectation dates, contained labels/titles) ·
`src/field_scoring.py` (v21-era date fixes) · `src/langfuse_config.py` +
`scripts/eval/sync_langfuse_prompts.py` (llm-dojo default + prompt sync) ·
`CHANGELOG.md` · corpus = CUAD (Hendrycks et al., 2021 —
[CUAD dataset](https://github.com/TheAtticusProject/cuad)) · runner =
[LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **The ko trade is deliberate.** v21 accepts ko 0.8168 for overall 0.9396.
   If the ko ceiling matters (the hardest field), v19×max holds it at 2.6x
cost — a deployment choice per workload.
2. **Same-scorer historical records.** v18/v19 records still hold pre-fix
   date scores; a permanent re-scoring pipeline would make every historical
comparison immune to scorer drift (flagged in the v20 memo).
3. **The duplicate v2 Langfuse prompt versions.** The first sync (pre-
   idempotency fix) left identical-content v2 versions in llm-dojo; the
version-delete API path 404s on this instance — a UI cleanup item.
4. **The 0-ko docs.** SPRINGBANK, QBIOMED, PelicanDelivers remain
   extraction-poor across arms; a trace-level postmortem is still open.