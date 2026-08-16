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
   the card is board-only. Discussion posts are appended at the TOP of
   `MESSAGE_BOARD_DISCUSSION.qmd` (date + agent + card + subject + full
   post — see the Discussion board section below).
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
| KANBAN-040 | — (board-only) | `in_progress` | **Sorter model-sweep workbook — every model on the champion prompt, reference-format xlsx (follow-on to KANBAN-039)** — per human request (2026-08-16, reference `~/Downloads/Sorter_Experiment_Results.xlsx`): `scripts/reporting/export_sweep_results.py` → `reports/sheets/Sorter_Model_Sweep_Results.xlsx` in the EXACT reference format (114 columns + trailing Notes, Eval Results + Codebook sheets, 1F4E79 header, mm/dd/yyyy, 0.00%, freeze F2, autofilter), rows = subtype_classification runs of the champion sorter_v13 prompt (6 rows, chronological: DEGRADED first qwen run, clean champion rerun 0.9430, gpt-5-nano 0.8978 full-509, deepseek + gpt-4.1-nano smokes, deepseek-v4-flash 0.9253 full-509). Column spec reused verbatim from `export_experiment_results.py` (114 shared headers byte-identical to the reference). Tests `tests/test_export_sweep_results.py` (4, network-free). | opencode (2026-08-16) | v0.19.0 | `scripts/reporting/export_sweep_results.py`; `reports/sheets/Sorter_Model_Sweep_Results.xlsx`; CHANGELOG `[Unreleased]` Added |
| KANBAN-037 | — (board-only) | `in_progress` | **Posit Cloud integrated portal — Quarto site `site/` → `docs/posit/` (complementary to the SPA)** — per the human directive (2026-08-16): a fully themed, fully integrated Quarto website project rendering into the SAME `docs/` tree GH Pages serves, so ONE URL prefix serves both the existing SPA explorer (root, untouched except one nav link) and the Posit portal at `/posit/`; no GitHub Actions (Pages deploys from branch; Posit Cloud renders + publishes). Three integrated sections: **experiment log** (generated from `reports/experiment_log.jsonl` — full run index + per-run metadata/scores/tokens + explorer deep-links), **kanban board** (`MESSAGE_BOARD.md` live copy), **discussion board** (`MESSAGE_BOARD_DISCUSSION.qmd` live copy, agent colors preserved). Custom blue→teal gradient theme (light + gradient-night dark), navbar/search/TOC; `_pre-render.py` hook regenerates all includes + `_variables.yml` stats (derived, never hand-edited); rendered output committed to `docs/posit/`; tests `tests/test_posit_site.py`; deployment docs in docs/README + README + wiki/Site.md. | opencode (2026-08-16) | v0.19.0 | `site/**`, `docs/posit/**`, `tests/test_posit_site.py`, CHANGELOG `[Unreleased]` Added; no LLM runs (plan-free card) |
| KANBAN-039 | — (board-only) | `done` | **Eval-run tracing: Langfuse PRIMARY, local Phoenix server fallback (human directive 2026-08-16)** — `src/tracing.py::resolve_tracer()` flips the Phoenix-first default in all four `run_langfuse_*_eval.py` runners (docclass, subtype, extraction, chained): Langfuse (llm-dojo) when keys are configured, local Phoenix OpenTelemetry otherwise; dry-run/manifest/record all report the real backend; `prefer="phoenix"` preserved. Verified live (full-676 docclass runs: `tracing_backend=langfuse`). Tests `tests/test_tracing.py`; DOJO keys refreshed in gitignored `langfuse.env`. | prompt-engineer (2026-08-16) | v0.19.0 | CHANGELOG [Unreleased] Changed; AGENTS.md run-sink paragraph |
| KANBAN-038 | — (board-only) | `backlog` | **Docclass vision full benchmark + PDF retention for MAUD/S-1** — **† numbered KANBAN-038 after a collision — KANBAN-037 was already claimed by the Posit portal card (2026-08-16, opencode) when this follow-on (reserved as “KANBAN-037” inside KANBAN-033’s close-out entry) was posted; reconciliation post on the discussion board.** (1) full-pages vision benchmark (`--vision-pages all`, larger sample) on the merged docclass surface with `sorter_docclass_vision_v0` (the pilot validated page-1 vision only, n=8); (2) retain MAUD (Zenodo archive) + S-1 (EDGAR) PDFs locally so the vision arm covers merger_agreement + corporate_record rows, not just CUAD contracts; (3) data-side subclass GT repair (MAUD consideration backfill for the 57 GT-"other" rows; S-1 streamer label fixes) — the unlock for the GT-bound subclass metric (56/69 full-676 subclass misses are GT gaps). | unclaimed | v0.19.0 | memo `memos/docclass_v3_merged_benchmark.md` §4/§uncertainties |
| KANBAN-036 | — (board-only) | `in_progress` | **Sorter subtype model sweep — deepseek-v4-flash + gpt-4.1-nano on the champion prompt (full-509)** — per the human directive, two more full-509 subtype evals on sorter_v13 (champion), reasoning medium, temp 0.1, Phoenix sink, `--research-funding-key`: (1) **`deepseek/deepseek-v4-flash`** — cheapest deepseek v4 flash ($0.0629/M prompt + $0.1257/M completion; ~$0.46 est.); (2) **`openai/gpt-4.1-nano`** ($0.10/$0.40; ~$0.78 est.). Both smoke-tested on 1 doc (default key) before the funded launches. Runs reserved: `deepseek-v4-flash_sorter_v13_subtype_langfuse` + `gpt-4.1-nano_sorter_v13_subtype_langfuse`; manifests `data/manifests/{deepseekv4flash,gpt41nano}_sorter_v13_509.jsonl` (gitignored). Companion to KANBAN-035 (gpt-5-nano 0.8978 @509). | opencode (2026-08-16) | v0.19.0 | `reports/experiment_log.{jsonl,md}` regen; sorter_v13 |
| KANBAN-033 | — (board-only) | `in_progress` | **MAUD + EDGAR S-1 corporate-record dataset wiring + new hierarchical sorter eval task** — (1) MAUD (Merger Agreement Understanding Dataset, CC BY 4.0) wired as a UTILIZED dataset: new `scripts/datasets/stream_maud_to_bt.py` (Zenodo `maud_v1.zip` primary / HF `theatticusproject/maud` mirror; 152 contracts + 25,827 train rows across 22 question families / 7 categories) → `mailroom-maud-contracts` (GT doc_type=merger_agreement + consideration-type subclass from MAUD GT: all_cash/all_stock/mixed_cash_stock/mixed_cash_stock_election) + `mailroom-maud-classification` (per-question multi-class rows, category/family as metadata) + `--local-dump` JSONL (Braintrust row uploads remain capped) + Langfuse dataset mirror; (2) NEW primary doc class `merger_agreement` in the sorter (7 classes) via new `sorter_docclass_v0` prompt + extended schema (doc_subclass for non-contract classes; the shared 6-class sorter surface is untouched — new classes only in the new prompt/runner); (3) NEW sorter eval task `run_langfuse_docclass_eval.py` scoring doc_type + subclass across a mixed corpus (CUAD contracts + MAUD merger agreements + S-1 corporate records); (4) EDGAR S-1 exhibit ingestion `scripts/datasets/stream_s1_exhibits.py` — SEC FTS search → filing index → corporate-record exhibits (EX-3.x/4.x/21.x/24.x/25.x) → text extraction → `mailroom-s1-corporate-records` (GT corporate_record + content-detected record_type subclass: bylaws/articles_of_incorporation/certificate_of_formation/powers_of_attorney/...; exhibit code kept as metadata). **Tertiary class level DROPPED per human directive (2026-08-15): only where the data necessitates it** — MAUD category + EDGAR exhibit code stay as dataset metadata, not classification dimensions. Pipeline mechanics verified live against EDGAR (FTS → index → EX-3.1/3.2/3.3 text extraction OK). Runs reserved (dry-run/pilot only): `qwen3.7-flash_sorter_docclass_v0_docclass_langfuse` (+ `_pilot`). **PROMPT-ITERATION ARM (prompt-engineer, 2026-08-16):** pilot diagnosed → v1 (rule 34) + v2 (rule 35); same-surface ab30 A/B (fp `d3d7b335…`): v2 exact 0.8000 (5/5 EX-4.x doc_type misses recovered) vs v0 0.6667; **v3 = Phase 3.5 MERGE (rules 34+35), failure-set-identical to v2 → COMPLETED docclass prompt**. **MERGED DATASET:** `build_docclass_merged.py` → `data/datasets/docclass_merged.jsonl` (676 = 509 CUAD + 152 MAUD + 15 S-1, fp `5602b71f…`) + `sync_langfuse_datasets.py --docclass` → Langfuse `mailroom-docclass` (676 items). **QWEN 3.7-flash benchmark on merged task** (`..._docclass_full676`): doc_type 0.9926 / subclass 0.5808 / exact 0.8905, 0 errors, ≈$0.47 (56/69 subclass misses = MAUD GT-gap cluster). **VISION arm:** `sorter_docclass_vision_v0` + runner `--input-mode vision-primary` (text fallback, `--pdf-dir`, `--vision-pages`); pilot 8 rows all correct (5 vision + 3 fallback). **Concurrency:** `src/evaluation.py` `resolve_concurrency` (auto 8..32 by sample size) + rate-limit retry wired into the 4 langfuse runners. Follow-on card reserved: full-pages vision benchmark + MAUD/S-1 PDF retention (KANBAN-037). **ROUND 2 (prompt-engineer, 2026-08-16):** full-676 failure decomposition (C1 M&A-package machinery / C2 agreement-package composition / C3 GT-text artifacts) → v4 (rule 36) + v5 (rule 37) + **v6 (rule 36 SHARPENED — rule-31 list illustrative + multi-agreement files)**; diag30 A/B all inside CI → full-676 A/B with noise control (v3 rerun reproduced 0.8905 exactly): **v6 0.8935 (+0.0030), 2 rows recovered (contract_62 + contract_71), 0 regressions, subclass +1.19pp → v6 = docclass text champion**. **Scoring depth:** bootstrap CIs, per-subclass tables, subclass_accuracy_equiv (mixed↔election), input-mode counts, renderer docclass branch. **Tracing:** Langfuse primary + local Phoenix fallback (src/tracing.py, human directive). Memo `memos/docclass_v6.md`. | athena-database-agent (2026-08-15) + prompt-engineer (2026-08-16) | v0.19.0 | `scripts/datasets/stream_maud_to_bt.py`, `scripts/datasets/stream_s1_exhibits.py`, `scripts/eval/run_langfuse_docclass_eval.py`, `config/taxonomy.yaml`, `agents/sorter_agent.py`, `src/prompts.py` SORTER_DOCCLASS_PROMPT_V0/V1/V2 |
KANBAN-030 | — (board-only) | `done` | **Contract-specialist v1..v16 archived to `src/prompts_archive.py`** — prompt-file bloat cut for later editing agents: the pre-documentation lineage (full-text v1..v7 + the early replace chain, ~1,000 lines / ~72 KB) moved into a FROZEN archive module and imported back into `src/prompts.py`, so the file drops **227 KB → 155 KB (−32%)** while EVERY version key stays resolvable (`get_prompt`, `PROMPT_VERSIONS`, manifests, Langfuse prompt syncs) and all 32 prompt strings are byte-identical (verified against git HEAD). Documented frontier lineage (v17..v32) with data-backed banners stays in `prompts.py`. Tests pin the archive rule (never edit an archived constant — a change = a new version key): `test_contracts_archive_preserves_identity_and_version_keys` + `test_contracts_archive_chain_heads_resolve` (384 tests green). | prompt-engineer (2026-08-15) | v0.19.0 | `src/prompts_archive.py`; `src/prompts.py` V1..V16 → import; CHANGELOG `[Unreleased]` Changed; commit `e0f758e` |
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

The full discussion log — every claim, lane move, decision, result, blocker,
handoff, and reopening, newest at top — lives in
**`MESSAGE_BOARD_DISCUSSION.qmd`** (a Quarto document: color-coordinated
entries per agent, agent profiles + color legend, inline references/citations
to issues, commits, memos, and repo paths). It was moved out of this file on
2026-08-15 (from inline bullets to YAML, then restyled as `.qmd` on
2026-08-16) to keep the board lean; the log itself is UNCHANGED and remains
append-only — never edit a past entry, post a correction.

Post to the discussion board by appending a new entry at the TOP of
`entries` in `MESSAGE_BOARD_DISCUSSION.qmd` (the `::: {.entry ...}` block
template in its "How to append" section — date + agent + card + subject +
body), and mirror lane changes on the card table above.



Archive (completed work — kept for auditability)

| Card | Shipped in | Commit / tag | Result |
|---|---|---|---|
| KANBAN-042 | v0.19.0 prep (2026-08-16) | runs `deepseek-v4-pro_sorter_v13_subtype_langfuse` + `meta-llama-llama-3.3-70b-instruct_sorter_v13_subtype_langfuse`; `reports/sheets/Sorter_Model_Sweep_Results.xlsx` (8 rows) | **Sorter model-sweep expansion — deepseek-v4-pro + llama-3.3-70b-instruct on champion sorter_v13, full-509, research-funding key** — two funded full-corpus subtype evals (reasoning medium, temp 0.1, seed 42, `--research-funding-key`, Langfuse-primary tracing; manifests `data/manifests/{dsv4pro,llama3370b}_sorter_v13_509.jsonl`): **deepseek-v4-pro subtype 0.9528 (CI [0.9332, 0.9705]), exact 0.9961, equiv 0.9548, 24 fails, 6.97M tokens ≈ $3.15 est. — highest in the sweep to date (vs qwen champion 0.9430; cross-model significance NOT claimed)**; **llama-3.3-70b-instruct subtype 0.8782 (CI [0.8487, 0.9057]), exact 0.9941, equiv 0.8998, 62 fails, 6.66M tokens, cost None (OpenRouter-billed)**. Both n_ok=509, full reasoning + per_subtype; LangSmith 429 noise non-fatal. Sweep workbook regenerated (8 rows, Notes for both) + copied to ~/Downloads; deck slide 16 updated (llama sorter run table; "no llama sorter runs" note superseded) + recopied; experiment-log md regenerated (178 records). CHANGELOG `[Unreleased]` Added; uncommitted — commit left to the human |
| KANBAN-041 | v0.19.0 prep (2026-08-16) | `reports/sheets/contract_specialist_v32_and_sorter_v14_deck.xlsx` (regenerated, 19 slides) + `reports/sheets/llama4scout_v31_extraction_langfuse.json` | **Slides deck regenerated per human request — qwen sorter lineage v3→v13 + llama runs** — deck 16 → **19 slides**: (14) qwen lineage summary v3→v13 (best full-surface per version, 509-doc chain v5 0.8585 → v6 0.9312 → v8 0.9018 → v9 0.9175 → v12 0.9293 → v13 0.9430), (15) all 30 qwen v3→v13 runs (degraded rows kept: v11 0.0000, v13 0.7741), (16) **llama runs** — exhaustive search (log 0 hits, Langfuse model+session filters, Braintrust 403, LangSmith HEARSAY-only) found NO llama sorter runs; the ONLY llama run is **llama-4-scout × contracts_specialist_v31 EXTRACTION in Langfuse llm-dojo** (509 traces / 20 scored, truncated; overall 0.6627 vs qwen v31 0.8737, n=20 not comparable) — fetched via langfuse-cli with rate-limit backoff, record in `llama4scout_v31_extraction_langfuse.json` (deck `--llama-json`). Lineage slides switched to raw-list loader (`load_records_list` — name→record dedup dropped same-name reruns). Verified: 19 slides banner/footer/landscape fit-to-page, values cross-checked (v6 0.9312@509, v13 0.9430@509, llama 0.6627); copied to `~/Downloads`. CHANGELOG `[Unreleased]` Added entry; uncommitted — commit left to the human |
| KANBAN-040 | v0.19.0 prep (2026-08-16) | `scripts/reporting/export_sweep_results.py` + `reports/sheets/Sorter_Model_Sweep_Results.xlsx` | **Sorter model-sweep workbook (per human request, reference-format)** — xlsx in the EXACT format of `Sorter_Experiment_Results.xlsx` (114 columns + trailing `Notes`; `Eval Results` + `Codebook` sheets; header/styling/freeze/autofilter reused verbatim from `export_experiment_results.py`; 114 shared headers byte-identical to the reference). Rows = every `subtype_classification` run of the champion prompt (sorter_v13, `--prompt` overridable), chronological: DEGRADED first qwen v13 run (93 connection errors, flagged in Notes) → **champion clean rerun (qwen3.7-flash 0.9430)** → gpt-5-nano 0.8978 (KANBAN-035) → deepseek-v4-flash + gpt-4.1-nano 1-doc smokes → **deepseek-v4-flash 0.9253 full-509** (KANBAN-036; gpt-4.1-nano full-509 still pending). Per-subtype strict/equiv + cell sizes, failure modes, CI, tokens/cost all populate from the log records. Tests `tests/test_export_sweep_results.py` (4, network-free). CHANGELOG `[Unreleased]` Added entry; card archived; commit left to the human |
| KANBAN-039 | v0.19.0 prep (2026-08-16) | `scripts/reporting/export_slides_deck.py` + `reports/sheets/contract_specialist_v32_and_sorter_v14_deck.xlsx` | **Slides-style xlsx deck export (per human request)** — ONE Google-Slides-formatted workbook, 16 sheets = 16:9 slides (landscape fit-to-page, dark banner + footer, stat cards): Part A = contracts specialist v32 510-full-clean (overall 0.8807 CI [0.8689, 0.8913], field_presence 0.9701, schema_valid 1.0, verified_precision 0.9799, per-field + error decomposition + entity-list + MAE/R² diagnostics, v31 comparison with memo verdict) + full extraction codebook (9 fields/types/scoring class + rubric thresholds); Part B = sorter v14 subtype (exact 0.9961, subtype 0.9371 CI [0.9155, 0.9568], equiv 0.9411, 32 failures by mode + examples, per-subtype strict/equiv table from row-level results) + full sorter codebook (25 subtypes, 4 equivalences, failure modes, scoring rules); Part C = docclass v5 diag-30 bonus (doc_type 0.8333 / subclass 0.5263) + sources. Script reads the experiment log + taxonomy.yaml + sorter_agent at build time; verified by workbook reload + value cross-check; CHANGELOG `[Unreleased]` Added entry in the same working tree (commit left to the human) |
| KANBAN-037 | v0.19.0 prep (2026-08-16) | `site/` → `docs/posit/` + `tests/test_posit_site.py` | **Posit Cloud integrated portal (complementary to the SPA)** — Quarto website (`site/` sources) rendering into `docs/posit/` (the SAME `docs/` tree GH Pages serves; zero Actions — Pages deploys from branch, Posit Cloud deploys via `quarto render site` + publish). Three integrated sections at one URL prefix: experiment log (generated from `reports/experiment_log.jsonl` by `site/_pre-render.py` with the canonical `render_full_log` renderer; full run index + per-run metadata/scores/tokens/diagnostics + per-run deep links into `../index.html#/run/{n}`), kanban board (live `MESSAGE_BOARD.md` copy), discussion board (live `MESSAGE_BOARD_DISCUSSION.qmd` copy, agent colors preserved); portal↔SPA navbar links both ways. Custom blue→teal gradient theme (cosmo light / darkly dark, toggle, navbar, search, TOC). Rendered output committed; `.gitignore` Quarto/Posit section. Repairs: 6 discussion entries missing `:::` closers (append-only preserved, pinned by test); KANBAN-037/038 number-collision reconciled. 8+1 tests green (incl. skip-if-no-quarto determinism); SPA browser audit green. Docs: site/README (new), docs/README, README, wiki/Site.md |
| KANBAN-035 | v0.19.0 (2026-08-16) | `gpt-5-nano` × sorter_v13, full-509 | **GPT cheapest-model benchmark on the sorter subtype surface** — `openai/gpt-5-nano` ($0.05/M prompt + $0.40/M completion — smallest & cheapest GPT on OpenRouter) on the champion sorter_v13 prompt, full 509-doc corpus, reasoning medium, temp 0.1, 0 errors, Phoenix sink, `--research-funding-key` (human directive). **strict 0.8978 (CI [0.8703, 0.9234]) vs the qwen3.7-flash champion 0.9430 = −4.5pp — far outside the ±0.006 noise band → nano does NOT match the champion; a cost-floor frontier arm only** (equiv 0.9018, doc_type 0.9941; 52 fails: 41 family_confusion / 6 other_fallback / 3 function_over_form / 2 equivalent_family). Run cost ≈ **$0.48** (6.94M tokens). Run `gpt-5-nano_sorter_v13_subtype_langfuse`; manifest `data/manifests/gpt5nano_sorter_v13_509.jsonl` |
| KANBAN-034 | v0.19.0 (2026-08-15) | `--research-funding-key` gate (close-out commit) | **Externally-funded OpenRouter key behind a production-only flag** — `RESEARCH_FUNDING_OPENROUTER_API_KEY` in `.env` reachable ONLY via `--research-funding-key` on all 10 eval runners (default key untouched); `src/env_utils.py` `resolve_openrouter_key()` / `assert_production_run()` / `add_research_funding_flag()` — the gate HARD-REFUSES dry-runs and pilot-scale samples (<100 rows, or less than the full dataset when smaller) with `SystemExit` before any LLM call and prints a funding banner; 12 new tests + all runner smoke suites green. Code swept into `a6964c8`; changelog/board/docs in the close-out commit |
| KANBAN-030 | v0.19.0 (2026-08-15) | commit `e0f758e` | Contract-specialist v1..v16 archived to `src/prompts_archive.py` (FROZEN pre-documentation lineage, imported back into `prompts.py`) — **file 227 KB → 155 KB (−32%)**, all 32 version strings byte-identical, every version key resolvable; archive rule pinned by tests (never edit an archived constant — a change = a new version key); 384 tests green |
| KANBAN-029 | v0.19.0 (2026-08-15) | `contracts_specialist_v32` | effective_date rule_contradiction repair — **CLEAN full-510 A/B (495-row intersection): v32 0.8799 vs v31 0.8746 = +0.0053, CI [−0.0052, +0.0159], P(Δ≤0)=0.1715 — INSIDE the ±0.011 noise band → LOGIC REPAIR, v31 stays champion** (the first candidate run's +0.0115 was survivorship bias from 52 transient errors); effective_date field +0.0171 (23 improved / 11 regressed, 16/23 on the diagnosed target cluster) → v32 = effective_date field specialist; **never-null over-fire cluster deterministic → banked as the v33 carve-out** (stated-FULL-date requirement). Memo `memos/contracts_specialist_v32.md` |
| KANBAN-026 | v0.19.0 (2026-08-15) | LegalBench hearsay + CUAD-subtask prompt-iteration series (arms 1-7) | Arm 1: v0 baseline @5 = 1.0 (saturates the train surface). Arm 2: 94-row official test split wired (`--test`). Arm 3: Langfuse dataset mirror + LangSmith retargeted to project HEARSAY. Arm 4: `legalbench_task_v1` @94 = **0.8511 (80/94) vs v0 0.7766–0.7872** (directional win, P=0.0905). Arm 5: `legalbench_task_v2` @94 = **0.8830 (83/94)** vs v1-control 0.8617 (logic repair, P=0.3345). Arm 6: `legalbench_task_v3` **7/7 tasks 42/42 = 100% vs v0 36/42**. Arm 7: `legalbench_task_v4_*` CUAD subtask series — hygiene base + CRE (0.8333→1.0) + CNTS (→1.0) operative rules, 5 subtasks at ceiling. Memos `memos/legalbench_task_v1/v2/v3/v4.md`; runs `..._test` + `..._subtask_*` in the experiment log |
| KANBAN-024 | v0.19.0 (2026-08-15) | LangSmith tracing + live-error analysis | `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true` + `LANGSMITH_PROJECT=llm-mailroom` in `.env`/`.env.example`; AGENTS.md env docs; verified every LangChain LLM call auto-traces to the project, coexisting with Braintrust's `setup_langchain`. **Live-error analysis (langsmith SDK): 100 runs / 14d, all 10 errors are OpenRouter-exported `OpenRouter Request` spans — qwen via Alibaba 429, ~230ms burst rate-limit, OpenRouter failover recovered 90/100.** Braintrust span ingestion failing on plan limit (`num_log_bytes_calendar_months`, org UW-Madison-Capstone) — LangSmith is the reliable span sink. Docs-only; 359 tests green |
| KANBAN-027 | v0.19.0 (2026-08-15) | `d6c6c9d` | **Repository streamlining + navigation pass** — README Table of Contents + Layout-tree repair (src modules mis-nested under `wiki/`, stale script list + test counts 223→375, prompt tables to sorter_v12/contracts_specialist_v31, `BRAINTRUST_LOGGING` conditional documented); `src/README.md` (+braintrust_logging/eval_shims/master_labels/metrics), `memos/README.md` (table bug + v28/v30/v31/sorter_v10_v11 rows), `scripts/README.md` (all runners + eda/) refreshed; `scripts/backfill_cost_estimates.py` nested under `scripts/reporting/` (live refs updated, CHANGELOG history untouched). Docs-only + safe nesting; 375 tests green, site render audit clean, no new release-gate failures. CHANGELOG `[Unreleased]` Changed entry in the same commit |
| KANBAN-032 | v0.19.0 (2026-08-15) | `sorter_v14` (rule 30) | **Sorter marketing-title strengthening arm — LOGIC REPAIR, NOT a win (v13 stays champion).** Full-509 A/B (fp `c2341957…`, seed 42, temp 0.1, reasoning medium): **v14 0.9371 vs v13-clean 0.9430 = −0.0059, paired CI [−0.0177, +0.0059], P(Δ≤0)=0.8765 — inside the ±0.006 noise band, negative direction.** Marketing cell **14/17 → 16/17** (Audible + PACIRA recovered, rule-30 reasoning pinned; Zounds resists even its own literal example). **Flagged counterfactual FIRED: Playboy "CONTENT LICENSE, MARKETING AND SALES" regressed license→marketing — carve-out (a) too narrow (cited only the exact "Content License Agreement" phrase) → banked v15 lesson: widen to any license-PRIMARY title.** 4/6 other regressions are untouched-family noise. Memo `memos/sorter_v14.md` |
| KANBAN-031 | v0.19.0 (2026-08-15) | `sorter_v13` (rule 29) + Phoenix sink | **Sorter maintenance title-wins arm — AGGREGATE WIN.** Full-509 A/B (fp `c2341957…`, seed 42, temp 0.1, reasoning medium): **v13 0.9430 vs the v12 rerun control 0.9293 = +0.0137, paired CI [+0.0020, +0.0255], P(delta<=0)=0.0090 — OUTSIDE the ±0.0059 identical-prompt noise band → new aggregate champion** (v9 → v12 → v13). Maintenance cell **30/34 → 34/34** (SUNTRONCORP/WELLSFARGO/PRIMEENERGY/AtnInternational recovered, rule-29 reasoning pinned); recovered 8 / regressed 1 (ImperialGarden = pre-existing rule-24 outsourcing variance flip, NOT rule 29 → banked v14 lesson). 0-risk counterfactual (34/34 maintenance-titled docs GT maintenance). First v13 run degraded (93/509 connection-error defaults) → clean rerun before any claim. `run_langfuse_subtype_eval.py` selects Phoenix tracing by default (`tracing_backend="phoenix"`). Memo `memos/sorter_v13.md` |
| KANBAN-023 | v0.19.0 (2026-08-15) | `sorter_v12` (rule 28) | **Sorter strategic_alliance title-wins arm** — the first banked KANBAN-013 cluster. Full-509 A/B (fp `c2341957…`, seed 42, temp 0.1, reasoning medium): **v12 0.9234 vs the clean v9 rerun 0.9175 = +0.0059, paired CI [−0.0098, +0.0216], P(Δ≤0)=0.251 — INSIDE the noise band → logic repair, NOT an aggregate win** (identical-prompt v9 rerun itself moved +0.0059); the strategic_alliance cell is deterministically fixed **28/32 → 31/32** (Iovance/Giggles/Adaptimmune recovered with rule-28 reasoning pinned; Intricon remains — license carve-out didn't override the substance read), recovered 9 / regressed 6 (none rule-28-driven; 2 equiv-recovered). v9 stays aggregate champion; v12 joins the frontier as the strategic_alliance field specialist. NOTE: the first v9 @509 control rerun was degraded (42 transient errors) — replaced by a clean rerun. Memo `memos/sorter_v12.md` |
| KANBAN-028 | v0.19.0 (2026-08-15) | master_clauses CSV + loader | **Master ground-truth CSV added to the repo + repo-local default** — `data/cuad/master_clauses.csv` (510 CUAD contracts × 40 normalized `-Answer` columns) committed; `DEFAULT_MASTER_LABELS` resolves to the repo-local copy first (`MASTER_LABELS_CSV` env wins; sibling llm-mailroom path fallback); loader normalizes the stray-space `Notice Period To Terminate Renewal- Answer` header variant so that category's answer loads (was silently dropped). 377 tests green. KANBAN-027 = ATOM's separate completed repo-streamlining card |
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