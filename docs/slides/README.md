# Scoring Methods — Slides

Example inputs, outputs, and concise scientific explanations of every method
used to score the entity-extraction runs in this project — written for
research scientists working in parallel who do **not** have time to read the
full documentation set (`SCORING.md`, README, AGENTS.md).

Each deck is standalone: a ~5–8 slide markdown file with the method, a
worked example (input → output → calculation), interpretation, and common
pitfalls. Read them in order, or jump to what you need.

## The decks

| Deck | Topic | Read when… |
|---|---|---|
| [01-overview](01-overview.md) | The pipeline, a run's anatomy, and what "success" means | You are new to the project and want the 5-minute map |
| [02-field-scoring](02-field-scoring.md) | Type-aware field scoring (date / money / name / free_text / containment) with worked examples | You want to know how a single extracted value becomes a score |
| [03-entity-lists](03-entity-lists.md) | List fields: bipartite matching, precision / recall / F1, macro vs micro | You are comparing list extractions (parties, obligations) across runs |
| [04-regression-diagnostics](04-regression-diagnostics.md) | MAE, median AE, R² (dates / durations / money) + span-count drift, vs the master-labels ground truth | You need to know HOW WRONG the near-misses are, not just how often |
| [05-factuality-audit](05-factuality-audit.md) | Verified precision, hallucination rate, document grounding | You care about fabrication, not just coverage |
| [06-failure-analysis](06-failure-analysis.md) | Error decomposition, confusion matrices, failure insights → prompt iteration | You are diagnosing WHY a run scored what it did |
| [07-reading-the-log](07-reading-the-log.md) | How to read `reports/experiment_log.md` / `.jsonl` and the GH Pages site (CIs, same-surface rule) | You want to compare runs without being misled by sample size |

## One-paragraph summary (the whole project's scoring in 90 seconds)

Every run sends real documents through LangChain agents (sorter → specialist
extractor) via OpenRouter, then scores the outputs **deterministically**
locally: each extracted field is scored by its declared type (`date`, `money`,
`name`, `free_text`, `id`, `entity_list`) against the CUAD ground truth —
never by exact-match-on-extraction. The headline `overall_extraction_score`
is the mean of per-field content scores. On top of that, every run carries
**run-level diagnostics** (`scores.diagnostics`): raw list precision/recall/F1
(macro + micro), **MAE + R²** regression errors for dates, durations, and
money amounts vs the curated master-labels CSV, **span-count drift** (over-
vs under-extraction), and a per-field **exact / partial / miss**
decomposition. Braintrust is only ever a lookup on these locally computed
composites, so the UI, the manifests, and the experiment log never disagree.

## How to verify a number yourself

Everything is reproducible offline:

```bash
# All metrics in one place (formulas + definitions)
less SCORING.md

# Unit tests for every metric (network-free)
python -m pytest tests/test_metrics.py -q

# The master ground-truth CSV the MAE diagnostics prefer
less ../llm-mailroom/data/cuad/master_clauses.csv
```
