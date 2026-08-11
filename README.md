# llm-entity-extraction

A prompt experiment loop environment for legal document entity extraction: the
building block for the llm-mailroom agents. Each evaluation tests **one prompt
version at a time**, runs the agents on **LangChain**, and logs everything to
**Braintrust** for comparison in the UI — plus a fully expanded, append-only
experiment log in the repo (`reports/experiment_log.{jsonl,md}`).

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
   Local PDFs are classified with a confidence-weighted **page vote**
   (``--vision-pages all``, the default).
2. **Multi-class LegalBench classification** — the sorter answers the
   LegalBench multi-class classification tasks (`cuad_*` Yes/No clause tasks,
   the 13k-row MAUD per-question suite, hearsay, and 60+ more) via
   `--prompt-mode task` with the `legalbench_task_v0` prompt.

The sorter receives **full documents** — either the full extracted text
(100k-char hard safety cap; past the cap the input becomes a HEAD + TAIL
window — opening portion plus the closing portion where term, termination,
renewal, governing law, and signatures live — truncation recorded on the span,
never a 50-token preview) or the complete PDF page set in one call.

## The pipeline under test

The eval loops exercise the same LangChain agents the mailroom runs:

| Agent | File | Role |
|---|---|---|
| `BaseAgent` | `agents/base_agent.py` | `ChatOpenAI` (OpenRouter) + structured output (JSON schema) + vision calls; `_last_usage` token/cost capture |
| `SorterAgent` | `agents/sorter_agent.py` | doc-type classification (text `classify_json` + image `classify_image`) plus the **contract subtype** dimension (25 CUAD contract families) |
| Specialists | `agents/specialist_agents.py` | per-doc-class field extraction (contract, corporate record, due diligence, correspondence, compliance filing, court opinion) + shared JSON schemas |
| `JudgeAgent` | `agents/judge_agent.py` | offline LLM-as-a-judge: classification / completeness / extraction correctness |

## Scoring (deterministic, field-type-aware)

Exact-match-on-extraction treats every field identically, which is wrong. The
evaluations score each field by its type (`config/taxonomy.yaml →
field_scoring:`):

- `id` — normalize + exact match (docket/reference numbers)
- `date` — canonical ISO parse, then exact match ("March 3, 2024" == "03/03/2024")
- `money` — strip symbols, float compare within one cent; unparseable prose
  falls back to fuzzy matching
- `name` — Jaro-Winkler + token-set ratio on normalized text
- `free_text` — SQuAD-style token F1
- `entity_list` — optimal bipartite matching (Hungarian algorithm) over
  pairwise similarity, then precision/recall/F1

`name`/`free_text` also use embedding cosine similarity
(`sentence-transformers/all-MiniLM-L6-v2`, lazy, graceful degradation) as a
second signal when the string score is ambiguous (below the `embedding_rescue_below`
threshold). The embedder prefers the local model and falls back to OpenRouter
embeddings (`openai/text-embedding-3-small`) when sentence-transformers is not
installed or the model cannot load — so the rescue works with a plain
`pip install -r requirements.txt` too. Empty predictions/labels are never
rescued by embeddings: a blank answer stays a miss.

Ground truth follows the CUAD dataset card (`theatticusproject/cuad`): all 41
clause categories are modeled — 9 string-answer categories map to schema
fields; the 32 YES/NO categories are scored as content **and** as binary
presence expectations. Expected fields are **type-aware**: the CUAD folder the
contract came from decides which categories apply (`ground_truth_mode
"cuad_type_aware"`, `src/cuad_ground_truth.py`). A **factuality guard**
verifies every predicted list item against a label or the source document and
reports `verified_precision` / `hallucination_rate`.

## Layout

```
agents/                  LangChain agents (sorter, specialists, judge)
  base_agent.py          ChatOpenAI (OpenRouter) + structured output + vision calls
  sorter_agent.py        doc-type + contract-subtype classification (text + image)
  specialist_agents.py   per-class field extraction + shared JSON schemas
  judge_agent.py         LLM-as-a-judge (classification/completeness/correctness)
config/taxonomy.yaml     doc classes, field types, agent->model mapping, thresholds
src/
  braintrust_config.py   loads braintrust.env / .env (org, project, model, api base)
  braintrust_utils.py    Braintrust HTTP, dataset load/upload, experiment fetch
  classifier.py          label/confidence/reasoning parsers (RVL-CDIP style)
  cuad_ground_truth.py   CUAD 41-category catalog -> expected fields + presence
  env_utils.py           dotenv loading + required-var validation
  evaluation.py          dataset validation, fingerprints, resumable manifests
  experiment_log.py      append-only repo experiment log (JSONL + markdown renderer)
  field_scoring.py       deterministic field-type-aware content scoring + factuality audit
  image_utils.py         PDF/TIFF -> 1024x1024 grayscale PNG helpers
  llm_chain.py           LangChain chain factory for eval loops
  openrouter_utils.py    OpenRouter constants + vision message builders
  prompts.py             ALL agent prompts, versioned
  scorers.py             deterministic Braintrust scorers (exact_match, failure, cost)
  taxonomy.py            YAML loader for config/taxonomy.yaml
scripts/
  datasets/              sync the HF corpora into Braintrust datasets
    stream_cuad_to_bt.py            CUAD v1: 510 contract PDFs, every page rendered
    stream_legalbench_to_bt.py      MAUD v1: 139 agreements + 13k-row classification suite
    stream_legalbench_tasks_to_bt.py 60+ LegalBench classification tasks
    download_cuad_pdfs.py           full CUAD v1 corpus (PDFs + CUAD_v1.json) to data/cuad_pdfs/
  eval/                  the experiment loops
    run_classification_eval.py      one prompt, text/vision/task modes, local PDFs
    run_extraction_eval.py          contracts specialist vs CUAD ground truth
    run_chained_eval.py             sorter -> extractor end-to-end pipeline eval
    run_binary_class_eval.py        binary question precision/recall/F1
    run_multiclass_eval.py          all-class eval with per-class accuracy
    run_subtype_eval.py             sorter-only contract-subtype eval (one call per PDF)
    evaluate_prompt_version.py      A/B two prompt versions on the same dataset
  reporting/
    report_generator.py             markdown experiment report from Braintrust
    confusion_matrix.py             PNG + CSV confusion matrix from Braintrust
    score_extraction_manifest.py    post-hoc extraction scoring from a manifest
    render_experiment_log.py        rebuild the markdown log from the JSONL source
    judge_experiment.py             post-hoc JudgeAgent review of failed classifications
    backfill_subtype_reasoning.py   one-time enrichment: full failure reasoning from spans
  site/
    build_site.py                   rebuild docs/ (GitHub Pages) data from the JSONL
tests/                   unit tests (183, no network)
```

## Experiment log

Every eval run appends ONE record to `reports/experiment_log.jsonl` (plus a
fully expanded section in `reports/experiment_log.md`): experiment name,
timestamp, git commit, model, prompt version, data source + fingerprint,
sample quantity/seed, ALL run parameters, token usage + cost totals, all
scores (overall, per-field, per-class), and every per-row result — including
the model's raw predicted outputs.

The markdown log is rendered as **tables, never JSON dumps**: per-document
results, a document × field scoring matrix (the full per-doc scoring
calculation), entity-list F1, the factuality audit, CUAD category presence,
expected × predicted **confusion matrices** (classification and sorter
contract-subtype), and predicted extractions. The JSONL is the source of
truth; the markdown is rebuilt from it at any time:

```bash
python scripts/reporting/render_experiment_log.py          # rebuild the whole markdown log
python scripts/reporting/render_experiment_log.py --dry-run  # print instead of write
python scripts/site/build_site.py                          # rebuild the site data (docs/)
python scripts/site/build_site.py --check                  # verify the site data is current
```

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

## Website

The associated website for this repo is a static experiment-log viewer
served by GitHub Pages — **no Actions runners**:

**https://exios66.github.io/llm-entity-extraction/**

- The site lives entirely in `docs/` (see `docs/README.md`): a
  dependency-free single-page viewer with a filterable/searchable runs index,
  per-run detail pages (scores, per-field breakdowns, per-document results,
  confusion matrices, failure insights), and lazy-loaded run data.
- `docs/data/` is DERIVED from `reports/experiment_log.jsonl` via
  `scripts/site/build_site.py` — never hand-edit it. After every run:

  ```bash
  python scripts/reporting/render_experiment_log.py   # markdown log
  python scripts/site/build_site.py                   # site data
  ```

- Enabling Pages is a one-time repo setting: **Settings → Pages → Deploy from
  a branch → `main` → `/docs`**.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # recommended; .venv/ is gitignored
pip install -r requirements.txt
# vision pipeline needs poppler for PDF -> PNG rendering:
brew install poppler   (or apt install poppler-utils)
cp braintrust.env.example braintrust.env   # fill in creds (org/project/API key)
cp .env.example .env                       # fill in OPENROUTER_API_KEY
```

The repo is also pip-installable so the LangChain agents can be imported and
called from OTHER codebases (e.g. the llm-mailroom LangGraph architecture):

```bash
pip install -e .        # editable: new agent/prompt changes are picked up immediately
# then, from anywhere:
from agents.sorter_agent import SorterAgent
from agents.judge_agent import JudgeAgent
from agents.specialist_agents import ContractsSpecialist
```

Optional — local semantic embedding rescue (recommended): install
`sentence-transformers` to embed with the local `all-MiniLM-L6-v2` model
(free, fast, offline, reproducible) instead of paid OpenRouter embedding calls:

```bash
pip install sentence-transformers   # pulls torch (~2-3 GB)
```

Both routes are verified and interchangeable: the scorer uses the local model
when available and falls back to OpenRouter embeddings automatically when it
isn't. Without sentence-transformers, the rescue still works (OpenRouter
fallback, tiny per-request cost); with it, nothing is sent to the network.

Required env vars (in `braintrust.env` or `.env`; see `src/env_utils.py`):

| Variable | Purpose |
|---|---|
| `BRAINTRUST_ORG_ID` | Braintrust org |
| `BRAINTRUST_PROJECT_ID` / `BRAINTRUST_PROJECT_NAME` | project for experiments/datasets |
| `BRAINTRUST_API_KEY` | key with write access to the project |
| `BRAINTRUST_API_BASE` | API base (default `https://api.braintrust.dev`) |
| `BRAINTRUST_MODEL` | default eval model (default `qwen/qwen3.7-flash`) |
| `BRAINTRUST_DATASET_PROJECT` | project holding the datasets |
| `OPENROUTER_API_KEY` | LLM calls through OpenRouter |
| `OPENROUTER_BASE_URL` | optional: any OpenAI-compatible endpoint (Ollama, vLLM) |
| `EXPERIMENT_LOG_PATH` / `EXPERIMENT_LOG_MD_PATH` | experiment log paths (optional) |

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

# OPTIONAL — keep the FULL CUAD corpus locally instead of streaming to Braintrust:
# all 510 contract PDFs (CUAD folder structure preserved) + CUAD_v1.json clause
# QA annotations, mirrored into data/cuad_pdfs/. Resumable: re-running skips
# already-downloaded files. Feed the local PDFs to the eval loop with --pdf-dir.
python scripts/datasets/download_cuad_pdfs.py --dry-run      # preview
python scripts/datasets/download_cuad_pdfs.py --limit 12     # first 12 PDFs
python scripts/datasets/download_cuad_pdfs.py                # all 510 + CUAD_v1.json
python scripts/datasets/download_cuad_pdfs.py --category "Franchise"
python scripts/datasets/download_cuad_pdfs.py --out-dir data/cuad_pdfs --skip-json
python scripts/datasets/download_cuad_pdfs.py --overwrite    # re-download everything
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
# labels with the field-type-aware scorer (date/money/name/free-text,
# entity-list bipartite F1, semantic embedding rescue — local
# sentence-transformers with an OpenRouter embedding fallback). The task
# computes ALL scores locally and returns a composite
# output; registered Braintrust scorers are trivial lookups on it.
# Default --bt-scores overall registers the cross-experiment tracker pair:
# overall_extraction_score (complex content accuracy) + field_presence
# (binary conformance) — comparable across every run in the Braintrust UI.
# With --bt-scores full, per-field trackers report the SAME list score that
# feeds the field scores (ground-truth coverage for partial-GT fields like
# parties/key_obligations/termination_clauses, F1 otherwise); raw
# precision/recall/F1 are kept in each row's entity_list_scores metadata.
python scripts/eval/run_extraction_eval.py \
    --dataset mailroom-cuad-contracts --prompt-version contracts_specialist_v2 \
    --manifest data/manifests/extract_v2.jsonl
python scripts/reporting/score_extraction_manifest.py data/manifests/extract_v2.jsonl \
    --output reports/extraction_v2.md          # post-hoc scoring report (free)
python scripts/eval/run_extraction_eval.py --bt-scores none --limit 3   # pure local
python scripts/eval/run_extraction_eval.py --bt-scores full --limit 3   # + per-field scorers
python scripts/eval/run_extraction_eval.py --judge --limit 3            # LLM-judge ambiguous band
python scripts/eval/run_extraction_eval.py --prompt-version contracts_specialist_v1  # A/B vs v2

# ---- Chained pipeline eval (sorter -> extractor, end to end) ----
python scripts/eval/run_chained_eval.py \
    --dataset mailroom-cuad-contracts \
    --sorter-prompt-version sorter_v1 --extractor-prompt-version contracts_specialist_v4 \
    --manifest data/manifests/chained_5.jsonl

# ---- SORTER-ONLY subtype eval (contract subclass classification) ----
# One sorter call per PDF; scored for doc_type accuracy, EXACT subtype
# accuracy (CUAD-folder key) AND family-level accuracy (subtype_accuracy_equiv
# — defensible family equivalents like reseller/distributor,
# maintenance/license, development/license, affiliate/joint_venture count as
# correct routing). Per-subtype accuracy + expected x predicted confusion
# matrix in the repo log.
python scripts/eval/run_subtype_eval.py --dry-run                  # preview
python scripts/eval/run_subtype_eval.py                            # all 50 contracts
python scripts/eval/run_subtype_eval.py --sorter-prompt-version sorter_v3 \
    --manifest data/manifests/subtype_50_v3.jsonl
python scripts/eval/run_subtype_eval.py --sample 10 --seed 42      # pilot slice

# Inspect results
python scripts/reporting/report_generator.py --experiment qwen3.7-flash_sorter_vision_v0
python scripts/reporting/confusion_matrix.py --experiment qwen3.7-flash_sorter_vision_v0
python scripts/reporting/render_experiment_log.py
```

Experiment naming is `{model-slug}_{prompt-version}` (optionally suffixed
`_binary-{class}` / `_multiclass` / `_extraction` / `_chained`), so re-running
the same command overwrites the same experiment — identical prompt versions
are directly comparable in the Braintrust UI, and different prompt versions
never collide.

### Eval runners

| Script | Tests |
|---|---|
| `run_classification_eval.py` | one prompt version; `--input-mode auto/text/vision`, `--prompt-mode sorter/task`, `--valid-classes`, `--vision-pages all/first` (all pages of each PDF in one call by default), `--pdf-dir`/`--documents-dir`/`--images-dir` for local inputs, exact_match/failure/cost scorers, resumable manifest |
| `run_extraction_eval.py` | contracts-specialist **entity extraction** vs CUAD clause-QA ground truth: `overall_extraction_score` (complex content accuracy) + `field_presence` (binary guard) registered by default as cross-experiment trackers — composite-output lookups, nothing recomputed on Braintrust; `--bt-scores none/overall/full`; optional `--judge` pass for the ambiguous band; manifest-based post-hoc scoring via `score_extraction_manifest.py` |
| `run_chained_eval.py` | end-to-end pipeline: sorter (doc_type + contract subtype) → contracts specialist; per-stage scores and token usage, sorter subtype accuracy + extractor content scores in one record |
| `run_binary_class_eval.py` | one prompt version on a binary question (e.g. `--positive contract`), precision/recall/F1 |
| `run_multiclass_eval.py` | one prompt version across all taxonomy classes, per-class + macro accuracy |
| `run_subtype_eval.py` | sorter-only contract-family eval: one classification per PDF; `sorter_exact_match` (doc_type), `sorter_subtype_accuracy` (EXACT CUAD-folder key) and `sorter_subtype_accuracy_equiv` (family-level — defensible equivalents like reseller/distributor, maintenance/license, development/license, affiliate/joint_venture recognized as correct routing), per-subtype accuracy + confusion matrix in the repo log |
| `evaluate_prompt_version.py` | A/B: two prompt versions on the same dataset, delta summary |
| `run_langfuse_subtype_eval.py` | **Langfuse mirror** of `run_subtype_eval` (same data/task/scorers) — traces into the SEPARATE `llm-mailroom-experiments` project, zero Braintrust scored-run quota |
| `run_langfuse_chained_eval.py` | **Langfuse mirror** of the chained eval: per-agent spans (`sorter`, `contracts_specialist`) with each agent's designated task scores attached to its own observation; `--handoff-scope subtype` (default) cues the specialist with the predicted subtype's CUAD field groups |
| `run_langfuse_extraction_eval.py` | **Langfuse mirror** of the specialist-only extraction eval |
| `run_langfuse_classification_eval.py` | **Langfuse mirror** of the doc-type classification eval (text mode) |

Every runner supports `--samples-per-class`/`--sample`, `--sample-seed`/`--seed`,
`--limit`, `--dry-run`, `--experiment-log`, and stamps the full prompt text
into experiment metadata. `run_classification_eval`/`run_extraction_eval`/
`run_chained_eval` additionally accept `--manifest` (JSONL checkpoint) so an
interrupted run resumes without re-paying LLM calls.

### Prompt versions

Registered in `src/prompts.py` → `PROMPT_VERSIONS` (aliases noted):

| Family | Versions |
|---|---|
| Sorter (text) | `sorter_v0` (alias `sorter`), `sorter_v1`, `sorter_v2`, `sorter_v3`, `sorter_v4`, `sorter_v5`, `sorter_v6` |
| Sorter (vision) | `sorter_vision_v0` |
| LegalBench task | `legalbench_task_v0` |
| Contracts specialist | `contracts_specialist` (v0), `contracts_specialist_v1` … `contracts_specialist_v12` |
| Other specialists | `corporate_records_specialist`, `due_diligence_specialist`, `correspondence_specialist`, `compliance_specialist`, `court_opinions_specialist` |
| Agents / judges | `boss`, `reporter`, `judge`, `judge-classification`, `judge-correctness` |
| PDF | `pdf_transcriber` |

### LangChain + Braintrust wiring

The eval runners call `braintrust.integrations.langchain.setup_langchain()`
before any model call. That installs the Braintrust LangChain callback handler,
so every `ChatPromptTemplate -> ChatOpenAI -> parser` chain invocation inside
the eval task is traced as a nested span under the Braintrust experiment row —
prompt, response, tokens, latency are all visible in the UI.

### Langfuse mirror (separate environment, per-agent tasks)

The `run_langfuse_*_eval.py` runners execute the SAME datasets, tasks, and
deterministic logic scorers as their Braintrust counterparts, but trace into a
SEPARATE Langfuse project — `llm-mailroom-experiments` (keys in gitignored
`langfuse.env`, `langfuse.env.example` in-repo). Every trace carries
`environment=llm-mailroom-experiments` and a session-scoped deterministic
trace id, so re-runs of one experiment update their traces in place and
different experiments never merge. Langfuse runs never consume Braintrust
scored-run quotas: the logic scorers are computed locally and logged per trace
as NUMERIC scores.

Each pipeline agent has a **designated task** traced as its own observation
with its scores attached to that observation — per-agent performance metrics
derivable over time in Langfuse:

| Agent | Observation | Task scores |
|---|---|---|
| `sorter` | span per document | `exact_match`, `subtype_accuracy`, `subtype_accuracy_equiv`, `confidence` |
| `contracts_specialist` | span per document | `overall_extraction_score`, `field_presence`, `overall_verified_precision`, `category_presence`, `schema_valid` |

The chained mirror passes the sorter's class + subclass to the specialist via
`handoff_context`; with `--handoff-scope subtype` (default) the specialist is
additionally cued with the PREDICTED subtype's CUAD field-group scope
(`build_subtype_handoff` — expected schema fields + applicable /
never-applicable clause categories; a pure function of the subtype, no
ground-truth answers). `--handoff-scope none` reproduces the legacy handoff.
Measured on the same 5-doc chained sample: overall 0.8666 vs 0.8497 (+1.7pp)
and category presence 0.7773 vs 0.7106 (+6.7pp).

```bash
cp langfuse.env.example langfuse.env   # fill in the SEPARATE project's keys
python scripts/eval/run_langfuse_chained_eval.py --sample 5 --seed 42 \
    --sorter-prompt-version sorter_v6 --extractor-prompt-version contracts_specialist_v11 \
    --manifest data/manifests/chained_langfuse.jsonl
```

## Adding a prompt version

1. Add a constant to `src/prompts.py` (e.g. `SORTER_PROMPT_V1`) and register it
   in `PROMPT_VERSIONS` under a version key (e.g. `"sorter_v1"`).
2. Run the eval with `--prompt-version sorter_v1`.
3. A/B against `sorter_v0` with `evaluate_prompt_version.py`.

## Tests

```bash
python -m pytest tests/ -v
```

223 tests, none hitting the network: prompts, scorers, taxonomy, evaluation
helpers, config loading, field scoring, CUAD ground truth, the subtype
handoff cue, page voting, the chained/extraction/classification/subtype/langfuse
eval smoke loops, and the streamer parsers are all mocked.

## Docs

- `SCORING.md` — every scorer and metric: classification, binary, multiclass,
  field-type-aware content scoring, factuality audit, chained stage trackers,
  A/B deltas, token/cost accounting.
- `CHANGELOG.md` — semantic-version history of all significant releases
  (each tagged `vX.Y.Z`).
- `AGENTS.md` — the agent workflow guide: setup, commands, architecture,
  conventions, and gotchas.
