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
never exact-match-on-extraction. The agents are pip-installable
(`pip install -e .`) so llm-mailroom's LangGraph architecture imports and
calls them directly; prompt versions are the experiment identity.

## Environment & setup

- Python 3.10+ (tested on 3.13). Deps in `requirements.txt`; the repo is also
  a Python package (`pyproject.toml` — packages `agents`, `src`, `config`).
- Two dotenv files, both gitignored: `braintrust.env` (Braintrust
  org/project/keys — the source of truth for config, see
  `src/braintrust_config.py`) and `.env` (OpenRouter key + provider overrides).
  Copy from the `.example` files. `src/env_utils.py` loads both; real shell
  env vars always win.
- Vision classification needs poppler (`brew install poppler` /
  `apt install poppler-utils`) for PDF→PNG rendering.
- `OPENROUTER_BASE_URL` can point at any OpenAI-compatible endpoint (Ollama,
  vLLM) — used for testing without paying.
- Optional but recommended: `pip install sentence-transformers` — the semantic
  embedding rescue then runs the local `all-MiniLM-L6-v2` model (free,
  offline, reproducible) instead of paid OpenRouter embedding calls. Both
  routes are verified; the fallback triggers automatically when the local
  model is unavailable.

```bash
python3 -m venv .venv && source .venv/bin/activate   # recommended; .venv/ is gitignored
pip install -r requirements.txt
pip install -e .        # editable install: agents/src/config importable from ANY codebase
                        # (e.g. llm-mailroom's LangGraph) — new changes picked up instantly
cp braintrust.env.example braintrust.env   # fill in creds
cp .env.example .env                       # fill in OPENROUTER_API_KEY
```

## Command cheatsheet

```bash
# Sync corpora -> Braintrust datasets
python scripts/datasets/stream_cuad_to_bt.py --limit 12 --dry-run   # preview first
python scripts/datasets/stream_cuad_to_bt.py                        # all 510 PDFs (page images)
python scripts/datasets/stream_cuad_to_bt.py --text-only            # 510 rows, TEXT only (no poppler)
python scripts/datasets/download_cuad_pdfs.py --dry-run             # keep the corpus locally
python scripts/datasets/stream_legalbench_to_bt.py --limit 6 --dry-run
python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks all

# Evals (each tests ONE prompt version; naming is {model-slug}_{prompt-version}[_suffix])
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --input-mode vision --prompt-version sorter_vision_v0          # vision, all pages
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --input-mode text --prompt-version sorter_v0                    # full text
python scripts/eval/run_extraction_eval.py --dataset mailroom-cuad-contracts \
    --prompt-version contracts_specialist_v2 --manifest data/manifests/extract_v2.jsonl
python scripts/eval/run_chained_eval.py --dataset mailroom-cuad-contracts \
    --sorter-prompt-version sorter_v5 --extractor-prompt-version contracts_specialist_v11 \
    --manifest data/manifests/chained_5.jsonl                      # sorter -> extractor
python scripts/eval/run_chained_eval.py ... --handoff-scope none   # legacy handoff (no subtype cue)
python scripts/eval/run_chained_eval.py ... --handoff-scope ground_truth  # error-propagation ablation:
                            # specialist ALSO runs with the GT-subtype handoff; scores.ablation
                            # splits sorter routing loss from specialist error
python scripts/eval/run_model_matrix.py --task subtype --models qwen/qwen3.7-flash,deepseek/deepseek-v4-flash \
                            --prompts sorter_v5,sorter_v6 --sample 10 --seed 42  # cross-model matrix
python scripts/eval/run_subtype_eval.py --dataset mailroom-cuad-contracts-full \
    --stratified 200 --seed 42 --sorter-prompt-version sorter_v5   # sorter-only, even across classes
python scripts/eval/evaluate_prompt_version.py --dataset mailroom-cuad-contracts \
    --prompt-a sorter_vision_v0 --prompt-b sorter_vision_v1         # A/B

# Langfuse projects (two environments, two purposes):
#   - llm-dojo: where THIS repo's prompt iterations run — individual prompt
#     improvements and enhancements, evaluated one prompt version at a time.
#     ALL eval runs trace here (keys in langfuse.env are project-scoped and
#     route every trace to llm-dojo; the LANGFUSE_PROJECT label and the code
#     default in src/langfuse_config.py are both "llm-dojo").
#   - llm-mailroom (llm-mailroom-experiments): EXCLUSIVELY for testing and
#     improving the FULL mailroom pipeline (the llm-mailroom repo). Insights
#     and results from llm-dojo iterations are applied there — prompt
#     enhancements flow llm-dojo -> llm-mailroom, never the reverse.
#   Prompt iteration sync: after every prompt iteration, mirror the versioned
#   prompts into Langfuse (idempotent; each PROMPT_VERSIONS key becomes a
#   text prompt; repeatable --env-file adds projects, e.g. a key file for the
#   llm-mailroom project when pipeline tests need the same prompt versions):
#   python scripts/eval/sync_langfuse_prompts.py            # -> llm-dojo (langfuse.env)
#   python scripts/eval/sync_langfuse_prompts.py --env-file langfuse.env \
#       --env-file langfuse-llm-mailroom.env               # -> both projects
#   (add --dry-run to preview; a missing env file / missing keys is skipped
#   with a warning, so another project is a drop-in — create an env file
#   with that project's key pair and pass it on the command line.)
python scripts/eval/run_langfuse_subtype_eval.py --dataset mailroom-cuad-contracts-full \
    --sorter-prompt-version sorter_v6
python scripts/eval/run_langfuse_chained_eval.py --sample 5 --seed 42 \
    --sorter-prompt-version sorter_v6 --extractor-prompt-version contracts_specialist_v11
python scripts/eval/run_langfuse_extraction_eval.py --prompt-version contracts_specialist_v11
python scripts/eval/run_langfuse_classification_eval.py --prompt-version sorter_v6

# HITL annotation queue (llm-dojo mirror): filter IN low-performing extraction traces
python scripts/eval/run_annotation_queue.py build --dry-run --threshold 0.85   # scan + rank, no writes
python scripts/eval/run_annotation_queue.py build --threshold 0.85             # create queue + enqueue PENDING items
python scripts/eval/run_annotation_queue.py status                            # queue items + scores + trace URLs

# Wiki (version-controlled here, pushed to the public GitHub wiki)
./wiki/sync-wiki.sh                     # push wiki/ -> https://github.com/Exios66/llm-entity-extraction/wiki

# Site data (derived from the experiment log; never hand-edit docs/data)
python scripts/site/build_site.py          # regenerate docs/data/ (index, meta, runs/, trends.json, prompts.json, benchmarks.json)
python scripts/site/build_site.py --check  # verify it is current
python scripts/site/build_site.py --benchmarks-key $OPENROUTER_API_KEY  # include live OpenRouter benchmarks (best-effort)
node tests/assets/site_render_audit.js     # headless render audit of EVERY view (after any site.js edit)

# Releases (mechanical steps automated; the commit/tag are always explicit)
python scripts/release.py --check                     # validate state (version == changelog header, site data, tests, audit)
python scripts/release.py --bump minor --note "<summary>"   # move [Unreleased] -> [vX.Y.Z], bump pyproject, print commands
python scripts/release.py --bump patch --note "<summary>" --dry-run
# Note: docs/assets/site.js + index.html are HAND-maintained (trend charts,
# cost-vs-quality scatter, failure-mode stacked bars, #/prompts diff view).
# Charts: log-scale cost axis, Catmull-Rom smoothing, curated palette/dashes,
# hover tooltips + click-to-run on every point; nav tasks live under the
# single "tasks" dropdown (populated from meta.tasks). Run
# `node tests/assets/site_render_audit.js` after any site.js edit.

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
| `src/prompts.py` | ALL prompts, versioned in `PROMPT_VERSIONS`; `get_prompt(version)`, `list_prompts()`. The version key IS the experiment identity. |
| `src/field_scoring.py` | field-type-aware content scorer: date/money/id/name/free_text/entity_list (bipartite matching), embedding rescue (local sentence-transformers, OpenRouter fallback, empty-string guard), factuality verification, ambiguous band. |
| `src/cuad_ground_truth.py` | CUAD 41-category catalog → per-document expected fields (type-aware by CUAD folder) + YES/NO presence expectations + `build_subtype_handoff()` (the subtype-scoped specialist cue used by `--handoff-scope subtype`). |
| `src/langfuse_tracing.py` | Langfuse mirror tracer: one trace per document (session-scoped deterministic id), `agent_observation()` opens one span per pipeline agent with its designated task scores attached to that observation; graceful no-op when keys are missing. |
| `src/experiment_log.py` | append-only JSONL + markdown renderer (tables, confusion matrices, scoring matrices, outputs, failure insights); `render_full_log()` for the rebuild. |
| `src/evaluation.py` | dataset validation, fingerprints, `ManifestStore` (thread-safe JSONL resume checkpoints). |
| `src/scorers.py` | deterministic Braintrust scorers (exact_match, failure, cost) + `normalize_label`. |
| `src/braintrust_utils.py` | Braintrust HTTP: list/fetch experiments, load/upload datasets, attachment handling. |
| `agents/` | LangChain agents: `BaseAgent` (structured output, vision, `_last_usage`, head+tail `truncate_input`), `SorterAgent` (doc_type + 25 contract subtypes, default `reasoning_effort="medium"`, `SUBTYPE_EQUIVALENCES`), specialists (per-class schemas), `JudgeAgent` (offline classification/completeness/correctness). |

## Scoring model (read before touching scorers)

The canonical, formula-level reference for every scorer and metric is
**`SCORING.md`** (classification, binary, multiclass, field-type-aware content
scoring, factuality audit, chained stage trackers, A/B deltas, token/cost
accounting). The rules below are the invariants:

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
- **Subtype equivalence** — the subtype eval reports BOTH strict accuracy
  (`subtype_accuracy`, exact CUAD-folder key) and family-level accuracy
  (`subtype_accuracy_equiv`; `equivalent_subtypes()` honors
  `SUBTYPE_EQUIVALENCES`: reseller↔distributor, maintenance↔license,
  development↔license, affiliate↔joint_venture). Strict stays the
  discriminating signal; equiv recognizes defensible family routing.

## Experimental testing workflow (the loop)

1. **Diagnose with data** — read `reports/experiment_log.md` (or the jsonl)
   for the last runs; identify the failure pattern (per-field scores,
   confusion matrices, `failure_insights` reasoning on failed rows, model
   reasoning quotes). Fetch full traces from Braintrust when the stored
   reasoning is truncated.
2. **Change ONE thing** — new prompt version (constant + `PROMPT_VERSIONS`
   entry in `src/prompts.py`), config flag, or scorer rule. The version key
   IS the experiment identity; never mutate a prompt string after it has run.
   Keep the change surgical and cite the data that motivates it in the
   prompt's section banner comment.
3. **Unit-test the change** — mock-level tests (prompt content assertions,
   option-list ↔ schema-enum wiring tests, runner smoke tests). Run
   `python -m pytest tests/ -q` before spending money.
4. **Dry-run** — `--dry-run` on the eval runner to confirm the plan
   (dataset size, prompt versions, experiment name).
5. **Run a cheap pilot** — small sample with the same seed as the previous
   run (e.g. `--sample 5 --seed 42`) so results are directly comparable.
6. **A/B on identical rows** — same dataset, same seed, different prompt
   versions; compare strict + equiv + cost + output cleanliness. Only prompt
   versions validated this way belong in a release.
7. **Full-sample run when meaningful** — e.g.
   `--stratified 200 --seed 42` on `mailroom-cuad-contracts-full` (8 docs per
   subtype × 25). Same-sample comparisons are the ONLY valid accuracy
   comparisons — never compare across different samples.
8. **Log & document** — verify the record in `reports/experiment_log.jsonl`
   (see "After every run" below), then update `CHANGELOG.md` (see "Release
   workflow").

## After every run (experiment log upkeep)

The eval runners append to `reports/experiment_log.jsonl` automatically. The
markdown log is DERIVED — after every completed run:

```bash
python scripts/reporting/render_experiment_log.py   # rebuild reports/experiment_log.md
python scripts/site/build_site.py                   # rebuild docs/data (the GH Pages site data)
```

Then commit + push — **GitHub Pages serves `/docs` from `main`**, so the
experiment-log site updates on every push:

```bash
git add reports/experiment_log.jsonl reports/experiment_log.md docs/data
git commit -m "EXPERIMENT: <experiment_name>"
git push origin main
```

**Mirror sync into llm-mailroom** (the synced copy at
`docs/reports/experiments/experiment_log.md` + its own GH Pages sync):

```bash
cd ../llm-mailroom
PYTHONPATH=src python -c "from legalbench.experiment_log import regenerate, default_log_path; regenerate(default_log_path())"
git add docs/reports/experiments/experiment_log.md
git commit -m "DOCS SYNC: experiment log re-synced"
git push origin main
```

Verify the record is COMPLETE before moving on:

- `reports/experiment_log.jsonl` gained exactly ONE new line (experiment
  name, model, git snapshot, prompt version(s), data source + fingerprint,
  ALL run parameters incl. `reasoning_effort` / `max_input_chars` /
  `stratified`, tokens/cost, all scores).
- The markdown section renders: metadata, data source, parameters, tokens,
  scores + breakdowns, per-document results, scoring matrices, confusion
  matrices, model outputs — and for subtype runs: per-class accuracy table
  plus **Failed classification insights** (each failed row with its failure
  mode and the model's FULL reasoning).
- Failed rows carry full reasoning (`failure_insights` / 4000-char span);
  successes carry a bounded excerpt. If a record lacks reasoning on failures,
  backfill it from the Braintrust LLM spans before regenerating.
- Never hand-edit `reports/experiment_log.md` — regenerate it.

## Release workflow (semantic versioning + tag)

The changelog follows [Keep a Changelog](https://keepachangelog.com/) and
semver; every release maps to ONE tagged commit (`vX.Y.Z`), and the tag must
match the CHANGELOG header exactly. The mechanical steps are automated by
`scripts/release.py` — the commit/tag are always explicit git commands.

### Changelog discipline (automatic, per commit)

- **Every behavior-changing commit carries its `[Unreleased]` entry in the
  SAME commit** — `### Added` / `### Changed` / `### Fixed` bullets naming
  files, prompt versions, and the data-backed results that motivated them
  (accuracy numbers, sample sizes, seeds). Docs-only and derived-artifact
  regenerations (log/site timestamps) do not need entries.
- Structure bullets exactly like the existing history: bold lead-in,
  backticked file/flag names, and concrete numbers where they exist.
- Bump rules (semver): **major** = breaking architecture/output-contract
  changes; **minor** = new features (new prompt versions, new eval runners,
  new dataset modes, new site capabilities); **patch** = bug fixes (scoring
  guards, prompt regressions, site display fixes).

### Release steps (vX.Y.Z)

1. **Update `CHANGELOG.md`** — `scripts/release.py --bump <patch|minor|major>
   --note "<summary>"` converts the accumulated `[Unreleased]` entries into
   `## [vX.Y.Z] - <date>`, adds the `[vX.Y.Z]:` release link, and keeps an
   empty `[Unreleased]` placeholder for future entries. `--dry-run` previews
   without writing; the script refuses to run on a dirty tree.
2. **Bump `pyproject.toml`** — the script does this automatically; the
   version MUST equal the latest CHANGELOG header (`release.py --check`
   enforces it).
3. **Update repository documentation when the change touches it** —
   `README.md` (layout tree, command examples, prompt tables, the Website
   section), `docs/README.md` (the site's own doc), `SCORING.md` (formula/
   metric changes), and this `AGENTS.md` itself (workflow/architecture
   changes). Never skip docs that describe the thing that changed.
4. **Regenerate derived artifacts** — `render_experiment_log.py` (new runs)
   + `scripts/site/build_site.py` (site data) + the headless render audit
   (`node tests/assets/site_render_audit.js`).
5. **Run the full suite** — `python -m pytest tests/ -q` (network-free) and
   `python scripts/release.py --check` (version/changelog consistency, site
   data freshness, tests, render audit).
6. **Commit** — one commit covering changelog + docs + pyproject + derived
   artifacts, message `vX.Y.Z: <summary>`.
7. **Tag and push** — annotated tag matching the changelog header exactly;
   pushing main updates the GH Pages site (`/docs` served from `main`):
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z — <summary>"
   git push origin main --tags
   ```
8. **Mirror sync into llm-mailroom** (synced experiment log + its docs):
   run the llm-mailroom `legalbench.experiment_log.regenerate()` command from
   the "After every run" section, then commit + push there.
9. Verify the tag exists on GitHub and the README/CHANGELOG/site render
   correctly (https://exios66.github.io/llm-entity-extraction/).

## Experiment log mechanics

- `reports/experiment_log.jsonl` is the source of truth: one JSON line per
  run, append-only, never rewritten (the one exception: a documented
  one-time backfill to enrich historical records with full failure reasoning,
  fetched from Braintrust LLM spans — record it in the changelog if used).
  The markdown log is DERIVED and rebuilt whole with
  `python scripts/reporting/render_experiment_log.py`.
- Every record carries: git snapshot (`git_snapshot()`), model, prompt
  version(s), data source + fingerprint, all run parameters, tokens/cost,
  all scores, per-row results including the model's predicted outputs.
- Subtype runs additionally carry `scores.sorter.failure_insights`
  (`mode_counts` + per-failed-row `{expected, predicted, mode,
  equiv_recovered, reasoning}`) and per-row `failure_mode`; failure modes:
  `function_over_form` (doc_type miss), `other_fallback`, `equivalent_family`
  (recovered by equivalence), `family_confusion`.
- `experiment_markdown()` in `src/experiment_log.py` renders each section as
  tables: metadata, data source, parameters, tokens, scores + breakdowns,
  per-document results, document × field scoring matrices, factuality audit,
  CUAD category presence, confusion matrices, model outputs, per-class
  subtype accuracy, failed-classification insights.
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
  (`src/prompts.py`); the version key IS the experiment identity. NEVER edit
  a prompt string after it has run — a changed prompt needs a new version
  key. Derived versions (v8/v9/v10/v11 style `.replace()` on a prior
  constant) are fine as long as the base string is untouched.
- **New doc classes**: add a `doc_classes:` entry in
  `config/taxonomy.yaml` (key, label, schema, specialist, field_types) AND a
  matching schema + specialist in `agents/specialist_agents.py` (and a prompt
  in `src/prompts.py`).
- **New eval runners**: mirror `run_subtype_eval.py` / `run_chained_eval.py`
  (same flags, `main_with_args`, Braintrust composite scoring, manifest,
  experiment-log append) and add a smoke test.
- **Never commit** real keys: `.env`, `braintrust.env`, `*.env.local` are
  gitignored; use the `.example` files.
- **Never edit `reports/experiment_log.md` by hand** — regenerate it.

## Testing rules

- All tests must be network-free (mocked LLM calls, tmp Braintrust config).
  Check `tests/conftest.py` for shared fixtures.
- New eval logic → add a smoke test (see `test_extraction_eval_smoke.py`,
  `test_chained_eval_smoke.py`, `test_subtype_eval_smoke.py`,
  `test_eval_loop_smoke.py`) that runs the runner's `main_with_args` with
  mocked agents/datasets.
- New agent behavior → unit tests: `test_sorter_agent.py` (prompt wiring,
  option-list ↔ schema-enum equality, subtype normalization + equivalence,
  head+tail truncation), `test_judge_agent.py` (steps, choices, reasoning,
  scoring for all three judge dimensions).
- New scoring behavior → unit tests in `test_field_scoring.py` /
  `test_extraction_normalization.py`.
- New Langfuse mirror tooling → unit tests in `test_annotation_queue.py`
  (network-free: a fake Langfuse API stand-in covers selection, idempotency,
  and CLI wiring of `run_annotation_queue.py`).
- New streamer parsing → `test_cuad_streamer.py` /
  `test_legalbench_streamer.py` / `test_streamers.py`.
- Run the full suite before committing: `python -m pytest tests/ -q`
  (currently 193 tests, all passing).

## Gotchas

- **Manifest resume**: `--manifest` checkpoints carry a header that must
  match the rerun's metadata exactly (dataset fingerprint, model, prompt
  version); a mismatch makes the resume invalid by design. Cached rows
  predating a scorer change must NOT be resumed — use a fresh manifest.
- **Manifest-replayed rows carry no usage** — token/cost summaries count only
  rows with usage (`rows_with_usage`).
- **Braintrust experiment naming**: re-running the same experiment name
  creates a SUFFIXED experiment (`-a1b2c3d4`) instead of overwriting; the
  name-suffixed experiment holds the newer run. Fetch experiments by
  `created` order when backfilling.
- **Same-sample comparisons only**: accuracy deltas across different samples
  are meaningless (the 50-doc and 195-doc subtype runs are NOT comparable;
  the 5-doc chained sample is the controlled A/B surface).
- **Vision mode** sends ALL pages of each PDF in one call by default
  (`--vision-pages all`); `first` is for cheap pilots.
- **The sorter subtypes**: the contract subtype is normalized against the
  CUAD folder names (see `CONTRACT_SUBTYPES` in `agents/sorter_agent.py`).
  Hybrids ("distribution and development agreement") can plausibly be either —
  that's what `subtype_accuracy_equiv` and the confusion matrix are for.
  The prompt option list MUST equal the schema enum (enforced by a test).
- **`braintrust.integrations.langchain.setup_langchain()`** must be called
  before any model call or the experiment rows won't carry nested spans.
- **reasoning_effort**: the SORTER defaults to `medium` (25 near-synonymous
  families need deliberation — verified +4.6pp strict on the 200-doc sample);
  the EXTRACTOR defaults to `none` — thinking models burn the whole token
  budget on reasoning otherwise. Flags: `--reasoning-effort` (subtype /
  extraction) and `--sorter-reasoning-effort` (chained).
- **max_tokens**: extraction of 50+ verbatim clauses exceeds 16k tokens —
  chained default is 32768; a truncated JSON zeroes the row.
- **Head+tail truncation**: past `--max-input-chars` the input keeps the
  opening 60% + closing 40% (`TRUNCATION_TAIL_FRACTION`); deal-critical
  sections live in the tail. `contracts_specialist_v9+` scan both sides of
  the truncation marker.
- **Extractor scope (v10/v11)**: `key_obligations` is scoped to the CUAD
  restriction/covenant families (the GT spans — mean 7.4, max 22 items);
  general operative duties are NOT expected items. Output cleanliness
  (2-12 items, `verified_precision` 1.0) beats raw recall on this partial-GT
  task.
- **Reports that fetch Braintrust** (`report_generator.py`,
  `confusion_matrix.py`) need `BRAINTRUST_API_KEY`; the manifest/log
  reporting paths are fully offline.
- **CUAD ground truth is type-aware**: expected fields derive from the
  contract's CUAD folder via `build_expected_fields`; don't assume all 41
  categories apply to every document.
- **Packaging**: the layout (`llm-mailroom/src/{agents,config,...}` with `src/` on the
  import path) is what llm-mailroom imports; after adding a new module, confirm it is covered by
  `pip install -e .` (setuptools `packages` list) and the out-of-repo import
  still works.

## Skills (all agents)

Project skills under `.opencode/skills/` are available to EVERY agent in this
repo (opencode auto-loads `SKILL.md` per skill; `allowed-tools` frontmatter
grants tool access when loaded):

- **langfuse** (from github.com/langfuse/skills) — CLI-based Langfuse API
  access, docs retrieval, prompt migration, trace debugging, evaluation
  setup. Consult before touching Langfuse data (queries, score configs,
  prompts, dashboards); the repo's own integration is the
  `run_langfuse_*_eval.py` mirror + `src/langfuse_tracing.py`.
- **langchain-\*** (from github.com/langchain-ai/langchain-skills) —
  `langchain-fundamentals` (create_agent, tools, middleware),
  `langchain-python-quickstart`, `langchain-dependencies` (version pinning),
  `langchain-middleware` (callbacks/instrumentation/HITL), `langchain-rag`.
- **langgraph-\*** (same upstream) — `langgraph-fundamentals` (StateGraph,
  nodes, edges, Command/Send, streaming), `langgraph-python-quickstart`,
  `langgraph-cli`, `langgraph-persistence` (checkpointers — llm-mailroom uses
  SqliteSaver), `langgraph-human-in-the-loop` (review/interrupt nodes).
- **ecosystem-primer** — how LangChain/LangGraph/LangSmith fit together.
- **eval-engineering** — Harbor-style eval design references (task design,
  verifier design, harness, multi-turn simulation) — complementary to this
  repo's own deterministic eval loop.

The agents under test and the llm-mailroom pipeline under evaluation are
built on LangChain + LangGraph — invoke the matching skill before writing or
changing any agent/graph code.

## Docs & READMEs

- Per-directory READMEs are the map: `src/README.md`, `agents/README.md`,
  `config/README.md`, `scripts/README.md`, `tests/README.md`,
  `reports/README.md`, `docs/README.md` (site), plus the root `README.md` —
  keep them current when the layout or a module's contract changes.
- The project **wiki** is version-controlled in `wiki/` (Home,
  Getting-Started, Architecture, Eval-Runners, Experiment-Log, Scoring, Site,
  Release-Process, Taxonomy, FAQ) and pushed to the public GitHub wiki with
  `./wiki/sync-wiki.sh` — run it after wiki edits and after major releases.
  The wiki is NOT a mirror of docs/; each lives its own life.

## Research memos

`memos/*.md` are the archived research memoranda — key findings from
experimental runs and prompt iterations, written for collaborators and
presentation. Format: **Research question** opener, **Companions** links,
`## Answer, Response, + Summary of Results` with a **Short answer**, data
tables (with same-surface identity + bootstrap CIs where applicable), an
`### Interpretation` numbered list, `*Sources:*`, and a closing
`## What questions or uncertainties remain?`. The site ships them under the
**memos** tab (`build_site.py` emits `docs/data/memos.json`; the viewer
renders the markdown subset). Add a memo in the same commit as the finding
it archives.

## Issue & PR templates

`.github/ISSUE_TEMPLATE/` (bug_report, feature_request, experiment_report +
config.yml contact links) and `.github/PULL_REQUEST_TEMPLATE/pull_request.yml`
are YAML forms enforcing this repo's discipline: same-surface identity on
every bug/experiment report, the [Unreleased]-in-the-same-commit changelog
rule, derived-artifact regeneration, the render audit, and the
`release.py --check` gate.

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

# Failure insights from the last subtype run
python - <<'PY'
import json
for line in open("reports/experiment_log.jsonl"):
    r = json.loads(line)
    if r["task"] != "subtype_classification":
        continue
    fi = r["scores"]["sorter"].get("failure_insights") or {}
    print(r["experiment_name"], r["timestamp"], fi.get("mode_counts"), "failed:", fi.get("n_failed"))
PY

# Import the agents from outside the repo (llm-mailroom pattern)
pip install -e . && python -c "from agents.sorter_agent import SorterAgent; from agents.judge_agent import JudgeAgent"
```
