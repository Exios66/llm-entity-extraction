# Posit Cloud portal — sources (`docs/posit-src/`) → rendered output (`docs/posit/`)

The **Quarto website** behind the Posit Cloud portal: a fully themed,
integrated view of the three working records of this repo — the **experiment
log**, the **agent kanban board**, and the **agent discussion board** — all
reachable from one URL. It is *complementary* to the interactive SPA explorer
at `docs/index.html` (the two link to each other from their navbars).

## What you get

| Page | Output | Source (derived, never hand-edited) |
|---|---|---|
| Portal landing | `docs/posit/index.html` | `index.qmd` + `_includes/recent-runs.md` |
| Experiment log | `docs/posit/experiment-log.html` | `reports/experiment_log.jsonl` (via `_pre-render.py`), rendered with the same `src/experiment_log.py::render_full_log` code as `reports/experiment_log.md` |
| Kanban board | `docs/posit/kanban.html` | `MESSAGE_BOARD.md` |
| Discussion board | `docs/posit/discussion.html` | `MESSAGE_BOARD_DISCUSSION.qmd` (YAML stripped, agent colors preserved) |

Theme: a custom blue→teal gradient (the repo's SPA identity) over
bootswatch cosmo (light) / darkly (dark, "gradient night" radial glows),
with navbar, client-side search, TOC, and a light/dark toggle.

## Build (regenerates everything)

```bash
# from the repo root — the pre-render hook regenerates the includes +
# _variables.yml first, so this single command is all you ever need:
quarto render site
```

The rendered site lands in `docs/posit/` — the SAME `docs/` tree GitHub
Pages serves, so one URL prefix hosts both this portal and the explorer
(`docs/index.html`). **The rendered pages ARE committed** (like
`docs/data/`): GH Pages serves `/docs` from `main` with no build step and no
Actions.

## Deploying from Posit Cloud

1. Open this repo in Posit Cloud (New Project → *From Git Repository*).
2. Terminal (or the Render button on `docs/posit-src/_quarto.yml` in RStudio/VS Code):
   `quarto render site` — output lands in `docs/posit/`.
3. Publish either way:
   - **GitHub Pages (zero extra setup)**: commit + push `docs/` — the portal
     is live at `https://exios66.github.io/llm-entity-extraction/posit/`.
   - **Quarto Pub**: `quarto publish quarto-pub` from `docs/posit-src/`.
   - **Posit Connect**: deploy `docs/` as a static site
     (`rsconnect::deployApp(appDir = "docs", appMode = "static")` or the
     Posit Cloud Publish button) — the whole tree, portal + explorer, goes
     with it. Relative links keep working under any URL prefix.

## Hygiene notes

- `_pre-render.py` writes `_includes/` + `_variables.yml` in this directory;
  both are gitignored (they carry generation stamps — see `.gitignore`).
  `docs/posit/` is committed; `site_libs/` and `search.json` are committed
  too — the served pages need them offline.
- Deterministic: page content embeds no timestamps, so re-rendering after a
  data change produces reviewable diffs.
- Tests: `tests/test_posit_site.py` (network-free) covers the pre-render
  output, the `_quarto.yml` contract, and the committed rendered pages.