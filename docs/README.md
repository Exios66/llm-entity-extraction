# Experiment Log — static viewing site

This directory is the static GitHub Pages site for the
[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)
experiment log: a clean, filterable, searchable viewer over every eval run in
`reports/experiment_log.jsonl`.

## Viewing

**Live site:** `https://exios66.github.io/llm-entity-extraction/`
(once GitHub Pages is enabled — see below).

## Layout

| Path | Contents |
|---|---|
| `index.html` | The viewer (single page, hash-routed: `#/` index, `#/task/{slug}` / `#/prompt/{v}` / `#/model/{m}` group views, `#/run/{n}` detail, `#/run/{n}/doc/{i}` single-document trace) |
| `assets/` | `site.css` + `site.js` — dependency-free, no CDN, no build step; dark "gradient night" theme via masthead toggle, `?theme=dark`, or system preference |
| `data/` | **Generated** — `meta.json`, `index.json` (run summaries), `runs/{n}.json` (full records) |
| `README.md` | this file |

## Viewer features

- **Sample-size-aware scoring** — every headline score carries a Wilson 95%
  CI (n=5 → ±27pp, n=509 → ±2.2pp) with the sample size shown; the
  **Δ vs best** column is colored only when the difference is statistically
  significant at 95% (two-proportion z-test), otherwise shown as "≈" — small
  samples are never presented as beating or losing to large ones.
- **Scoring reference card** — display bands (≥85% Strong · 60–85% Moderate ·
  <60% Weak), per-task headline formulas, each metric's calculation +
  meaning, a "sample sizes matter" explainer, and links to `SCORING.md`.
- **Group views** — `#/task/{slug}`, `#/prompt/{version}`, `#/model/{model}`:
  aggregates (runs / documents / tokens / best / median / worst), a
  grouped-by table (tasks → prompts, prompts → tasks), and the filtered run
  list. Task tags, prompt names, and models link to their group views
  everywhere.
- **Dashboard** — stat cards per task (best / median / worst + run link),
  filterable runs table (search + task/model/prompt + **minimum sample
  size**), score cells with band-colored %, raw value, CI + n, and
  composition line.
- **Run detail** — banded metric cards, task-specific **score composition**
  card, per-field content scores, per-subtype accuracy + confusion matrix +
  failure insights, and a per-document results table.
- **Trace view** — `#/run/{n}/doc/{i}` shows the full record: classification
  verdicts + reasoning, and — where applicable — **interpreted extraction
  scores** (what each metric means, type-aware field scoring, entity-list
  factuality audit with hallucination counts, CUAD category presence,
  ambiguous fields, and the raw predicted extraction), with prev/next
  navigation.
- **Dark mode** — light and dark themes share the same markup; the dark
  "gradient night" theme adds radial glows, gradient score bars and title,
  and tuned chips/tables. `?theme=light|dark` forces a theme (shareable).

## Rebuilding the data

`docs/data/` is DERIVED from `reports/experiment_log.jsonl`, exactly like
`reports/experiment_log.md` — never hand-edit it. After every run:

```bash
python scripts/site/build_site.py                 # regenerate docs/data/
python scripts/site/build_site.py --check         # verify it is current
```

The index view is served by `data/index.json` (small); detail pages lazy-load
`data/runs/{id}.json`, so the site stays fast as the log grows.

## Enabling GitHub Pages (one-time, no Actions runners)

The site is committed to the repo and served directly from the `main` branch,
so no CI is involved:

1. GitHub → repo → **Settings → Pages**
2. **Source**: *Deploy from a branch*
3. **Branch**: `main` → `/docs` → **Save**
4. The site appears at `https://exios66.github.io/llm-entity-extraction/`

## Keeping the log and site in sync

The source of truth is `reports/experiment_log.jsonl`. The pipeline is:

```bash
# after every completed run:
python scripts/reporting/render_experiment_log.py   # -> reports/experiment_log.md
python scripts/site/build_site.py                   # -> docs/data/
```
