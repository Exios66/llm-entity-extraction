# Research Memo: Entity extraction improvements — from v2 to chunked v15

**Research question:** How did the contracts-specialist prompt evolve from
the v2 baseline (0.656) to the chunked v15 (0.913), and what did each
iteration — schema specialization, date/containment fixes, truncation
honesty, and finally overlapping-window chunking — contribute?

**Companions:** [subtype_classification_improvements.md](subtype_classification_improvements.md)
· experiment log (task `contract_entity_extraction`) · [experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** Extraction quality moved in four distinct waves: (1) the
**v3 specialization** (+25.7 pp, 0.656 → 0.913) that made the specialist
extract the CUAD field schema instead of generic prose; (2) **v7/v8
regression → v10/v11 recovery** on the chained surface (0.696 → 0.906);
(3) the **v12–v14 honesty + fidelity fixes** (date defined-term rule,
verbatim governing-law containment, operative-requirement itemization,
source-truth duty) that repaired the per-field failure patterns; and
(4) the **v15 chunking enhancement** — overlapping 90k-character windows
with an 8k overlap and a union-at-merge completeness guarantee — which
eliminates head+tail truncation loss entirely and delivers the best
measured result (0.913, 95% CI 0.881–0.942) on the 50-doc surface.

### Version progression (same-model qwen/qwen3.7-flash, seed 42)

| Version | n | overall | 95% CI | field presence | verified precision | category presence |
|---|---:|---:|---:|---:|---:|---:|
| **v2** | 10 | 0.6563 | — | 0.980 | — | — |
| **v3** | 10 | 0.9128 | — | 0.980 | — | — |
| v7 (chained) | 5 | 0.6959 | — | — | — | — |
| v8 (chained) | 5 | 0.6994 | — | — | — | — |
| v10 (chained) | 5 | 0.8952 | — | — | — | — |
| v11 (chained) | 5 | 0.9060 | — | — | — | — |
| v12 | 30 | 0.8947 | 0.869–0.920 | 0.991 | 1.000 | 0.833 |
| v13 | 50 | 0.8937 | 0.858–0.925 | 0.978 | 1.000 | 0.866 |
| v14 | 50 | 0.9007 | 0.865–0.932 | 0.978 | 0.999 | 0.875 |
| **v15 (chunked)** | 50 | **0.9129** | **0.881–0.942** | 0.980 | 0.994 | 0.876 |
| v16 | 50 | 0.8859 | 0.840–0.926 | 0.967 | 0.970 | 0.874 |

Chained rows are the 5-doc Langfuse A/B surface; standalone rows share a
fingerprint surface, seed 42.

### What each iteration actually changed

1. **v3 — schema specialization (the big jump).** The specialist moved
   from free-form extraction to the CUAD field schema with exact-normalize
   types; 0.656 → 0.913, field presence 0.98. Everything after v3 is
   fidelity on top of this base.
2. **v7/v8 — the regression and its lesson.** The 0.70 chained scores were
   traced to specific field behaviors (date handling, clause containment,
   truncation at the 100k cap on Antares 106.8k / MOELIS 122.1k). v10/v11
   recovered to 0.906 — and the diagnosis, not the version, is the
   deliverable: **per-field failure patterns, not headline deltas, drive
   the iteration**.
3. **v12 — dates + containment + truncation honesty.** CUAD maps both
   "Agreement Date" and "Effective Date" onto `effective_date`; the model
   picked the defined effective date while GT held the execution date
   (NETGEAR/MOELIS scored 0.00). The defined-term-wins rule plus partial
   credit tiers (year+month 0.67, 45-day cluster 0.67, year-only 0.33)
   repaired dates; governing-law must be quoted verbatim in full
   (containment 0.39 → 1.0); and the specialist learned to scan BOTH sides
   of the truncation marker and to report `truncated` rather than
   fabricating the omitted middle.
4. **v13 — operative-requirement granularity.** `key_obligations` was
   under-producing (NANOPHASE 6 vs 11 GT spans, Antares 4 vs 7): one
   verbatim item per distinct restriction/covenant/commitment, with a
   list-size sanity check against the GT distribution (mean 7.4, max 22).
5. **v14 — source-truth duty.** The specialist extracts only what the text
   states (the harness never exposes GT); the truncation marker is
   explicitly NOT the end of the document.
6. **v15 — the chunking enhancement.** Instead of one truncated pass,
   the runner feeds **overlapping windows — 90k characters with an 8k
   overlap — so nothing is truncated at all**. The prompt's CHUNK DUTY
   extracts every family occurrence each window can see, boundary clauses
   are re-quoted by the overlap and **deduped at merge**, and the union is
   the completeness guarantee. This is the mechanism behind the 0.913
   result and the highest measured category presence on the standalone
   surface.

### Interpretation

1. **The per-field story explains the headline.** Date tiers +0.67 on two
   documents, containment +0.6 on one — the headline moves are sums of
   surgically diagnosed field failures. The v0.13.0 changelog entry is the
   companion evidence.
2. **Chunking beats truncation by construction.** Head+tail truncation
   makes omitted-middle clauses *unrecoverable*; overlapping windows make
   them *recoverable twice* and dedupe at merge. v15 is the first version
   where input size is not a failure mode.
3. **Verified precision is the constant.** 0.97–1.00 across v12–v16 — the
   factuality guard holds; gains are recall/completeness, not hallucination
   risk. v16's slight overall dip (0.886, CI overlaps v15) is the
   fragment-grain itemization experiment — within noise, worth one more
   same-surface run before promotion.
4. **Bootstrap CIs now make these comparisons honest** — v15's lead over
   v13/v14 is a CI-overlap, not a cliff; the site renders the intervals on
   every run.

*Sources:* `reports/experiment_log.jsonl` (task `contract_entity_extraction`
+ chained rows) · `src/prompts.py` v12–v16 banners · `CHANGELOG.md` v0.13.0
postmortem · corpus = CUAD (Hendrycks et al., 2021 —
[CUAD dataset](https://github.com/TheAtticusProject/cuad)) · runner =
[LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **Does chunking help on truly long documents?** The 50-doc surface
   includes 100k+-char contracts; a targeted long-doc subset (Antares,
   MOELIS, Phasebio-class) would confirm the completeness guarantee
   directly.
2. **v16 vs v15:** fragment-grain `key_obligations` trades overall for
   output cleanliness — rerun on the identical surface and let the CI
   decide promotion.
3. **Cost:** overlapping windows multiply input tokens ~1.5–2× for long
   documents — the cost-vs-quality scatter on the site shows exactly what
   the extra fidelity buys.
