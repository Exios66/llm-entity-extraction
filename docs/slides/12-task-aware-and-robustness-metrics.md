# 12 — Beyond CUAD extraction: subtype, docclass, task-aware & Monte Carlo metrics

---

## What this deck covers

Decks 02–07 document the CUAD **entity-extraction** surface. The pipeline now
scores MORE than that: the **sorter subtype** eval, the hierarchical
**docclass** eval (doc_type + doc_subclass), the **task-aware dispatcher**
that generalizes scoring to MAUD / LegalBench / multiclass / court opinions /
chained runs, and the **Monte Carlo robustness** suite that simulates what-if
pipelines over the stored reasoning corpus — all without spending LLM budget.

All of it lives in the shared `llm-dojo-scoring` package (`@v0.7.0`), reached
through the repo's thin `src/*.py` shims.

---

## Subtype metrics — strict vs equivalence-aware family accuracy

The sorter routes each contract to one of 25 CUAD families + `other`
(`run_subtype_eval.py` / `run_langfuse_subtype_eval.py`). Two numbers, not
one:

| Tracker | Definition | Reading |
|---|---|---|
| `subtype_accuracy` | share of rows whose normalized subtype == the CUAD ground-truth folder | the **strict** discriminating signal |
| `subtype_accuracy_equiv` | strict OR a **defensible equivalent family** (`SUBTYPE_EQUIVALENCES`: reseller↔distributor, maintenance↔license, development↔license, affiliate↔joint_venture) | recognizes defensible family routing |

Per-row flags: `doc_type_ok`, `subtype_ok`, `subtype_ok_equiv`, `confidence`.
Supporting outputs: `per_subtype` (per-family strict/equiv accuracy +
counts), the expected×predicted **confusion matrix**, and
`failure_insights` — the model's FULL reasoning on every failed row, each
tagged with a failure mode:

| Mode | Meaning |
|---|---|
| `function_over_form` | doc_type miss — a document whose function overrode its contract form |
| `other_fallback` | answered "other" for a corpus-filed family |
| `equivalent_family` | defensible equivalent (recovered by `subtype_accuracy_equiv`) |
| `family_confusion` | genuine wrong-family pick |

Headlines carry **bootstrap 95% CIs** (`subtype_accuracy_ci` /
`exact_match_ci`) — e.g. the champion sorter_v13 run: **0.9430, CI
[0.9214, 0.9627]**.

---

## Docclass hierarchical metrics — doc_type AND a second level

The merged docclass surface (`docclass_merged.jsonl`, 676 rows = CUAD 509 +
MAUD 152 + S-1 15) is scored on TWO dimensions
(`run_langfuse_docclass_eval.py`):

| Tracker | Definition |
|---|---|
| `doc_type_accuracy` (+CI) | share with the correct primary class (`contract` / `merger_agreement` / `corporate_record` / …) |
| `subclass_accuracy` (+CI) | share whose `doc_subclass` equals the GT — **rows without a subclass GT are unscored, not penalized** |
| `subclass_accuracy_equiv` | strict OR a defensible equivalent subclass (`DOC_SUBCLASS_EQUIVALENCES`: `mixed_cash_stock` ↔ `mixed_cash_stock_election`) |
| `exact_match` (+CI) | doc_type AND subclass both exact |
| `per_subclass_accuracy` / `per_subclass_support` | per-subclass accuracy with support counts |
| `input_mode_counts` | text / vision / text_fallback split (the vision-primary arm) |

Failure modes are the docclass mirror of the subtype ones: `doc_type_miss`
(primary wrong) and `subclass_miss` (primary right, subclass wrong).

Worked example (full-676, qwen3.7-flash, `sorter_docclass_v6`):
`doc_type 0.9941` (5→4 misses), `subclass 0.5868` (+1.19pp vs v3),
`exact 0.8935` — most subclass misses are the MAUD GT-gap cluster (GT
"other" where the model reads an explicit consideration), which is
data-side, not prompt-fixable.

---

## Task-aware scoring dispatcher — one `score_task` for every task kind

`llm_dojo_scoring.tasks::score_task(task, expected, predicted, …)` dispatches
on the task kind (`TASK_KINDS`) and returns a task-appropriate score dict —
always deterministic, always with a bootstrap CI:

| Kind | What is scored | Output |
|---|---|---|
| `maud_docclass` | merger-agreement doc_type + **consideration-type subclass** (strict + equiv; unknown answers degrade to `other`, the GT-gap convention) | doc_type/subclass accuracy + equiv + exact |
| `maud_question` | the 25,827-row per-question suite | exact match + per-class |
| `legalbench` | binary Yes/No tasks | exact match + per-class + **binary P/R/F1** (positive = `yes`) |
| `multiclass` | multi-classification | `macro_accuracy` + `micro_accuracy` + per-class + confusion |
| `court_opinion` | the `court_opinion` doc class | exact match + per-class |
| `chained` | sorter→extractor pipeline | `chained_composite` / `chained_summary` |

**Chained composite** — the extractor carries the document-level output the
pipeline is ultimately judged on, so it dominates the default weighting:

```
chained_composite = 0.25 × sorter_score + 0.75 × extractor_score
```

The dispatch + label normalization (`normalize_maud_consideration`,
`normalize_legalbench`, `normalize_task_answer`) live in the package; the
registries (`DOC_CLASS_KEYS`, `MAUD_CONSIDERATION_*`,
`LEGALBENCH_BINARY_LABELS`, `COURT_OPINION_CLASS`, `TASK_KINDS`) are in the
package `config`.

---

## Monte Carlo robustness metrics — zero-spend what-if analysis

`src/monte_carlo.py` (KANBAN-048) treats every completed eval row in the
joint reasoning corpus (17,691 rows from the experiment log + manifests) as
one sample from a per-document / per-prompt / per-model label distribution,
then simulates pipelines **without paying for LLM calls**. Key scenario
metrics (`scripts/reporting/monte_carlo_*.py` → `reports/monte_carlo/`):

| Scenario | Metric | Reference result |
|---|---|---|
| **Ensemble voting** | committee accuracy @ K (majority vote over K simulated votes) with bootstrap CIs | subtype 0.9209 → 0.9513 @ K=25 (weak lever); doc_type saturated at 0.9928 (no gain) |
| **Confidence-gated escalation** | headroom vs cost at an alpha confidence threshold (Pareto) | subtype +0.44 pp @ alpha 0.15 to a 0.95 model (1.3× cost); docclass escalation loses |
| **Paired-bootstrap prompt ablation** | P(win) + CI-excludes-zero per (model, A, B) pair on shared docs | 156 subtype + 12 docclass pairs; sorter_v10/v11 vs v3 +14.1 pp P(win)=1.000 |
| **Failure pipeline** | retry/fallback event simulation from the observed 0.2374% failure rate | max_tries=1 + fallback → 0.004% vs 0.202% without |
| **Exemplar mining** | near-miss detection (decoy mention in free-form reasoning) + token-budget subset selection | 6 subtype + 4 docclass exemplar appendices |

The GEPA prompt-iteration loop folds the paired-bootstrap ablation +
committee-voting robustness in as a **champion-contender selection step**
(KANBAN-049). Full results + interpretation:
`memos/monte_carlo_robustness.md`.

---

## The one rule that ties them together

Every metric in this deck is a **deterministic pure function** of
`(predicted, expected)` pairs. That is what makes offline rescoring, manifest
re-scoring, and live Langfuse/Phoenix scoring agree, and what lets the Monte
Carlo suite resample historical rows as if they were fresh samples.

**Read every headline with its bootstrap CI + n** — a 5-doc 0.94-vs-0.88 gap
is a CI overlap, not a win.

## Next

- Back to [01-overview](01-overview.md) or the [deck index](README.md)