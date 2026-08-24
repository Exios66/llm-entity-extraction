# Notebooks

Dedicated Jupyter notebooks per **scoring process** — one of the KANBAN-067
close-out directives ([#33](https://github.com/Exios66/llm-entity-extraction/issues/33),
board card KANBAN-068). Pattern follows the KANBAN-078 dataset-browser
precedent: **thin notebook + real logic in importable modules**, network-free,
executable headlessly.

## The six-process plan

| # | Notebook | Scoring process | Status |
|---|---|---|---|
| 03 | [`03_doc_type_bundles.ipynb`](03_doc_type_bundles.ipynb) | Doc-type bundles (`DOC_TYPE_BUNDLES`, `get_doc_bundle` honesty fallback) vs real benchmark coverage from `reports/experiment_log.jsonl` | **shipped** (exemplar) |
| 01 | `01_classification_scoring.ipynb` | Classification: sorter/judge/boss metrics, confusion matrices, per-class stats, calibration | planned — same pattern |
| 02 | `02_typed_field_extraction.ipynb` | Typed-field extraction: `score_extraction`/`score_field`, entity-list P/R, verified precision, completeness | planned |
| 04 | `04_audit_verification.ipynb` | Audit/verification: disagreement/resolution metrics, hallucination rate | planned |
| 05 | `05_chained_pipelines.ipynb` | Chained pipelines: `chained_composite` / `chained_summary` | planned |
| 06 | `06_report_aggregation.ipynb` | Report & aggregation: derived metrics, dashboards, export | planned |

## Conventions (enforced by tests)

- **Kernel-cwd-proof bootstrap**: first code cell locates the repo root by
  walking up for `pyproject.toml` + `reports/` — run it from anywhere.
- **Network-free & LLM-free**: code cells never call APIs; everything runs
  against the pinned `llm-dojo-scoring @v0.7.0` and local repo data.
- **Honest-gap doctrine**: wherever coverage is declared but unmeasured, the
  notebook says so from data (see 03's closing table).
- Guard suite: [`tests/test_kanban068_bundles_notebook.py`](../tests/test_kanban068_bundles_notebook.py)
  executes the shipped notebook headlessly (hostile cwd included) and asserts
  its honest-gap summary matches known reality.

## Install

```bash
pip install -e ".[notebooks]"   # nbformat, nbclient, ipykernel
```

Execute any notebook headlessly:

```bash
.venv/bin/python -m nbclient ...        # or just open in Jupyter
jupyter execute notebooks/03_doc_type_bundles.ipynb
```
