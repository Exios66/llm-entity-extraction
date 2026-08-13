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

### 5. Status moves — when and who

| Move | Who | When |
|---|---|---|
| `backlog` → `in_progress` | anyone (self-assign) | You are actively working it, OR any work exists for it (draft, diff, branch, run started) — Owner set + dated, immediately, never deferred |
| → `blocked` | owner | Stuck — post the blocker in Discussion + on the issue; name what unblocks it (data, keys, decision, card) |
| `blocked` → `backlog`/`in_progress` | owner | Blocker cleared — post what cleared it |
| → `in_review` | owner | Work done; awaiting validation (tests, A/B, release gate). Link the evidence (run, commit, PR) in the card |
| `in_review` → `done` (Archive) | reviewer/releaser | Validation passed; CHANGELOG entry exists (same-commit rule); issue CLOSED in the same commit |
| `done` → `backlog` (reopen) | anyone | Regression / new data / superseded assumption — Discussion post explains why; issue reopened with the post |

A card is **not done until**: its CHANGELOG entry exists (same commit), the
Archive row is filled (version + commit + result), and — for synced cards —
the GitHub issue is closed.

### 7. GitHub issue sync (critical / high-priority tasks)

**Critical and cross-repo tasks are synced to GitHub issues** so agents can
open/close them like normal issues while the board remains the source of
truth.

- **When a new critical card is added**, open its issue in the repo where
  the work lands: `gh issue create --title "KANBAN-00N: <task>" --label kanban --body "<card summary + evidence + procedure>"`. Put the issue number in the card's `Issue` column.
- **When a card ships**, close its issue in the same commit that archives
  the card (`gh issue close NNN`), with a closing comment naming the commit
  and CHANGELOG entry.
- **When a card is reopened**, reopen its issue with the Discussion post as
  the comment.
- Issues carry the `kanban` label; the issue body always links back to the
  card number, and the card always carries the issue number — the two must
  never disagree about status.
- Board-only cards (small, single-session tasks) do NOT need issues.

### 8. Commit discipline

Reference cards in commits — `MESSAGE BOARD: KANBAN-004 claimed` or
`v24 diagnostic (KANBAN-004): ...`. A commit that lands a card's work
carries its CHANGELOG entry in the same commit (AGENTS.md rule) and closes
its issue.

### 9. Release sweep

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
| KANBAN-012 | [#10](https://github.com/Exios66/llm-entity-extraction/issues/10) | `in_progress` | **sorter_v9 A/B (title-wins rules)** — `SORTER_PROMPT_V9` draft in the working tree (promotion-title wins, outsourcing-title wins, customization-schedules-are-maintenance + rule-22 rewrite) targeting the v8 243-doc A/B's 25 fails (strict 0.8971); uncommitted: prompt constant + test + site-derived artifacts. Next: commit the registration + test, then run the same stratified surface; target strict > 0.92, verify each rule with failure-insight quotes. | opencode — 2026-08-13 | `[Unreleased]` → v0.16.0 | v8 run: qwen3.7-flash_sorter_v8_subtype_langfuse (strict 0.8971, 25 fails); `SORTER_PROMPT_V9` + test draft in `git status` (`src/prompts.py`, `tests/test_prompts.py`) |
| KANBAN-004 | [#3](https://github.com/Exios66/llm-entity-extraction/issues/3) | `backlog` | **Extraction next arm (v24 candidate)** — attack the 30-span residual: span-choice/boundary divergence at token level (34→30 spans still missed; ko ~0.85 ceiling at reasoning=none). Diagnostic first: classify the 30 misses (boundary-shift vs abbreviation vs wrong-span) before writing prompt rules. | unclaimed | v0.16.0 | `V16_PROPOSITION.md` §14.3/§15.1; `reports/same_scorer_scores.json` |
| KANBAN-005 | [#4](https://github.com/Exios66/llm-entity-extraction/issues/4) | `backlog` | **Mirror sync → llm-mailroom (cross-repo)** — apply the v22/v23 champion prompts to the llm-mailroom pipeline project (Langfuse key file drop-in + `sync_langfuse_prompts.py --env-file`); regenerate its synced experiment log. | unclaimed | v0.16.0 | AGENTS.md "Langfuse projects" / "Mirror sync"; `scripts/eval/sync_langfuse_prompts.py` |
| KANBAN-006 | [#5](https://github.com/Exios66/llm-entity-extraction/issues/5) | `backlog` | **HITL annotation queue processing** — work the pending llm-dojo queue items (extraction < 0.85 + sorter failure queue): adjudicate, feed corrections into the next prompt iteration. | unclaimed | v0.16.0 | `scripts/eval/run_annotation_queue.py status`; wiki `Annotation-Queues.md` |
| KANBAN-008 | [#6](https://github.com/Exios66/llm-entity-extraction/issues/6) | `backlog` | **v23×max ko arm — production decision** — ko 0.8510 @ 2.6× cost, 0 parse errors vs v22×none 0.9512 overall. Decide/documented the recommended production config (or split: overall arm vs ko arm) and record it in README/AGENTS docs. | unclaimed | v0.16.0 | `V16_PROPOSITION.md` §15.1; memo `contracts_specialist_v23.md` |
| KANBAN-009 | [#7](https://github.com/Exios66/llm-entity-extraction/issues/7) | `backlog` | **Score-drift hygiene** — extend the same-scorer rescore pipeline beyond the 50-doc series if a scorer rule changes again; keep `reports/same_scorer_scores.json` current per run. | unclaimed | v0.16.0 | `scripts/reporting/rescore_manifests.py`; `tests/test_rescore_manifests.py` |
| KANBAN-010 | [#8](https://github.com/Exios66/llm-entity-extraction/issues/8) | `backlog` | **Restore OpenRouter cost accounting on the site** — the latest `build_site.py` regen dropped the `costs` meta + per-run `cost` blocks because no activity CSV was present. Re-ingest the OpenRouter activity-log export (Settings → Activity Logs) and rebuild; verify the cumulative-cost card renders. | unclaimed | v0.16.0 | `scripts/site/build_site.py` (activity CSV ingest); site `#/` cost card; this commit's regen has no `costs` block in `docs/data/meta.json` |
| KANBAN-011 | [#9](https://github.com/Exios66/llm-entity-extraction/issues/9) | `backlog` | **Post-v23 model sweep (gated OPEN)** — run v22/v23 prompts × {deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs to quantify the remaining model-bound segmentation gap (the v18 sweep proved scope-fidelity is model-agnostic; confirm the ko 0.85→0.89 plateau closes at the newest prompts). | unclaimed | v0.16.0 | memo `model_sweep_v18.md`; `V16_PROPOSITION.md` §9.3/§15 |

**Sweep rule:** when a release ships, re-target every non-done card to the
new `[Unreleased]` version and move landed cards to the Archive. (Last sweep:
v0.15.0 shipped 2026-08-12 — KANBAN-001/002/007 archived below.)

## Discussion board

Dated, append-only log. Newest entry goes at the TOP. Format:
`**YYYY-MM-DD — <agent/human> — <card ref(s)>** <what happened / decision / question / blocker>`. No editing history.

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
| KANBAN-003 | v0.16.0 prep (2026-08-12) | commit `cbb5b93` | sorter_v7 250-doc A/B landed: **v7 wins (+0.82pp strict, 0.8765)** — promotion cluster fixed; issue #2 closed on sweep |
| *(user-run, no card)* — sorter_v8 A/B | v0.16.0 prep (2026-08-12) | commit `43ef2ab` | **v8 wins (+2.06pp strict, 0.8971)** on the 243-doc stratified surface — development & IP clusters eliminated; memo addendum + proposition §17 |
| KANBAN-007 | v0.15.0 (2026-08-12) | tag `v0.15.0` → `4b6ad5f`; commits `93eb938`, `0a4051e`, `0afdf2e` | Release finalized: changelog dedup-repaired, tag pushed, GitHub release with dedicated notes published; `release.py --check` green (303 tests) |
| KANBAN-002 | v0.16.0 prep (2026-08-12) | commit `ac156a5` | Dirty tree landed: experiment log regen (57 runs), site data regen, `sorter_v7` registration + test, AGENTS.md board governance, changelog `[Unreleased]` entry for sorter_v7 |
| KANBAN-001 | v0.16.0 prep (2026-08-12) | commit `ac156a5` | `SORTER_PROMPT_V7` constant + `PROMPT_VERSIONS["sorter_v7"]` + `test_sorter_v7_data_backed_rules` landed (18 prompt tests green). Evaluation tracked in KANBAN-003 |
| *(v0.15.0 content)* | v0.15.0 (2026-08-12) | tag `v0.15.0` | All v0.15.0 changelog entries (v18 sweep → v19 → v20 → v21 → v22 → v23 → v23×max; scorer fixes; annotation queues ×2; memos tab + 6 memos; wiki Langfuse-Traces + Annotation-Queues; rescore pipeline; two-project Langfuse strategy; prompt-store cleanup) — cataloged in CHANGELOG.md v0.15.0, each with its own commit in `git log v0.14.0..v0.15.0` |

When moving a card here: fill this table AND leave the lane row visible in
the Key Kanban table only if the card is still open; closed cards live ONLY
here (the table above holds open work, the archive holds the record).
