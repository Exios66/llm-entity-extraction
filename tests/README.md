# `tests/` — network-free suite

```bash
python -m pytest tests/ -q
node tests/assets/site_render_audit.js   # headless render audit of the site (skipped without node)
```

All tests are mocked — no network, no LLM, no Braintrust. `conftest.py`
fakes the env (Braintrust/Langfuse keys, `EXPERIMENT_LOG_PATH` to tmp) and
provides `sample_dataset_rows` + `sample_maud_zip` fixtures.

Coverage areas: prompts, scorers, taxonomy, evaluation helpers, config
loading, field scoring, CUAD ground truth, subtype handoff, page voting,
bootstrap CI math, cost models, the release workflow, the site builder
(guardrail/trends/prompts), the headless site render audit, and the
chained/extraction/classification/subtype/langfuse eval smoke loops.

Smoke-test pattern: each eval runner test defines `FakeEvalResult` +
`FakeEvalRun`, monkeypatches `braintrust.Eval` + the agents, and asserts the
wiring + the repo-log record written to the tmp JSONL.
