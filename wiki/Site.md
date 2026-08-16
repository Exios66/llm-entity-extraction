# The Experiment-Log Site

> ### [https://exios66.github.io/llm-entity-extraction/](https://exios66.github.io/llm-entity-extraction/)

A dependency-free, vanilla-JS single-page viewer over the experiment log.
`docs/data/` is DERIVED by `scripts/site/build_site.py`; `index.html`,
`assets/site.js`, and `assets/site.css` are hand-maintained.

## Posit Cloud portal (complementary)

> ### [https://exios66.github.io/llm-entity-extraction/posit/](https://exios66.github.io/llm-entity-extraction/posit/)

A Quarto website under `docs/posit/` (sources in `site/`) integrating the
**experiment log** (generated from `reports/experiment_log.jsonl` by
`site/_pre-render.py` on every render), the **agent kanban board**
(`MESSAGE_BOARD.md`), and the **discussion board**
(`MESSAGE_BOARD_DISCUSSION.qmd`) under one themed URL — custom blue→teal
gradient theme with light/dark toggle, navbar, and client-side search.
Deploy from Posit Cloud with `quarto render site` + publish, or let GH Pages
serve it (rendered output is committed; no Actions). See `site/README.md`.

## Views

| View | Contents |
|---|---|
| `#/` | stats (runs, documents, tokens, models, **total cost est.**), scoring reference, filterable/searchable runs table |
| `#/task/{task}` | per-task aggregates, grouped-by-prompt table, **trend chart**, **cost-vs-quality scatter**, (subtype) **failure-mode stacked bars**, runs |
| `#/prompt/{prompt}` / `#/model/{model}` | all runs of a prompt/model, grouped by task |
| `#/run/{id}` | headline cards with **bootstrap CI**, composition, metadata, parameters, tokens & cost (estimate + billed), judge calibration, error-propagation ablation, per-document results, confusion matrix, failure insights |
| `#/run/{id}/doc/{i}` | single-document trace: classification, reasoning, extraction scores, entity audits, CUAD category presence |
| `#/prompts` | **prompt diff viewer** — side-by-side line diff between any two versions + their score delta |

## Charts & interaction

- **Score trends** — one smoothed (Catmull-Rom) line per prompt version with
  the raw run points on top; curated palette + dash patterns; hovering a
  series dims the others.
- **Cost-vs-quality** — log-scale cost axis (runs span ~4 orders of
  magnitude); filled points = billed OpenRouter totals, hollow = deterministic
  estimates.
- **Every chart point is hover-inspectable** (run detail tooltip: experiment,
  model, prompt, headline, cost, n rows, sample key, timestamp) and
  **click-navigates to its run**.
- Failure-mode stacked bars trend `function_over_form` / `other_fallback` /
  `equivalent_family` / `family_confusion` across sorter versions.

## Veracity guarantees

- **Same-surface guardrail** — every row carries `fingerprint`/`seed`/
  `sample_key`; "Δ vs best" is only computed and colored against the best run
  on the SAME surface (dataset fingerprint + seed + sample size). Cross-
  surface deltas show `≈ Δ surface` and are never presented as wins.
- **Bootstrap CIs** on every headline (runner-computed, else resampled from
  the stored per-doc arrays, else Wilson).
- **Cost** — deterministic token × price estimates on every run, labeled
  `est.`, with billed OpenRouter totals when the CSV is ingested.
- **Headless render audit** (`tests/assets/site_render_audit.js`) exercises
  every view against the real data and requires zero rendering errors.

## Rebuild + deploy

```bash
python scripts/site/build_site.py                      # docs/data/*
python scripts/site/build_site.py --check              # freshness gate
node tests/assets/site_render_audit.js                 # render audit
git add docs/ && git commit -m "SITE: ..." && git push origin main
```

GitHub Pages serves `/docs` from `main` — every push deploys.
