# llm-entity-extraction

A prompt experiment loop environment for legal document entity extraction: the
building block for the llm-mailroom agents. Each evaluation tests **one prompt
version at a time**, runs the agents on **LangChain**, and logs everything to
**Braintrust** for comparison in the UI.

Modeled on the [RVL-CDIP-Classifier](https://github.com/Exios66/RVL-CDIP-Classifier)
repo's Braintrust evaluation pattern (vision classification of document page
images) and the [llm-mailroom](https://github.com/Exios66/llm-mailroom)
taxonomy/prompts.

## The sorter's two jobs

1. **Vision classification of the ACTUAL PDFs (RVL-CDIP pipeline)** — every
   eval row is ONE PDF with ALL of its pages: the streamer renders every page
   of the real CUAD contract PDFs into the dataset row, and the sorter sends
   **all pages of the document in a single vision call** (one classification
   per PDF, however large or small — no text files, no page-1 stubs). The
   ``sorter_vision_v0`` prompt (ordered check cascade + scratchpad +
   ``<label>/<confidence>/<reasoning>`` tag output) reads the entire agreement
   — recitals, sections, exhibits, signature pages — before deciding.
2. **Multi-class LegalBench classification** — the sorter answers the
   LegalBench multi-class classification tasks (`cuad_*` Yes/No clause tasks,
   the 13k-row MAUD per-question suite, hearsay, and 60+ more) via
   `--prompt-mode task` with the `legalbench_task_v0` prompt.

The sorter receives **full documents** — either the full extracted text
(100k-char hard safety cap, truncation recorded on the span, never a 50-token
preview) or the complete PDF page set in one call.

## Layout

```
agents/                  LangChain agents (sorter, specialists, judge)
  base_agent.py          ChatOpenAI (OpenRouter) + structured output + vision calls
  sorter_agent.py        doc-type classification: text (classify_json) + image (classify_image)
  specialist_agents.py   per-class field extraction + shared schemas
  judge_agent.py         LLM-as-a-judge (classification/completeness/correctness)
config/taxonomy.yaml     doc classes, agent->model mapping, thresholds
src/
  braintrust_config.py   loads braintrust.env / .env (org, project, model)
  braintrust_utils.py    Braintrust HTTP, dataset load/upload, attachment fetch
  classifier.py          label/confidence/reasoning parsers (RVL-CDIP style)
  evaluation.py          dataset validation, fingerprints, resumable manifests
  image_utils.py         PDF/TIFF -> 1024x1024 grayscale PNG helpers
  llm_chain.py           LangChain chain factory for eval loops
  prompts.py             ALL agent prompts, versioned (sorter_v0, sorter_vision_v0, ...)
  scorers.py             deterministic Braintrust scorers (exact_match, failure, cost)
  taxonomy.py            YAML loader for config/taxonomy.yaml
scripts/
  datasets/              sync the HF corpora into Braintrust datasets
  eval/                  the experiment loops (classification, binary, multiclass, A/B)
  reporting/             confusion matrix + markdown experiment reports
tests/                   unit tests
```

## Experiment log

Every eval run appends ONE record to `reports/experiment_log.jsonl` (plus a
human-readable section in `reports/experiment_log.md`): experiment name,
timestamp, git commit, model, prompt version, data source + fingerprint,
sample quantity/seed, ALL run parameters, token usage + cost totals, all
scores (overall, per-field, per-class), and every per-row result. The log is
append-only and updated automatically by `run_classification_eval.py` and
`run_extraction_eval.py` (including each arm of `evaluate_prompt_version.py`).

```bash
# Inspect the whole history
python - <<'PY'
import json
for line in open("reports/experiment_log.jsonl"):
    r = json.loads(line)
    print(r["experiment_name"], r["model"], r["prompt_version"],
          r["scores"].get("overall_extraction_score"), r["tokens"]["total_tokens"])
PY
```

Paths default to `reports/experiment_log.{jsonl,md}` and are overridable with
`EXPERIMENT_LOG_PATH` / `EXPERIMENT_LOG_MD_PATH` or `--experiment-log`.

## Setup

```bash
pip install -r requirements.txt
# vision pipeline needs poppler for PDF -> PNG rendering:
brew install poppler   (or apt install poppler-utils)
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

## Sync the HF corpora into Braintrust

```bash
# 1. CUAD / The Atticus Project (510 contract PDFs): ONE row per PDF with ALL
#    of its pages as image attachments + full contract text + 41 clause-category
#    QA ground truth (the extraction agent's labels), expected doc_type=contract
python scripts/datasets/stream_cuad_to_bt.py --limit 12 --dry-run     # preview
python scripts/datasets/stream_cuad_to_bt.py --limit 12               # 12 PDFs, every page
python scripts/datasets/stream_cuad_to_bt.py                          # all 510 PDFs
python scripts/datasets/stream_cuad_to_bt.py --category "Franchise" --max-pages 30

# 2. LegalBench MAUD: 139 merger agreements (full text) + the per-question
#    multi-class classification suite (13,256 rows, answer spaces embedded)
python scripts/datasets/stream_legalbench_to_bt.py --limit 6 --dry-run
python scripts/datasets/stream_legalbench_to_bt.py

# 3. LegalBench multi-class classification tasks (cuad_*, hearsay, and more)
#    from the GitHub raw data — one Braintrust dataset per task
python scripts/datasets/stream_legalbench_tasks_to_bt.py --dry-run
python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks all
```

## The loop (one prompt at a time)

```bash
# Vision classification of the CUAD PDFs (ONE row per PDF, ALL pages in one call)
python scripts/eval/run_classification_eval.py \
    --dataset mailroom-cuad-contracts --input-mode vision \
    --prompt-version sorter_vision_v0

# Same, but for a local folder of ACTUAL PDFs (rendered at eval time)
python scripts/eval/run_classification_eval.py \
    --pdf-dir ./pipeline/inbox --expected contract \
    --prompt-version sorter_vision_v0

# Full-text classification
python scripts/eval/run_classification_eval.py \
    --dataset mailroom-cuad-contracts --input-mode text --prompt-version sorter_v0

# LegalBench multi-class task eval (Yes/No clause classification)
python scripts/eval/run_classification_eval.py \
    --dataset mailroom-lb-cuad_governing_law --prompt-mode task \
    --valid-classes Yes,No --prompt-version legalbench_task_v0

# A/B two prompt versions on the same dataset
python scripts/eval/evaluate_prompt_version.py \
    --dataset mailroom-cuad-contracts --input-mode vision \
    --prompt-a sorter_vision_v0 --prompt-b sorter_vision_v1

# ---- Entity EXTRACTION eval (contracts specialist vs CUAD ground truth) ----
# Content-scored: every extracted field is compared against the CUAD clause-QA
# labels with the field-type-aware scorer (date/money/name/free-text
# normalization, entity-list bipartite F1, semantic embedding rescue via
# OpenRouter embeddings). The task computes ALL scores locally and returns a
# composite output; registered Braintrust scorers are trivial lookups on it.
# Default --bt-scores overall registers the cross-experiment tracker pair:
# overall_extraction_score (complex content accuracy) + field_presence
# (binary conformance) — comparable across every run in the Braintrust UI.
# With --bt-scores full, per-field trackers report the SAME list score that
# feeds the field scores (ground-truth coverage for partial-GT fields like
# parties/key_obligations/termination_clauses, F1 otherwise); raw
# precision/recall/F1 are kept in each row's entity_list_scores metadata.

# Ground truth follows the CUAD dataset card (theatticusproject/cuad):
# all 41 clause categories are modeled — 9 string-answer categories
# (Document Name -> document_name, Parties, dates, Renewal Term, Governing
# Law, ...) map to schema fields; the 32 YES/NO categories are scored as
# content AND as binary presence expectations (category_presence tracker:
# a labeled clause must be covered; an unlabeled one is satisfied unless
# fabricated, which the factuality guard catches). Expected fields are
# TYPE-AWARE: the contract type (CUAD folder) the document belongs to
# decides which categories/fields are expected (ground_truth_mode
# "cuad_type_aware").
python scripts/eval/run_extraction_eval.py \
    --dataset mailroom-cuad-contracts --prompt-version contracts_specialist_v2 \
    --manifest data/manifests/extract_v2.jsonl
python scripts/reporting/score_extraction_manifest.py data/manifests/extract_v2.jsonl \
    --output reports/extraction_v2.md          # post-hoc scoring report (free)
python scripts/eval/run_extraction_eval.py --bt-scores none --limit 3   # pure local
python scripts/eval/run_extraction_eval.py --bt-scores full --limit 3   # + per-field scorers
python scripts/eval/run_extraction_eval.py --judge --limit 3              # LLM-judge ambiguous band
python scripts/eval/run_extraction_eval.py --prompt-version contracts_specialist_v1  # A/B vs v2

# Inspect results
python scripts/reporting/report_generator.py --experiment qwen3.7-flash_sorter_vision_v0
python scripts/reporting/confusion_matrix.py --experiment qwen3.7-flash_sorter_vision_v0
```

Experiment naming is `{model-slug}_{prompt-version}` (optionally suffixed
`_binary-{class}` / `_multiclass`), so re-running the same command overwrites
the same experiment — identical prompt versions are directly comparable in the
Braintrust UI, and different prompt versions never collide.

### Eval runners

| Script | Tests |
|---|---|
| `run_classification_eval.py` | one prompt version; `--input-mode auto/text/vision`, `--prompt-mode sorter/task`, `--valid-classes`, `--vision-pages all/first` (all pages of each PDF in one call by default), `--pdf-dir` for local PDFs, exact_match/failure/cost scorers, resumable manifest |
| `run_extraction_eval.py` | contracts-specialist **entity extraction** vs CUAD clause-QA ground truth: `overall_extraction_score` (complex content accuracy) + `field_presence` (binary guard) registered by default as cross-experiment trackers — composite-output lookups, nothing recomputed on Braintrust; `--bt-scores none|overall|full`; optional `--judge` pass for the ambiguous band; manifest-based post-hoc scoring via `score_extraction_manifest.py` |
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
config loading, and the streamer parsers are all mocked.

