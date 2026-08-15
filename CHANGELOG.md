# Changelog

All notable changes to **llm-entity-extraction** are cataloged here in
[semantic version](https://semver.org/) order. Every significant milestone is
tagged `vX.Y.Z`; each version maps to a single commit, so the changelog is a
history of the repository's tags. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **`sorter_v10` + `sorter_v11` — marketing title-wins arm (KANBAN-013)** —
  the v9 close-out's "1-off long tail" plateau reading is superseded by
  cluster analysis: the **marketing cell ran 0.5/10 (243-doc) and 7/17
  (full-509) — the worst family accuracy on both surfaces, unchanged since
  v6** (v8/v9 both 10/17), all fails being marketing-titled docs
  re-classified by operative machinery (Monsanto→agency, Zounds→
  manufacturing, Principal→endorsement = rule-6 over-fire, Pacira→
  distributor, Todos→reseller, Vertex→JV, Audible→co_branding). **v10** =
  v9 + rule 26 MARKETING TITLE WINS (the R23/R24 title-wins doctrine
  mirrored to marketing; carve-outs: license-primary titles per annex
  inheritance, operational-service families transportation/hosting);
  **v11** = v10 + rule 27 AFFILIATE IS NOT MARKETING (boundary for the
  measured rule-26 over-fire: Cybergy + SteelVault, content-titled
  "Marketing Affiliate Agreement"). Same-surface 243-doc A/B (fp
  fb9f939d, seed 42, temp 0.1): **champion rerun noise floor = ±1 doc
  (0.9259 → 0.9300); v10 0.9342 and v11 0.9342 strict / 0.9424 equiv —
  delta +0.4pp inside the band (paired bootstrap CI [−0.0247, +0.0165],
  P(Δ≤0)=0.710) → logic repair, not a claimed win**. Rule-driven
  accounting: 4 deterministic recoveries (Monsanto, Principal, Todos,
  Dynamex), 2 affiliate restorations, 1 R27-wording regression (LinkPlus,
  equiv-recovered via affiliate↔joint_venture); **marketing cell 0.5 → 0.8
  at 243**. Banked lessons for the next arm (KANBAN-023): strategic_alliance
  title-wins (5 fails @509, 0-risk counterfactual), cooperation-title is
  collaboration (3 fails), rule-21 inversion mechanism. Memo
  `memos/sorter_v10_v11.md`; 357 tests green. (One append-only artifact: the
  first v11 launch hit a transient OpenRouter weekly-limit 403 and logged a
  strict-0.0 record; the rerun 15 min later succeeded — both records remain
  in the log.)
- **`contracts_specialist_v31` — token-efficiency refactor (KANBAN-021)** —
  same operative rules as v30, compressed: **−8.0% (2,679 chars; 8,377 →
  7,700 system tokens)** with every constraint preserved (28 family-catalog
  entries, multi-item family-section rule, CoC-definition carve-out,
  additive re-scan, chunk-mode scalar quoting, term_length opener
  discipline, reasoning trace, formats). The v23 worked-example block
  (2,810 chars of verbatim quotes) is distilled into one-line
  family-boundary guidance — the lesson, not the text — and the
  EXHAUSTIVENESS/RE-SCAN/VERBATIM/SIZE-CALIBRATION boilerplate is merged
  with its overlapping neighbours. Prompt-level compression verified (349
  tests green incl. `test_contracts_v31_token_efficiency_refactor`);
  **accuracy A/B BLOCKED by the OpenRouter weekly key limit (403)** — v28@510
  completed 217/509 rows, v31@510 0/509; resumes after the key reset via
  the resumable manifests (~$0.19/run, `mailroom-cuad-contracts-full`
  surface). Memo `memos/contracts_specialist_v31.md` (v22→v31 token
  audit: 6,309 → 8,377 → 7,700). The full-corpus v28 baseline remains
  incomplete — the partial 0.8558 (217 docs) is a biased subset, not a
  full-corpus number.
- **LegalBench HEARSAY task fully wired (KANBAN-022)** — the half-done sync
  completed end-to-end: `mailroom-lb-hearsay` synced from the actual
  LegalBench task data (binary Yes/No, 5 train rows / 95 test, 5 slices —
  statement made in-court, non-assertive conduct, standard hearsay,
  non-verbal hearsay, not-introduced-to-prove-truth; CC BY 4.0, Neel Guha),
  classes manifest written (`data/legalbench_classes.jsonl`), Braintrust
  task-mode eval path verified (`run_classification_eval.py --prompt-mode
  task --valid-classes Yes,No`), and **`run_langfuse_classification_eval.py`
  gains `--prompt-mode task`** (the mirror previously hardcoded the sorter
  doc-type path) — LegalBench tasks now trace into the llm-dojo Langfuse
  project with one `legalbench_task` observation per row carrying
  exact_match/confidence; task mode requires `--valid-classes` and defaults
  the prompt to `legalbench_task_v0`; 3 new smoke tests + 3
  `_deterministic_record_id` tests.
- **`upload_text_dataset` now inserts rows with deterministic
  content-addressed ids** (`src/braintrust_utils.py
  _deterministic_record_id`) — Braintrust's `insert` otherwise assigns a
  fresh random UUID per call, so every streamer rerun APPENDED duplicate
  rows (observed: `mailroom-lb-hearsay` held 2×5 identical rows after a
  partial + rerun). Reruns now upsert in place as the streamer docstrings
  always promised. KANBAN-022.
- **Root README credits section** — LegalBench (NeurIPS 2023, CC BY 4.0),
  CUAD / The Atticus Project (NeurIPS 2021), MAUD (Zenodo), the GEPA
  framework (arXiv 2507.19457), and the LangChain/LangGraph/Braintrust/
  Langfuse stack. KANBAN-022.
- **LegalBench-task docs updated with the actual hearsay data** — README
  (sorter's two jobs, sync step 3, loop examples incl. the Langfuse task
  mode), AGENTS.md cheatsheet, wiki/Eval-Runners.md (classification task
  mode + Langfuse mirrors + datasets), scripts/README.md,
  `stream_legalbench_tasks_to_bt.py` docstring. KANBAN-022.
- **First hearsay benchmark (KANBAN-022 live run)** —
  `qwen3.7-flash_legalbench_task_v0` on `mailroom-lb-hearsay` (5 rows, 2 Yes
  / 3 No, one row per slice): **exact_match 1.0 (5/5), failure 0.0,
  per-class no 1.0 / yes 1.0** — run twice, identical results on both the
  Braintrust-named surface (`_usage` rerun, 3,441 tokens, ~$0.00024) and the
  llm-dojo Langfuse mirror (`_classification_langfuse_usage`, 3,276 tokens,
  ~$0.00022, 5 `legalbench_task_classification` traces with exact_match +
  confidence scores, verified in llm-dojo). Caveats: the OpenRouter key used
  had a fresh weekly budget; the Braintrust ORG is at its monthly
  log-bytes plan limit (`num_log_bytes_calendar_months`), so the experiment
  row data does NOT upload to Braintrust until billing is addressed — the
  repo experiment log records (source of truth) are complete either way.

### Fixed
- **`BaseAgent._call_llm` now captures usage/cost** (`agents/base_agent.py`)
  — the plain-text completion path (LegalBench `--prompt-mode task`
  answers, judge calls) previously returned the string through
  `StrOutputParser` and NEVER set `_last_usage`, so task-mode experiment
  records carried `tokens: 0` / `cost: 0`. Now reads usage_metadata +
  response cost from the raw AIMessage, mirroring the structured + vision
  paths; content blocks are joined for list-form AIMessage content. 2 new
  unit tests. KANBAN-022.

## [v0.18.0] - 2026-08-15

> v0.18.0 — contracts specialist v26-v30 (term_length containment, multi-item family-section rule +4.48pp, noise-floor follow-up arm), extraction runner chunking, GEPA prompt-engineer agent, slides post-mortem decks

### Changed
- **`contracts_specialist_v29` + `contracts_specialist_v30` — follow-up
  logic repairs (KANBAN-020 arm)** — the v28 residuals, resolved with a
  noise-floor control (identical-prompt rerun of the v28 champion on the
  same 50-doc chunked surface: **±0.03 overall band, ~12 docs move >±0.02
  per field** — the surface's resolution limit). Per-span sim-matrix diff
  on the 4 regressed docs: Ediets' Change-of-Control DEFINITION spans were
  suppressed by v28's "definitions are NEVER items" criterion — a
  rule-vs-rule contradiction with the v10 re-scan note ("the defined term
  itself"); **v29 adds the carve-out** (CoC-family definitions ARE items —
  Ediets recovers 0.692→0.769). **v30 patches CHUNK DUTY** (scalar fields
  keep their exact quoting rules in every chunk; prefix-only/null
  term_length with the clause visible is a miss — the chunked-v26 collapse
  mechanism: Ritter "five (5) years" only, Phasebio null). Both measure
  INSIDE the noise band (paired deltas −0.0264/−0.0382 vs the identical-
  prompt rerun's −0.0293) — shipped as unmeasured logic repairs; **v28
  remains the champion (re-validated vs v26: +0.0448, CI [+0.0087,
  +0.0891], P=0.004)**. Also resolved: renewal_terms dip = 1 doc (NOVO,
  quote-truncation variance); Gridiron `":"` = 1-off (fresh runs 1.0);
  LinkPlus/Innerscope/LegacyTechnology regressions = noise. Memo
  `memos/contracts_specialist_v30.md`.
- **`run_extraction_eval.py` gains `--chunked/--chunk-chars/
  --chunk-overlap`** (the Braintrust runner previously could NOT chunk) +
  a dry-run truncation-confound warning when unchunked + `chunked`/
  `n_chunks` audit fields per row (`_last_chunked`/`_last_n_chunks` on
  `_SpecialistBase`). KANBAN-020.
- **`.opencode/agents/prompt-engineer.md` now runs the full GEPA workflow**
  (arXiv 2507.19457 reflective prompt evolution): sample trajectories →
  natural-language reflection on failures (sim-matrix miss classification)
  → one-lesson mutations → same-surface A/B with the noise-floor control →
  Pareto-aware selection across score/cost/robustness with a candidate
  frontier and cross-candidate lesson combining; plus the chunked-surface
  discipline and the rule-contradiction check in every mutation. AGENTS.md
  agent section updated. KANBAN-020.
- **`contracts_specialist_v27` + `contracts_specialist_v28` — multi-item
  family-section rule (KANBAN-004 arm)** — the key_obligations span
  residual: pairwise-similarity classification of every miss on the 50-doc +
  sample5 surfaces showed ~60–70% of misses are NEAR (sim 0.35–0.59) —
  **wrong-span at sentence level inside multi-requirement family sections**
  (the model quotes ONE sentence per insurance/audit/license/ROFR section
  while the GT holds 3–10 distinct requirement sentences: Ritter emitted
  insurance-procurement but not primary-of-all-purposes/additional-insured;
  the audit section's 10 GT spans went ~0). v27 states the rule directly
  (a family section is MULTI-ITEM — each distinct requirement sentence is
  its own item); v28 sharpens it with the two trace lessons (definitional
  sentences — "any X Property or improvements thereto which are used…" —
  are NEVER items; the completion re-scan only ADDS items, never removes).
  Same-surface 50-doc chunked A/B (seed 42, qwen3.7-flash, current scorer):
  **v28 0.9228 vs v26 0.8780 overall (+4.48pp, bootstrap 95% CI [+0.0094,
  +0.0907], P(Δ≤0)=0.004)**; key_obligations +11.4pp (0.7606→0.8747, 20
  recovered vs 4 regressed docs — regressions are single-span losses on
  ≥0.85 docs, no new pattern); term_length +0.040; tokens +6.7%. Also
  documented: the sample5 A/B surface is truncation-confounded
  (`chunked=false` — Phasebio 0.125 unchunked vs 0.94 chunked) — pilot
  surfaces must use `--chunked` for key_obligations to be measurable.
  KANBAN-004, issue #3 closed.
- **`contracts_specialist_v26` — term_length containment fix (KANBAN-017
  arm)** — v24's canonical-duration-prefix rule made the model REPLACE the
  clause opener with the duration phrase (the CUAD ground-truth span IS the
  opener: Ediets "This Agreement will become effective as of the Effective
  Date and, unless sooner terminated pursuant to Sections 3.1" — containment
  1.0→0.3333). v25's additive-prefix wording + worked example recovered
  Ediets (containment 1.0) but leaked the example's sentence template into
  OTHER documents (Ritter/Phasebio quoted the example clause with the
  duration swapped in). **v26** keeps the additive prefix and forbids
  dropping the opener, shows opener variants to match THIS document's
  wording, and bans reusing the instructions' wording — no template
  leakage. Same-surface 5-doc A/B (seed 42): **v26 term_length 1.0000 and
  overall 0.9447 — best of the arm** (v23 0.9366, v24 0.9336, v25 0.9154);
  all three term_length docs containment 1.0. KANBAN-017.
> Extraction regression diagnostics (date/duration/money MAE + R² vs master labels, span-count drift, error decomposition), contracts specialist v24 reasoning trace + metrics-aligned formats, inter-agent workflow (AGENTS.md), full-corpus CUAD EDA, sorter v9 full-scale benchmark, annotation-queue status fix
### Added
- **`prompt-engineer` agent — the master diagnostic evaluator & prompt
  engineer** — new `.opencode/agents/prompt-engineer.md` (project agent,
  `mode: all`): its SOLE role is to review all traces, reasoning logic,
  failures, error messages, and results of every evaluated prompt and
  produce a stronger, refined, data-backed mutation (new `PROMPT_VERSIONS`
  key, never an edit to a run prompt). Encodes the repo's full iteration
  contract: the diagnose → root-cause → mutate → verify → land loop, the
  failure taxonomy (extraction: boundary-shift / abbreviation / wrong-span
  / hallucination / scope; sorter: `function_over_form` /
  `other_fallback` / `equivalent_family` / `family_confusion`),
  same-surface A/B discipline with bootstrap-CI verdicts and per-row
  recovered-vs-regressed checks, the **plateau/overfit doctrine** (rules
  for failure CLUSTERS not 1-off outliers, family-level generalization
  test, MAE/R² evidence floor on pair counts, cost-as-tradeoff), and
  board + CHANGELOG + memo close-out with proof. `AGENTS.md` gains the
  "Agents (this repo)" section documenting it alongside
  experiment-log-sync. KANBAN-018.


### Changed

## [v0.17.0] - 2026-08-15

### Changed
- **`ContractsSpecialist` extraction carries a full per-field reasoning
  trace** — `CONTRACTS_SCHEMA` gains a required `reasoning` object (leading
  the schema: `summary` + `entries[{field, evidence, section_ref}]`),
  produced BEFORE the extraction values are finalized; the chunked-merge
  unions reasoning entries across windows (dedupe by field, first-witness
  evidence wins, summaries joined) so the trace covers the whole document;
  `_evidence_confidence` excludes the meta field. New prompt
  `contracts_specialist_v24` (derived from v23, base untouched): the
  REASONING BEFORE OUTPUT duty + metrics-aligned format discipline —
  `term_length` leads with the canonical duration phrase ("two (2) years"),
  `contract_value` stays a plain currency phrase ("$2,000,000") so the
  date/duration/money regression diagnostics (MAE + R² vs master labels)
  can parse more predicted values (format alignment only — the master CSV
  never reaches the model). 5-doc same-surface A/B (seed 42):
  v24 0.9336 vs v23 0.9366 overall (noise), **key_obligations +10.2pp
  (0.5984→0.7006)**, reasoning trace on 5/5 rows both runs (schema-driven),
  tokens +2.5%; term_length containment dipped on 1 doc (leading-phrase
  quote trades containment credit for parseability — monitored in the next
  arm). 6 new network-free tests; 341 total green. KANBAN-016.
- **`AGENTS.md` board section restructured into the full inter-agent
  workflow** — "Agent message board & inter-agent workflow": session
  pre-flight protocol (board read → rule-4 sanity sweep → name check →
  announce intent), the six-phase task lifecycle (card-first → claim →
  in_progress-from-first-edit → communicate-during → verify → close with
  proof → finish protocol), the inter-agent communication framework
  (channel hierarchy with the board discussion log canonical, what-to-post-
  when table), and the anti-trampling protocol (one owner per card, card-
  owned files, **experiment-name reservation before any run** — Braintrust
  silently suffixes re-runs so a shared name is a silent collision — one
  run one owner, task-relation rule, conflict rule, no silent completion).
  GitHub issue sync formalized as §5. KANBAN-015.
### Added
- **Full-corpus EDA of the CUAD contracts dataset** — new
  `scripts/eda/explore_cuad.py` (Braintrust full-corpus text aligned 510/510
  to the CUAD titles, with local-txt / CUAD-context fallback) rendering
  `data/eda/report.md`, `data/eda/findings.md`, and `data/eda/figures/01`–`10`
  (subtype distribution, text-length hist + pipeline budget lines, category
  YES rates, category span load, spans/doc, filing families, per-subtype
  lengths, restriction co-occurrence heatmap, annotation density) — all
  git-tracked. Headline numbers: median 33,425 chars (mean 52,563, max
  338,211); 17.1% of contracts exceed the 90k-char chunk window and 9.4% a
  32k-token context; the extractor's `key_obligations` scope (31 of 41
  categories) averages 16.0 spans/doc (49 contracts null); Anti-Assignment +
  Change Of Control co-occur in 98% of the less-common docs; 131 contracts
  carry `[***]`-style redaction markers. KANBAN-014.
- **Extraction regression diagnostics — MAE + R² as tracked performance
  metrics** — new `src/metrics.py` (run-level `scores.diagnostics`:
  field-level error decomposition, raw list P/R/F1 macro+micro, date and
  duration MAE, and the **coefficient of determination** `date_r2` /
  `duration_r2` = `1 − SS_res/SS_tot` over predicted-vs-expected
  date/duration pairs, negative kept as a signal) + new
  `src/master_labels.py` (curated `master_clauses.csv` loader; preferred
  parse source for the expected values, raw CUAD clause text the fallback)
  + `--master-labels` flag / `MASTER_LABELS_CSV` env on the extraction
  runners (Braintrust + Langfuse mirror); `field_scoring.parse_date` public
  alias; GH Pages per-run breakdown surfaces the headline diagnostics.
  18 new network-free tests (`tests/test_metrics.py` + smoke coverage).
  KANBAN-015.
- **Diagnostics extended: money MAE + span-count drift + support sizes** —
  `src/metrics.py` gains `money_mae_usd`/`money_median_ae_usd` (+
  per-field buckets; `parse_money` public alias in `src/field_scoring.py`),
  `span_count_mae` / `span_count_signed_mean` (+ per-field buckets,
  `span_count_n_docs` — symmetric item-count error vs signed
  over/under-extraction direction over list fields), and evidence
  denominators `date_n_pairs` / `duration_n_pairs` / `money_n_pairs` on
  every MAE/R² row. 4 new network-free tests (30 in `tests/test_metrics.py`).
  KANBAN-015.
- **Run-level diagnostics rendered in the experiment log + site** — new
  `_diagnostics_lines()` in `src/experiment_log.py` renders
  `scores.diagnostics` as grouped markdown tables (list quality with
  macro+micro P/R/F1, regression error with MAE/R² + pair counts, span-count
  drift, field error decomposition); the generic nested-scores path now
  skips `diagnostics` (dedicated section only). The GH Pages run-detail view
  gains a **Run-level diagnostics card** (`docs/assets/site.js`
  `diagnosticsCard()` + `.diag-block` styles). Renderer test added
  (`test_experiment_markdown_renders_diagnostics_section`); site render
  audit green. KANBAN-015.
- **Scoring-method slide decks** — `docs/slides/` (7 decks + index): example
  inputs/outputs and concise scientific explanations of every scoring
  method (field-type scoring, entity-list bipartite matching + P/R/F1
  macro/micro, MAE/R² regression diagnostics with the master-labels ground
  truth, factuality audit, failure analysis, reading the experiment log) —
  written for parallel researchers without time for the full docs. Includes
  a REAL diagnostics block captured from a 2-doc pilot
  (`pilot_diag_v22_sample2`, seed 42, master labels CSV active: dates MAE 0 /
  R² 1.0; `key_obligations` 43 predicted vs 18 expected → span-count +10.5,
  raw precision 0.31 — a textbook over-extraction signal). KANBAN-015.
### Fixed
- **`run_annotation_queue.py status` unbounded trace scan** — `status` now
  honors `--since-days` (default 30, shared with `build`) when building the
  item metadata map; previously it scanned the full trace history
  (`list_extraction_traces(..., since=None)`), which stalled for minutes on
  the subtype task under Langfuse rate limits. `--session-contains` remains
  the way to scope either subcommand to one run family.
### Added
- **Sorter scale-up — v9 re-baseline + full-509 v8/v9 benchmark**: three
  cheap runs (~$0.25, 1213 classifications) settle the scale question.
  **v9 @ 509 = 0.9116 strict / 0.9194 equiv, beating v8 @ 509 (0.9018 /
  0.9096) by +0.98pp — the v6→v9 rule iterations hold at full scale.**
  The re-baseline (v9 @ 195 = 0.8872) settles the 0.95-era question: the
  0.9436-era v6 number lived on the OLDER corpus revision (fingerprint
  2e1fe4b7 vs fb9f939d) — the 0.95 target was revision-confounded.
  Sample-size behavior is non-monotonic but bounded (v9: 0.8872 → 0.9259
  → 0.9116 across 195/243/509); the full-set number is the stable
  estimate. Full matrix: `V16_PROPOSITION.md` §19.

## [v0.16.0] - 2026-08-13

### Added
- **`sorter_v9` — the title-wins A/B (v9 WINS, +2.88pp strict)**: three
  data-backed rules from the exact v8 residual — 23. PROMOTION TITLE WINS
  (COLOGUARD/CO-PROMOTION/PROMOTION AND DISTRIBUTION agreements are
  promotion despite marketing/distribution machinery), 24. OUTSOURCING
  TITLE WINS (outsourcing-titled docs are outsourcing even when the
  outsourced services ARE manufacturing), 25. CUSTOMIZATION SCHEDULES ARE
  MAINTENANCE (annex inheritance for customization schedules). Same-surface
  A/B (243-doc stratified, seed 42, qwen3.7-flash, medium, llm-dojo):
  **strict 0.8971 → 0.9259 (+2.88pp), equiv 0.9012 → 0.9259, 25 → 18
  fails; all three target clusters eliminated**. Cumulative v6→v9:
  **+5.8pp strict (0.8683 → 0.9259)**. The remaining 18 fails are a 1-off
  long tail (no cluster >2) — ~0.93 is the practical plateau on this
  corpus revision; 0.95 needs tail-sampling iterations or a re-baseline.
  Full record: `V16_PROPOSITION.md` §18.
- **`sorter_v8` — the development/IP clusters A/B (v8 WINS, +2.06pp
  strict)**: two data-backed rules from the exact 8 v7 failures —
  21. DEVELOPMENT VERSUS COLLABORATION, LICENSE, AND FRANCHISE STRUCTURES
  ("Collaborative Development" agreements are development; "Development
  Agreement" titles stay development when grants/franchise structures
  deliver the developed materials) and 22. INTELLECTUAL PROPERTY
  AGREEMENTS ARE ip (IP-titled docs are ip despite license/JV sections).
  Same-surface A/B (243-doc stratified, seed 42, qwen3.7-flash, medium,
  llm-dojo): **strict 0.8765 → 0.8971 (+2.06pp), equiv 0.8889 → 0.9012,
  30 → 25 fails; both target clusters eliminated** (development→
  collaboration/license/franchise 5 → 0, ip→license/joint_venture 3 → 0).
  Cumulative v6→v8: +2.9pp strict. Remaining: promotion-title→marketing
  (2), outsourcing→manufacturing (2), customization-schedule annex (1)
  plus a 1-off tail — v9 rules designed, 0.95 strict is a multi-iteration
  target on this corpus revision. Full record: `V16_PROPOSITION.md` §17.
- **`sorter_v7` — the final classification A/B (250-sample) — v7 WINS
  (+0.82pp strict)**: three data-backed rules targeting the v6 509-doc
  full-corpus fails (strict 0.9312, 35 fails): consortium O&M →
  maintenance (shared-infrastructure governance wrappers do not make an
  agreement a joint_venture), development-over-license (development
  machinery wins over license grants for the developed IP), and the
  promotion guard (promotion title/core is its own family, not marketing or
  distributor). Constant + `PROMPT_VERSIONS` entry + unit tests landed;
  **same-surface A/B (mailroom-cuad-contracts-full, stratified 250 seed 42
  → 243 docs, qwen3.7-flash, medium reasoning, llm-dojo): strict 0.8683 →
  0.8765 (+0.82pp), equiv 0.8807 → 0.8889 (+0.82pp); the promotion→
  marketing cluster (6 errors) is eliminated; 32 → 30 fails.** Caveat: the
  current corpus revision (fingerprint fb9f939d…) is harder than the
  revision behind the 195-doc 0.9436 runs (2e1fe4b7…) — v6 itself scores
  0.8683 on it, so the >0.95 strict target needs further iterations on the
  development-family and ip→license confusions. Full record:
  `V16_PROPOSITION.md` §16.
- **Research memos — site polish + visualization pass**: all 9 memos
  re-checked through the site's actual `renderMd` — fixed two rendering
  glitches (a `[***]` redaction marker inside a table cell that stole the
  next bold pair; a `\*` footnote escape), de-indented paragraph
  continuations (double-space artifacts), and added a standardized
  **scorecard table + Verdict callout** to each memo that lacked a top-line
  results display. All memos verified CLEAN through the render harness and
  the headless render audit.
- **Annotation-queue score-config support**: `run_annotation_queue.py` now
  lists and creates Langfuse score-configs
  (`get_or_create_annotation_config`) and auto-provisions the default
  annotation score-config id when `--score-config-ids` is not given;
  `FakeLangfuse` mocks the new GET/POST routes to exercise the flow in
  `tests/test_annotation_queue.py`.
- **Agent message board — the cross-repo Kanban + GitHub issue routing**:
  `MESSAGE_BOARD.md` is the living Kanban canvas shared by ALL agents
  across **llm-entity-extraction and llm-mailroom** — `backlog` /
  `in_progress` / `blocked` / `in_review` / `done` lanes with timestamps,
  an append-only discussion log, and an audit archive (finished cards are
  kept for auditability, never deleted). Governance codified in `AGENTS.md`
  (§"Agent message board — READ THIS FIRST, EVERY SESSION"):
  read-the-board-first every session; claim → Owner + timestamp; **work
  underway = `in_progress` immediately, never `backlog`** (the `git status`
  sanity check before every commit); the six-point completion & issue-close
  criteria (verified work + clean tree, CHANGELOG entry in the same commit,
  card archived with version/commit/result, timestamped closing discussion
  entry, issue closed in the same commit, no orphaned scope); releases
  sweep cards to the Archive in semver lockstep with `CHANGELOG.md`.
- **Kanban → GitHub issue routing**: critical / high-priority / cross-repo
  cards route to dedicated GitHub issues (label `kanban`) opened in the
  repo where the work lands — each synced card's `Issue` column carries the
  FULL markdown link to its own dedicated issue (`[#NNN](url)`),
  one card = one issue, issue body ↔ card never disagree about status,
  issues close in the same commit that archives their card. Board-only
  cards (small, single-session) skip issues.
- **Site — agent board tab**: the Kanban board renders read-only on the
  experiment-log site as the `#/board` view (`build_site.py` emits
  `docs/data/board.json`; docs/README documents it); card links jump to
  the corresponding GitHub issue.
### Removed
- **Per-run cost/usage telemetry from the site data**: `docs/data/` now
  omits embedded OpenRouter cost/usage objects (the `costs` meta block and
  per-run `cost`) — the site no longer displays detailed cost telemetry;
  the append-only `reports/experiment_log.jsonl` remains the record of
  tokens/cost per run.


### Added
- **`sorter_v9` — the title-wins A/B (v9 WINS, +2.88pp strict)**: three
  data-backed rules from the exact v8 residual — 23. PROMOTION TITLE WINS
  (COLOGUARD/CO-PROMOTION/PROMOTION AND DISTRIBUTION agreements are
  promotion despite marketing/distribution machinery), 24. OUTSOURCING
  TITLE WINS (outsourcing-titled docs are outsourcing even when the
  outsourced services ARE manufacturing), 25. CUSTOMIZATION SCHEDULES ARE
  MAINTENANCE (annex inheritance for customization schedules). Same-surface
  A/B (243-doc stratified, seed 42, qwen3.7-flash, medium, llm-dojo):
  **strict 0.8971 → 0.9259 (+2.88pp), equiv 0.9012 → 0.9259, 25 → 18
  fails; all three target clusters eliminated**. Cumulative v6→v9:
  **+5.8pp strict (0.8683 → 0.9259)**. The remaining 18 fails are a 1-off
  long tail (no cluster >2) — ~0.93 is the practical plateau on this
  corpus revision; 0.95 needs tail-sampling iterations or a re-baseline.
  Full record: `V16_PROPOSITION.md` §18.
- **`sorter_v8` — the development/IP clusters A/B (v8 WINS, +2.06pp
  strict)**: two data-backed rules from the exact 8 v7 failures —
  21. DEVELOPMENT VERSUS COLLABORATION, LICENSE, AND FRANCHISE STRUCTURES
  ("Collaborative Development" agreements are development; "Development
  Agreement" titles stay development when grants/franchise structures
  deliver the developed materials) and 22. INTELLECTUAL PROPERTY
  AGREEMENTS ARE ip (IP-titled docs are ip despite license/JV sections).
  Same-surface A/B (243-doc stratified, seed 42, qwen3.7-flash, medium,
  llm-dojo): **strict 0.8765 → 0.8971 (+2.06pp), equiv 0.8889 → 0.9012,
  30 → 25 fails; both target clusters eliminated** (development→
  collaboration/license/franchise 5 → 0, ip→license/joint_venture 3 → 0).
  Cumulative v6→v8: +2.9pp strict. Remaining: promotion-title→marketing
  (2), outsourcing→manufacturing (2), customization-schedule annex (1)
  plus a 1-off tail — v9 rules designed, 0.95 strict is a multi-iteration
  target on this corpus revision. Full record: `V16_PROPOSITION.md` §17.
- **`sorter_v7` — the final classification A/B (250-sample) — v7 WINS
  (+0.82pp strict)**: three data-backed rules targeting the v6 509-doc
  full-corpus fails (strict 0.9312, 35 fails): consortium O&M →
  maintenance (shared-infrastructure governance wrappers do not make an
  agreement a joint_venture), development-over-license (development
  machinery wins over license grants for the developed IP), and the
  promotion guard (promotion title/core is its own family, not marketing or
  distributor). Constant + `PROMPT_VERSIONS` entry + unit tests landed;
  **same-surface A/B (mailroom-cuad-contracts-full, stratified 250 seed 42
  → 243 docs, qwen3.7-flash, medium reasoning, llm-dojo): strict 0.8683 →
  0.8765 (+0.82pp), equiv 0.8807 → 0.8889 (+0.82pp); the promotion→
  marketing cluster (6 errors) is eliminated; 32 → 30 fails.** Caveat: the
  current corpus revision (fingerprint fb9f939d…) is harder than the
  revision behind the 195-doc 0.9436 runs (2e1fe4b7…) — v6 itself scores
  0.8683 on it, so the >0.95 strict target needs further iterations on the
  development-family and ip→license confusions. Full record:
  `V16_PROPOSITION.md` §16.
- **Research memos — site polish + visualization pass**: all 9 memos
  re-checked through the site's actual `renderMd` — fixed two rendering
  glitches (a `[***]` redaction marker inside a table cell that stole the
  next bold pair; a `\*` footnote escape), de-indented paragraph
  continuations (double-space artifacts), and added a standardized
  **scorecard table + Verdict callout** to each memo that lacked a top-line
  results display. All memos verified CLEAN through the render harness and
  the headless render audit.
- **Annotation-queue score-config support**: `run_annotation_queue.py` now
  lists and creates Langfuse score-configs
  (`get_or_create_annotation_config`) and auto-provisions the default
  annotation score-config id when `--score-config-ids` is not given;
  `FakeLangfuse` mocks the new GET/POST routes to exercise the flow in
  `tests/test_annotation_queue.py`.
- **Agent message board — the cross-repo Kanban + GitHub issue routing**:
  `MESSAGE_BOARD.md` is the living Kanban canvas shared by ALL agents
  across **llm-entity-extraction and llm-mailroom** — `backlog` /
  `in_progress` / `blocked` / `in_review` / `done` lanes with timestamps,
  an append-only discussion log, and an audit archive (finished cards are
  kept for auditability, never deleted). Governance codified in `AGENTS.md`
  (§"Agent message board — READ THIS FIRST, EVERY SESSION"):
  read-the-board-first every session; claim → Owner + timestamp; **work
  underway = `in_progress` immediately, never `backlog`** (the `git status`
  sanity check before every commit); the six-point completion & issue-close
  criteria (verified work + clean tree, CHANGELOG entry in the same commit,
  card archived with version/commit/result, timestamped closing discussion
  entry, issue closed in the same commit, no orphaned scope); releases
  sweep cards to the Archive in semver lockstep with `CHANGELOG.md`.
- **Kanban → GitHub issue routing**: critical / high-priority / cross-repo
  cards route to dedicated GitHub issues (label `kanban`) opened in the
  repo where the work lands — each synced card's `Issue` column carries the
  FULL markdown link to its own dedicated issue (`[#NNN](url)`),
  one card = one issue, issue body ↔ card never disagree about status,
  issues close in the same commit that archives their card. Board-only
  cards (small, single-session) skip issues.
- **Site — agent board tab**: the Kanban board renders read-only on the
  experiment-log site as the `#/board` view (`build_site.py` emits
  `docs/data/board.json`; docs/README documents it); card links jump to
  the corresponding GitHub issue.

### Removed
- **Per-run cost/usage telemetry from the site data**: `docs/data/` now
  omits embedded OpenRouter cost/usage objects (the `costs` meta block and
  per-run `cost`) — the site no longer displays detailed cost telemetry;
  the append-only `reports/experiment_log.jsonl` remains the record of
  tokens/cost per run.

## [v0.15.0] - 2026-08-12


### Added
- **`contracts_specialist_v23` × reasoning=max — the ko-justified arm**:
  ko **0.8510** (best since v19's 0.8840), 50/50 rows (zero parse errors —
  vs v19's 1/50), ellipsis 18.7% (lowest of the max arms), overall 0.9363
  (CI .899-.964), verified_precision 0.974, $0.103. Within 3.3pp of the
  v19 peak without its parse-error risk or −2.3pp overall penalty —
  v23×max is the ko-justified production arm; v22×none (overall 0.9512)
  remains the overall champion. Full matrix: `V16_PROPOSITION.md` §15.
- **Same-scorer re-scoring pipeline** (`scripts/reporting/rescore_manifests.py`):
  re-scores any extraction manifest with the CURRENT scorer (consistent
  no-embedding pass) — the historical records stay append-only while every
  comparison becomes immune to scorer drift. `--auto-50` covers the 50-doc
  seed-42 series (v13→v23); report in `reports/same_scorer_scores.json`.
  String-level insight: the v19+ arms lean harder on the embedding rescue
  (official ko 0.83-0.85 vs string-level 0.38-0.43). Network-free smoke
  tests in `tests/test_rescore_manifests.py`.
- **Langfuse prompt-store cleanup**: the pre-idempotency-fix duplicate v2
  prompt versions are gone — the version-scoped delete route 404s on this
  instance, but delete-all + re-sync left all 45 prompts with exactly one
  version (verified version=1) and clean production/latest labels.
- **0-ko docs postmortem (corrected)**: SPRINGBANK/QBIOMED/PelicanDelivers
  are NOT failures — their CUAD GT holds ZERO obligation-family spans
  (QBIOMED is a Schedule 13G joint filing), so ko is None (excluded), not
  0.0, in every arm. Earlier "0-ko" references were token-level-audit
  artifacts. One scope note: PelicanDelivers' 11 payment-milestone items
  are general payment duties the prompt excludes (harmless — no GT).
- **`contracts_specialist_v23` — worked-example set v2 (the residual-34
  spans)**: built from the exact 34 GT spans v18 matched that v22 misses.
  Key finding: the v19 trademark NEGATIVE example was over-broad — it
  suppressed GT-labeled mark-ownership-use restrictions (Ritter "register,
  use or claim ownership") and mark non-tarnishment (ARMSTRONGFLOORING)
  along with the intended hygiene duties; v23 disambiguates mark-HYGIENE
  (operational) from mark-ownership-use / non-tarnishment (items) and adds
  verbatim positives for the recurring missed shapes (audited-statement
  delivery, revenue remittance/commissions, all-requirements supply,
  firm-service commitments, liability-cap fragments, post-termination
  exhaustion, sell-off revenues subject to royalties, joint trademark
  registration, sublicense-to-affiliates, option windows, "at cost without
  markup"). Results (same 50 docs, seed 42, chunked, llm-dojo,
  reasoning=none): **ko 0.8374 (best none-reasoning arm; trend 0.8168 →
  0.8294 → 0.8374), 42 spans recovered at token level (Ritter supply,
  PHREESIA assignment, Phasebio additional-insured) vs 31 lost**, overall
  0.9315 (v22's 0.9512 stays the champion — v23's field variance
  effective_date 0.917 / verified_precision 0.973 is same-surface noise,
  not a prompt effect). Full record: `V16_PROPOSITION.md` §14.
- **`contracts_specialist_v22` — ko-recovery rules (verbatim completeness +
  disciplined dedupe)**: the v21 span-level audit found 38 v18-matched GT
  spans lost to (1) ellipsis abbreviation (23.6% of v21 items contain
  "...", vs v18 15.8%) and (2) over-deduplication (LegacyEducation fell
  19→12 items — records, insurance, sell-off and assignment-exception
  clauses dropped). v22 narrows the dedupe to exact repeats and
  sentence/fragment pairs of the SAME requirement and adds VERBATIM
  COMPLETENESS (never ellipses). Results on the same 50 docs (seed 42,
  chunked, llm-dojo): **v22×none — overall 0.9512 (series best, CI
  .934-.967), ko 0.8294, ellipsis 19.5%, 50/50 rows, $0.039; v22×max —
  ko 0.8442, overall 0.9446, verified_precision 0.996, 50/50 rows (zero
  parse errors — the v22 output discipline retired the max-reasoning
  error rate), $0.100**. The ko regression is diagnosed as partially
  variance (identical-setting passes swing ±2.2pp), partially content
  (the v19+ content family plateaus ~0.83-0.85 at reasoning=none), and
  partially the reasoning setting (max adds +1.5pp on v22; v19's 0.8840
  was the favorable max roll). Production arm: v22×none. Full matrix:
  `V16_PROPOSITION.md` §13.
- **Langfuse two-project strategy (per direction)**: llm-dojo is where
  THIS repo's prompt iterations run (individual prompt improvements);
  llm-mailroom (llm-mailroom-experiments) is EXCLUSIVELY for testing and
  improving the full mailroom pipeline in the llm-mailroom repo — insights
  flow llm-dojo → llm-mailroom, never the reverse. Documented in AGENTS.md
  and `src/langfuse_config.py`; `sync_langfuse_prompts.py` supports both
  projects via repeatable `--env-file` (v22 synced to llm-dojo — 1 created,
  43 unchanged, idempotent).
- **Human-in-the-loop annotation queue for low-performing extraction
  traces** (`scripts/eval/run_annotation_queue.py`): scans the llm-dojo
  mirror's `contract_entity_extraction` traces (session-scoped to the
  extraction pipeline, prompt-version scoped to the contracts specialist),
  ranks them by the attached deterministic `overall_extraction_score`
  (worst first), and enqueues the ones below `--threshold` (default 0.85)
  into a Langfuse **annotation queue** as `PENDING` review items —
  idempotent (queue created once by name; already-enqueued traces never
  re-enqueued). `status` subcommand lists queue items with per-trace
  scores and review URLs. The queue is the HITL loop around the
  experiment cycle: `build` → human review/annotation in the Langfuse UI →
  annotations feed the next prompt iteration. `--dry-run` scans without
  writing; 10 network-free tests (`tests/test_annotation_queue.py`).
  Live-setup hardening: the queue auto-creates its own `annotation-verdict`
  categorical score config (correct/partial/incorrect) when none is passed
  (the API requires ≥1 config id); 429 rate-limit retries honor the
  server's `retryAfterSeconds`; `status` reads scores via the bulk v3
  scores endpoint (cursor-paginated, `subject` field group) instead of one
  request per trace; the queue's review URL is printed. Live on llm-dojo:
  queue `entity-extraction-low-performers` with 137 PENDING items.
- **Sorter failure queue (`--task subtype`)**: the same tool now serves the
  subtype-classification pipeline — `build --task subtype` enqueues every
  trace where the PRIMARY CLASS (doc_type), the contract SUBTYPE (CUAD
  folder), or both FAILED (read from the sorter's output composite,
  `doc_type_ok`/`subtype_ok`; both-failures lead). The Langfuse Hobby plan
  allows ONE annotation queue per project, so sorter items share the
  existing queue and `status --task <task>` filters items by trace name
  (extraction vs `subtype_classification`); sorter status shows
  exact_match / subtype_accuracy / subtype_accuracy_equiv / confidence
  with the failure flags. Live on llm-dojo: +35 PENDING sorter failures
  (2 class-failed, 35 subtype-failed) across the sorter_v6 runs.
- **`contracts_specialist_v21` — the merge arm, ADOPTED as the production
  arm**: v20's prompt text (v19 ko content + the four field rules) at
  **reasoning_effort=none**, same 50 docs, seed 42, chunked, Langfuse
  llm-dojo. Canonical record (run 051, `_50b`, fixed scorer): **overall
  0.9283 → 0.9396 (+1.7pp vs v18 — best on the flash line), 50/50 rows
  (zero parse errors — the EdietsComInc EX-10.4 failure from v19 is
  resolved: max reasoning burned the 32k structured-output budget; at
  reasoning=none the completion budget is the JSON alone), verified_precision
  0.997, effective_date 0.945, renewal_terms 0.905 (+6.4pp), parties 0.980,
  document_name 0.991, cost $0.039 (2.6x cheaper than max reasoning)**.
  The prompt-vs-reasoning confound is resolved: the +3pp v19 ko gain was
  the max-reasoning setting, not the worked examples (at fixed none,
  v19/v20 content scores ko 0.8385 vs v18's 0.8535; v19 keeps the ko crown
  0.8840 at 2.6x the cost and a 1/50 parse-error risk). Full record:
  `V16_PROPOSITION.md` §12.
- **Date-scorer bug fixes (field_scoring.py)**: the v20-era null-expectation
  rule (a) fired on parseable compact dates ("11/4/10" — three PERFECT
  matches scored 0.0) — now gated on `_parse_date(expected) is None`; and
  (b) was never reached for `pred is None` (the short-circuit returned 0.0)
  — the None path now consults the rule, so the five blank-template docs
  score 1.0 for the model's CORRECT null answer. effective_date 0.806 →
  0.945 on v21. SCORING.md §3 updated; regression tests added.
- **All experiments run in llm-dojo; prompts synced between projects**:
  `src/langfuse_config.py` defaults and `langfuse.env` label now read
  llm-dojo (the project-scoped keys have routed every trace there all
  along — verified via the traces API). New
  `scripts/eval/sync_langfuse_prompts.py` mirrors every PROMPT_VERSIONS key
  as a Langfuse text prompt — idempotent (skips unchanged latest-version
  content), `--dry-run`, repeatable `--env-file` so a second project
  (e.g. the primary llm-mailroom environment) is a drop-in with its own
  key file. 43 prompts synced to llm-dojo; network-free smoke tests in
  `tests/test_sync_langfuse_prompts.py`; workflow documented in AGENTS.md
  ("After every run"). Note: the first sync predated the idempotency fix
  and left duplicate v2 versions with identical content in llm-dojo
  (cosmetic; the version-delete API path 404s on this instance).
- **`contracts_specialist_v20` — non-obligation field fidelity (rules
  validated; arm ko-variance-dominated)**: four surgical prompt rules from
  the v19 per-field audit — renewal_terms EVERGREEN CLAUSES ("shall
  continue in full force and effect thereafter until terminated by N days'
  notice" — no "renew" word needed) + DEAL-TERMS TABLES; term_length
  DEFINED-TERM SENTENCES (carve-out of the no-definitions rule); governing
  law regulatory-jurisdiction sentences; termination_clauses REDACTED
  SECTIONS (heading + "[***]" marker). Same-scorer re-score (embedding
  off, both arms): **renewal_terms +4.5pp, termination_clauses +5.4pp** on
  target; official overall 0.9142 vs 0.9135 (tie) because ko −7.3pp was
  diffuse run variance (2 up vs 14 down, 34 flat — docs the rules never
  touch) + one parse-error row per arm. **Not adopted as champion** (v19
  holds ko 0.8840); next step v21 = v19 content + v20 field rules.
- **Scorer fixes (field_scoring.py, ADOPTED — all future runs)**: (1)
  blank-template/label-only expected dates ("_____ day of ________,
  19____", "Effective Date:") are null expectations — a null prediction
  scores 1.0 (3 of 5 v19 zero-date docs); (2) partial-GT party labels whose
  tokens appear verbatim in a predicted item are instantiated (role and
  pronoun labels: "Consultant", "Member", '"we," "us," or "our"' — 3 of 4
  v19 zero-parties docs; parties 0.918→1.000 on v20); (3) name fields score
  full token-containment → 1.0 (document_name 0.960→0.991 on v20).
  Historical records keep their stored scores; SCORING.md §3 documents the
  rules. Full record: `V16_PROPOSITION.md` §11.
- **Research memo `memos/contracts_specialist_v20.md`**: the field-fidelity
  iteration (scorer correctness fixes + field-rule validation), linked from
  the memos README and shipped on the site's memos tab.
- **`contracts_specialist_v19` — worked span examples + span discipline
  (flash-line ko champion)**: v18's residual (93/241 token-unmatched GT
  spans license-shaped, only 25/107 with naive "grants ... a license"
  phrasing) motivated WORKED SPAN EXAMPLES drawn verbatim from the misses
  (grants-and-assigns with territories, restriction-on-rights, options,
  end-user access grants; verified negatives: trademark-hygiene/product-
  marketing duties, sentence+fragment repeats). v18's 225 near-duplicate
  items motivated SPAN DISCIPLINE (one item per operative requirement +
  post-build dedupe). Run: qwen3.7-flash × **reasoning_effort=max**, same
  50 docs, seed 42, chunked, Langfuse llm-dojo — **ko 0.8535 → 0.8840
  (+3.0pp; +10.9pp vs v15), alignment precision 0.619 → 0.662, items −29%
  (1118→792), verified_precision 0.988**; gains concentrate in the target
  license docs (HPIL 0.5→1.0, NOVO 0.667→1.0, Fulucai 0.5→0.833).
  Caveats: 1/50 parse-error row (Ediets EX-10.4 — max reasoning overran
  the structured budget; ko ≈ 0.90 without it), prompt-vs-reasoning
  confound unresolved, cost 2.6x ($0.098). Full record: `V16_PROPOSITION.md`
  §10, `memos/contracts_specialist_v19.md`.
- **Research memo `memos/contracts_specialist_v19.md`**: dedicated memo for
  the worked-examples iteration (span examples beat prose shapes for the
  license family; reasoning-effort reliability trade), linked from the memos
  README and shipped on the site's memos tab.
- **v18 model sweep — scope-fidelity is model-agnostic, segmentation is
  model-bound**: v18 × {deepseek-v4-flash, deepseek-v4-pro} on the same
  50-doc surface (seed 42, chunked, Langfuse llm-dojo). Every model gains
  +6.0 to +11.5pp on key_obligations from v15 to v18; **deepseek-v4-pro ×
  v18 is the series champion — ko 0.7755 → 0.8907 (+11.5pp), overall 0.9289
  (series best), verified_precision 1.000 (zero hallucinations), alignment
  precision 0.685 (best)**, at an estimated $0.053 for the 50-doc surface.
  deepseek-v4-flash over-produces (1735 items, +56% over the GT sample;
  alignment precision 0.549) and lands ko 0.8358 (+6.0pp). The catalog
  fixed a prompt-layer scope defect, not a model quirk. Full table +
  interpretation in `memos/model_sweep_v18.md`; runs 047–048 in the
  experiment log.
- **`SCORING.md` §4/§8 — post-hoc scoring logic synthesized**: the
  per-row `entity_list_audit` artifact (`n_predicted`, `matched_gt`,
  `verified_in_doc`, `true_items`, `verified_precision`, `hallucinated`,
  `hallucination_rate`, `doc_verification`) is documented as the canonical
  post-hoc analysis record, with the derived post-hoc metrics (item count,
  matched GT spans, alignment precision = Σmatched/Σpredicted, verified
  precision) and the chunked-extraction scoring semantics (list union with
  normalized dedupe, scalar first-non-null, confidence max, failed-chunk
  skip). New §8 documents the sanctioned span-level miss-attribution
  chain: unmatched-span extraction → containment test → family
  decomposition → recovery check.
- **Research memo `memos/model_sweep_v18.md`**: the dedicated sweep memo
  (research question → answer + results tables → interpretation →
  remaining uncertainties) with same-surface identity and bootstrap-CI
  discipline, linked from the memos README and shipped on the site's
  memos tab.
- **Research memo on the v17→v18 contract-specialist findings**
  (`memos/contracts_specialist_v17_v18_enhancements.md`): documents the
  grain-vs-scope experiment — v16 fragment contract (+0.6pp ko, −2.7pp
  overall, over-fragmentation), v17 length anchor (627 matched spans,
  below v15), the refuted containment hypothesis (0/160 spans embedded),
  and the adopted v18 family-fidelity catalog (ko 0.7755→0.8535 +7.8pp,
  overall 0.9230, series best). Ships on the site's memos tab.
- **`contracts_specialist_v18` — family-fidelity catalog (ADOPTED)**: the
  terse 26-family list in `src/prompts.py` is replaced by a CUAD-category
  catalog (1:1 mirror of the 41-category catalog, 26 obligation families)
  with each category's operative clause shapes, derived from the 50-doc
  v15/v16/v17 decomposition of the 160 unmatched GT spans (cap-on-liability
  consequential-damages waivers, license grants phrased "right and
  license ... for the territory of", minimum guarantees/royalties, audit
  deficiency remedies, insurance coverage lists, IP-prosecution elections,
  family-term definitions). The exclusion rule narrows to true general
  duties with a WHERE-IT-SITS guard (family clauses inside
  indemnity/damages sections still count). v17's length-anchored grain is
  kept. A/B (same 50 docs, chunked, seed 42, Langfuse llm-dojo):
  **key_obligations 0.7755 → 0.8535 (+7.8pp)**, overall 0.9129 → **0.9230**
  (series best), parties/term_length tie v15, verified_precision 0.991.
  30/160 missed spans recovered at token level (cap liability +8, IP
  ownership +4, license +4); Penntex now extracts its labeled
  cap-on-liability clause (0 liability items in v15). Decision rule met
  (ko ≥ +3pp, no field regressed >2pp) — champion. Design + full table in
  `V16_PROPOSITION.md` §9.
- **Research memos + memos tab on the site**: `memos/*.md` archive the key
  findings from experimental runs and prompt iterations (research-question →
  answer + results summary → remaining uncertainties), shipped to the site
  under a new **memos** navigation tab (`build_site.py` emits
  `docs/data/memos.json`; the viewer renders the markdown subset with
  tables, inline formatting, and cross-memo links). Initial memos:
  subtype-classification improvements (sorter v3→v6) and entity-extraction
  improvements (specialist v2→v15 incl. the chunking enhancement).

### Fixed
- **Runs table sorts chronologically by default**: the `id` column (the
  chronological run number) fell through to a lexicographic string compare,
  so the default newest-first sort produced a garbled order ("9" before
  "43", newest runs buried mid-table). `id` now sorts numerically in every
  view's runs table; the default remains id desc (newest first), and the
  header click toggles numeric asc/desc correctly.
- **Stylized graph favicon for the site**: the GH Pages favicon is now a
  directed-graph motif (four nodes on the site's accent gradient with a
  highlighted vertex) replacing the placeholder "E" — matching the
  experiment-log/LangGraph identity. Also adds a Safari `mask-icon`.
- **Benchmarks view showed "OPENROUTER_API_KEY not set" despite a configured
  key**: `build_site.py` never loaded the repo's credential files
  (`braintrust.env` / `.env`), so the benchmarks fetch silently reported
  unavailable. It now calls `src.env_utils.load_env()` like the eval runners
  — rebuilt with the configured key, the site ships **1387 live benchmark
  rows** (133 Artificial Analysis + 1021 Design Arena, as-of 2026-08-12) in
  `docs/data/benchmarks.json`. Pricing rendering handles both `$X/1M`
  strings and per-token decimals (`$X/token`).

### Added
- **Real-browser audit of the GH Pages site** (`tests/test_browser_audit.py`
  + `tests/assets/browser_audit.mjs`, skipped without Chrome/node): serves
  docs/ and drives headless Chrome via the DevTools Protocol over every
  route, asserting zero console errors/exceptions, no layout overflow, and
  that each view renders — catching silent errors, visual breakage, and
  uncaught issues the stubbed-DOM audit cannot see.
- **OpenRouter benchmarks on the experiment-log site**: a dedicated
  `#/benchmarks` navigation tab rendering Artificial Analysis
  (intelligence/coding/agentic index rankings with per-model pricing) and
  Design Arena (ELO, win-rate, avg generation time, tournament stats) —
  fetched best-effort at build time (`build_site.py --benchmarks-key` or
  `$OPENROUTER_API_KEY`) into `docs/data/benchmarks.json`, with citation
  metadata preserved and the "benchmarks are evidence, not proof of
  availability" caveat surfaced in the view. Unavailable builds render a
  rebuild hint instead of failing; the headless render audit covers the view.
- **Issue & PR templates (YAML forms)**: `.github/ISSUE_TEMPLATE/`
  (`bug_report`, `feature_request`, `experiment_report`, `config.yml`) and
  `.github/PULL_REQUEST_TEMPLATE/pull_request.yml` enforcing this repo's
  discipline — same-surface identity on every bug/experiment report, the
  changelog-in-the-same-commit rule, derived-artifact regeneration, the
  render audit, and the `release.py --check` gate.
- **LangChain + LangGraph skills installed for all agents** (from
  github.com/langchain-ai/langchain-skills): `langchain-fundamentals`,
  `langchain-python-quickstart`, `langchain-dependencies`,
  `langchain-middleware`, `langchain-rag`, `langgraph-fundamentals`,
  `langgraph-python-quickstart`, `langgraph-cli`, `langgraph-persistence`,
  `langgraph-human-in-the-loop`, `ecosystem-primer`, and `eval-engineering`
  — project skills covering the full agent/graph stack the repo builds on
  and evaluates. AGENTS.md documents the skill set.
- **Langfuse skill installed for all agents**: `.opencode/skills/langfuse/`
  (SKILL.md + 11 reference files, from github.com/langfuse/skills) — a
  project skill, available to every agent in this repo, granting langfuse-cli
  API access + docs retrieval when loaded. AGENTS.md documents it.
- **Complete documentation pass**: per-directory READMEs added where missing —
  `src/README.md` (core modules incl. `bootstrap.py`/`cost_models.py`),
  `agents/README.md` (agent roster), `config/README.md` (taxonomy.yaml),
  `scripts/README.md` (ops/evals/reporting/site/releases), `tests/README.md`
  (conventions + render audit), `reports/README.md` (the experiment log) —
  and the root `README.md` layout + Website sections updated to reference
  them. AGENTS.md gained a "Docs & READMEs" convention.
- **Public GitHub wiki fully expanded** (`wiki/`, pushed by
  `./wiki/sync-wiki.sh` to https://github.com/Exios66/llm-entity-extraction/wiki):
  Home, Getting-Started, Architecture, Eval-Runners, Experiment-Log, Scoring
  (expanded from the previous Experiment-Scoring-Breakdown), Site, Release-
  Process, Taxonomy, FAQ, plus _Sidebar/_Footer — covering setup, every eval
  runner, the JSONL/md/site pipeline, all metrics (bootstrap CIs, judge
  calibration, ablation, cost scoring), the visualization site, and the
  release workflow.
- **Release automation (`scripts/release.py`)**: `--bump <patch|minor|major>
  --note "<summary>"` converts the accumulated `[Unreleased]` entries into
  `## [vX.Y.Z] - <date>` (keeping the empty placeholder), bumps
  `pyproject.toml` in lockstep, and prints the exact commit/tag/GH-Pages-push/
  llm-mailroom-sync commands; `--check` validates version == changelog
  header, site-data freshness (`build_site.py --check`), the full suite, and
  the headless render audit; `--dry-run` previews without writing; refuses on
  a dirty tree.
- **AGENTS.md release workflow codified**: changelog entries land in the SAME
  commit as every behavior-changing change ([Unreleased] discipline), docs
  (README/docs/SCORING/AGENTS) are updated when the change touches them,
  pyproject.toml must equal the changelog header, tags must match the header
  exactly, and the post-run GH Pages sync (render → build_site → audit →
  push) plus the llm-mailroom mirror sync are the expected pipeline.


## [v0.14.0] - 2026-08-11

### Added
- **Bootstrap confidence intervals (GitHub issue #1)**: `src/bootstrap.py` —
  percentile-bootstrap 95% CIs over per-document scores (`bootstrap_ci`) and
  two-sample bootstrap delta tests with significance verdicts
  (`delta_significance`, min-detectable-effect guard for A/Bs). Wired into
  all four eval runners as `scores.*_ci` (`overall_extraction_score_ci`,
  `subtype_accuracy_ci`, `exact_match_ci`, …) in every experiment record;
  `evaluate_prompt_version.py` prints the delta CI + significance for A/Bs.
  Older records get CIs too — the site resamples the per-doc arrays already
  stored in `results[]`, then falls back to Wilson (`_record_ci`).
- **Chained error-propagation ablation (`--handoff-scope ground_truth`)**:
  the specialist now ALSO extracts the same docs with the ground-truth-subtype
  handoff; `scores.ablation` records predicted-vs-GT handoff scores and the
  sorter routing loss (pp) — chained loss is split into sorter error vs
  specialist error instead of being attributed "mostly by inference" (both
  chained runners).
- **Judge-calibration tracker**: extraction `--judge` rows are persisted to
  `data/judgments/<experiment>.jsonl` (`kind: calibration` with the
  deterministic score + judge labels) and aggregated into
  `scores.judge_calibration` — agree rate vs the deterministic scorer plus a
  lenient/strict lean signal (strong ≥ 0.85 / weak ≤ 0.5 bands).
- **Cross-model matrix runner (`scripts/eval/run_model_matrix.py`)**: runs a
  fixed sample (same dataset/seed/size — one surface) across a model x prompt
  grid using the existing runners and prints a score (+bootstrap CI) x cost
  matrix.
- **Cost scoring for every run**: OpenRouter usage payloads carry no cost
  field, so every run previously recorded `cost_total_usd = 0.0` despite
  ~30M real tokens. `src/cost_models.py` scores cost deterministically from
  the recorded prompt/completion token counts x verified per-model prices
  (qwen $0.03/$0.13 per 1M, deepseek-v4-flash $0.05/$0.25, deepseek-v4-pro
  $0.435/$0.87; unknown models resolve by prefix or honestly report None).
  `tokens_summary()` now takes `model=` and stamps `cost_estimated_usd` on
  every future record; a documented one-time backfill
  (`scripts/backfill_cost_estimates.py`, append-only-log exception) scored
  all 38 historical records / 81 token buckets (est. $2.28 total). The site
  shows billed (OpenRouter CSV) when covered and the estimate otherwise —
  runs table, run detail (with price source), cost-vs-quality scatter, and
  trends.
- **Site — same-surface guardrail**: every index row carries
  `fingerprint`/`seed`/`sample_key`; `delta_best_pp` is computed only against
  the best run on the SAME surface (dataset fingerprint + seed + sample
  size), and the frontend refuses to color deltas across different surfaces
  — the v0.13.0 "regression" class of misread is now structurally
  impossible.
- **Site — trends, scatter, stacked bars, prompt diff**: `docs/data/trends.json`
  (per-task series with headline/cost/sample-key/failure-mode counts) and
  `docs/data/prompts.json` (full prompt text per version); the task view
  renders an SVG score-trend chart per prompt version, a cost-vs-quality
  scatter, and (subtype) failure-mode stacked bars; a `#/prompts` prompt-diff
  view shows a side-by-side line diff between two versions with their score
  delta.
- **Headless render audit for the site**: `tests/assets/site_render_audit.js`
  + `tests/test_site_render.py` exercise EVERY view (index, all task/prompt/
  model groups, all 38 runs, 114 document traces, prompt diff) against the
  real built data with a stubbed DOM and assert zero rendering errors
  (skipped when node is absent).
- `sorter_classification` gained a headline handler (exact_match + per-class
  detail), so its runs chart like every other task.

### Changed
- **Charts are legible, inspectable, and navigable**: the cost-vs-quality
  scatter uses a **log-scale x axis** (runs span ~4 orders of magnitude; the
  linear axis piled every point on the y axis) with $ grid ticks and filled
  (billed) vs hollow (estimated) points; trend lines are **smoothed**
  (Catmull-Rom splines) with raw points on top, from a **curated palette
  with dash patterns**; hovering a series dims the others. Every chart point
  is **hover-inspectable** (tooltip panel: experiment name, run id, model,
  prompt, headline, cost, n rows, sample key, timestamp) and **click-
  navigates to the coordinated run**; failure-mode stack rows are clickable
  too.
- **Navigation grouped**: task links live under a single **"tasks" dropdown**
  populated from `meta.tasks` (hardcoded per-task links removed — the nav no
  longer repeats task names twice): runs | tasks ▾ | prompt diff | repo |
  theme.
- **Site polish**: dynamic nav + confusion matrices sorted by expected-class
  frequency (Σ totals, per-class accuracy, cell tooltips); index gains a
  "Total cost (est.)" stat card; focus-visible outlines and
  `prefers-reduced-motion` support.

### Fixed
- **Chart tooltip overflow**: tooltip rows now wrap long unbroken strings
  (trace IDs, experiment names, sample keys) — nothing spills out of the box.
- **Chart panel + gridlines were invisible**: chart/nav/tooltip CSS
  referenced undefined vars (`--panel`/`--line`/`--ink`/`--gold`) — defined
  as theme-aware aliases in `:root`; charts now render on a panel surface
  with visible gridlines in both themes.
- **Hollow (estimated-cost) scatter points were invisible**: a global
  `.dot{stroke:var(--bg)}` rule overrode the per-point color presentation
  attribute — removed; hollow points render with their colored ring (crisp
  at any scale via `vector-effect: non-scaling-stroke`).
- **Tasks dropdown was transparent** (undefined `--panel` background) — now a
  proper surface that right-aligns to the viewport on mobile.
- Long kv labels (ablation/judge-calibration cards) no longer force table
  overflow.

## [v0.13.0] - 2026-08-11

### Fixed
- **Chained extraction "regression" diagnosed and disproven** — the apparent
  drop (0.906 → 0.85) was a measurement artifact: the historical chained runs
  evaluated on `mailroom-cuad-contracts` (50 docs) while the new runs use
  `mailroom-cuad-contracts-full` (509 docs), whose seed-42 5-doc samples are
  DISJOINT (0 overlapping documents). On the controlled same-surface A/B
  (Langfuse-audited, identical docs), sorter_v6 + specialist_v11 chained
  scores **0.946 vs the historical v11 0.906** — the newest pipeline is the
  best measured; the subtype handoff adds +4pp overall / +19pp category
  presence vs `--handoff-scope none`. Extraction score is dominated by the
  specialist's per-field accuracy, not the sorter's routing (sorter is
  subtype-perfect on the sample; verified_precision 1.0 — zero hallucinations
  in every chained run). The only true within-surface regressions were
  specialist v7/v8 (0.696-0.699 vs 0.89-0.92), recovered by v10/v11.
- **Date scorer containment + partial credit** (`score_date_field`) — CUAD
  maps BOTH "Agreement Date" and "Effective Date" onto `effective_date`;
  strict date equality scored legitimate multi-date documents 0.00 (NETGEAR
  GT `November 5, 1996` vs predicted `1996-03-01`; MOELIS GT `December 27,
  2011` vs `2012-01-01`). New tiers: label-date phrase contained in the
  prediction (or vice versa) → 1.0; shared year+month → 0.67; within a
  45-day cluster (execution vs defined effective date) → 0.67; year-only →
  0.33. A bare year never earns full credit. Documented in SCORING.md.
- **Contracts specialist v12** (`src/prompts.py`, derived from v11) —
  effective-date rule (the agreement's defined term wins, full date phrase);
  governing-law quoted VERBATIM in full (containment fix for the 0.39
  fragment scores); RE-SCAN DUTY for the families the 5-doc sample missed
  (volume restrictions, caps on liability, uncapped liability, audit rights,
  third-party beneficiary, change of control, anti-assignment); truncation
  honesty (scan both sides of the marker, never fabricate the omitted
  middle).
- **Truncation auditability** — chained/extraction composites and Langfuse
  `contracts_specialist` spans now carry the `truncated` flag
  (`specialist._last_truncated`); chained/extraction `--max-input-chars`
  default raised 100k → **150k** (fully covers Antares 106.8k and MOELIS
  122.1k; Phasebio 292k remains head+tail by design).
- **Measured on the identical full-corpus 5-doc sample** (Langfuse, seed 42):
  chained overall 0.8666 (v11) → **0.8882 (v12)** with category presence
  held at 0.777, field presence 1.0, verified_precision 1.0; MOELIS 0.823 →
  0.907, NETGEAR 0.792 → 0.828 (dates 0.00 → 0.67/0.33). Test count 223.

## [v0.12.0] - 2026-08-11

### Added
- **Full-corpus sorter baseline** — `qwen3.7-flash_sorter_v5_subtype`: the
  complete 509-contract CUAD run (sorter_v5, reasoning `medium`): doc_type
  exact_match 0.9843, strict subtype 0.8585, family-level equiv 0.8743, mean
  confidence 0.9404; 72 misses classified by failure mode (40 family
  confusion / 16 other-fallback / 8 function-over-form / 8 equivalent-family).
- **Sorter v6** (`src/prompts.py`) — surgical derivation of v5 (base string
  untouched, registered in `PROMPT_VERSIONS`) with data-backed rules for the
  509-run's miss clusters: rule 12 SEC Joint Filing Agreements →
  joint_venture (13/72 misses); rule 13 maintenance preference (license+
  maintenance hybrids + financial-sense maintenance, 17/72); rule 14 hosting
  is not license/development (8/72); rule 15 remarketing → marketing; rule 16
  marketing-core guard; rule 17 annex inheritance; plus the rule-10
  refinement (development preference does not override an operating core —
  manufacturing/marketing/hosting).
- **Same-sample 195-doc A/B** (`--stratified 200 --seed 42`, the documented
  baseline sample): sorter_v6 0.9385 strict vs v5 0.8410 (**+9.75pp**),
  equiv 0.9436 vs 0.8667, exact_match 1.0, failures 31→12 — vs the
  historical v3-medium 0.8359 / v4 0.8103 baselines on the same sample.
- **Langfuse mirror environment** — dedicated project
  (`llm-mailroom-experiments`, keys in gitignored `langfuse.env`), every
  trace tagged with `LANGFUSE_ENVIRONMENT`, session-scoped deterministic
  trace ids (`sha256(session|filename)`) so re-runs of the SAME experiment
  update traces in place while different experiments never merge.
- **Per-agent designated tasks on Langfuse** — `LangfuseTracer.agent_observation`
  opens one nested span per pipeline agent (sorter / contracts_specialist)
  with its own LangChain generation and its designated task scores attached
  to the agent's OWN observation: sorter (exact_match, subtype_accuracy,
  confidence) and contracts_specialist (overall_extraction_score,
  field_presence, overall_verified_precision, category_presence,
  schema_valid) — per-agent performance metrics derivable over time.
- **Langfuse mirror runners** — `run_langfuse_subtype_eval.py` (existing),
  `run_langfuse_chained_eval.py`, `run_langfuse_extraction_eval.py`,
  `run_langfuse_classification_eval.py` (text): same data/tasks/scorers/
  manifest/experiment-log as their Braintrust counterparts, zero scored-run
  quota (deterministic NUMERIC scores per trace). Braintrust loggers gained
  additive `tracing_backend`/`tracing_meta` record fields.
- **Subtype-scoped chained handoff** — `build_subtype_handoff(subtype)` in
  `src/cuad_ground_truth.py` (SUBTYPE_CUAD_FOLDERS reverse-mapping + the CUAD
  per-type category tables): with the new `--handoff-scope subtype` default
  the specialist is cued with the PREDICTED subtype's expected field groups
  and never-applicable clause categories. 5-doc chained A/B (sorter_v6 +
  specialist_v11, seed 42): overall 0.8666 vs 0.8497 (+1.7pp), category
  presence 0.7773 vs 0.7106 (+6.7pp). `--handoff-scope none` reproduces the
  legacy handoff.
- **GH Pages site** (`docs/`) — static, dependency-free viewer over the
  experiment log (`index.html` + `site.css`/`site.js` + generated
  `docs/data/`); `scripts/site/build_site.py` regenerates the data
  (`--check` verifies currency). Pages source fixed to `main → /docs`.

### Changed
- `agents/base_agent.py` accepts optional LangChain `callbacks` (Langfuse
  handler threading; Braintrust path unchanged); `ContractsSpecialist` and
  `SorterAgent` forward them.
- `requirements.txt`: +`langchain>=1.0`, +`langfuse>=3.0`.
- README/AGENTS.md document the Langfuse mirror workflow, per-agent task
  matrix, and handoff scope flag; test count 220.

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

[v0.15.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.15.0
[Unreleased]: https://github.com/Exios66/llm-entity-extraction
[v0.18.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.18.0
https://github.com/Exios66/llm-entity-extraction
[v0.17.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.17.0
https://github.com/Exios66/llm-entity-extraction
[v0.16.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.16.0
https://github.com/Exios66/llm-entity-extraction
[v0.14.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.14.0
[v0.13.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.13.0
[v0.12.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.12.0
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
