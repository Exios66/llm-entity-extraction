# Research Memos

Individual research memoranda capturing the key findings from experimental
runs and prompt iterations — archived for collaborators and for presenting
the evidence trail. Format: research question → answer + results summary →
remaining uncertainties.

| Memo | Topic |
|---|---|
| [`subtype_classification_improvements.md`](subtype_classification_improvements.md) | Sorter v3→v6: corpus-convention rules lift strict subtype accuracy +9.8 pp on the same-surface A/B and +7.3 pp on the full corpus |
| [`entity_extraction_improvements.md`](entity_extraction_improvements.md) | Contracts-specialist v2→v15: schema specialization, date/containment fidelity, truncation honesty, and the chunking enhancement |
| [`contracts_specialist_v17_v18_enhancements.md`](contracts_specialist_v17_v18_enhancements.md) | Contracts-specialist v17→v18: segmentation grain is exhausted at the prompt layer; the CUAD-mirror family-fidelity catalog lifts key_obligations +7.8 pp (0.7755→0.8535), overall 0.9230 (champion) |
| [`model_sweep_v18.md`](model_sweep_v18.md) | v18 × {qwen3.7-flash, deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs: the catalog is model-agnostic (+6.0 to +11.5 pp ko); deepseek-v4-pro × v18 is the series champion (ko 0.8907, overall 0.9289, verified_precision 1.000) — segmentation capability is the model-bound separator |
| [`contracts_specialist_v19.md`](contracts_specialist_v19.md) | v19 (worked span examples + span discipline, qwen3.7-flash × max reasoning): ko 0.8535→0.8840 (+3.0 pp, flash-line champion), alignment precision 0.619→0.662, items −29% — with a 1/50 max-reasoning parse-error caveat and the prompt-vs-reasoning confound unresolved |

Rendered on the experiment-log site under the **memos** tab
(https://exios66.github.io/llm-entity-extraction/).
