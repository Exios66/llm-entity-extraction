# AGENTS.md

Working guide for AI agents (and humans) contributing to
**llm-entity-extraction** — the prompt experiment loop environment for the
llm-mailroom legal document pipeline.

## Project in one paragraph

This repo measures how well prompt versions classify legal documents and
extract entities, one prompt at a time. Datasets (CUAD contracts, LegalBench
tasks) are synced into Braintrust; eval runners send real documents through
the LangChain agents (sorter, specialists, judge) via OpenRouter; every run
produces a Braintrust experiment PLUS one append-only record in
`reports/experiment_log.jsonl` and a fully expanded markdown section in
`reports/experiment_log.md`. Scoring is deterministic and field-type-aware —
never exact-match-on-extraction.

## Environment & setup

- Python 3.10+ (tested on 3.13). Deps in `requirements.txt`.
- Two dotenv files, both gitignored: `braintrust.env` (Braintrust
  org/project/keys — the source of truth for config, see
  `src/braintrust_config.py`) and `.env` (OpenRouter key + provider overrides).
  Copy from the `.example` files. `src/env_utils.py` loads both; real shell
  env vars always win.
- Vision classification needs poppler (`brew install poppler` /
  `apt install poppler-utils`) for PDF→PNG rendering.
- `OPENROUTER_BASE_URL` can point at any OpenAI-compatible endpoint (Ollama,
  vLLM) — used for testing without paying.

```bash
pip install -r requirements.txt
cp braintrust.env.example braintrust.env   # fill in creds
cp .env.example .env                       # fill in OPENROUTER_API_KEY
```

## Command cheatsheet

```bash
# Sync corpora -> Braintrust datasets
python scripts/datasets/stream_cuad_to_bt.py --limit 12 --dry-run   # preview first
python scripts/datasets/stream_cuad_to_bt.py                        # all 510 PDFs
python scripts/datasets/stream_legalbench_to_bt.py --limit 6 --dry-run
python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks all

# Evals (each tests ONE prompt version; naming is {model-slug}_{prompt-version}[_suffix])
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --input-mode vision --prompt-version sorter_vision_v0          # vision, all pages
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --input-mode text --prompt-version sorter_v0                    # full text
python scripts/eval/run_extraction_eval.py --dataset mailroom-cuad-contracts \
    --prompt-version contracts_specialist_v2 --manifest data/manifests/extract_v2.jsonl
python scripts/eval/run_extraction_eval.py --bt-scores none --limit 3   # pure local
python scripts/eval/run_extraction_eval.py --judge --limit 3            # + LLM judge
python scripts/eval/run_chained_eval.py --dataset mailroom-cuad-contracts \
    --sorter-prompt-version sorter_v1 --extractor-prompt-version contracts_specialist_v4
python scripts/eval/evaluate_prompt_version.py --dataset mailroom-cuad-contracts \
    --prompt-a sorter_vision_v0 --prompt-b sorter_vision_v1         # A/B

# Reporting (all offline except the two Braintrust fetchers)
python scripts/reporting/report_generator.py --experiment <name>        # fetches Braintrust
python scripts/reporting/confusion_matrix.py --experiment <name>        # fetches Braintrust
python scripts/reporting/score_extraction_manifest.py data/manifests/extract_v2.jsonl
python scripts/reporting/render_experiment_log.py                       # rebuild md log from jsonl

# Tests (never hit the network)
python -m pytest tests/ -v
```

Always run `--dry-run` on an unfamiliar eval before paying for LLM calls.

## Architecture & data flow

```
HF/GitHub corpora ──stream_cuad/legalbench──▶ Braintrust datasets
                                                  │
local PDFs ──--pdf-dir──┐                        │ load_braintrust_dataset()
                         ▼                        ▼
               run_*_eval.py ──▶ LangChain agent ──▶ OpenRouter LLM
                    │                                │
                    │                 setup_langchain() traces spans
                    ▼                                ▼
             deterministic scoring          Braintrust experiment
             (src/field_scoring.py)              │
                    │                             │
                    ▼                             ▼
   data/manifests/*.jsonl ◀── resumable ──  report_generator / confusion_matrix
                    │
                    ▼
   reports/experiment_log.{jsonl,md}   (append-only; md rebuilt by render script)
```

Key modules:

| Module | Responsibility |
|---|---|
| `src/taxonomy.py` | loads `config/taxonomy.yaml` — doc classes, field types, agent→model mapping, thresholds. Changing the taxonomy = YAML edit, not code. |
| `src/prompts.py` | ALL prompts, versioned in `PROMPT_VERSIONS`; `get_prompt(version)`, `list_prompts()`. |
| `src/field_scoring.py` | field-type-aware content scorer: date/money/id/name/free_text/entity_list (bipartite matching), embedding rescue, factuality verification, ambiguous band. |
| `src/cuad_ground_truth.py` | CUAD 41-category catalog → per-document expected fields (type-aware by CUAD folder) + YES/NO presence expectations. |
| `src/experiment_log.py` | append-only JSONL + markdown renderer (tables, confusion matrices, scoring matrices, outputs); `render_full_log()` for the rebuild. |
| `src/evaluation.py` | dataset validation, fingerprints, `ManifestStore` (thread-safe JSONL resume checkpoints). |
| `src/scorers.py` | deterministic Braintrust scorers (exact_match, failure, cost) + `normalize_label`. |
| `src/braintrust_utils.py` | Braintrust HTTP: list/fetch experiments, load/upload datasets, attachment handling. |
| `agents/` | LangChain agents: `BaseAgent` (structured output, vision, `_last_usage`), `SorterAgent` (doc_type + contract subtype), specialists (per-class schemas), `JudgeAgent` (offline classification/completeness/correctness). |

## Scoring model (read before touching scorers)

- **Content accuracy** — per-field deterministic scores by type
  (see README "Scoring"); entity lists via optimal bipartite matching
  (Hungarian) over pairwise similarity, threshold 0.6.
- **Partial ground truth** — CUAD clause-QA labels are partial samples of the
  document. List fields in `partial_gt_fields` (`parties`,
  `key_obligations`, `termination_clauses`) are scored by **ground-truth
  coverage** (recall over matched labels), NOT F1, which would penalize
  correct extractions. Raw precision/recall/F1 always stay in
  `entity_list_scores`.
- **Containment fields** — `containment_fields` (`governing_law`,
  `term_length`, `renewal_terms`) are scored by expected-within-predicted
  token containment.
- **Factuality guard** — every predicted list item must match a GT label OR
  be grounded in the source document (token coverage ≥ 0.7). Neither ⇒
  hallucination ⇒ drives `verified_precision` down.
- **Ambiguous band** `[0.5, 0.85]` — fields in this band trigger the optional
  `--judge` LLM pass.
- **Tracker consistency rule** — the per-field score, the `*_f1` tracker, and
  `overall_extraction_score` must all report the SAME list score. Registered
  Braintrust scorers are trivial lookups on the locally computed composite —
  never recompute on the Braintrust side.

## Experiment log mechanics

- `reports/experiment_log.jsonl` is the source of truth: one JSON line per
  run, append-only, never rewritten. The markdown log is DERIVED and rebuilt
  whole with `python scripts/reporting/render_experiment_log.py`.
- Every record carries: git snapshot (`git_snapshot()`), model, prompt
  version(s), data source + fingerprint, all run parameters, tokens/cost,
  all scores, per-row results including the model's predicted outputs.
- `experiment_markdown()` in `src/experiment_log.py` renders each section as
  tables: metadata, data source, parameters, tokens, scores + breakdowns,
  per-document results, document × field scoring matrices, factuality audit,
  CUAD category presence, confusion matrices, model outputs.
- Log paths: `EXPERIMENT_LOG_PATH` / `EXPERIMENT_LOG_MD_PATH` env vars or
  `--experiment-log`. Tests redirect to tmp dirs.
- If you change the renderer, regenerate the md log so it stays in sync.

## Code conventions

- **Style**: PEP 8, `from __future__ import annotations` at the top of every
  module, docstrings on every module/function, `structlog` for logging
  (`logger = structlog.get_logger(__name__)`), type hints throughout.
- **Imports**: stdlib → third-party → repo (`sys.path.insert(0, ...)` before
  repo imports in scripts; plain absolute imports inside packages).
- **Comments**: the repo uses explanatory docstrings and section banners;
  avoid noisy inline comments in new code.
- **Scripts** are `#!/usr/bin/env python3`, live in `scripts/<area>/`, are
  runnable from the repo root, and expose `--dry-run` on anything that spends
  money. Entry points call `main_with_args(argv)` (testable) from `main()`.
- **New prompts**: add the constant + register in `PROMPT_VERSIONS`
  (`src/prompts.py`); the version key IS the experiment identity.
- **New doc classes**: add a `doc_classes:` entry in
  `config/taxonomy.yaml` (key, label, schema, specialist, field_types) AND a
  matching schema + specialist in `agents/specialist_agents.py` (and a prompt
  in `src/prompts.py`).
- **Never commit** real keys: `.env`, `braintrust.env`, `*.env.local` are
  gitignored; use the `.example` files.
- **Never edit `reports/experiment_log.md` by hand** — regenerate it.

## Testing rules

- All tests must be network-free (mocked LLM calls, tmp Braintrust config).
  Check `tests/conftest.py` for shared fixtures.
- New eval logic → add a smoke test (see `test_extraction_eval_smoke.py`,
  `test_chained_eval_smoke.py`, `test_eval_loop_smoke.py`) that runs the
  runner's `main_with_args` with mocked agents/datasets.
- New scoring behavior → unit tests in `test_field_scoring.py` /
  `test_extraction_normalization.py`.
- New streamer parsing → `test_cuad_streamer.py` /
  `test_legalbench_streamer.py` / `test_streamers.py`.
- Run the full suite before committing: `python -m pytest tests/ -q`
  (currently 180 tests, all passing).

## Gotchas

- **Manifest resume**: `--manifest` checkpoints carry a header that must
  match the rerun's metadata exactly (dataset fingerprint, model, prompt
  version); a mismatch makes the resume invalid by design.
- **Manifest-replayed rows carry no usage** — token/cost summaries count only
  rows with usage (`rows_with_usage`).
- **Vision mode** sends ALL pages of each PDF in one call by default
  (`--vision-pages all`); `first` is for cheap pilots.
- **The sorter subtypes**: the contract subtype is normalized against the
  CUAD folder names (see `CONTRACT_SUBTYPES` in `agents/sorter_agent.py`).
  A "distribution and development agreement" can plausibly be labeled either —
  that's what the subtype confusion matrix in the log is for.
- **`braintrust.integrations.langchain.setup_langchain()`** must be called
  before any model call or the experiment rows won't carry nested spans.
- **reasoning_effort**: default `none` for extraction — thinking models burn
  the whole token budget on reasoning otherwise.
- **Reports that fetch Braintrust** (`report_generator.py`,
  `confusion_matrix.py`) need `BRAINTRUST_API_KEY`; the manifest/log
  reporting paths are fully offline.
- **CUAD ground truth is type-aware**: expected fields derive from the
  contract's CUAD folder via `build_expected_fields`; don't assume all 41
  categories apply to every document.

## Useful one-liners

```bash
# List prompt versions
python -c "from src.prompts import list_prompts; print('\n'.join(list_prompts()))"

# Tail the experiment log
python - <<'PY'
import json
for line in open("reports/experiment_log.jsonl"):
    r = json.loads(line)
    print(r["experiment_name"], r["scores"].get("overall_extraction_score") or
          r["scores"].get("exact_match"), r["timestamp"])
PY
```
