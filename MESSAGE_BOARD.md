# Agent Message Board — llm-entity-extraction

The living, shared Kanban canvas for ALL agents (and humans) working in this
**cross-repository project** — the prompt-experiment loop in this repo
(`llm-entity-extraction`) and the pipeline it feeds (`llm-mailroom`). It is
the single place where tasks that still need to be completed, are in
progress, are blocked, need to be revisited, or have been finished are
tracked — with every card tied to a semantic-version release in
`CHANGELOG.md` and, when critical, to a GitHub issue in the repo where the
work lands.

**This is a WORKING DOCUMENT, not documentation.** It is meant to be
modified progressively as work happens. Finished work is never deleted — it
moves to the Archive (bottom of this file) so the full audit trail stays
intact.

## How to use this board — the procedures (READ FIRST, every session)

### 1. Read before you work

Read this board **before starting ANY task** — the Kanban table, the
discussion log, and the open GitHub issues — for (a) cards/issues already
claimed by another agent, (b) cards that cover the work you were about to
do, and (c) context posts that affect your work.

### 2. Scope — one board for both repos

Cards can target either repository. The **task summary states the repo** or
the card names it in the evidence column; `llm-mailroom` work (pipeline
integration, synced prompts/logs) is tracked here with the other cards.
Issues for cross-repo work open in the repo where the work lands.

### 3. Self-assignment (claiming a task)

A task is yours only after you **claim it**, in this order:

1. **Comment on the GitHub issue** (if the card has one — the `Issue`
   column) saying you are claiming it, OR post to the Discussion board if
   the card is board-only.
2. **Move the card to `in_progress`** and set **Owner** to your agent name
   + today's date.
3. **Reference the card in your first commit**: `sorter_v7 (KANBAN-003): ...`
   or `MESSAGE BOARD: KANBAN-004 claimed`.

Never work silently; never race a claimed card. ONE owner per card — if a
card is claimed, build off it (offer help / pick an unclaimed card).

### 4. Work underway = `in_progress`, immediately — never `backlog`

`backlog` means ZERO work has started: no draft, no diff, no run in
flight, no partially landed commit. The moment ANY work exists for a
card's scope — a first working-tree edit, an uncommitted prompt/test/
script draft, a branch, a run that has started — the card MUST be moved
to `in_progress` (Owner set, `Updated` dated), NOT left in `backlog`.

- **Label it before the code, not after.** The status move happens when
  work begins; never when it finishes.
- **Sanity check every session (and before every commit):** if `git status`
  (or a branch, or a running eval) shows changes that belong to a card,
  that card must read `in_progress` in the table. If a card is found
  underway-but-labeled-`backlog`, move it to `in_progress` at that moment,
  set Owner to whoever holds the work, and post a dated note in the
  discussion log. Uncommitted work on the board = an `in_progress` card.
- **The table must never lie about reality:** a card whose summary says
  "draft in the working tree" is, by definition, `in_progress` — update
  the lane at the same time you write the summary.

### 5. Work that relates to an existing task MUST update that task

If your work **addresses the problem identified in a card** — even
partially, or from a different angle — you update THAT card: comment on the
issue / post to the discussion board, move its status to reflect reality,
and extend its summary with what you found. **Never create a parallel card
for a covered problem** and never open a duplicate issue. Only add a NEW
card (next free number, new issue if critical) when NO card covers the
task.

### 6. Status moves — when and who

| Move | Who | When |
|---|---|---|
| `backlog` → `in_progress` | anyone (self-assign) | You are actively working it, OR any work exists for it (draft, diff, branch, run started) — Owner set + dated, immediately, never deferred |
| → `blocked` | owner | Stuck — post the blocker in Discussion + on the issue; name what unblocks it (data, keys, decision, card) |
| `blocked` → `backlog`/`in_progress` | owner | Blocker cleared — post what cleared it |
| → `in_review` | owner | Work done; awaiting validation (tests, A/B, release gate). Link the evidence (run, commit, PR) in the card |
| `in_review` → `done` (Archive) | reviewer/releaser | Validation passed; CHANGELOG entry exists (same-commit rule); issue CLOSED in the same commit |
| `done` → `backlog` (reopen) | anyone | Regression / new data / superseded assumption — Discussion post explains why; issue reopened with the post |

A card is **not done until** every criterion in §7 holds; a synced card's
`done` and its issue's `closed` are the SAME event.

### 7. Completion — the done & issue-close criteria

A task is COMPLETE — and its dedicated GitHub issue CLOSABLE — only when EVERY
requirement holds. All six must be true before you report done:

1. **Work verified** — tests pass (network-free suite), the A/B run landed,
   and/or the release gate (`release.py --check`) is green. **No uncommitted
   work may remain in the card's scope** — `git status` is clean for the
   card's files (stray diffs mean the card is still `in_progress`, not done).
2. **CHANGELOG entry exists** — the `[Unreleased]` (or released) entry
   describing the work lands in the SAME commit that ships it (AGENTS.md
   same-commit rule). No changelog entry = no done.
3. **Card archived** — the card moved to the Archive with: shipped version,
   commit/tag, key result, and the Owner/`Updated` timestamp filled.
4. **Discussion closed out** — a dated closing entry on the discussion board
   (result + verdict), newest-at-top, history never edited.
5. **Issue closed in the same commit** — for synced cards, `gh issue close
   NNN` runs with a closing comment naming the commit and CHANGELOG entry,
   IN the same commit that archives the card. The card must never sit
   `done` with its issue open, nor the issue closed with the card unarchived.
6. **No orphaned scope** — anything discovered but NOT delivered (a new
   confusion cluster, a follow-on arm) spawns its own card + issue BEFORE
   this card closes; unfinished discovery is not a silent done.

Completion close-out is the LAST action of every task: verify → changelog →
archive → discussion post → close issue → report.

Reopen protocol (regression / new data / superseded assumption): move the
card back to `backlog` AND reopen its issue with the Discussion post as the
comment — in the same pass.

### 8. GitHub issue sync (critical / high-priority tasks)

**Critical, high-priority, and cross-repo tasks are routed to GitHub issues**
(label `kanban`), opened in the repo where the work lands, so agents can
open/close them like normal issues while the board remains the source of
truth.

- **Which tasks route to issues:** critical / high-priority cards, cross-repo
  work, anything whose completion must be externally verifiable, and any
  card the human asks to track as an issue. Board-only cards (small,
  single-session, low-risk) do NOT need issues.
- **The card ALWAYS carries the dedicated issue link.** Every synced card's
  `Issue` column holds the FULL markdown link to its own dedicated issue —
  `[#NNN](https://github.com/Exios66/<repo>/issues/NNN)` — never a bare
  number, never a link to another card's issue. One card = one issue.
- **Order of operations when adding a critical card:** open the issue FIRST
  (in the repo where the work lands), then write its link into the card:
  `gh issue create --title "KANBAN-00N: <task>" --label kanban --body "<card summary + evidence + procedure>"`.
- **Cross-reference both ways.** The issue body names its `KANBAN-00N`; the
  card names its issue link. They must never disagree about status — a lane
  move on the card is mirrored on the issue (claim → comment, blocked →
  blocker comment, done → closed).
- **When a card ships**, close its issue in the same commit that archives
  the card (`gh issue close NNN`), with a closing comment naming the commit
  and CHANGELOG entry (see §7.5).
- **When a card is reopened**, reopen its issue with the Discussion post as
  the comment.
- **Sync sweep:** after any board edit, audit the table — every open card
  has a link in its `Issue` column, and every link points at an issue that
  is OPEN (`gh issue list --label kanban`), except cards in the Archive,
  whose issues are CLOSED. A missing link = an unsynced card = not ready
  for assignment.

### 9. Commit discipline

Reference cards in commits — `MESSAGE BOARD: KANBAN-004 claimed` or
`v24 diagnostic (KANBAN-004): ...`. A commit that lands a card's work
carries its CHANGELOG entry in the same commit (AGENTS.md rule) and closes
its issue.

### 10. Release sweep

Semantic versioning is the spine: every open card names its target release.
When a release ships (`scripts/release.py --bump`), sweep the board: cards
that landed move to the Archive under that version (issues already closed),
cards that did not land are re-targeted to the next release. The board and
`CHANGELOG.md` must never disagree about what is done.

## Status lanes

| Lane | Meaning | Who can move it |
|---|---|---|
| `backlog` | Todo — not yet started, NOTHING underway: no draft, no diff, no branch, no run in flight. The release it targets is set in the table. | anyone (add/claim) |
| `in_progress` | Work EXISTS and is being actively worked by the Owner — OR any work for the card exists at all (uncommitted draft, started run, partial commit). ONE owner per card. Cards with uncommitted work in the tree must be here, never `backlog`. | owner (or any agent fixing a mislabeled card, with a dated discussion note) |
| `blocked` | Stuck — waiting on data, keys, a decision, or another card. Post the blocker in Discussion. | owner |
| `in_review` | Work done, awaiting validation (tests, A/B, release gate) before it can land. | owner → reviewer |
| `done` | Finished and recorded in the Archive with CHANGELOG linkage. | reviewer/releaser |

## Key Kanban table

Status codes: `backlog` · `in_progress` · `blocked` · `in_review` · `done`

| Card | Issue | Status | Task (summary) | Owner | Target release | CHANGELOG / evidence |
|---|---|---|---|---|---|---|
| KANBAN-018 | — | `in_progress` | **prompt-engineer agent (master diagnostic evaluator & prompt engineer)** — dedicated `.opencode/agents/prompt-engineer.md` whose SOLE role is reviewing all traces/reasoning/failures/errors/results of evaluated prompts and producing stronger data-backed mutations (new version keys): diagnose → root-cause taxonomy (boundary-shift/abbreviation/wrong-span/hallucination/scope + sorter modes) → one-rule-per-version mutation with data-backed tests → same-seed pilot → same-surface A/B with bootstrap-CI verdicts → plateau/overfit doctrine (clusters not outliers, generalization test, evidence floor) → board + CHANGELOG + memo close-out. AGENTS.md "Agents (this repo)" section documents it next to experiment-log-sync. | opencode (2026-08-15) | v0.18.0 | tree: `.opencode/agents/prompt-engineer.md`, AGENTS.md §Agents |
| KANBAN-017 | — | `in_progress` | **term_length containment dip (v24 leading-phrase arm)** — v24's canonical-duration-prefix rule made the model REPLACE the clause opener ("This Agreement will become effective as of the Effective Date and, unless sooner terminated pursuant to Sections 3.1") instead of prefixing it — Ediets containment 1.0→0.3333 (the CUAD span IS the opener). Fix: `contracts_specialist_v25` — prefix is ADDITIVE, full verbatim clause (opener first) must follow; same-surface 5-doc A/B vs v24 (seed 42) to verify recovery + no regression. | opencode (2026-08-15) | v0.18.0 | flagged on KANBAN-016 close-out; v24 run: qwen3.7-flash_contracts_specialist_v24_sample5 |
| KANBAN-013 | [#11](https://github.com/Exios66/llm-entity-extraction/issues/11) | `backlog` | **Sorter >0.93 tail-sampling iteration** — the v9 A/B left 18 fails, a 1-off long tail (no cluster >2); ~0.93 is the practical plateau on this corpus revision. 0.95 strict needs either tail-sampling iterations (per-error-class rules on the long tail) or a corpus re-baseline; proposal + data first (`V16_PROPOSITION.md` §18 risk register). | unclaimed | v0.18.0 | `V16_PROPOSITION.md` §18; v9 run: qwen3.7-flash_sorter_v9_subtype_langfuse (strict 0.9259, 18 fails) |
| KANBAN-004 | [#3](https://github.com/Exios66/llm-entity-extraction/issues/3) | `backlog` | **Extraction next arm (v24 candidate)** — attack the 30-span residual: span-choice/boundary divergence at token level (34→30 spans still missed; ko ~0.85 ceiling at reasoning=none). Diagnostic first: classify the 30 misses (boundary-shift vs abbreviation vs wrong-span) before writing prompt rules. | unclaimed | v0.18.0 | `V16_PROPOSITION.md` §14.3/§15.1; `reports/same_scorer_scores.json` |
| KANBAN-005 | [#4](https://github.com/Exios66/llm-entity-extraction/issues/4) | `backlog` | **Mirror sync → llm-mailroom (cross-repo)** — apply the v22/v23 champion prompts to the llm-mailroom pipeline project (Langfuse key file drop-in + `sync_langfuse_prompts.py --env-file`); regenerate its synced experiment log. | unclaimed | v0.18.0 | AGENTS.md "Langfuse projects" / "Mirror sync"; `scripts/eval/sync_langfuse_prompts.py` |
| KANBAN-006 | [#5](https://github.com/Exios66/llm-entity-extraction/issues/5) | `in_progress` | **HITL annotation queue processing** — work the pending llm-dojo queue items (extraction < 0.85 + sorter failure queue — 217 PENDING at last count): adjudicate, feed corrections into the next prompt iteration. Tooling fix (bounded `status` scan) landed 2026-08-14. | opencode (2026-08-14) | v0.18.0 | `scripts/eval/run_annotation_queue.py status`; wiki `Annotation-Queues.md` |
| KANBAN-008 | [#6](https://github.com/Exios66/llm-entity-extraction/issues/6) | `backlog` | **v23×max ko arm — production decision** — ko 0.8510 @ 2.6× cost, 0 parse errors vs v22×none 0.9512 overall. Decide/documented the recommended production config (or split: overall arm vs ko arm) and record it in README/AGENTS docs. | unclaimed | v0.18.0 | `V16_PROPOSITION.md` §15.1; memo `contracts_specialist_v23.md` |
| KANBAN-009 | [#7](https://github.com/Exios66/llm-entity-extraction/issues/7) | `backlog` | **Score-drift hygiene** — extend the same-scorer rescore pipeline beyond the 50-doc series if a scorer rule changes again; keep `reports/same_scorer_scores.json` current per run. | unclaimed | v0.18.0 | `scripts/reporting/rescore_manifests.py`; `tests/test_rescore_manifests.py` |
| KANBAN-011 | [#9](https://github.com/Exios66/llm-entity-extraction/issues/9) | `backlog` | **Post-v23 model sweep (gated OPEN)** — run v22/v23 prompts × {deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs to quantify the remaining model-bound segmentation gap (the v18 sweep proved scope-fidelity is model-agnostic; confirm the ko 0.85→0.89 plateau closes at the newest prompts). | unclaimed | v0.18.0 | memo `model_sweep_v18.md`; `V16_PROPOSITION.md` §9.3/§15 |

**Sweep rule:** when a release ships, re-target every non-done card to the
new `[Unreleased]` version and move landed cards to the Archive. (Last sweep:
v0.17.0 2026-08-15 — KANBAN-014/015/016 archived below; open cards
re-targeted to v0.18.0.)

## Discussion board

Dated, append-only log. Newest entry goes at the TOP. Format:
`**YYYY-MM-DD — <agent/human> — <card ref(s)>** <what happened / decision / question / blocker>`. No editing history.

- **2026-08-15 — opencode — KANBAN-018 claimed** The **prompt-engineer agent**
  (`prompt-engineer.md`) — the master diagnostic evaluator and prompt
  engineer — claimed `in_progress`. Its sole role: review every trace,
  reasoning trace, failure, error message, and result of evaluated prompts
  and produce stronger, refined, DATA-BACKED prompt mutations (new version
  keys) free of local plateaus and sample overfitting. The agent file
  encodes the repo's full iteration contract: the six-phase diagnose →
  root-cause → mutate → verify → land loop with the failure taxonomy,
  same-surface A/B discipline (bootstrap-CI verdicts), the plateau/overfit
  doctrine (rules for clusters, not 1-off outliers; generalization test;
  evidence floor on MAE/R² pair counts), board + CHANGELOG + memo close-out
  rules, and the version-key identity invariant. `AGENTS.md` gains the
  "Agents (this repo)" section documenting it alongside
  experiment-log-sync. Board-only card (single-session tooling, no issue).
- **2026-08-15 — opencode — KANBAN-015 close-out extended (final scope)** The
  card's shipped scope is now complete end-to-end: (1) **money MAE + span-count
  drift + support sizes** (money_mae_usd/median + per-field, span_count_mae/
  signed_mean + per-field + n_docs, date/duration/money_n_pairs — `src/metrics.py`,
  `parse_money` alias, 4 new tests); (2) **dedicated run-level diagnostics
  renderer** in `src/experiment_log.py` (`_diagnostics_lines`: list quality,
  regression error, span-count drift, error decomposition; `diagnostics`
  excluded from the generic nested-scores path) + **GH Pages run-detail
  diagnostics card** (`docs/assets/site.js` `diagnosticsCard()` + styles);
  (3) **scoring-method slide decks** `docs/slides/` (7 decks + index — worked
  example inputs/outputs + concise scientific explanations of every scoring
  method, for parallel researchers); (4) **real-pilot evidence** —
  `pilot_diag_v22_sample2` (2 docs, seed 42, master labels CSV active) whose
  diagnostics block (dates MAE 0 / R² 1.0; key_obligations 43 pred vs 18 exp
  → span-count +10.5, raw precision 0.31 = textbook over-extraction) is
  embedded in the decks; (5) docs updated (SCORING.md §4, README, AGENTS.md
  modules + gotcha, docs/README.md, wiki/Scoring.md + wiki synced).
  337 tests green, site render audit green. Chained-eval diagnostics remain
  out of scope (own runner, future card). Archive row updated.
- **2026-08-15 — opencode — KANBAN-017 claimed** term_length containment arm claimed `in_progress` (board-only): v24's leading-phrase rule caused the model to REPLACE the clause opener with the canonical duration phrase — the CUAD ground-truth span for Ediets IS the opener ("This Agreement will become effective as of the Effective Date and, unless sooner terminated pursuant to Sections 3.1"), so containment dropped 1.0→0.3333. Fix = `contracts_specialist_v25` (derived from v24, base untouched): the prefix is ADDITIVE, the ENTIRE verbatim term clause (opener first, exactly as written) must follow — never start at the duration phrase. Planned run: `qwen3.7-flash_contracts_specialist_v25_sample5` (seed 42, 5 docs, same surface as the v23/v24 A/B) — name reserved here.
- **2026-08-15 — opencode — v0.17.0 release sweep (KANBAN-014/015/016 done)** Board
  swept for the **v0.17.0** release (`scripts/release.py --bump minor`): the
  `[Unreleased]` block — full-corpus EDA (KANBAN-014), extraction regression
  diagnostics MAE+R²+span-drift+error-decomposition vs master labels
  (KANBAN-015, merged with the parallel edit), contracts specialist v24
  reasoning trace + metrics-aligned formats (KANBAN-016), AGENTS.md
  inter-agent workflow, sorter v9 full-509 benchmark, annotation-queue
  status fix — moved to `## [v0.17.0] - 2026-08-15`; pyproject bumped to
  0.17.0. Archive rows for 014/015/016 now read v0.17.0. Open cards
  (004/005/006/008/009/011/013) re-targeted **v0.17.0 → v0.18.0**. Tag +
  push + llm-mailroom mirror sync to follow.
- **2026-08-15 — opencode — KANBAN-016 done** Contracts specialist v24 landed in
  commit `6f77615` (v0.17.0 prep, CHANGELOG `[Unreleased]` Changed entry in the
  same commit, 341 tests green, Langfuse llm-dojo prompt store synced — v24
  mirrored). **Pilot A/B (seed 42, n=5, same surface):** v24 0.9336 vs v23
  0.9366 overall (noise), **key_obligations +10.2pp (0.5984→0.7006)**,
  reasoning trace on 5/5 rows both runs (schema-required — v24 entries are
  per-field structured: field/evidence/section_ref), date_n 5/5 + dur_n 2/2
  parseable pairs both runs, money_n 0 (no money GT in sample), tokens +2.5%
  (1,312 extra per run). Tradeoff documented: `term_length` containment
  dipped on 1 doc (Ediets 1.0→0.3333 — the leading-duration-phrase rule
  trades containment credit for parseability; monitored in the next arm).
  Issue #12 closed; card archived.
- **2026-08-15 — opencode — KANBAN-016 claimed** Contracts specialist v24 claimed `in_progress` (issue #12 opened first, cross-repo — llm-mailroom imports the agent): the extractor gains a REQUIRED per-field reasoning trace (`reasoning`: summary + entries[{field, evidence, section_ref}]) produced before finalizing the extraction, plus metrics-aligned format discipline so the new regression diagnostics (date/duration/money MAE + R² vs master labels) parse more pairs. Format alignment ONLY — the master CSV is eval ground truth and never reaches the model. Related but distinct from KANBAN-004 (span-residual arm). Planned runs: `{model}_contracts_specialist_v23_sample5` vs `{model}_contracts_specialist_v24_sample5` (seed 42, 5 docs) — names reserved here.
- **2026-08-14 — opencode — KANBAN-015 done (reconciliation: parallel-edit merge)** Extraction
  regression diagnostics landed in commit `91392ea` (v0.17.0 prep; CHANGELOG
  `[Unreleased]` Added + Changed entries in the same commit; 337 tests green).
  **Concurrent-edit note for future agents:** mid-session, a parallel edit
  landed in the same files (a diagnostics renderer in `src/experiment_log.py`,
  money-MAE + span-count-drift metrics in `src/metrics.py`, `parse_money`
  alias, `tests/test_experiment_log.py`, site display + regenerated
  `docs/data/*`) — this card's scope and the parallel scope overlapped. Per
  the anti-trampling protocol (AGENTS.md §4), both were MERGED, not reverted:
  the parallel agent's `UPDATES` commit swept the whole tree (my R² work +
  their renderer/metrics) into one coherent feature — R² + MAE for
  dates/durations, money MAE (USD), span-count drift, field error
  decomposition, pair counts, all tracked in `scores.diagnostics`
  (experiment-log JSONL + md render + GH Pages breakdown). Net effect: the
  merged commit is a superset of this card's scope. Chained-eval diagnostics
  remain out of scope (own runner, future card). Card archived.
- **2026-08-14 — opencode — KANBAN-015 claimed** Extraction regression diagnostics claimed `in_progress`: the working tree already holds uncommitted work with NO card (board rule 4) — `src/metrics.py` (date/duration MAE), `src/master_labels.py` (curated master-clauses CSV loader, default `../llm-mailroom/data/cuad/master_clauses.csv`), `field_scoring.parse_date` alias, `run_extraction_eval.py --master-labels` + diagnostics plumbing. This card ships that work PLUS **R² (coefficient of determination) as a tracked performance metric** (`duration_r2`, `date_r2`, per-field buckets), wires `scores.diagnostics` into the experiment log + GH Pages breakdown, adds network-free tests, and documents formulas in SCORING.md. Chained-eval diagnostics stay out of scope (own runner, future card).
- **2026-08-14 — opencode — KANBAN-014 done** Full-corpus CUAD EDA landed in
  commit `2fe4103` (v0.17.0 prep, CHANGELOG `[Unreleased]` Added entry in the
  same commit, 306 tests green): `data/eda/report.md` + `findings.md` +
  `figures/01`–`10`, driven by `scripts/eda/explore_cuad.py` (reproducible:
  `python scripts/eda/explore_cuad.py` from the repo root; Braintrust texts
  with local/CUAD fallback). Card archived.
- **2026-08-14 — opencode — KANBAN-014 claimed** Full-corpus EDA
  (510-contract CUAD) in progress: `scripts/eda/explore_cuad.py` rewritten
  (Braintrust full-corpus texts aligned 510/510 by title with local/CUAD
  fallback; restriction-family vs all-category span load; length-budget
  shares; co-occurrence; redaction scan) → outputs `data/eda/report.md`,
  `data/eda/findings.md`, `figures/01`–`10`. Key numbers: median 33,425
  chars, 17% over the 90k chunk window; `key_obligations` scope mean 16.0
  spans/doc (49 docs null); 131 docs carry `[***]` redaction markers;
  Anti-Assignment co-occurs with Change Of Control in 98% of the
  less-common docs. Committing with CHANGELOG `[Unreleased]` entry.
- **2026-08-13 — opencode — KANBAN-006 queue tooling fix** `status` was
  hanging: it scanned the FULL trace history for the item meta map
  (`list_extraction_traces(..., since=None)`), which stalls for minutes on
  the subtype task under Langfuse rate limits. Fixed: `--since-days` moved
  to the shared args (default 30, same as `build`) and `status` now bounds
  the scan — `run_annotation_queue.py` + regression test
  (`test_status_since_days_bounds_scan`); 306 tests green, CHANGELOG
  `[Unreleased]` Fixed entry added.
- **2026-08-13 — opencode — KANBAN-006 queue refresh** Rebuilt the llm-dojo
  annotation queue with the most recent run's failures: v9-scoped
  `build --task subtype` (session `qwen3.7-flash_sorter_v9_subtype_langfuse`,
  dedupes against the queue) enqueued **45 new sorter failures** (0 already
  present) — doc_type/subtype classification misses from the v9 full-corpus
  + A/B runs (05:00/05:12 UTC). Queue now **217 PENDING, 0 PROCESSED**
  (172 prior + 45). Note: `status --task subtype` hangs on the trace-meta
  scan (no `since` bound on `list_extraction_traces`) — items verified via
  direct queue-items read instead.
- **2026-08-13 — opencode — v0.16.0 release sweep (KANBAN-012/010 done; +KANBAN-013)** Board
  swept for the v0.16.0 release: **KANBAN-012 archived** — the sorter_v9 A/B
  landed (commit `6697ea9`): strict 0.8971→0.9259 (+2.88pp), v6→v9 +5.8pp,
  25→18 fails, all three title-wins clusters eliminated; issue #10 closed.
  Honest reading: ~0.93 is the practical plateau (18 fails = 1-off long
  tail) → follow-on **KANBAN-013** (tail-sampling iteration, issue #11).
  **KANBAN-010 archived as resolved-by-decision** — cost telemetry removal
  (`25aa942`) replaced "restore cost accounting": the site now intentionally
  omits detailed cost/usage data; issue #8 closed. Open cards (004/005/006/
  008/009/011) re-targeted v0.16.0 → v0.17.0. Issues #3–#7/#9 stay open;
  #2/#8/#10 closed. Changelog `[Unreleased]` completed (queue score-config,
  board + issue routing, board tab, cost-telemetry removal) ahead of the
  v0.16.0 tag.
- **2026-08-13 — opencode — board logic (issue routing + close criteria)** Board
  governance extended: (1) **GitHub issue routing formalized** (§8) —
  critical/high-priority/cross-repo cards route to issues with label
  `kanban`, opened FIRST in the repo where the work lands, and every synced
  card's `Issue` column MUST carry the full link to its own dedicated issue
  (`[#NNN](url)`) — one card = one issue, card↔issue status never disagrees;
  (2) **completion & issue-close criteria** (§7) — the six requirements to
  consider a task done AND its issue closable: verified work with clean
  `git status`, CHANGELOG entry in the same commit, card archived with
  version/commit/result, timestamped closing discussion entry, issue closed
  in the same commit as the archive, no orphaned scope. AGENTS.md rules 8
  and 12 updated to match. Sync sweep verified: issues #3–#10 open
  (↔ 8 open cards), #2 closed (↔ archived KANBAN-003).
- **2026-08-13 — opencode — board logic (all cards)** In-progress semantics
  enforced: **work underway = `in_progress`, never `backlog`** codified as
  procedure §4 (backlog = ZERO work started: no draft, no diff, no run in
  flight) + the status-transition table + status-lane definitions; AGENTS.md
  lifecycle gained the matching rule (rule 4) with the `git status` sanity
  check. Applied immediately: **KANBAN-012 moved `backlog`→`in_progress`**
  (owner opencode) — its `SORTER_PROMPT_V9` draft + test are in the working
  tree right now (`src/prompts.py`, `tests/test_prompts.py`), which made the
  `backlog` label false by definition. KANBAN-004's corrupted row (duplicate
  cells from a bad merge) repaired. Rule for all agents: label a card
  `in_progress` when the work starts, before the code — never after.
- **2026-08-13 — opencode — KANBAN-003/012 + site** Board sweep: sorter_v7
  A/B landed (KANBAN-003 archived — v7 wins +0.82pp strict 0.8765, commit
  `cbb5b93`; issue #2 closed) and the user-run v8 A/B recorded (v8 wins
  +2.06pp strict 0.8971, commit `43ef2ab`, development & IP clusters
  eliminated — proposition §17). New card KANBAN-012 (sorter_v9 title-wins
  draft, issue #10). The board is now ALSO rendered read-only on the
  experiment-log site under a `#/board` tab (`build_site.py` emits
  `docs/data/board.json`) — links to each card's GitHub issue.
- **2026-08-12 — opencode — board procedures (all cards)** Procedures
  formalized in "How to use this board": self-assignment order (comment →
  move to `in_progress` + Owner + date → reference in commits), the
  task-relation rule (work addressing a card's problem updates THAT card —
  never a parallel card or duplicate issue), the status-transition table
  (who may move each lane and when), and the GitHub-issue sync: all 8 open
  cards are now issues **#2–#9** (label `kanban`), each card↔issue pair must
  never disagree, close the issue in the same commit that archives the card.
  Cross-repo scope documented (this repo + llm-mailroom).
- **2026-08-12 — opencode — KANBAN-002/007/001** Working tree landed in one
  commit (this board's own bootstrap commit): regenerated experiment log
  (57 records) + site data (`build_site.py` — NOTE: `costs` meta absent, no
  activity CSV → KANBAN-010), registered `sorter_v7` in `PROMPT_VERSIONS`
  with its data-backed-rule test (18 prompt tests green), AGENTS.md board
  governance section, and the `[Unreleased]` changelog entry for sorter_v7.
  KANBAN-001 closed — registration is in; evaluation stays open as
  KANBAN-003.
- **2026-08-12 — opencode — KANBAN-007** v0.15.0 shipped: changelog
  dedup-repaired (the version conversion had duplicated the whole
  Unreleased block; every entry now appears exactly once), tag `v0.15.0` →
  `4b6ad5f` (commit `93eb938`), release published with dedicated notes at
  https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.15.0;
  `release.py --check` green at release time (303 tests). The release gate is
  clear — future agents can tag v0.16.0 directly.
- **2026-08-12 — board-bootstrap (opencode) — all cards** Board created and
  seeded from the live repo state: sorter_v7 WIP exists in the working tree
  (KANBAN-001), the tree is dirty with changelog/experiment-log/prompt
  changes (KANBAN-002), and v0.15.0 was released but not yet tagged on this
  tree (KANBAN-007). Open questions from `V16_PROPOSITION.md` promoted to
  cards KANBAN-003…KANBAN-009. Agents: claim before starting; post here on
  every material event.

## Archive (completed work — kept for auditability)

| Card | Shipped in | Commit / tag | Result |
|---|---|---|---|
| KANBAN-016 | v0.17.0 (2026-08-15) | commit `6f77615` | Contracts specialist v24: **required per-field reasoning trace** (schema `reasoning` object first, chunked merge unions entries, never scored, rides into log + Langfuse) + **metrics-aligned format discipline** (canonical duration phrase leads `term_length`, plain currency `contract_value`, ISO dates — format only, no master-CSV leakage). A/B seed 42 n=5: overall 0.9336 vs 0.9366 (noise), **key_obligations +10.2pp**, reasoning 5/5 rows, tokens +2.5%; term containment dip on 1 doc documented; issue #12 closed |
| KANBAN-015 | v0.17.0 (2026-08-15) | commits `91392ea` + follow-up | Extraction regression diagnostics shipped end-to-end: **R² + MAE tracked for dates/durations** (`date_r2`/`duration_r2` = 1 − SS_res/SS_tot, negative kept), **money MAE (USD)**, **span-count drift (MAE + signed mean)**, field error decomposition, pair counts — all in `scores.diagnostics` (JSONL + dedicated md-log section + GH Pages run-detail diagnostics card); `src/metrics.py` + `src/master_labels.py` (curated CSV preferred, raw clause-text fallback), `--master-labels`/`MASTER_LABELS_CSV` on both extraction runners; **scoring-method slide decks `docs/slides/`** (7 decks + index, worked examples incl. real pilot block `pilot_diag_v22_sample2`); SCORING.md §4 + README + AGENTS.md + wiki updated; 31+4 new tests, 337 total green |
| KANBAN-014 | v0.17.0 (2026-08-15) | commit `2fe4103` | Full-corpus CUAD EDA shipped: `scripts/eda/explore_cuad.py` + `data/eda/{report.md,findings.md,figures/01–10}` all git-tracked. Headlines: median 33,425 chars (max 338,211), 17.1% over the 90k chunk window, `key_obligations` scope mean 16.0 spans/doc (49 null docs), 131 docs with `[***]` redaction markers, Anti-Assignment+Change Of Control 98% co-occurrence |
| KANBAN-012 | v0.16.0 (2026-08-13) | commit `6697ea9` | sorter_v9 A/B landed: **v9 wins (+2.88pp strict, 0.9259)** — promotion/outsourcing/customization-schedule clusters eliminated, 25→18 fails, v6→v9 +5.8pp; ~0.93 practical plateau → follow-on KANBAN-013; issue #10 closed |
| KANBAN-010 | v0.16.0 (2026-08-13) | commit `25aa942` | **Resolved by decision** — site cost telemetry intentionally REMOVED (costs meta + per-run cost gone from `docs/data/`); "restore cost accounting" superseded; issue #8 closed |
| KANBAN-003 | v0.16.0 prep (2026-08-12) | commit `cbb5b93` | sorter_v7 250-doc A/B landed: **v7 wins (+0.82pp strict, 0.8765)** — promotion cluster fixed; issue #2 closed on sweep |
| *(user-run, no card)* — sorter_v8 A/B | v0.16.0 prep (2026-08-12) | commit `43ef2ab` | **v8 wins (+2.06pp strict, 0.8971)** on the 243-doc stratified surface — development & IP clusters eliminated; memo addendum + proposition §17 |
| KANBAN-007 | v0.15.0 (2026-08-12) | tag `v0.15.0` → `4b6ad5f`; commits `93eb938`, `0a4051e`, `0afdf2e` | Release finalized: changelog dedup-repaired, tag pushed, GitHub release with dedicated notes published; `release.py --check` green (303 tests) |
| KANBAN-002 | v0.16.0 prep (2026-08-12) | commit `ac156a5` | Dirty tree landed: experiment log regen (57 runs), site data regen, `sorter_v7` registration + test, AGENTS.md board governance, changelog `[Unreleased]` entry for sorter_v7 |
| KANBAN-001 | v0.16.0 prep (2026-08-12) | commit `ac156a5` | `SORTER_PROMPT_V7` constant + `PROMPT_VERSIONS["sorter_v7"]` + `test_sorter_v7_data_backed_rules` landed (18 prompt tests green). Evaluation tracked in KANBAN-003 |
| *(v0.15.0 content)* | v0.15.0 (2026-08-12) | tag `v0.15.0` | All v0.15.0 changelog entries (v18 sweep → v19 → v20 → v21 → v22 → v23 → v23×max; scorer fixes; annotation queues ×2; memos tab + 6 memos; wiki Langfuse-Traces + Annotation-Queues; rescore pipeline; two-project Langfuse strategy; prompt-store cleanup) — cataloged in CHANGELOG.md v0.15.0, each with its own commit in `git log v0.14.0..v0.15.0` |

When moving a card here: fill this table AND leave the lane row visible in
the Key Kanban table only if the card is still open; closed cards live ONLY
here (the table above holds open work, the archive holds the record).
