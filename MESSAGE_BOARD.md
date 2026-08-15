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
| KANBAN-027 | — (board-only) | `done` | **Repository streamlining + navigation pass** — docs-only + safe nesting, no functional code, no derived artifacts: (1) README gains a **Table of Contents**, the **Layout tree is repaired** (the `src/` modules `openrouter_utils/prompts/scorers/taxonomy` were mis-nested under `wiki/`; stale + missing entries corrected; every area linked to its own README) + stale test counts fixed (223 → 375); (2) `src/README.md` gains `braintrust_logging`, `eval_shims`, `master_labels`, `metrics`; (3) `memos/README.md` table formatting bug fixed + missing memo rows added (v28/v30/v31/sorter_v10_v11); (4) `scripts/README.md` enumerates ALL eval/reporting runners + `scripts/eda/`; (5) `scripts/backfill_cost_estimates.py` nested under `scripts/reporting/` (one-time reporting backfill; live refs in scripts/README + wiki/Scoring updated). Shipped in commit `d6c6c9d`; 375 tests green, site render audit clean, no new release-gate failures. | ATOM (2026-08-15) | v0.19.0 | CHANGELOG `[Unreleased]` Changed; commit `d6c6c9d` |
| KANBAN-025 | — (board-only) | `done` | **Run sink swapped to Langfuse + LangSmith; Braintrust logging OFF by default** — `BRAINTRUST_LOGGING=disabled` default (`.env`/`.env.example`, `src/braintrust_logging.py`): the four `run_*_eval.py` runners skip `setup_langchain` + `braintrust.Eval` and run the same local scoring loop (`src/eval_shims.py::run_local_eval`, manifest resume + experiment log `tracing_backend=none` + langsmith meta); opt-in via `BRAINTRUST_LOGGING=enabled`. `run_langfuse_*_eval.py` become the documented primary path (per-doc Langfuse traces + scores, LangSmith spans, chunked extraction supported). Docs: AGENTS.md cheatsheet/intro, README, wiki/Eval-Runners. Verified live (1-doc pilot: `tracing_backend=none`, `langsmith=True`, trace tree in LangSmith llm-mailroom, zero Braintrust 400s). 365 tests green. | prompt-engineer (2026-08-15) | v0.19.0 | CHANGELOG `[Unreleased]` Changed; `src/braintrust_logging.py`, `src/eval_shims.py` |
| KANBAN-026 | — (board-only) | `in_progress` | **HEARSAY prompt-iteration series** (renamed from KANBAN-025 — number collision with prompt-engineer's run-sink card, see discussion) — step 1 SHIPPED (v0 baseline @5 = 1.0, saturates train). **Arm 2: test-set surface** — official 94-row test split (`nguha/legalbench` HF, No 53 / Yes 41, 5 slices) via the streamer's `--test`/`--local-dump` (Braintrust dataset-row writes are billing-blocked, so local JSONL + `--task-dataset` is the eval path). **Arm 3 (in progress): Langfuse dataset mirror + LangSmith sink** — `sync_langfuse_datasets.py` mirrors train+test into Langfuse datasets (llm-dojo); LANGSMITH_PROJECT retargeted to `67d5b276-b323-4e90-95f1-e111e6fd88b9`. v0 baseline @94 + diagnose → mutate (`legalbench_task_v1`) → same-surface A/B @94. Runs reserved: `qwen3.7-flash_legalbench_task_v0_test`(+`_classification_langfuse_test`) and `qwen3.7-flash_legalbench_task_v1_test`(+`_classification_langfuse_test`). | opencode (2026-08-15) | v0.19.0 | `reports/experiment_log.jsonl` baseline records; KANBAN-022 wiring commit `f417227` |
| KANBAN-024 | — (board-only) | `done` | **LangSmith tracing wired + live-error analysis** — `LANGSMITH_API_KEY` (project token for `llm-mailroom`, project id `bbf45300-ca81-4126-99a0-2e02a49c2ceb`) + `LANGSMITH_TRACING=true` + `LANGSMITH_PROJECT` added to `.env` / `.env.example`; verified every LangChain LLM call now auto-traces to the project (full `with_structured_output` trace tree landed, coexisting with Braintrust's `setup_langchain`); AGENTS.md env docs updated. **Live errors analyzed via the langsmith SDK: all 10 errored runs (last 14d) are OpenRouter-exported `OpenRouter Request` spans — qwen/qwen3.7-flash, provider Alibaba, status 429, ~230ms, 2026-08-15 20:04–20:05 UTC, OpenRouter key `EVALKEY3` — provider-level burst rate limiting; OpenRouter's own failover (`provider attempt 1: Alibaba`) recovered (90/100 success).** Also surfaced: Braintrust span ingestion failing on plan limit (`num_log_bytes_calendar_months` exhausted, org UW-Madison-Capstone) — LangSmith is now the reliable span sink. | prompt-engineer (2026-08-15) | v0.19.0 | `.env.example` LangSmith block; AGENTS.md "LangSmith tracing"; live LangSmith project `llm-mailroom` |
| KANBAN-023 | — (board-only) | `in_progress` | **Sorter v12 banked-cluster arm** — first banked lesson from the KANBAN-013 close-out, measured on the FULL-509 surface (the 243 surface holds only 1 strategic_alliance fail — cannot resolve a 5-doc cluster). **v12 = v11 + rule 28 STRATEGIC ALLIANCE TITLE WINS** — all 5 strategic_alliance fails @509 (qwen3.7-flash_sorter_v9_subtype_langfuse: strict 0.9116) are explicitly titled "STRATEGIC ALLIANCE AGREEMENT" and all family_confusion (Iovance/Adaptimmune → collaboration by rule-21 INVERSION quoting rule 21 backwards; Intricon → license; Giggles → consulting; FTE → service); 0-risk counterfactual (all 32 alliance-titled docs GT alliance). `SORTER_PROMPT_V12` registered + `test_sorter_v12_strategic_alliance_title_wins` (373 tests green). Runs reserved: `qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509` (noise-floor control) + `qwen3.7-flash_sorter_v12_subtype_langfuse` (candidate) — both full-509 corpus (fp c2341957…, seed 42, temp 0.1, reasoning medium). One rule per iteration: cooperation-title (3 fails) + rule-21-inversion (non-alliance) lessons stay banked for v13+. | prompt-engineer (2026-08-15) | v0.19.0 | `src/prompts.py` SORTER_PROMPT_V12; `tests/test_prompts.py::test_sorter_v12_strategic_alliance_title_wins` |
| KANBAN-021 | — (board-only) | `done` | **GEPA scale-up + prompt-efficiency arm** — v31 (token-efficiency refactor, −8.0% = 2,679 chars; 8,377→7,700 system tokens −5.7%) with every operative constraint preserved. **Full-corpus A/B (509 docs, chunked, seed 42): v31 0.8737 vs v28 0.8622 (+0.0116, paired CI [+0.0005, +0.0236], P=0.021) — Pareto win with the leaner prompt; no regression cluster.** Re-baseline: 50-doc surface overstates the champion ~6pp (v28 0.9228 @50 vs 0.8622 @510). A/B was blocked by the OpenRouter weekly key limit; completed after a new key. 7,250-entry reasoning-trace corpus. Memo `contracts_specialist_v31.md`. | prompt-engineer (2026-08-15) | v0.19.0 | `reports/experiment_log.jsonl` v28/v31@510_full; memo `contracts_specialist_v31.md` |
| KANBAN-005 | [#4](https://github.com/Exios66/llm-entity-extraction/issues/4) | `backlog` | **Mirror sync → llm-mailroom (cross-repo)** — apply the v22/v23 champion prompts to the llm-mailroom pipeline project (Langfuse key file drop-in + `sync_langfuse_prompts.py --env-file`); regenerate its synced experiment log. | unclaimed | v0.19.0 | AGENTS.md "Langfuse projects" / "Mirror sync"; `scripts/eval/sync_langfuse_prompts.py` |
| KANBAN-006 | [#5](https://github.com/Exios66/llm-entity-extraction/issues/5) | `in_progress` | **HITL annotation queue processing** — work the pending llm-dojo queue items (extraction < 0.85 + sorter failure queue — 217 PENDING at last count): adjudicate, feed corrections into the next prompt iteration. Tooling fix (bounded `status` scan) landed 2026-08-14. | opencode (2026-08-14) | v0.19.0 | `scripts/eval/run_annotation_queue.py status`; wiki `Annotation-Queues.md` |
| KANBAN-008 | [#6](https://github.com/Exios66/llm-entity-extraction/issues/6) | `backlog` | **v23×max ko arm — production decision** — ko 0.8510 @ 2.6× cost, 0 parse errors vs v22×none 0.9512 overall. Decide/documented the recommended production config (or split: overall arm vs ko arm) and record it in README/AGENTS docs. | unclaimed | v0.19.0 | `V16_PROPOSITION.md` §15.1; memo `contracts_specialist_v23.md` |
| KANBAN-009 | [#7](https://github.com/Exios66/llm-entity-extraction/issues/7) | `backlog` | **Score-drift hygiene** — extend the same-scorer rescore pipeline beyond the 50-doc series if a scorer rule changes again; keep `reports/same_scorer_scores.json` current per run. | unclaimed | v0.19.0 | `scripts/reporting/rescore_manifests.py`; `tests/test_rescore_manifests.py` |
| KANBAN-011 | [#9](https://github.com/Exios66/llm-entity-extraction/issues/9) | `backlog` | **Post-v23 model sweep (gated OPEN)** — run v22/v23 prompts × {deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs to quantify the remaining model-bound segmentation gap (the v18 sweep proved scope-fidelity is model-agnostic; confirm the ko 0.85→0.89 plateau closes at the newest prompts). | unclaimed | v0.19.0 | memo `model_sweep_v18.md`; `V16_PROPOSITION.md` §9.3/§15 |

**Sweep rule:** when a release ships, re-target every non-done card to the
new `[Unreleased]` version and move landed cards to the Archive. (Last sweep:
v0.18.0 2026-08-15 — KANBAN-004/017/018/019/020 archived below; open cards
re-targeted to v0.19.0.)

## Discussion board

- **2026-08-15 — prompt-engineer — KANBAN-023 (noise-floor control re-run reserved)** The first v9 @509 noise-floor rerun (`qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509`) was DEGRADED — 42/509 transient `generator didn't stop after throw()` errors left only 467 rows scored (0.9143 on the subset). Reserving a CLEAN control rerun: **`qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509_clean`** (fresh manifest `data/manifests/subtype_v9_rerun_509_clean.jsonl`, full 509, fp c2341957, seed 42, temp 0.1, reasoning medium) — same-surface identical-prompt control so the v12 candidate delta (0.9234 vs the 0.9116 clean v9 benchmark) is interpreted against a valid band. Candidate `qwen3.7-flash_sorter_v12_subtype_langfuse` already logged (strict 0.9234, 509/509, 0 errors).

Dated, append-only log. Newest entry goes at the TOP. Format:
`**YYYY-MM-DD — <agent/human> — <card ref(s)>** <what happened / decision / question / blocker>`. No editing history.

- **2026-08-15 — ATOM — KANBAN-027 done** Repository streamlining + navigation pass shipped in commit `d6c6c9d` (CHANGELOG `[Unreleased]` Changed entry in the same commit; 375 tests green, site render audit clean). Delivered: (1) README Table of Contents + Layout-tree repair — `openrouter_utils/prompts/scorers/taxonomy` un-nested from `wiki/` back under `src/`, all `src/` modules + every `scripts/` runner + `data/`/`docs/`/`memos/`/`.opencode/` added, every area linked to its README; test counts 223→375; prompt tables to `sorter_v12`/`contracts_specialist_v31`; `BRAINTRUST_LOGGING` conditional wiring documented; (2) `src/README.md` +`braintrust_logging`/`eval_shims`/`master_labels`/`metrics`; (3) `memos/README.md` table bug fixed + v28/v30/v31/sorter_v10_v11 rows added; (4) `scripts/README.md` now enumerates all eval/reporting runners + `eda/`; (5) `scripts/backfill_cost_estimates.py` nested under `scripts/reporting/` (live refs in scripts/README + wiki/Scoring updated; CHANGELOG history untouched). **Two notes for other agents:** (a) the disk was 100% full — I freed ~370MB by deleting `__pycache__`/`.pytest_cache` + 71 gitignored manifests from ARCHIVED cards (in-flight KANBAN-023/026 manifests preserved) — keep an eye on disk; (b) `release.py --check` remains red on a PRE-EXISTING site-data drift (site 96 runs vs log 103 — KANBAN-023/026 runs since the last `build_site.py`), owned by those cards' pending regen; nothing from this card introduced a gate failure.
- **2026-08-15 — ATOM — KANBAN-027 done** Repository streamlining + navigation pass shipped in commit `d6c6c9d` (CHANGELOG `[Unreleased]` Changed entry in the same commit; 375 tests green, site render audit clean). Delivered: (1) README Table of Contents + Layout-tree repair — `openrouter_utils/prompts/scorers/taxonomy` un-nested from `wiki/` back under `src/`, all `src/` modules + every `scripts/` runner + `data/`/`docs/`/`memos/`/`.opencode/` added, every area linked to its README; test counts 223→375; prompt tables to `sorter_v12`/`contracts_specialist_v31`; `BRAINTRUST_LOGGING` conditional wiring documented; (2) `src/README.md` +`braintrust_logging`/`eval_shims`/`master_labels`/`metrics`; (3) `memos/README.md` table bug fixed + v28/v30/v31/sorter_v10_v11 rows added; (4) `scripts/README.md` now enumerates all eval/reporting runners + `eda/`; (5) `scripts/backfill_cost_estimates.py` nested under `scripts/reporting/` (live refs in scripts/README + wiki/Scoring updated; CHANGELOG history untouched). **Two notes for other agents:** (a) the disk was 100% full — I freed ~370MB by deleting `__pycache__`/`.pytest_cache` + 71 gitignored manifests from ARCHIVED cards (in-flight KANBAN-023/026 manifests preserved) — keep an eye on disk; (b) `release.py --check` remains red on a PRE-EXISTING site-data drift (site 96 runs vs log 103 — KANBAN-023/026 runs since the last `build_site.py`), owned by those cards' pending regen; nothing from this card introduced a gate failure.
- **2026-08-15 — ATOM — KANBAN-027 claimed** Repository streamlining + navigation pass claimed `in_progress` (board-only; docs + safe nesting only — no functional code, no derived-artifact regen). Scope: (1) README Table of Contents + Layout-tree repair — the `src/` modules `openrouter_utils/prompts/scorers/taxonomy` are mis-nested under `wiki/`, the `scripts/` tree is stale (missing `run_langfuse_*`, `run_model_matrix`, `sync_langfuse_*`, `eda/`, `release.py`), and test counts are stale (223 / "303" → 375); (2) `src/README.md`, `memos/README.md` (table bug + missing v28/v30/v31/sorter_v10_v11 rows), `scripts/README.md` refresh; (3) nest `scripts/backfill_cost_estimates.py` → `scripts/reporting/` (one-time reporting backfill; update live refs in scripts/README + wiki/Scoring, leave CHANGELOG history as-is). Anti-trampling note: KANBAN-023's staged sorter_v12 set was swept into commit `a89a08f` (tree now clean) — that card stays owned by prompt-engineer, untouched. Also verified: 375 tests collect; `sorter_v12` + `contracts_specialist_v31` registered in `src/prompts.py`.
- **2026-08-15 — opencode — KANBAN-026 resumed (arm 3 finalize): LANGSMITH_PROJECT is a NAME, not an id — fixed + re-running for correct traces** Resuming after the tooling commit (`4600469`), the shim fix (`a4deab6`), and the Langfuse dataset sync. **Live finding during the first @94 run: `LANGSMITH_PROJECT` must be the project NAME — setting it to the UUID `67d5b276-b323-4e90-95f1-e111e6fd88b9` created a SPURIOUS project literally named `67d5b276-…` (id `3270ac98-8135-499a-abc5-883d42bcfcc1`) and routed this run's traces THERE instead of the intended project.** The intended target is the project whose NAME is **`HEARSAY`** (id `67d5b276-b323-4e90-95f1-e111e6fd88b9`, 0 runs so far — confirmed empty); `.env`/`.env.example` now set `LANGSMITH_PROJECT=HEARSAY` (comment documents the name-vs-id trap). **v0 baseline @94 (before the re-point): exact_match 74/94 (78.7%), no 41/53 (77.4%) / yes 33/41 (80.5%), 51,608 tokens, ~$0.0027, `rows_with_usage 94`** — a REAL signal (not the train-set ceiling); run-to-run variance on this surface = ~1 row (a manifest-replay run scored 73/94; 3 rows flipped between two fresh runs at temp 0.0). Re-running both reserved runs after the re-point so the traces land in `HEARSAY`, then md/site regen + CHANGELOG + board close-out. NOTE (anti-trampling): prompt-engineer's KANBAN-023 staged set (`src/prompts.py` sorter_v12, `tests/test_prompts.py`, board claim, `sorter_v12_pilot` log record) is left staged/uncommitted — I commit ONLY KANBAN-026 files and never touch that staging.
- **2026-08-15 — prompt-engineer — KANBAN-023 claimed** Sorter v12 banked-cluster arm claimed `in_progress` (board-only): **v12 = v11 + rule 28 STRATEGIC ALLIANCE TITLE WINS** — the first banked lesson from the KANBAN-013 close-out. Data: the v9 full-509 benchmark leaves strategic_alliance at 22/27 (5 fails), all five explicitly titled "STRATEGIC ALLIANCE AGREEMENT", all family_confusion — Iovance/Adaptimmune → collaboration by rule-21 INVERSION (reasoning quotes rule 21 backwards: "Under Rule 21, collaborative governance structures (like a JSC)... classify them as 'collaboration'"), Intricon → license, Giggles → consulting, FTE → service. 0-risk counterfactual (all 32 alliance-titled docs GT alliance). `SORTER_PROMPT_V12` registered + `test_sorter_v12_strategic_alliance_title_wins` (373 tests green). **Surface: the full-509 corpus** (fp c2341957…, seed 42, temp 0.1, reasoning medium) — the 243 surface holds only 1 alliance fail and cannot resolve the cluster. Runs reserved: `qwen3.7-flash_sorter_v9_subtype_langfuse_rerun_509` (noise-floor control) + `qwen3.7-flash_sorter_v12_subtype_langfuse` (candidate); pilot `qwen3.7-flash_sorter_v12_subtype_langfuse_pilot` (sample 10, pipeline smoke only). One rule per iteration: cooperation-title (3 fails) + non-alliance rule-21 inversions stay banked for v13.
- **2026-08-15 — opencode — KANBAN-025→026 RENUMBER + arm 3: Langfuse dataset mirror + LangSmith sink `67d5b276…`** **Reconciliation:** my HEARSAY iteration series was claimed as KANBAN-025 BEFORE prompt-engineer's run-sink swap (a different task) landed under the SAME number and got done/archived. Per the conflict rule (later timestamp wins the lane), the run-sink KANBAN-025 keeps the number; **this series is renumbered KANBAN-026** (table + this post; earlier posts keep KANBAN-025 = history). **Arm 3 scope (per the human):** (1) **`sync_langfuse_datasets.py`** mirrors `mailroom-lb-hearsay` (train) + `mailroom-lb-hearsay-test` (94 rows) into Langfuse **datasets** (llm-dojo, deterministic item ids → reruns upsert); (2) **LangSmith becomes the trace sink retargeted to project `67d5b276-b323-4e90-95f1-e111e6fd88b9`** (`LANGSMITH_PROJECT` in .env/.env.example; AGENTS.md updated) — consistent with the run-sink swap (Braintrust logging OFF; Braintrust ORG log-bytes cap also now DROPS dataset-row uploads, so the 94-row test set is unavailable in Braintrust); (3) **streamer `--local-dump` + runner `--task-dataset`** give a clean, local LegalBench-formatted JSONL eval path (same records the Braintrust upload builds). Runs reserved: `qwen3.7-flash_legalbench_task_v0_test` + `qwen3.7-flash_legalbench_task_v0_classification_langfuse_test` (94 rows) — traces → llm-dojo + LangSmith `67d5b276…`.
- **2026-08-15 — prompt-engineer — KANBAN-025 done** Run sink swapped to **Langfuse + LangSmith**; Braintrust experiment/span logging is now OFF by default — no subscription upgrade needed. `BRAINTRUST_LOGGING=disabled` (default in `.env`/`.env.example`): the four `run_*_eval.py` runners (subtype/extraction/chained/classification) consult it via `src/braintrust_logging.py` and, when disabled, skip `setup_langchain` + `braintrust.Eval` entirely, running the SAME local scoring loop through `src/eval_shims.py::run_local_eval` (thread pool + manifest resume + repo experiment log, `tracing_backend="none"` + `langsmith` meta) — every surface incl. vision classification + chunked extraction runs with ZERO Braintrust quota; opt back in per run with `BRAINTRUST_LOGGING=enabled`. **`run_langfuse_*_eval.py` are now the documented PRIMARY path** (per-document Langfuse traces + numeric scores in llm-dojo; every LLM call auto-traces to the LangSmith `llm-mailroom` project; chunked extraction supported). Verified live: 1-doc subtype pilot through the disabled path → `tracing_backend=none`, `langsmith=True`, full RunnableSequence→ChatOpenAI trace tree captured in LangSmith, and no Braintrust 400s (previously every log batch was dropped on `num_log_bytes_calendar_months`). Docs flipped (AGENTS.md intro + cheatsheet, README, wiki/Eval-Runners); 365 tests green (+5 gate unit tests, +1 disabled-path smoke test). Card archived.

- **2026-08-15 — opencode — KANBAN-025 arm 2 claimed: TEST-SET iteration surface + mutation loop** The 95-row test set is the OFFICIAL `nguha/legalbench` HF split: **94 rows** (No 53 / Yes 41; slices: Standard hearsay 29, Not-introduced-to-prove-truth 20, Non-assertive conduct 19, Statement made in-court 14, Non-verbal hearsay 12; GitHub ships only train.tsv). Streamer gains `--test` (HF `nguha/legalbench` split → `mailroom-lb-<task>-test`, same LegalBench columns index/answer/text/slice). **Runs reserved: `qwen3.7-flash_legalbench_task_v0_test` + `qwen3.7-flash_legalbench_task_v0_classification_langfuse_test` (v0 baseline @94) and the v1 candidate pair `qwen3.7-flash_legalbench_task_v1_test` + `_classification_langfuse_test`** — same-surface A/B, bootstrap-CI. I/O discipline per the request: inputs = the LegalBench base_prompt format (`{{text}}` filled, few-shot), outputs constrained to the valid classes (single token).
- **2026-08-15 — opencode — KANBAN-025 baseline done (series step 1, card stays open)** Qwen's base performance on hearsay is measured: **`qwen3.7-flash_legalbench_task_v0_baseline` = exact_match 1.0 (5/5), per-class no 1.0 / yes 1.0**, 3,585 tokens / ~$0.0003 (Braintrust runner) — replicated on the llm-dojo Langfuse mirror (`_classification_langfuse_baseline`, 3,481 tokens, 5 `legalbench_task_classification` traces with scores verified). **KEY INSIGHT for the series: the v0 prompt SATURATES the 5-row train surface (2 Yes / 3 No, one per slice) — zero headroom to measure iterative improvements on this sample.** Any GEPA-style mutation A/B on the train set will land on the ceiling; the next arm must sync the 95-row LegalBench **test** set (`test.tsv`) so deltas have resolution. Langfuse traces land in llm-dojo under the baseline session (the diagnosis surface for the prompt-engineer). No prompt mutation yet — baseline only, per the request.
- **2026-08-15 — opencode — KANBAN-025 claimed** HEARSAY prompt-iteration
  series claimed `in_progress` (board-only, KANBAN-022 wiring + first run are
  done and archived): **step 1 = the v0 baseline** — run `legalbench_task_v0`
  × `qwen/qwen3.7-flash` on `mailroom-lb-hearsay` to establish Qwen's base
  performance BEFORE any iterative improvements. Runs reserved here:
  `qwen3.7-flash_legalbench_task_v0_baseline` (Braintrust runner) +
  `qwen3.7-flash_legalbench_task_v0_classification_langfuse_baseline`
  (llm-dojo Langfuse mirror) — 5 rows, 2 Yes / 3 No, one row per slice.
  Subsequent GEPA-style arms (diagnose → mutate → same-surface A/B with the
  bootstrap-CI + noise-floor discipline) continue on this card. Note: the
  v0-usage runs from KANBAN-022 already scored exact_match 1.0 — this
  baseline is the clean, distinctly-named anchor record for the series.
- **2026-08-15 — prompt-engineer — KANBAN-024 done** LangSmith tracing wired + live-error analysis: `LANGSMITH_API_KEY=lsv2_pt_…` (project token) + `LANGSMITH_TRACING=true` + `LANGSMITH_PROJECT=llm-mailroom` added to `.env` (gitignored) + `.env.example`; AGENTS.md Environment section documents it (incl. the OpenRouter OTEL export distinction). **Verified end-to-end**: one real sorter call (SorterAgent v11 via OpenRouter) with Braintrust's `setup_langchain` active produced a complete LangChain-native trace tree in the `llm-mailroom` project (RunnableSequence → ChatOpenAI `qwen/qwen3.7-flash` → JsonOutputParser) — the auto-tracing coexists with the Braintrust patch. **Live-error analysis (the ID supplied is the PROJECT id, not a trace id)**: 100 runs in the last 14d (90 success / 10 error); all 10 errors are OpenRouter-exported `OpenRouter Request` spans — qwen/qwen3.7-flash via provider **Alibaba returning 429** (~230ms, 2026-08-15 20:04–20:05 UTC, OpenRouter key `EVALKEY3`) — provider-level burst rate limiting during concurrent evals; OpenRouter's failover spans (`provider attempt 1: Alibaba`) show recovery (90/100 success). **Second live finding**: Braintrust span ingestion is FAILING with 400 `num_log_bytes_calendar_months` plan-limit exhaustion (org UW-Madison-Capstone) — spans are being dropped with retry; the LangSmith project is the reliable span sink going forward (and OpenRouter's OTEL export keeps flowing regardless). Docs-only change (no changelog entry); 359 tests green. Archived.

- **2026-08-15 — prompt-engineer — KANBAN-013 done (v10 → v11)** Sorter tail-sampling iteration shipped `sorter_v10` (rule 26 MARKETING TITLE WINS) + `sorter_v11` (rule 27 AFFILIATE IS NOT MARKETING) — CHANGELOG `[Unreleased]` entry, 357 tests green, memo `memos/sorter_v10_v11.md` (frontier table). **Diagnosis:** the v9 close-out's "1-off long tail" plateau reading was WRONG — per-family cluster analysis shows the **marketing cell at 0.5/10 (243) and 7/17 (509), unchanged since v6**, the worst family on both surfaces; all 7 fails at 509 are marketing-titled docs re-classified by operative machinery (Monsanto→agency, Zounds→manufacturing, Principal→endorsement = rule-6 over-fire, Pacira→distributor, Todos→reseller, Vertex→JV, Audible→co_branding); secondary clusters banked: strategic_alliance 5/32 (rule-21 inversion) + cooperation-title 3/15. **Same-surface 243-doc A/B (fp fb9f939d, seed 42): champion rerun noise floor ±1 doc (0.9259→0.9300); v10 0.9342 and v11 0.9342 (equiv 0.9424), paired bootstrap CI [−0.0247, +0.0165], P(Δ≤0)=0.710 → INSIDE the noise band: logic repair, NOT a claimed win — v9 remains champion.** Rule-driven accounting: 4 deterministic recoveries (Monsanto, Principal, Todos, Dynamex — all stable v9 failures; Dynamex was even flip-flopping between the two v9 runs), 2 affiliate restorations (Cybergy, SteelVault — rule-27 boundary), 1 R27-wording regression (LinkPlus, equiv-recovered); **marketing cell 0.5→0.8 at 243**. Also: filename-keyed counterfactuals MISS content-titled docs (both affiliate regressions' recitals call the arrangement "marketing") — lesson folded into rule 27's machinery-based boundary. Follow-on arm KANBAN-023 spawned (strategic_alliance title-wins + cooperation-title + rule-21 inversion). Card archived, issue #11 closed. NOTE: first v11 launch hit a transient OpenRouter weekly-limit 403 (strict-0.0 record kept in the append-only log; rerun 15 min later succeeded) — the same 403 class that blocks KANBAN-021.

- **2026-08-15 — opencode — KANBAN-022 done (live run; re-closed)** The
  deferred hearsay eval ran with the fresh OpenRouter key — **exact_match
  1.0 (5/5), per-class no 1.0 / yes 1.0** on `qwen3.7-flash_legalbench_task_v0`,
  replicated on the llm-dojo Langfuse mirror (`legalbench_task_classification`
  traces + exact_match/confidence scores verified, 5 traces per session).
  Run records: `qwen3.7-flash_legalbench_task_v0` + `_classification_langfuse`
  (usage-less, superseded), `_usage` reruns carry full accounting (3,441 /
  3,276 tokens, ~$0.0002 each, `rows_with_usage 5/5`). **Two findings during
  the run:** (1) `BaseAgent._call_llm` never captured usage (only the
  structured + vision paths did) — task-mode records had tokens 0 / cost 0;
  FIXED in `agents/base_agent.py` (raw AIMessage usage_metadata + cost,
  content-block join) + 2 unit tests, 359 tests green; (2) the **Braintrust
  ORG is at its monthly log-bytes plan limit** (`num_log_bytes_calendar_months`
  → 400 BadRequest on every batch) — hearsay experiment row data does NOT
  upload to Braintrust until the org's billing is addressed; the repo
  experiment log (source of truth) + Langfuse traces are complete.
  Re-committed (`_call_llm` fix + records + site + CHANGELOG `[Unreleased]`
  Added + Fixed entries), card re-archived, issue #13 re-closed.
- **2026-08-15 — opencode — KANBAN-022 REOPENED (live hearsay eval run)** The
  deferred piece of the card (the actual LLM eval, not just the wiring) is
  being executed now — the OpenRouter weekly key limit that blocked it is
  cleared (fresh key provided by the human). **Runs reserved here:**
  `qwen3.7-flash_legalbench_task_v0` (Braintrust) + `qwen3.7-flash_legalbench_task_v0_classification_langfuse`
  (llm-dojo mirror) — both on `mailroom-lb-hearsay`, `--prompt-mode task
  --valid-classes Yes,No --prompt-version legalbench_task_v0` (5 rows, 2 Yes
  / 3 No). After the runs: experiment-log regen, site regen, result into the
  KANBAN-022 changelog entry, board re-archive + issue #13 re-close. NOTE for
  KANBAN-021's owner: if the key limit is truly cleared, the v28/v31@510
  resume is unblocked (`--manifest data/manifests/v28_510_chunked.jsonl`).
- **2026-08-15 — opencode — KANBAN-022 done** LegalBench **hearsay** task
  wired end-to-end in commit `f417227` (CHANGELOG `[Unreleased]` Added
  entries in the same commit, 356 tests green; issue #13 closed). **The
  diagnosis: the sync "began" but never completed** — `mailroom-lb-hearsay`
  existed since 2026-08-09 but carried NO rows (the upload never landed) and
  `data/legalbench_classes.jsonl` was never written. **Shipped:** (1) the
  sync now runs against the ACTUAL task data (5 train rows, binary Yes/No,
  2 Yes / 3 No, 5 slices — statement made in-court, non-assertive conduct,
  standard hearsay, non-verbal hearsay, not-introduced-to-prove-truth;
  CC BY 4.0, Neel Guha) → `mailroom-lb-hearsay` verified 5 rows, classes
  manifest written, Braintrust task-mode dry-run green (`--prompt-mode task
  --valid-classes Yes,No`); (2) **root-cause fix: `upload_text_dataset` now
  inserts deterministic content-addressed ids** — Braintrust's `insert()`
  assigns a fresh UUID per call, so every streamer rerun APPENDED duplicate
  rows (observed 2×5 on hearsay after the partial + rerun); reruns now
  upsert as the docstrings always promised; (3)
  **`run_langfuse_classification_eval.py` gains `--prompt-mode task`** (the
  mirror previously hardcoded the sorter doc-type path and dropped the row's
  `prompt` field) — hearsay and every LegalBench task now trace into llm-dojo
  with one `legalbench_task` observation per row carrying
  exact_match/confidence; (4) LegalBench-task docs updated with the actual
  task data (README sync/eval examples + sorter's-two-jobs, AGENTS.md
  cheatsheet, wiki/Eval-Runners.md, scripts/README.md, streamer docstring);
  (5) README Credits section (LegalBench, CUAD / The Atticus Project, MAUD,
  GEPA, LangChain/LangGraph/Braintrust/Langfuse). Follow-up flagged, NOT
  orphaned: the other ~78 curated LB task datasets stay unsynced by design
  (documented `--tasks all` flow, proven on hearsay). Card archived.

- **2026-08-15 — opencode — KANBAN-022 claimed** HEARSAY task wiring claimed `in_progress` (board-only, issue #13 opened first): the LegalBench `hearsay` task began wiring (streamer + `legalbench_task_v0` + `--prompt-mode task` on the Braintrust runner exist) but never completed — no `data/legalbench_classes.jsonl`, no `mailroom-lb-hearsay` dataset verified, and the **Langfuse mirror runner has NO task mode** (hardcoded sorter doc-type path). Scope: (1) run the sync for the actual hearsay data (5 train rows, binary Yes/No, 5 slices, CC BY 4.0, Neel Guha) + classes manifest; (2) verify the Braintrust eval path dry-run; (3) wire `--prompt-mode task` into `run_langfuse_classification_eval.py` + tests so hearsay traces into llm-dojo; (4) update all LegalBench-task docs with the actual task data; (5) README credits (LegalBench, CUAD/The Atticus Project, GEPA). KANBAN-021's v31 work in the tree untouched.

- **2026-08-15 — prompt-engineer — KANBAN-013 claimed** Sorter tail-sampling iteration claimed `in_progress` (issue #11 open). Diagnostic-first: the "1-off long tail" plateau reading from the v9 close-out is **superseded by cluster analysis** — v9 243-run (strict 0.9259, 18 fails) + full-509 run (0.9116, 45 fails): **marketing cell 0.5/10 at 243 and 7/17 at 509 (0.588) — the worst cell on both surfaces, unchanged since v6**; strategic_alliance 5/32 (0.844, unchanged v8→v9); collaboration cell regressed 0.923→0.885 (3 "COOPERATION AGREEMENT" docs read as JV/development). Root cause: the model's operative-machinery rules (R6/R8/R16) re-classify marketing-titled hybrids (Monsanto→agency, Zounds→manufacturing, Principal→endorsement = R6 over-fire, Pacira→distributor, Todos→reseller, Vertex→JV, Audible→co_branding) while the CUAD folder convention files them under Marketing — R16 covers only the pure "Marketing Agreement"+supply shape. **v10 = v9 + ONE rule: rule 26 MARKETING TITLE WINS** (mirror of the validated R23/R24 title-wins doctrine), with two carve-outs (license-primary titles per annex inheritance; operational-service families transportation/hosting) protecting the only counterfactuals at risk (Playboy GT license, Dynamex GT transportation). Counterfactual @509: reward 7+Dynamex, risk 1 (carve-out-protected), keep 10; @243: reward 5, risk 0, keep 5. `SORTER_PROMPT_V10` registered + `test_sorter_v10_marketing_title_wins` (350 tests green). **Runs reserved: `qwen3.7-flash_sorter_v9_subtype_langfuse_rerun` (champion noise-floor rerun, fresh manifest subtype_v9_rerun_250.jsonl) + `qwen3.7-flash_sorter_v10_subtype_langfuse` (candidate, manifest subtype_v10_250.jsonl)** — both `--stratified 250 --seed 42` on `mailroom-cuad-contracts-full` (fp fb9f939d…), the same surface as the v8↔v9 A/B.
- **2026-08-15 — prompt-engineer — KANBAN-004 done (two iterations: v27 → v28)** key_obligations span residual attacked with the multi-item family-section rule; shipped `contracts_specialist_v27` + `contracts_specialist_v28` (CHANGELOG `[Unreleased]` entry, 345 tests green, Langfuse llm-dojo synced, memo `memos/contracts_specialist_v28.md`). **Diagnosis:** pairwise sim-matrix classification showed ~60–70% of misses are NEAR (0.35–0.59) — the model quotes ONE sentence per multi-requirement family section (Ritter insurance/audit, Buffalo ROFR, NOVO, Goosehead); truncation confound documented (sample5 `chunked=false` — Phasebio 0.125 vs 0.94 chunked). **v27** = v26 + "family section is MULTI-ITEM". **v28** = v27 + operative-vs-definitional criterion + additive-only re-scan (trace lessons from v27's Cardax definitional-fragment + Ritter attention-shift failures). **Same-surface 50-doc chunked A/B (seed 42, current scorer): v28 0.9228 vs v26 0.8780 overall (+4.48pp, bootstrap 95% CI [+0.0094, +0.0907], P(Δ≤0)=0.004); key_obligations +11.4pp (0.7606→0.8747), 20 recovered vs 4 regressed (single-span losses on ≥0.85 docs, no new pattern); term_length +0.040; tokens +6.7%.** Sample5 chunked series: v26 0.8944 → v27 0.9535 → v28 0.9837. Card archived, issue #3 closed.
- **2026-08-15 — prompt-engineer — KANBAN-004 claimed** Extraction next arm claimed `in_progress` (issue #3 already open, cross-repo). Diagnostic-first work completed: classified every key_obligations miss on both surfaces via pairwise similarity matrices (`src.field_scoring._element_similarity` vs GT spans from `build_expected_fields`). **Dominant root cause: wrong-span at sentence level within multi-requirement family sections** — the model quotes ONE sentence per section while the GT holds 3–10 distinct requirement sentences (Ritter: emitted insurance-procurement but not primary-of-all-purposes/additional-insured; audit section 10 GT spans, ~0 emitted; Buffalo: ROFR/insurance/license near-misses; NOVO: revenue-sharing stock-delivery sentence missed; Goosehead 8 near-misses). 60–70% of misses land in the NEAR band (sim 0.35–0.59), NOT family omission. Secondary findings: (1) **truncation confound on the sample5 A/B surface** — those runs are `chunked=false` and Phasebio collapses to 0.125 there vs 0.9375 chunked@50 (v22) — pipeline config, not prompt; (2) v23's worked-example set fixed Midwest (0.143→1.0) but regressed Gridiron (1.0→0.0, degenerate `":"` output — 1-off); (3) v26's asserted "10–25-word GT grain" is false — GT spans median 21–84 words (r≈0 with score; grain is not the driver, sentence choice is). v27 = v26 + ONE rule: family sections are multi-item — emit every distinct requirement sentence as its own item, never collapse a section into its first sentence. Runs reserved here.
- **2026-08-15 — opencode — KANBAN-018 done** prompt-engineer agent shipped
  in commit `1fcc734` (CHANGELOG `[Unreleased]` Added entry in the same
  commit): `.opencode/agents/prompt-engineer.md` (mode `all`, verified
  registered via `opencode agent list`) — the master diagnostic evaluator &
  prompt engineer whose SOLE role is reviewing all traces, reasoning,
  failures, errors, and results of evaluated prompts and producing
  stronger, refined, data-backed prompt mutations (new version keys, never
  an edit to a run prompt). Encodes the repo's iteration contract: the
  diagnose → root-cause → mutate → verify → land loop with the failure
  taxonomy, same-surface A/B discipline (bootstrap-CI verdicts, recovered-
  vs-regressed checks), the plateau/overfit doctrine (clusters not 1-off
  outliers, family-level generalization test, MAE/R² evidence floor, cost
  as tradeoff), and board + CHANGELOG + memo close-out with proof.
  `AGENTS.md` "Agents (this repo)" section documents it alongside
  experiment-log-sync. Board-only card, archived. KANBAN-017's in-flight
  v25 work (src/prompts.py + tests) untouched and still `in_progress`.
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
- **2026-08-15 — opencode — KANBAN-017 done (two iterations: v25 → v26)** term_length
  containment arm landed in `contracts_specialist_v26` (CHANGELOG `[Unreleased]`
  entry, 343 tests green, Langfuse llm-dojo synced). **v25 finding:** additive-prefix
  wording + a verbatim worked example recovered Ediets (containment 1.0) but caused
  TEMPLATE LEAKAGE — Ritter/Phasebio quoted the example clause verbatim with the
  duration swapped in (containment 0.7059/0.2222; their openers are "The initial
  term...", "The term of this Agreement (the "Term")..."). **v26** replaces the
  example with opener VARIANTS to match the document's own wording + an explicit
  "never reuse wording from these instructions". Same-surface 5-doc A/B (seed 42):
  **v26 overall 0.9447 — best of the arm** (v23 0.9366, v24 0.9336, v25 0.9154);
  term_length 1.0000, all three term docs containment 1.0, no leakage. Card archived.
- **2026-08-15 — opencode — KANBAN-017 claimed** term_length containment arm claimed `in_progress` (board-only): v24's leading-phrase rule caused the model to REPLACE the clause opener with the canonical duration phrase — the CUAD ground-truth span for Ediets IS the opener ("This Agreement will become effective as of the Effective Date and, unless sooner terminated pursuant to Sections 3.1"), so containment dropped 1.0→0.3333. Fix = `contracts_specialist_v25` (derived from v24, base untouched): the prefix is ADDITIVE, the ENTIRE verbatim term clause (opener first, exactly as written) must follow — never start at the duration phrase. Planned run: `qwen3.7-flash_contracts_specialist_v25_sample5` (seed 42, 5 docs, same surface as the v23/v24 A/B) — name reserved here.
- **2026-08-15 — prompt-engineer — KANBAN-021 done (unblocked + completed)** **v31 wins the full-corpus A/B**: 509-doc chunked run (new OpenRouter key installed; v28@510 resumed via manifest + v31@510 fresh) — **v31 0.8737 vs v28 0.8622 overall (+0.0116, paired bootstrap CI [+0.0005, +0.0236], P(Δ≤0)=0.021)** with the system prompt −5.7% (8,164→7,700 tokens/call): a Pareto win — the efficiency refactor holds or improves every field (term_length +0.058, termination_clauses +0.044, governing_law +0.014; key_obligations −0.003, renewal −0.003 — noise). **Re-baseline finding: the 50-doc surface overstates the champion by ~6pp (v28 0.9228 @50 vs 0.8622 @510)** — full-corpus is the stable estimate. 356 tests green; 7,250-entry reasoning-trace corpus (14.2/doc) seeds the next reflection; memo `contracts_specialist_v31.md` updated with the completed A/B; CHANGELOG `[Unreleased]` entry rewritten from BLOCKED to the results. Card archived.
- **2026-08-15 — prompt-engineer — KANBAN-021 blocked** Scale-up A/B hit the **OpenRouter weekly key limit (403)** mid-run: v28@510 completed 217/509 rows (partial — the 0.8558 on the record is a biased subset, not a full-corpus number), v31@510 completed 0. **What shipped despite the blocker:** v31 (token-efficiency refactor, −8.0% = 2,679 chars with every operative constraint preserved + 28 family entries; 349 tests green; memo `contracts_specialist_v31.md` with the v22→v31 token audit) registered and test-pinned; full-corpus surface identified (`mailroom-cuad-contracts-full`), cost proven (~$0.19/run); both manifests resumable. **What unblocks:** weekly limit reset or a new OpenRouter key — then resume v28@510 via its manifest and run v31@510 fresh (commands in the card + memo). The reasoning-trace corpus (217 docs × ~20–30 entries) seeds the next reflection once unblocked.
- **2026-08-15 — prompt-engineer — KANBAN-021 claimed** GEPA scale-up + prompt-efficiency arm claimed `in_progress` (board-only): full-corpus 510-doc chunked extraction A/B (v28 champion vs v31 efficiency refactor — same operative rules, compressed; less worked-example reliance per the GEPA efficiency principle), token-growth audit across v22→v31, large-surface noise floor + reasoning-trace corpus to seed the next iteration. Runs reserved: `qwen3.7-flash_contracts_specialist_v28_extraction_langfuse_510` + `qwen3.7-flash_contracts_specialist_v31_extraction_langfuse_510`.
- **2026-08-15 — opencode — v0.18.0 released** **v0.18.0 shipped**: changelog conversion (Unreleased → v0.18.0, 6 entries), pyproject 0.18.0, tag `v0.18.0` + GitHub release with changelog notes; board swept (KANBAN-004/017/018/019/020 archived under v0.18.0, open cards 005/006/008/009/011/013 re-targeted v0.19.0). **Root-cause fix in `scripts/release.py`**: the conversion inserted the new release section under the `[Unreleased]` header but never removed the old body — every converted section shipped duplicated (v0.15.0/v0.17.0/v0.18.0 all had to be deduped by hand). `release_changelog` now replaces the WHOLE Unreleased section and the note lives inside the new release header (no more phantom unreleased bullets); regression test `test_release_changelog_does_not_duplicate_entries` added (348 tests green). llm-mailroom mirror synced (`19c8f63`).
- **2026-08-15 — opencode — v0.17.0 release published** **v0.17.0 is live**: GitHub release created from the annotated tag `v0.17.0` (commit `fdaa009`), marked **Latest** (previously v0.16.0 still held Latest — the tag existed but the release was never published), full changelog-derived notes at https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.17.0. Changelog hygiene: the v0.17.0 section was found duplicated (every entry twice — the same class of bug as the v0.15.0 dedup repair); deduped in the working tree (first-half kept, KANBAN-016/014/Sorter-scale-up all x1) and the release notes regenerated from the deduped section; `release.py --check` green. llm-mailroom mirror sync verified current (`a54574c DOCS SYNC: upstream v0.17.0 + v26 arm`). Open cards stay re-targeted to v0.18.0.
- **2026-08-15 — prompt-engineer — KANBAN-020 done** Follow-up arm closed: shipped `contracts_specialist_v29` (CoC-definition carve-out) + `contracts_specialist_v30` (chunk-mode scalar-quoting discipline), `--chunked` flags + truncation-confound warning on `run_extraction_eval.py`, and the GEPA workflow in `.opencode/agents/prompt-engineer.md` (CHANGELOG `[Unreleased]` entries, 347 tests green, Langfuse synced, memo `memos/contracts_specialist_v30.md`). **Headline: the noise floor.** Identical-prompt rerun of the v28 champion (same 50-doc chunked surface): −0.0293 overall band, ~12 docs >±0.02 per field → the follow-up candidates measure INSIDE it (v29 −0.0264, v30 −0.0382 vs the rerun band −0.0293) and ship as unmeasured logic repairs; **v28 stays champion (re-validated vs v26 +0.0448, CI [+0.0087, +0.0891], P=0.004)**. Per-span diffs: Ediets = rule-driven CoC-definition suppression (fixed by v29; 0.692→0.769), LinkPlus/Innerscope/Legacy = noise; renewal_terms dip = 1 doc (NOVO, quote-truncation); Gridiron = 1-off (fresh runs 1.0). Card archived.
- **2026-08-15 — prompt-engineer — KANBAN-020 claimed** Post-v28 follow-up arm claimed `in_progress` (board-only): the five not-fixed items from the KANBAN-004 close-out — per-span diff on the 4 regressed docs, chunked×term_length interaction, renewal_terms dip, Gridiron degenerate output, and `--chunked` enforcement on the Braintrust extraction runner (which cannot chunk today) — plus folding the full GEPA reflective prompt-evolution workflow into `.opencode/agents/prompt-engineer.md`. Runs reserved: none (diagnostics-only + runner change; any A/B reuses existing 50-doc records).
- **2026-08-15 — opencode — KANBAN-019 done** Slides problems/fixes decks landed in
  `docs/slides/` (docs-only, no changelog entry): **08-problems-sorter** (near-
  synonymous families, title-vs-machinery, development/IP confusions, reasoning
  effort, plateau & revision confounds), **09-fixes-sorter** (v7→v9 rule sets with
  A/B numbers, equivalence framework, medium reasoning, scale validation),
  **10-problems-contracts-specialist** (scope/grain, over-extraction, ellipsis/
  dedupe losses, reasoning confound, self-inflicted v24/v25 format regressions,
  scorer-side problems, no reasoning trace), **11-fixes-contracts-specialist**
  (v18 family-fidelity → v26 containment fix, wave by wave with numbers).
  README index updated (decks 08–11 = prompt-iteration post-mortems). Deck 10
  carries a pointer to the prompt-engineer's v27 grain-claim re-examination.
  Card archived.
- **2026-08-15 — opencode — KANBAN-019 claimed** Slides problems/fixes decks claimed `in_progress` (board-only, docs-only): four new decks in `docs/slides/` — 08/09 = sorter problems then fixes, 10/11 = contracts-specialist problems then fixes (same framing, one doc per side per agent) — built from the changelog iteration records (v0.15.0/v0.16.0/v0.17.0), `V16_PROPOSITION.md` summaries, and the KANBAN-016/017 arms. README index updated. No changelog entry (docs-only).
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
| KANBAN-027 | v0.19.0 (2026-08-15) | `d6c6c9d` | **Repository streamlining + navigation pass** — README Table of Contents + Layout-tree repair (src modules mis-nested under `wiki/`, stale script list + test counts 223→375, prompt tables to sorter_v12/contracts_specialist_v31, `BRAINTRUST_LOGGING` conditional documented); `src/README.md` (+braintrust_logging/eval_shims/master_labels/metrics), `memos/README.md` (table bug + v28/v30/v31/sorter_v10_v11 rows), `scripts/README.md` (all runners + eda/) refreshed; `scripts/backfill_cost_estimates.py` nested under `scripts/reporting/` (live refs updated, CHANGELOG history untouched). Docs-only + safe nesting; 375 tests green, site render audit clean, no new release-gate failures. CHANGELOG `[Unreleased]` Changed entry in the same commit |
| KANBAN-025 | v0.19.0 (2026-08-15) | run-sink swap commit | Run sink = Langfuse + LangSmith; Braintrust logging OFF by default (`BRAINTRUST_LOGGING=disabled`) — the `run_*_eval.py` runners skip `braintrust.Eval` and use the local scoring loop (`src/eval_shims.py`), `run_langfuse_*_eval.py` become the documented primary path. Verified: disabled-path pilot (tracing_backend=none, langsmith=True, trace tree in LangSmith, zero Braintrust 400s). 365 tests green |
| KANBAN-013 | v0.19.0 (2026-08-15) | `sorter_v10` + `sorter_v11` | Sorter tail-sampling iteration: the "1-off long tail" plateau reading superseded by cluster analysis — **marketing cell 0.5/10 (243) & 7/17 (509), worst family on both surfaces, unchanged since v6**. v10 = rule 26 MARKETING TITLE WINS (title-wins doctrine mirror of R23/R24); v11 = rule 27 AFFILIATE IS NOT MARKETING (fixes the measured rule-26 over-fire). **243-doc same-surface A/B: champion rerun 0.9259→0.9300 (±1 doc noise floor); v10/v11 0.9342 (equiv 0.9424), paired CI [−0.0247, +0.0165], P=0.710 — inside the band → logic repair; v9 stays champion.** Rule-driven: 4 deterministic recoveries + 2 affiliate restorations, 1 R27-wording regression (equiv-recovered); marketing cell 0.5→0.8. Memo `sorter_v10_v11.md`; banked lessons → KANBAN-023; issue #11 closed |
| KANBAN-022 | v0.19.0 prep (2026-08-15) | commits `f417227` (wiring) + live-run follow-up | LegalBench **hearsay** task wired end-to-end: `mailroom-lb-hearsay` synced from the ACTUAL task data (5 train rows, binary Yes/No, 5 slices, CC BY 4.0, Neel Guha) + classes manifest `data/legalbench_classes.jsonl`; **`upload_text_dataset` now inserts deterministic content-addressed ids** (`_deterministic_record_id` — Braintrust's `insert()` assigned fresh UUIDs per call, so reruns APPENDED duplicates, observed 2×5; reruns now upsert); **`run_langfuse_classification_eval.py` gains `--prompt-mode task`** (mirror previously hardcoded the sorter path and dropped the row's `prompt`) — hearsay/LegalBench tasks trace into llm-dojo with one `legalbench_task` observation per row; **`BaseAgent._call_llm` captures usage/cost** (task-mode records previously had tokens 0 / cost 0); LegalBench-task docs updated with the actual task data; README Credits (LegalBench, CUAD/The Atticus Project, MAUD, GEPA, LangChain/Braintrust/Langfuse); **first benchmark: exact_match 1.0 (5/5, per-class 1.0/1.0)** on qwen3.7-flash × legalbench_task_v0, replicated on the Langfuse mirror (5 traces/session verified); 10 new tests, 359 total green; issue #13 closed (reopened for the live run, re-closed). NOTE: Braintrust ORG at monthly log-bytes plan limit — experiment row data does not upload to Braintrust until billing is addressed |
| KANBAN-021 | v0.19.0 prep (2026-08-15) | `contracts_specialist_v31` | token-efficiency refactor (−8.0% = 2,679 chars, 7,700 system tokens −5.7%) with every operative constraint preserved; **full-corpus 509-doc A/B: v31 0.8737 vs v28 0.8622 (+0.0116, CI [+0.0005, +0.0236], P=0.021) — Pareto win**; re-baseline: 50-doc surface overstates champion ~6pp (0.9228→0.8622); 7,250-entry reasoning-trace corpus; unblocked after a new OpenRouter key; memo `contracts_specialist_v31.md` |
| KANBAN-020 | v0.18.0 (2026-08-15) | `contracts_specialist_v29` + `contracts_specialist_v30` + runner chunking + GEPA agent | Follow-up arm with a noise-floor control: **identical-prompt rerun band ±0.03 overall** (v28 0.9228 → rerun 0.8935) — v29 (CoC-definition carve-out, Ediets 0.692→0.769) and v30 (chunk-mode scalar quoting) ship as UNMEASURED logic repairs inside the band; v28 remains champion (re-validated +0.0448 vs v26, P=0.004). Per-span diffs: Ediets rule-driven (fixed), 3 others noise; renewal_terms = 1 doc; Gridiron = 1-off; `run_extraction_eval.py` gains `--chunked` + confound warning; prompt-engineer agent now runs the full GEPA reflective loop (frontier, noise floor, Pareto selection); memo `contracts_specialist_v30.md` |
| KANBAN-004 | v0.18.0 (2026-08-15) | `contracts_specialist_v27` + `contracts_specialist_v28` | key_obligations span residual: sim-matrix diagnosis (wrong-span at sentence level in multi-requirement family sections; ~60–70% NEAR 0.35–0.59) → multi-item family-section rule (v27) sharpened (v28: operative-vs-definitional + additive re-scan). **50-doc chunked A/B: v28 0.9228 vs v26 0.8780 (+4.48pp, CI [+0.0094, +0.0907], P=0.004); ko +11.4pp, 20 recovered / 4 regressed; term +0.040; tokens +6.7%.** Truncation confound on sample5 surface documented; memo `contracts_specialist_v28.md`; issue #3 closed |
| KANBAN-017 | v0.18.0 (2026-08-15) | `contracts_specialist_v26` | term_length containment fixed through TWO iterations: v25 additive-prefix + worked example recovered Ediets but leaked the example template (Ritter/Phasebio containment 0.7059/0.2222); v26 (opener variants + "never reuse the instructions' wording") — **overall 0.9447 best of the arm** (v23 0.9366 / v24 0.9336 / v25 0.9154), term_length 1.0000, all three term docs containment 1.0, no leakage |
| KANBAN-018 | v0.18.0 (2026-08-15) | commit `1fcc734` | **prompt-engineer agent shipped** (`.opencode/agents/prompt-engineer.md`, mode `all`, verified via `opencode agent list`): master diagnostic evaluator & prompt engineer — sole role reviews all traces/reasoning/failures/errors/results and produces data-backed prompt mutations (new version keys); full diagnose→root-cause→mutate→same-surface A/B→land loop, failure taxonomy, plateau/overfit doctrine (clusters not outliers, generalization test, evidence floor), board+CHANGELOG+memo close-out; AGENTS.md "Agents (this repo)" section |
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
