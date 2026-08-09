# llm-entity-extraction

A prompt experiment loop environment for legal document entity extraction: the
building block for the llm-mailroom agents. Each evaluation tests **one prompt
version at a time**, runs the agents on **LangChain**, and logs everything to
**Braintrust** for comparison in the UI.

Modeled on the [RVL-CDIP-Classifier](https://github.com/Exios66/RVL-CDIP-Classifier)
repo's Braintrust evaluation pattern and the [llm-mailroom](https://github.com/Exios66/llm-mailroom)
taxonomy/prompts.

## Layout

```
agents/                  LangChain agents (sorter, specialists, judge)
  base_agent.py          ChatOpenAI (OpenRouter) + structured output helpers
  sorter_agent.py        doc-type classification (one prompt version per run)
  specialist_agents.py   per-class field extraction + shared schemas
  judge_agent.py         LLM-as-a-judge (classification/completeness/correctness)
config/taxonomy.yaml     doc classes, agent->model mapping, thresholds
src/
  braintrust_config.py   loads braintrust.env / .env (org, project, model)
  braintrust_utils.py    Braintrust HTTP, dataset load/upload, experiment fetch
  evaluation.py          dataset validation, fingerprints, resumable manifests
  llm_chain.py           LangChain chain factory for eval loops
  prompts.py             ALL agent prompts, versioned (sorter_v0, ...)
  scorers.py             deterministic Braintrust scorers (exact_match, failure, cost)
  taxonomy.py            YAML loader for config/taxonomy.yaml
scripts/
  datasets/              stream CUAD v1 / LegalBench MAUD into Braintrust datasets
  eval/                  the experiment loops (classification, binary, multiclass, A/B)
  reporting/             confusion matrix + markdown experiment reports
tests/                   unit tests
```

## Setup

```bash
pip install -r requirements.txt
cp braintrust.env.example braintrust.env   # fill in creds (org/project/API key)
cp .env.example .env                       # fill in OPENROUTER_API_KEY
```

Required env vars (in `braintrust.env` or `.env`):

| Variable | Purpose |
|---|---|
| `BRAINTRUST_ORG_ID` | Braintrust org |
| `BRAINTRUST_PROJECT_ID` / `BRAINTRUST_PROJECT_NAME` | project for experiments/datasets |
| `BRAINTRUST_API_KEY` | key with write access to the project |
| `OPENROUTER_API_KEY` | LLM calls through OpenRouter |

## The loop (one prompt at a time)

```bash
# 1. Build a dataset (streams from the public corpus, nothing committed)
python scripts/datasets/stream_cuad_to_bt.py --limit 12 --dry-run
python scripts/datasets/stream_cuad_to_bt.py --limit 12
python scripts/datasets/stream_legalbench_to_bt.py --limit 6

# 2. Evaluate ONE prompt version
python scripts/eval/run_classification_eval.py \
    --dataset mailroom-cuad-contracts \
    --prompt-version sorter_v0 \
    --model qwen/qwen3.7-flash

# 3. A/B two prompt versions on the same dataset
python scripts/eval/evaluate_prompt_version.py \
    --dataset mailroom-cuad-contracts \
    --prompt-a sorter_v0 --prompt-b sorter_v1

# 4. Inspect results
python scripts/reporting/report_generator.py --experiment qwen3.7-flash_sorter_v0
python scripts/reporting/confusion_matrix.py --experiment qwen3.7-flash_sorter_v0
```

Experiment naming is `{model-slug}_p{prompt-version}` (optionally suffixed
`_binary-{class}` / `_multiclass`), so re-running the same command overwrites
the same experiment — identical prompt versions are directly comparable in the
Braintrust UI, and different prompt versions never collide.

### Eval runners

| Script | Tests |
|---|---|
| `run_classification_eval.py` | one prompt version, multiclass, exact_match/failure/cost scorers, resumable manifest |
| `run_binary_class_eval.py` | one prompt version on a binary question (e.g. `--positive contract`), precision/recall/F1 |
| `run_multiclass_eval.py` | one prompt version across all taxonomy classes, per-class + macro accuracy |
| `evaluate_prompt_version.py` | A/B: two prompt versions on the same dataset, delta summary |

Every runner supports `--samples-per-class`, `--sample-seed`, `--limit`,
`--dry-run`, and stamps the full prompt text into experiment metadata.
`run_classification_eval` additionally accepts `--manifest` (JSONL checkpoint)
so an interrupted run resumes without re-paying LLM calls.

### LangChain + Braintrust wiring

The eval runners call `braintrust.integrations.langchain.setup_langchain()`
before any model call. That installs the Braintrust LangChain callback handler,
so every `ChatPromptTemplate -> ChatOpenAI -> parser` chain invocation inside
the eval task is traced as a nested span under the Braintrust experiment row —
prompt, response, tokens, latency are all visible in the UI.

## Adding a prompt version

1. Add a constant to `src/prompts.py` (e.g. `SORTER_PROMPT_V1`) and register it
   in `PROMPT_VERSIONS` under a version key (e.g. `"sorter_v1"`).
2. Run the eval with `--prompt-version sorter_v1`.
3. A/B against `sorter_v0` with `evaluate_prompt_version.py`.

## Tests

```bash
python -m pytest tests/ -v
```

Tests never hit the network: prompts, scorers, taxonomy, evaluation helpers,
and config loading are all mocked.
