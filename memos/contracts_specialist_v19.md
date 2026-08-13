# Research Memo: Contracts-specialist v19 — worked span examples + span discipline (key_obligations 0.8535 → 0.8840, +3.0pp; alignment precision 0.619 → 0.662)

**Research question:** v18's family-fidelity catalog lifted ko to 0.8535 but
left two measurable residuals on the qwen3.7-flash 50-doc surface: (1) 93 of
241 token-level-unmatched GT spans were license-shaped — yet only 25 of the
107 license-ish GT spans carry the naive "grants ... a license" phrasing —
and (2) 71% of predicted items were token-unmatched, 225 of them
near-duplicates of another emitted item (sentence+fragment pairs; one audit
clause emitted twice in a single chunk). Do WORKED SPAN EXAMPLES drawn
verbatim from the residual misses (instead of prose shapes) plus a SPAN
DISCIPLINE dedupe rule close both gaps — and at what reliability/cost
trade when run at reasoning_effort=max?

**Companions:**
[contracts_specialist_v17_v18_enhancements.md](contracts_specialist_v17_v18_enhancements.md)
· [model_sweep_v18.md](model_sweep_v18.md) ·
[entity_extraction_improvements.md](entity_extraction_improvements.md) ·
experiment log (runs 044–049, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** Yes on both fronts, with one reliability caveat. **v19
reaches ko 0.8840 (+3.0pp vs v18, +10.9pp vs v15 — the flash-line
champion), alignment precision 0.619 → 0.662, and items 1118 → 792 (−29%,
near-dup emissions 159 → 101)**, all on the identical surface. The gains
concentrate exactly where the worked examples point: the license-family
docs HPIL 0.5→1.0, NOVO 0.667→1.0, Fulucai 0.5→0.833, LinkPlus 0.571→0.857.
The one red mark: reasoning_effort=max overran the structured-output budget
on a 2-chunk doc (Ediets EX-10.4, 9.8k completion tokens → unparseable
JSON), costing a full row (ko ≈ 0.90 without it) — and the prompt-vs-
reasoning confound is unresolved by design.

### The v19 arm (qwen3.7-flash × max reasoning, same 50 docs, chunked, seed 42, Langfuse llm-dojo)

| Metric | v18 (none) | v19 (max) | Δ |
|---|---:|---:|---:|
| key_obligations | 0.8535 | **0.8840** | **+3.0pp** |
| overall | 0.9230 | 0.9135 | −1.0pp (error row + noise; excl. ≈ 0.932) |
| items | 1118 | **792** | **−29%** |
| near-dup emissions | 159 | 101 | −58 |
| alignment precision | 0.619 | **0.662** | +4.3pp |
| verified_precision | 0.991 | 0.988 | −0.3pp |
| parties / eff_date / term / gov | .940/.883/.979/.934 | .918/.865/.968/.932 | 1–2 docs of noise |
| tokens / cost | 993k / $0.037 | 1.52M / $0.098 | +53% / 2.6x |

ko motion: **10 docs up vs 7 down, 33 flat** — the gains are concentrated,
not diffuse. All other fields move by 1–2 documents (noise), not signal.

### Interpretation

1. **Span examples beat prose shapes.** The residual license-grant spans
   were unenumerable by keyword (grants-and-assigns with territories,
   restriction-on-rights clauses, options, end-user access grants) — but
   the seven verbatim positive examples taught the shape class: the target
   docs (Fulucai = a distribution-license grant doc, NOVO, HPIL) recovered
   +0.33 to +0.50 per doc at zero hallucination cost (verified_precision
   0.988).
2. **Span discipline is a precision lever, not a recall tax.** Items −29%
   with matched-span ratio up: the sentence+fragment pairs were pure waste;
   the 225 near-duplicates dropped to 101 with no loss on the scored ko.
3. **Max reasoning has a structured-output reliability floor.** One
   parse-error row in 50 (2.6x cost for +3.0pp ko) — the marginal ko value
   of reasoning beyond "none" is positive, but its failure mode (token-
   budget overrun on multi-chunk docs) is a production risk the repo's
   reasoning_effort=none default exists to avoid.
4. **Confound by design.** The arm varies prompt AND reasoning together; a
   v19 × none run would isolate the prompt's true contribution (the next
   $0.04 arm, not yet spent). The safe reading: the worked examples
   recovered the license-family spans; reasoning bought the rest.
5. **Decision rule held.** ko ≥ +3pp met exactly; no field regressed >2pp.
   v19 is the flash-line ko champion; v18 stays the overall champion
   (0.9230) until the confound is resolved.

*Sources:* `reports/experiment_log.jsonl` (runs 044–049, task
`contract_entity_extraction`) · `V16_PROPOSITION.md` §9–10 (catalog,
worked examples, decision rule) · `SCORING.md` §4/§8 (entity_list_audit
artifacts, span-level diagnostics) · `src/prompts.py` v18/v19 banners ·
`CHANGELOG.md` · corpus = CUAD (Hendrycks et al., 2021 —
[CUAD dataset](https://github.com/TheAtticusProject/cuad)) · runner =
[LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **The prompt-vs-reasoning split.** A v19 × reasoning_effort=none arm
   (≈$0.04) isolates how much of the +3.0pp is the worked examples alone —
   the input for the production config decision.
2. **The parse-error pathology.** Ediets EX-10.4 burned 9.8k completion
   tokens on 2 chunks; a reasoning-token cap or per-chunk retry would
   harden max-reasoning mode.
3. **The 217 still-missing spans.** Token-level misses persist (241 → 217);
   the "other" bucket (~42) deserves its own decomposition before a v20.
4. **Doc-level noise floor.** With 33/50 docs flat, the next improvements
   need a per-doc error budget rather than aggregate ko.
