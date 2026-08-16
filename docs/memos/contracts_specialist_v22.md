# Research Memo: v22 — the ko-recovery arm (verbatim completeness + disciplined dedupe; overall 0.9512, ko 0.8294 → 0.8442 across reasoning settings)

**Research question:** key_obligations accuracy dropped from v19's 0.8840 to
~0.82 on the v21 production arm. What exactly did the v19/v20 prompt changes
cost the obligation extraction — and can a surgical prompt fix recover the
spans at reasoning=none (the production setting)?

**Companions:**
[contracts_specialist_v21.md](contracts_specialist_v21.md)
· [contracts_specialist_v20.md](contracts_specialist_v20.md) ·
[contracts_specialist_v19.md](contracts_specialist_v19.md) ·
experiment log (runs 044–054, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** The regression decomposes into two measurable mechanisms
plus variance. (1) **Ellipsis abbreviation** — 23.6% of v21 items contain
"..." (v18: 15.8%): truncated quotes fail token overlap AND embedding
similarity. (2) **Over-deduplication** — the v19 SPAN DISCIPLINE dedupe
dropped distinct requirements sharing wording (LegacyEducation fell 19 → 12
items: records-keeping, insurance, sell-off period and assignment-exception
clauses lost). v22 narrows the dedupe to same-requirement pairs and adds a
VERBATIM COMPLETENESS rule; the scored result is **ko 0.8294 at
reasoning=none and 0.8442 at max, with overall 0.9512 (series best) and
0.9446 respectively, both 50/50 rows**. The span-level recovery is partial
(34 of 38 v18-matched spans still missed at token level) — the residual is
span-choice/boundary divergence plus residual abbreviation, and the
identical-setting pass variance (±2.2pp) means the v19 0.8840 was the
favorable max-reasoning roll, not a reproducible config.

### The reasoning-matrix (same 50 docs, chunked, seed 42, llm-dojo, qwen3.7-flash)

| Metric | v18 none | v19 max | v21 none | v22 none | v22 max |
|---|---:|---:|---:|---:|---:|
| key_obligations | 0.8535 | **0.8840** | 0.8168 | 0.8294 | 0.8442 |
| overall | 0.9230 | 0.9135 | 0.9396 | **0.9512** | 0.9446 |
| overall CI | .891-.949 | .877-.946 | .904-.965 | **.934-.967** | .922-.965 |
| items / ellipsis | 1118 / 15.8% | 792 / 27.1% | 890 / 23.6% | 841 / **19.5%** | 902 / 20.5% |
| rows ok/errors | 50/0 | 49/1 | 50/0 | **50/0** | **50/0** |
| verified_precision | 0.991 | 0.988 | 0.980 | 0.991 | **0.996** |
| cost | $0.037 | $0.098 | $0.039 | **$0.039** | $0.100 |

### Interpretation

1. **Ellipsis was a real, quantified regression mechanism.** The v19 length-
   anchor + discipline rules pushed the model to abbreviate clauses with
"...", and a 23.6% ellipsis rate directly explains a large share of the
token-level misses (an item like "T&B hereby grants to LEA... the sole
and exclusive worldwide right" cannot match the full GT span). v22's
VERBATIM COMPLETENESS rule cut this to 19.5-20.5% — and the max arm's
zero parse errors (vs 1/50 for v19/v20 max) suggest the output
discipline also kept the structured-output budget in check.
2. **The dedupe fix held LegacyEducation-class clauses** (the 19-item list
   rebuilt) but the scored ko gain is modest (+1.3pp none, +2.7pp vs v21 at
max): 34 of the 38 lost spans remain token-level misses — the residual
is the annotator-vs-model span choice, which no output rule has fully
bridged since v15.
3. **The ko ceiling is ~0.85 at none and ~0.88 at max (best roll).** Two
   identical-setting passes swing ±2.2pp; v19's 0.8840 was the favorable
roll. The honest production choice is v22×none (overall 0.9512, CI
.934-.967 — the first arm whose CI clears v18's point estimate) with ko
~0.83, or v22×max for +1.5pp ko at 2.6x cost. v19×max is not
reproducible at its headline number.
4. **Project strategy locked in (per direction):** llm-dojo = prompt
   iteration (this repo); llm-mailroom = full-pipeline testing (the
llm-mailroom repo); insights flow llm-dojo → llm-mailroom. v22 synced
to llm-dojo's prompt store; the llm-mailroom project is one key file
away via `sync_langfuse_prompts.py --env-file`.

*Sources:* `reports/experiment_log.jsonl` (runs 044–054, task
`contract_entity_extraction`) · `V16_PROPOSITION.md` §12–13 ·
`SCORING.md` §4/§8 (entity_list_audit, span-level diagnostics) ·
`src/prompts.py` v21/v22 banners · `AGENTS.md` (two-project strategy) ·
`CHANGELOG.md` · corpus = CUAD (Hendrycks et al., 2021 —
[CUAD dataset](https://github.com/TheAtticusProject/cuad)) · runner =
[LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **The residual 34 spans.** Span-choice divergence (the model picks a
   different fragment of the same clause than the annotator) survives every
output rule; a worked-example set built from those 34 exact spans is the
next lever (v23).
2. **The annotation-queue loop.** The parallel annotation-queue tool
   (`run_annotation_queue.py`) is now available for the low-performing
traces — the 0-ko docs (SPRINGBANK, QBIOMED, PelicanDelivers) are its
first target.
3. **Roll variance.** ±2.2pp between identical passes means single-run
   deltas below ~3pp should be treated as noise; the same-surface CI is the
decision instrument.
4. **The full-pipeline handoff.** Porting the v22 prompt into the
   llm-mailroom agents is the deliverable of the llm-dojo → llm-mailroom
flow; the sync script makes the prompt versions available to that
project on demand.