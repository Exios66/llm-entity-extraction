# Changelog

All notable changes to **llm-entity-extraction** are cataloged here in
[semantic version](https://semver.org/) order. Every significant milestone is
tagged `vX.Y.Z`; each version maps to a single commit, so the changelog is a
history of the repository's tags. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v0.11.0] - 2026-08-10

### Added
- **Sorter-only subtype evaluation** (`scripts/eval/run_subtype_eval.py`) — one
  sorter call per PDF; strict + family-level (`subtype_accuracy_equiv`)
  scoring, per-subtype accuracy, confusion matrix, resumable manifest,
  `--stratified N` for even, class-representative sampling (200-doc run over
  the full 510-contract corpus: 8 docs per subtype × 25).
- **Subtype equivalence scoring** — `SUBTYPE_EQUIVALENCES` +
  `equivalent_subtypes()`: reseller↔distributor, maintenance↔license,
  development↔license, affiliate↔joint_venture count as correct routing
  (strict accuracy stays the discriminating tracker).
- **Sorter medium reasoning** — `SorterAgent` defaults to
  `reasoning_effort="medium"` (verified: 95→483 completion tokens vs `none` +
  4.6pp strict on the same 195-doc stratified sample); the eval runners
  expose `--reasoning-effort` / `--sorter-reasoning-effort` and stamp it in
  Braintrust experiment metadata.
- **Sorter prompts v4/v5** — the option list is now the COMPLETE, precise set
  of valid keys (25 families + `other`, matching the schema enum exactly —
  enforced by a wiring test over every CUAD folder); v5's `other`-guard fixes
  v4's over-caution (title-obvious contracts → `other` regressions).
- **Chained eval subtype-focus** — the chained runner now calls
  `classify_json(..., subtype_focus=True)`: the sorter is explicitly tasked
  with sorting each document into its contract subtype (all chained rows are
  contracts), so its scores measure the subtype task, not a doc-type gate.
- **Contracts specialist v10/v11** — data-scoped extraction from the full
  510-doc corpus: the GT `key_obligations` spans are exactly the CUAD
  restriction/covenant families (mean 7.4, max 22 items). v10 scoped
  `key_obligations` to those families (overproduction 21-58 → 2-6 items);
  v11 adds section-by-section family exhaustiveness — measured best overall
  (chained 5-doc sample: 0.906, obligations 2-12, `verified_precision` 1.0).
- **Post-hoc judge reviews** (`scripts/reporting/judge_experiment.py`) — the
  offline JudgeAgent audits every failed classification against the source
  document; judgments append to `data/judgments/<experiment>.jsonl` and the
  markdown log renders a **Judge agent review** section (judgment counts +
  per-row verdicts with the judge's reasoning). 31 judgments logged on the
  v4 195-doc run.
- **Failure-insights logging** — the subtype runner now stores full reasoning
  (4000 chars) on failed rows + per-row `failure_mode`
  (`function_over_form` / `other_fallback` / `equivalent_family` /
  `family_confusion`) + `scores.sorter.failure_insights`, rendered as a
  failed-classification insights section in the markdown log.
- **Backfill script** (`scripts/reporting/backfill_subtype_reasoning.py`) —
  one-time enrichment of the 5 historical subtype records: failure modes
  derived and full reasoning recovered from the Braintrust LLM spans
  (documented append-only exception; the v4 record's 139 manifest-cached rows
  have no spans and keep their 500-char excerpts).
- **Packaging** — `pyproject.toml` + `config/__init__.py`: `pip install -e .`
  exposes `agents`/`src`/`config` (taxonomy.yaml included) so the LangChain
  agents import and run inside the llm-mailroom LangGraph architecture;
  verified by an out-of-repo import test.
- **Judge agent test suite** (`tests/test_judge_agent.py`, 14 tests) — the
  evaluator's steps, choices, reasoning passthrough, and scoring fallbacks
  for all three dimensions.
- **Head + tail truncation window** (`BaseAgent.truncate_input`),
  `contracts_specialist_v9` (scan both sides of the marker), `--text-only`
  CUAD streamer mode, and wiring/option-list/renderer tests. Test count 194.

### Changed
- Chained eval: sorter reasoning flag wired through; sorter explicitly tasked
  with subtype sorting; `--max-tokens` default 32768.
- 200-doc stratified A/B (same 195 docs, seed 42): v3-none 0.7897 →
  v3-medium 0.8359 strict (+4.6pp — medium reasoning helps); v4 0.8103
  (option-list precision, over-cautious); the earlier "regression" vs the
  50-doc run (0.84/0.94) was sample composition (50-run: 5/8
  equivalence-recoverable misses; 200-run: 4/32), not the enhancements.
- AGENTS.md rewritten with the full experimental workflow, run→log→release
  lifecycle, configurations (reasoning, truncation, equivalence), and
  release-process steps; README documents packaging, the subtype eval, judge
  reviews, and the new prompt versions.

## [v0.10.0] - 2026-08-09

### Added
- `scripts/datasets/download_cuad_pdfs.py` — download the FULL CUAD v1 corpus
  (all 510 contract PDFs + `CUAD_v1.json` clause QA annotations) into a local
  subdirectory (`data/cuad_pdfs/` default), preserving the CUAD folder
  structure so `category_of()` still works locally. Resumable (existing
  non-empty files are skipped), `--limit`, `--category`, `--out-dir`,
  `--skip-json`, `--overwrite`, `--dry-run`. Complements the streaming
  `stream_cuad_to_bt.py`: keeps the PDFs on disk for `--pdf-dir` evals.
- `.venv` setup with `sentence-transformers` (torch-backed) — the semantic
  embedding rescue now runs the LOCAL `all-MiniLM-L6-v2` model (free, fast,
  offline, reproducible) with the OpenRouter `text-embedding-3-small`
  fallback verified working end-to-end when the local model is unavailable.
- **Sorter prompt v3** (`sorter_v3`) — hybrid-agreement development
  preference: when one named family is development AND development machinery
  is present (development plan, milestones, joint R&D committee, development
  funding), development wins over the commercial family (matches the CUAD
  corpus filing convention), and two-family hybrids are capped at 0.85
  confidence with the runner-up named. Fixes the last sorter subtype error:
  "Distribution and Development Agreement" → development (was distributor).
- **Contracts specialist prompts v6–v8** (`contracts_specialist_v6/v7/v8`) —
  v6 added the term-length definition guard (never answer with a defined
  term's definition — extract the agreement's own Term clause), per-clause
  key_obligations granularity, and truncated-tail governing-law scanning.
  Chained A/B showed v6's granularity rule fragmented single clauses into
  per-subsection micro-items (eDiets key_obligations 0.92 → 0.69, lost the
  "Minimum Commitment" GT span); v7's clause-complete counter-fix blew the
  16k-token output budget on a 122k-char agreement (JSON truncated, row
  scored 0.0). **v8 is the empirically validated synthesis**: v5's
  sentence-level granularity restored verbatim, keeping ONLY the two v6 rules
  that survived (term-length definition guard + truncated-tail governing
  law).
- `run_chained_eval.py` default `--max-tokens` raised 16384 → 32768 — full
  verbatim extraction of 50+ clauses on long agreements exceeds 16k tokens,
  which truncated the JSON and zeroed rows.

### Changed
- **Embedding rescue guard** (`src/field_scoring.py`, `_with_embedding_rescue`):
  empty/whitespace predictions or labels are never rescued by embeddings — a
  blank answer stays a miss. Previously an empty prediction could be inflated
  to ~0.45 by cosine similarity to any text once a real embedder was
  available; the bug only surfaced when the local sentence-transformers route
  became active (the OpenRouter fallback silently failed under the fake test
  key). Test suite still fully network-free, 183 tests passing.
- **Chained eval post-mortem (v2+v5 vs v3+v8, same 5-doc sample, seed 42)**:
  sorter subtype accuracy 0.8 → **1.0** (the Ritter hybrid fix, confidence
  correctly capped at 0.85); extractor overall 0.9165 → 0.8933, with the
  entire delta coming from the Phasebio 292k-char agreement whose ground-truth
  governing law (char 276k), term clause (char 196k), cap-on-liability
  (char 283k), and non-compete (char 109k) all sit beyond the 100k input cap —
  a pipeline truncation limit, not a prompt failure (all extractions remain
  100% verified, zero hallucinations). eDiets key_obligations varies 0.69–0.92
  run-to-run on identical prompt semantics (51 items, ±2 GT-span matches) —
  stochastic, not prompt-driven.
- `README.md` — setup documents the `.venv` + optional `sentence-transformers`
  install and both embedding routes; the corpus-sync section documents
  `download_cuad_pdfs.py`; layout adds the new streamer; prompt table lists
  `sorter_v3` and `contracts_specialist_v6/v7/v8`; test count fixed to 183 in
  the layout tree.

## [v0.9.0] - 2026-08-09

### Added
- `CHANGELOG.md` — full semantic version history (this file).
- `SCORING.md` — a complete scoring & metrics reference: every scorer, every
  metric, every formula (classification, binary, multiclass, field-type-aware
  content scoring, factuality audit, chained stage trackers, A/B deltas).
- Version tags `v0.1.0` … `v0.8.0` on every prior milestone commit, plus this
  release's `v0.9.0`.

### Changed
- `README.md` links `SCORING.md` and `CHANGELOG.md` from the docs section and
  updates the test count to 183.
- `AGENTS.md` points to `SCORING.md` as the canonical scorer documentation and
  updates the test count to 183.
- `reports/extraction_v2.md` and `reports/experiment_log.md` regenerated to
  match the current code state (no stale artifacts).

## [v0.8.0] - 2026-08-09

### Added
- `AGENTS.md` — comprehensive working guide for AI agents and contributors:
  setup, command cheatsheet, architecture & data flow, module map, scoring
  model rules, experiment-log mechanics, code conventions, testing rules,
  gotchas, useful one-liners.
- Three new unit tests in `tests/test_experiment_log.py` verifying the
  markdown renderer: score tables + per-field matrices, expected-vs-predicted
  confusion matrices, and `render_full_log` index/sections. Test count 183.

## [v0.7.0] - 2026-08-09

### Added
- `scripts/reporting/render_experiment_log.py` — CLI that rebuilds the whole
  human-readable experiment log from the append-only JSONL source of truth
  (title, experiment index table, one fully expanded section per run;
  `--dry-run` prints instead of writing).
- Rich markdown rendering in `src/experiment_log.py` (`experiment_markdown`,
  `render_full_log`): every section rendered as tables — run metadata, data
  source, parameters, per-stage token usage, scores + per-field breakdowns,
  per-document results, document × field scoring matrices with mean column,
  entity-list F1 matrices, aggregated factuality audit, CUAD category
  presence, expected × predicted confusion matrices (classification and sorter
  contract-subtype), sorter outputs, and the model's raw predicted
  extractions per document. No more raw JSON dumps.
- Extraction eval now persists the specialist's raw `predicted` extraction in
  the experiment log (`scripts/eval/run_extraction_eval.py`), so logged
  records carry outputs, not just scores.

### Changed
- `README.md` fully rewritten to match the repository's current state.
- `reports/experiment_log.md` regenerated with the new renderer.

## [v0.6.0] - 2026-08-09

### Added
- **CUAD type-aware ground truth** (`src/cuad_ground_truth.py`): the full
  41-category CUAD v1 catalog (9 string-answer, 32 YES/NO), grouped into
  clause families; expected fields derived per contract TYPE (CUAD folder) via
  `build_expected_fields` / `build_presence_expectations` — a document's
  expectations only cover categories applicable to its type
  (`ground_truth_mode: cuad_type_aware`).
- **Factuality guard** in `src/field_scoring.py`: every predicted list item
  must match a ground-truth label OR be grounded in the source document
  (token coverage ≥ 0.7; dates grounded via date-candidate parsing in any
  format); ungrounded items are hallucinations driving `verified_precision`
  down / `hallucination_rate` up. Scalar fields audited too.
- **CUAD category presence scoring** (`score_category_presence`): binary
  YES/NO conformance per presence-type category, with per-category detail.
- `scripts/eval/run_chained_eval.py` — end-to-end pipeline eval: sorter
  (doc_type + contract subtype) → contracts specialist, per-stage token
  usage and scores, subtype confusion matrix, resumable manifest.
- Specialist prompts v3–v5 (`contracts_specialist_v3/v4/v5`) and sorter
  prompt v2; chained smoke tests; expanded field-scoring, ground-truth, and
  sorter tests. Test count 180.
- `partial_gt_fields` (ground-truth coverage instead of F1) and
  `containment_fields` (expected-within-predicted containment) scoring modes
  in the taxonomy-driven scorer.

### Changed
- Extraction eval registers the factuality and category-presence trackers
  (`overall_verified_precision`, `category_presence`) in the default tracker
  set; per-row logs include the entity-list audit and presence detail.
- `score_extraction_manifest.py` post-hoc report extended with category
  presence, factuality audit, and per-document scoring matrices.
- First experiment records appended to `reports/experiment_log.jsonl` / `.md`
  (7 runs: specialist v2–v3 extraction, type-aware v3 runs, chained v1+v4 /
  v2+v5).

## [v0.5.0] - 2026-08-09

### Added
- **Repository experiment log** (`src/experiment_log.py`): every eval run
  appends ONE JSON record to `reports/experiment_log.jsonl` (append-only) plus
  a human-readable section to `reports/experiment_log.md` — git snapshot,
  model, prompt version, data source + fingerprint, all run parameters, token
  usage/cost, all scores, per-row results. Paths overridable via
  `EXPERIMENT_LOG_PATH` / `EXPERIMENT_LOG_MD_PATH` / `--experiment-log`.
- Logging wired into `run_classification_eval.py` and `run_extraction_eval.py`
  (each arm of `evaluate_prompt_version.py` included).
- `tests/test_experiment_log.py` (append-only semantics, token aggregation,
  markdown sections, env-overridable paths, git snapshot).

## [v0.4.0] - 2026-08-09

### Added
- **Composite-output extraction scoring** in `run_extraction_eval.py`: the
  task computes every score locally (deterministic field-type-aware content
  scoring) and returns a composite; registered Braintrust scorers
  (`overall_extraction_score`, `field_presence`, `schema_valid`) are trivial
  lookups on it — nothing recomputed on the Braintrust side, so UI, manifest,
  and log always agree.
- **Embedding rescue**: `name`/`free_text` fields and list elements consult
  sentence-transformers cosine similarity (OpenRouter embeddings fallback)
  when the string score is ambiguous (< 0.7), never overriding a confident
  string-level match.
- `--bt-scores none|overall|full` (with per-field + entity-list F1 trackers),
  `--judge` ambiguous-band LLM pass, and post-hoc offline reporting via
  `score_extraction_manifest.py` (`reports/extraction_v2.md`).
- Extraction smoke tests updated for the composite contract.

## [v0.3.0] - 2026-08-09

### Added
- **Vision classification pipeline**: `stream_cuad_to_bt.py` renders every
  page of the 510 real CUAD contract PDFs to 1024×1024 grayscale PNGs and
  uploads them as image attachments (one row per PDF, all pages); the sorter
  classifies the complete page set in a single vision call
  (`sorter_vision_v0`, `--input-mode vision`, `--vision-pages all/first`,
  confidence-weighted page voting for local PDFs via `--pdf-dir`).
- **LegalBench dataset streamers**: `stream_legalbench_to_bt.py` (MAUD v1:
  139 full-text merger agreements + the 13,256-row per-question
  classification suite with embedded answer spaces) and
  `stream_legalbench_tasks_to_bt.py` (60+ classification tasks —
  `cuad_*`, `maud_*`, hearsay, etc. — one Braintrust dataset per task with
  `metadata.valid_classes`).
- **Task-mode classification**: `--prompt-mode task` with the
  `legalbench_task_v0` prompt answers LegalBench multi-class tasks against
  `--valid-classes`.
- **Field-type-aware content scorer** (`src/field_scoring.py`, first pass):
  `id`/`date`/`money`/`name`/`free_text`/`entity_list` (bipartite matching)
  with the taxonomy-driven `field_types` mapping and heuristic fallback.
- **CUAD ground truth mapping** (`src/cuad_ground_truth.py`, first pass) and
  the extraction eval runner (`run_extraction_eval.py`, initial).
- Vision + extraction smoke tests, streamer tests, field-scoring tests,
  page-voting tests, post-hoc scorer tests. Test count 144.

## [v0.2.0] - 2026-08-09

### Added
- **LangChain agents** (`agents/`): `BaseAgent` (ChatOpenAI on OpenRouter,
  structured JSON output, vision calls, `_last_usage` token capture),
  `SorterAgent` (text + image classification), per-doc-class specialists with
  shared schemas (`specialist_agents.py`), and the offline `JudgeAgent`
  (classification/completeness/correctness).
- **Versioned prompt registry** (`src/prompts.py`): `PROMPT_VERSIONS` with
  `get_prompt` / `list_prompts`; initial versions for the sorter,
  specialists, boss/reporter, judges, and PDF transcriber.
- **Eval runners**: `run_classification_eval.py` (one prompt per experiment,
  text mode, exact_match/failure/cost scorers, resumable manifests),
  `run_binary_class_eval.py` (precision/recall/F1 on a binary question),
  `run_multiclass_eval.py` (per-class + macro accuracy), and
  `evaluate_prompt_version.py` (A/B with delta summary and `--compare-only`).
- **Dataset streamers** (initial): `stream_cuad_to_bt.py` (CUAD v1) and
  `stream_legalbench_to_bt.py` (MAUD v1) uploading full-text rows.
- **Reporting**: `report_generator.py` (markdown experiment report with
  per-class accuracy, confusion matrix, misclassification ledger) and
  `confusion_matrix.py` (PNG heatmap + CSV from a Braintrust experiment).
- `config/taxonomy.yaml` (doc classes, field types, agent→model mapping,
  confidence thresholds, cost models), `src/braintrust_config.py`,
  `src/braintrust_utils.py`, `src/env_utils.py`, `src/evaluation.py`
  (fingerprints + `ManifestStore`), `src/classifier.py`, `src/image_utils.py`,
  `src/llm_chain.py`, `src/openrouter_utils.py`.
- `.env.example` / `braintrust.env.example`, `.gitignore`, `requirements.txt`,
  first test suite (79 tests).

## [v0.1.0] - 2026-08-09

### Added
- Repository bootstrap: `.gitattributes`, initial `README.md` scaffold.

[Unreleased]: https://github.com/Exios66/llm-entity-extraction
[v0.11.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.11.0
[v0.10.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.10.0
[v0.9.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.9.0
[v0.8.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.8.0
[v0.7.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.7.0
[v0.6.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.6.0
[v0.5.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.5.0
[v0.4.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.4.0
[v0.3.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.3.0
[v0.2.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.2.0
[v0.1.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.1.0
