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
| `index.html` | The viewer (single page, hash-routed: `#/` index, `#/run/{n}` detail) |
| `assets/` | `site.css` + `site.js` — dependency-free, no CDN, no build step |
| `data/` | **Generated** — `meta.json`, `index.json` (run summaries), `runs/{n}.json` (full records) |
| `README.md` | this file |

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
