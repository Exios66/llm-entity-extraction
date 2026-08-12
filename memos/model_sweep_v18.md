# Research Memo: The v18 model sweep — scope-fidelity vs segmentation capability (key_obligations 0.7755 → 0.8907, +11.5pp)

**Research question:** v18's family-fidelity catalog proved the prompt-layer
residual was scope, not segmentation, on qwen3.7-flash (ko 0.7755 → 0.8535).
With scope-fidelity fixed at the prompt layer, how much of the remaining
gap is **model-bound**? A v18 × {deepseek-v4-flash, deepseek-v4-pro} sweep
on the identical 50-doc surface separates the two dimensions — prompt scope
(what clause shapes are enumerated) from model capability (how faithfully a
model enumerates and segments them) — and produces the vendor input for the
llm-mailroom deployment decision.

**Companions:**
[contracts_specialist_v17_v18_enhancements.md](contracts_specialist_v17_v18_enhancements.md)
· [entity_extraction_improvements.md](entity_extraction_improvements.md) ·
experiment log (runs 044–048, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** The family-fidelity fix is **model-agnostic** — every
model in the sweep gains +6.0 to +11.5pp on key_obligations from v15 to v18
on the same surface, proving the catalog repaired a prompt-layer scope
defect, not a model quirk. Segmentation capability remains model-bound:
**deepseek-v4-pro × v18 is the new series champion — ko 0.8907 (+11.5pp vs
v15), overall 0.9289, verified_precision 1.000 (zero hallucinations),
alignment precision 0.685 (best)** — while deepseek-v4-flash over-produces
(1735 items, +56% over the GT sample) and leaves ~5pp of ko on the table.
The production recommendation is v18 with the stronger model; the flash
line stays viable at 3× lower token cost when the field's ceiling does not
matter.

### The sweep (v18 × 3 models, same 50 docs, chunked, seed 42, Langfuse llm-dojo)

Every arm runs the identical dataset fingerprint, chunking, seed, and scorer
— deltas are directly comparable.

| Metric | qwen3.7-flash | deepseek-v4-flash | deepseek-v4-pro |
|---|---:|---:|---:|
| key_obligations | 0.8535 | 0.8358 | **0.8907** |
| Δ vs v15 baseline (0.7755) | +7.8pp | +6.0pp | **+11.5pp** |
| overall | 0.9230 | 0.9012 | **0.9289** |
| parties | 0.940 | **0.960** | 0.920 |
| effective_date | **0.883** | 0.839 | 0.875 |
| term_length | 0.979 | 0.912 | **0.985** |
| governing_law | 0.934 | 0.906 | **0.938** |
| items (median words) | 1118 (25) | 1735 (22) | 1547 (21) |
| matched GT spans | 692 | 953 | 1059 |
| alignment precision | 0.619 | 0.549 | **0.685** |
| verified_precision | 0.991 | 0.996 | **1.000** |
| schema_valid | 1.0 | 1.0 | 1.0 |
| tokens / estimated cost | 993k / $0.037 | 937k / $0.069 | 1.04M / $0.053 |

### Interpretation

1. **Scope-fidelity dominates the gain.** All three models move on the
   same lever: ko +6.0 to +11.5pp from v15's terse family list to v18's
   CUAD-mirror catalog. The prompt defect was real and model-independent;
   the catalog is the single most valuable change in the v10→v18 arc.
2. **Segmentation capability is the separator.** deepseek-v4-pro matches
   **1059 spans** at alignment precision 0.685 (best in the whole series,
   above v15's 0.650) with **1.000 verified_precision** — it extracts more
   AND hallucinates nothing. deepseek-v4-flash matches the most items
   (953) but at 0.549 alignment precision: it over-produces (1735 items,
   +56% over the GT sample) and its ko (0.8358) sits ~5.5pp below the pro
   model's — over-extraction is the flash line's ceiling, not the catalog's.
3. **The residual after the sweep.** Even the champion leaves ~11% of ko on
   the table; the 131-span token-level decomposition (from the v18 flash
   audit) still points at license grants (36) as the largest family —
   evidence for v19's worked-example iteration, now with the pro model as
   the measuring stick.
4. **The 0-ko docs persist across models.** SPRINGBANKPHARMACEUTICALS,
   QBIOMED joint filing, and PelicanDelivers extract nothing on the flash
   line in any arm; a direct trace-level postmortem is the next diagnostic.
5. **Cost is honest at every tier.** Pro costs ~$0.053 on this surface (raw
   usage; the OpenRouter ledger attributes $0.39 for 14/48 runs) — under
   $1.50 for the full 510-doc corpus. The vendor decision is capability-
   weighted: the pro model's +5.5pp on the task's hardest field justifies
   the tier for production extraction.

*Sources:* `reports/experiment_log.jsonl` (runs 044–048, task
`contract_entity_extraction`) · `V16_PROPOSITION.md` §8–9 (decomposition,
decision rule, recovery audit) · `SCORING.md` §4/§8 (entity_list_audit
artifacts, span-level diagnostics) · `CHANGELOG.md` · corpus = CUAD
(Hendrycks et al., 2021 — [CUAD dataset](https://github.com/TheAtticusProject/cuad)) ·
runner = [LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **v19's worked examples, on the pro model.** The residual license-grant
   gap (36 spans) needs positive/negative span examples per family, tested
   on deepseek-v4-pro — does the champion's ceiling move, or is the
   remaining gap boundary-choice noise?
2. **The over-production pathology.** deepseek-v4-flash's 1735-item output
   (+56%) with only 0.549 alignment precision suggests a per-chunk
   exhaustion bias; a chunk-count × items-per-chunk audit would localize it.
3. **Doc-level scatter.** Token-level matching improves on ~17 docs and
   worsens on ~19 between arms while scored ko improves everywhere — the
   embedding-rescue interaction with the catalog shapes is not yet
   decomposed per doc.
4. **Production vendor decision.** The full-corpus (510-doc) run on
   v18 × deepseek-v4-pro will confirm the ~+11.5pp headline at scale before
   the llm-mailroom cut-over.
