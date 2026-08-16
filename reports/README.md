# `reports/` — the experiment log

| File | What it is |
|---|---|
| `experiment_log.jsonl` | **the source of truth** — append-only, one JSON line per run |
| `experiment_log.md` | DERIVED — rebuilt whole by `scripts/reporting/render_experiment_log.py`; never hand-edit |

Related runtime state (repo-root `data/`, gitignored): `data/judgments/`
(per-experiment LLM-judge judgments incl. the `--judge` calibration tracker)
and `data/manifests/` (resumable run checkpoints — same metadata = resumable,
mismatch = invalid by design).

`monte_carlo/` (derived — KANBAN-048): the Monte Carlo simulation suite's
outputs — `corpus.jsonl` (gitignored, rebuilt by
`scripts/reporting/monte_carlo_corpus.py`), `corpus-summary.md`, and the
per-scenario markdown/PNG reports (`ensemble-voting-*`, `escalation-*`,
`prompt-ablation-*`, `failure-pipeline`, `exemplars-*`, `exemplar-appendix-*`,
`verify-*`, `escalation_candidates-*`). Never hand-edit — regenerate with the
scenario scripts (reproducibility pinned by `tests/test_monte_carlo.py`).

Every JSONL record carries: git snapshot, model, prompt version(s), data
source + dataset fingerprint + seed, all run parameters, tokens + costs
(incl. the deterministic `cost_estimated_usd`), all scores (with bootstrap
CIs, judge calibration, ablation), and per-document results with the model's
predicted outputs.

The markdown + the GH Pages site (https://exios66.github.io/llm-entity-extraction/)
are regenerated after every run — see wiki: [Experiment-Log](https://github.com/Exios66/llm-entity-extraction/wiki/Experiment-Log).
