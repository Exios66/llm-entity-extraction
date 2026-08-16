# llm-dojo-scoring integration — the shared scoring/analysis library

**Research question:** Can the scoring, error-analysis, visualization, and
report code be moved out of this repo into a single pip-installable package
(`Exios66/llm-dojo-scoring`) that BOTH this repo and llm-mailroom import,
without changing any local import site or scoring result?

**Companions:** KANBAN-044 board card + Archive, `src/dojo_config.py`,
`src/dojo_compat.py`, the six re-export shims (`src/field_scoring.py`,
`src/metrics.py`, `src/scorers.py`, `src/bootstrap.py`, `src/cost_models.py`,
`src/experiment_log.py` core), `tests/test_dojo_integration.py` (11 tests).

## Answer, Response, + Summary of Results

**Short answer:** Yes — the integration is complete and green. The scoring
definitions now live in `llm-dojo-scoring` (pinned `@v0.1.2`), the six local
modules are thin re-export shims so `pip install -e .` and llm-mailroom's
imports work unchanged, and the package's CLI (`dojo-analyze`/`dojo-export`/
`dojo-sync`) runs against this repo's workbook artifacts. Three contract
differences required local adapters; the external package needed one upstream
fix (the missing `python -m` entry dispatch) that shipped as `v0.1.1`→`v0.1.2`.

## Results

### 1. What the repo maps onto the package (`src/dojo_config.py`)

`config/taxonomy.yaml` stays the local source of truth; `apply_taxonomy_settings()`
wires it into the package `Settings` at import time (idempotent, honors
`LLM_DOJO_SCORING_CONFIG` when set). Adaptations needed because the package's
`configure()` sets values verbatim — only its YAML-file loader coerces types:

- `cost_models` dict form (`{input_per_million, output_per_million}`) → the
  package's `[input, output]` list form (the package silently ignores dicts).
- `ambiguous_band` list → tuple; `partial_gt_fields` / `containment_fields`
  list → set (the package's canonical types).
- `load_env()` runs first so the package's embedding rescue sees the repo keys.

### 2. Compat shims (`src/dojo_compat.py`)

`classify_failure(doc_type_ok, subclass_ok, predicted_subclass)` preserves the
runner's original positional-boolean contract (`None` on success) against the
package's row-dict `classify_docclass_failure`.

### 3. The metrics-layer fix (`src/metrics.py`)

The package's `extraction_diagnostics` injects the master preference via an
`expected_resolver(master, filename, field, fallback)` callable, but drops the
`master=` keyword. The local shim keeps `extraction_diagnostics(rows,
field_types, master=...)` and **binds the master dict into a resolver closure**
(the repo's `_FIELD_CATEGORIES` field→CUAD-category map + `master_labels`
resolver are recreated locally, since the package removed them). Without the
closure, MAE/R² silently preferred the raw clause text over the curated
normalized answers.

### 4. The upstream fix (external repo)

`python -m llm_dojo_scoring.cli <input> …` was a silent no-op — the module had
no `__main__` dispatch. Added a `_dispatch()` that routes a leading
`analyze|export|sync` subcommand and defaults to `dojo-analyze`; the console
entry points now accept an optional argv (unchanged console-script behavior).
Pushed to `Exios66/llm-dojo-scoring` (`3ad2ef4` → `1f291ba`) and tagged
**`v0.1.1` → `v0.1.2`**; this repo's `pyproject.toml` + `requirements.txt`
re-pinned to `@v0.1.2`.

### 5. Test-contract corrections (`tests/test_dojo_integration.py`)

Four expectations in the committed suite asserted the wrong contract and were
corrected to the real one:

| Test | Committed expectation | Real contract |
|---|---|---|
| `get_field_types` | `"entity_list"` | compound `"entity_list:free_text"` (resolves to entity-list scoring via `is_entity_list`) |
| export columns | `sorter_columns() == package()` | re-export identity + header equality (column dicts embed per-call lambdas — deep equality is meaningless) |
| sweep workbook headers | 114 == package | 115 = 114 shared + trailing reference-format `Notes` column (KANBAN-040 contract) |
| `extraction_diagnostics` master | bare `{"Agreement Date": …}` | master-CSV key format `{"<Category>-Answer": …}` under the normalized filename |

## Interpretation

1. **The dependency is now genuinely the single source** — scoring code is
   line-for-line identical (verified in the KANBAN-044 API audit), and the
   re-export shims keep every existing import site (eval runners, reporting
   scripts, llm-mailroom) byte-compatible.
2. **Type coercion belongs on the consumer side** until the package's
   `configure()` matches its YAML-loader coercion; the repo-side adapter is the
   pragmatic seam (and the natural place for the taxonomy mapping anyway).
3. **The master-label preference is subtle** — the package's resolver
   signature (`master` as the FIRST resolver argument) made the naive pass-
   through silently drop the master map. The closure binding is the correct
   pattern; any future resolver-shaped API needs a binding test like
   `test_diagnostics_keeps_master_keyword`.

*Sources:* `src/dojo_config.py`, `src/dojo_compat.py`, `src/metrics.py`,
`src/field_scoring.py`, `src/scorers.py`, `src/bootstrap.py`,
`src/cost_models.py`, `src/experiment_log.py`, `scripts/reporting/export_experiment_results.py`,
`tests/test_dojo_integration.py`, `pyproject.toml`/`requirements.txt`,
llm-dojo-scoring `v0.1.0`→`v0.1.2` (`29c192f`→`3ad2ef4`→`1f291ba`).

## What questions or uncertainties remain?

- **llm-mailroom migration** (KANBAN-005 territory): the pipeline project must
  add the same pinned dependency and delete its vendored scoring code — the
  integration is proven here but not yet exercised there.
- **Cost model drift**: the package `cost_models` table is fed from the
  taxonomy; when a new provider appears only the taxonomy needs the entry
  (verify `estimate_cost` picks it up — covered by `test_cost_models_dict_form_converted`).