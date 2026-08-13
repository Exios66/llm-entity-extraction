# Agent Message Board — llm-entity-extraction

The living, shared Kanban canvas for ALL agents (and humans) working in this
repository. It is the single place where tasks that still need to be
completed, are in progress, are blocked, need to be revisited, or have been
finished are tracked — with every card tied to a semantic-version release in
`CHANGELOG.md`.

**This is a WORKING DOCUMENT, not documentation.** It is meant to be
modified progressively as work happens. Finished work is never deleted — it
moves to the Archive (bottom of this file) so the full audit trail stays
intact.

## How to use this board (READ FIRST — every agent, every session)

1. **Read this board before starting ANY task** — check the Kanban table and
   the discussion log for (a) cards already claimed by another agent,
   (b) cards that cover the work you were about to do, and (c) context posts
   that affect your work.
2. **Never start work that is already claimed.** If a card exists, build off
   it — comment on it, don't duplicate it. If a card is In Progress with an
   owner, that owner has the work; offer to help on the discussion board
   instead of racing them.
3. **Claim a card by moving it to `in_progress`** and setting Owner to your
   agent name + today's date. If no card covers your task, ADD a new card
   (next free number) and claim it — never work silently.
4. **Update the board while you work, not just when you finish.** Post a
   dated entry to the Discussion board on: claiming a card, any material
   decision/result, a blocker, a scope change, or handing work off.
5. **Finish = card moved to Archive** with: the CHANGELOG version or
   `[Unreleased]` bullet it landed in, the commit, and the key result. A card
   is not done until its CHANGELOG entry exists (same-commit rule in
   AGENTS.md).
6. **Every lane change is timestamped.** Status column never moves without
   updating the `Updated` column (`YYYY-MM-DD`) and a dated discussion
   entry. The `Updated` column is the truth about when a card last changed.
7. **Close out before you report done.** Updating your card (correct status
   + timestamp + closing discussion entry) is the LAST step of EVERY task,
   objective, and experimental run — before you tell the user it finished.
8. **Revisits are normal.** A card in `done` can be reopened by moving it
   back to `backlog` with a discussion post explaining why (regression,
   new data, superseded assumption). Never edit history — add a post.
9. **Semantic versioning is the spine.** Every open card must name its
   target release (`[Unreleased]`, `v0.X.Y`). When a release ships
   (`scripts/release.py --bump`), sweep the board: cards that landed move to
   Archive under that version; cards that did not land are re-targeted to the
   next release. Keep the board in sync with `CHANGELOG.md` — the two must
   never disagree about what is done.
10. **Reference cards in commits** — `MESSAGE BOARD: KANBAN-004 claimed`
    or `sorter_v7 (KANBAN-001): ...` so the git history maps to the board.

## Status lanes

| Lane | Meaning | Who can move it |
|---|---|---|
| `backlog` | Todo — not yet started. The release it targets is set in the table. | anyone (add/claim) |
| `in_progress` | Actively being worked by the Owner. ONE owner per card. | owner |
| `blocked` | Stuck — waiting on data, keys, a decision, or another card. Post the blocker in Discussion. | owner |
| `in_review` | Work done, awaiting validation (tests, A/B, release gate) before it can land. | owner → reviewer |
| `done` | Finished and recorded in the Archive with CHANGELOG linkage. | reviewer/releaser |

## Key Kanban table

Status codes: `backlog` · `in_progress` · `blocked` · `in_review` · `done`

| Card | Status | Task (summary) | Owner | Target release | CHANGELOG / evidence |
|---|---|---|---|---|---|
| KANBAN-003 | `backlog` | **sorter_v7 A/B on the 250-doc stratified surface** — same seed as the v6 run; target strict > 0.95; verify each of the 3 rules (consortium O&M→maintenance, development-over-license, promotion guard) with failure-insight quotes before calling it. | unclaimed | `[Unreleased]` → v0.16.0 | v6 full-corpus run: strict 0.9312, 35 fails (qwen3.7-flash_sorter_v6_subtype_langfuse, run 57); prompt registered as `sorter_v7` |
| KANBAN-004 | `backlog` | **Extraction next arm (v24 candidate)** — attack the 30-span residual: span-choice/boundary divergence at token level (34→30 spans still missed; ko ~0.85 ceiling at reasoning=none). Diagnostic first: classify the 30 misses (boundary-shift vs abbreviation vs wrong-span) before writing prompt rules. | unclaimed | v0.16.0 | `V16_PROPOSITION.md` §14.3/§15.1; `reports/same_scorer_scores.json` |
| KANBAN-005 | `backlog` | **Mirror sync → llm-mailroom** — apply the v22/v23 champion prompts to the llm-mailroom pipeline project (Langfuse key file drop-in + `sync_langfuse_prompts.py --env-file`); regenerate its synced experiment log. | unclaimed | v0.16.0 | AGENTS.md "Langfuse projects" / "Mirror sync"; `scripts/eval/sync_langfuse_prompts.py` |
| KANBAN-006 | `backlog` | **HITL annotation queue processing** — work the pending llm-dojo queue items (extraction < 0.85 + sorter failure queue): adjudicate, feed corrections into the next prompt iteration. | unclaimed | v0.16.0 | `scripts/eval/run_annotation_queue.py status`; wiki `Annotation-Queues.md` |
| KANBAN-008 | `backlog` | **v23×max ko arm — production decision** — ko 0.8510 @ 2.6× cost, 0 parse errors vs v22×none 0.9512 overall. Decide/documented the recommended production config (or split: overall arm vs ko arm) and record it in README/AGENTS docs. | unclaimed | v0.16.0 | `V16_PROPOSITION.md` §15.1; memo `contracts_specialist_v23.md` |
| KANBAN-009 | `backlog` | **Score-drift hygiene** — extend the same-scorer rescore pipeline beyond the 50-doc series if a scorer rule changes again; keep `reports/same_scorer_scores.json` current per run. | unclaimed | v0.16.0 | `scripts/reporting/rescore_manifests.py`; `tests/test_rescore_manifests.py` |
| KANBAN-010 | `backlog` | **Restore OpenRouter cost accounting on the site** — the latest `build_site.py` regen dropped the `costs` meta + per-run `cost` blocks because no activity CSV was present. Re-ingest the OpenRouter activity-log export (Settings → Activity Logs) and rebuild; verify the cumulative-cost card renders. | unclaimed | v0.16.0 | `scripts/site/build_site.py` (activity CSV ingest); site `#/` cost card; this commit's regen has no `costs` block in `docs/data/meta.json` |
| KANBAN-011 | `backlog` | **Post-v23 model sweep (gated OPEN)** — run v22/v23 prompts × {deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs to quantify the remaining model-bound segmentation gap (the v18 sweep proved scope-fidelity is model-agnostic; confirm the ko 0.85→0.89 plateau closes at the newest prompts). | unclaimed | v0.16.0 | memo `model_sweep_v18.md`; `V16_PROPOSITION.md` §9.3/§15 |

**Sweep rule:** when a release ships, re-target every non-done card to the
new `[Unreleased]` version and move landed cards to the Archive. (Last sweep:
v0.15.0 shipped 2026-08-12 — KANBAN-001/002/007 archived below.)

## Discussion board

Dated, append-only log. Newest entry goes at the TOP. Format:
`**YYYY-MM-DD — <agent/human> — <card ref(s)>** <what happened / decision / question / blocker>`. No editing history.

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
| KANBAN-007 | v0.15.0 (2026-08-12) | tag `v0.15.0` → `4b6ad5f`; commits `93eb938`, `0a4051e`, `0afdf2e` | Release finalized: changelog dedup-repaired, tag pushed, GitHub release with dedicated notes published; `release.py --check` green (303 tests) |
| KANBAN-002 | v0.16.0 prep (2026-08-12) | this commit (`KANBAN-002/007/001` board bootstrap) | Dirty tree landed: experiment log regen (57 runs), site data regen, `sorter_v7` registration + test, AGENTS.md board governance, changelog `[Unreleased]` entry for sorter_v7 |
| KANBAN-001 | v0.16.0 prep (2026-08-12) | this commit | `SORTER_PROMPT_V7` constant + `PROMPT_VERSIONS["sorter_v7"]` + `test_sorter_v7_data_backed_rules` landed (18 prompt tests green). Evaluation tracked in KANBAN-003 |
| *(v0.15.0 content)* | v0.15.0 (2026-08-12) | tag `v0.15.0` | All v0.15.0 changelog entries (v18 sweep → v19 → v20 → v21 → v22 → v23 → v23×max; scorer fixes; annotation queues ×2; memos tab + 6 memos; wiki Langfuse-Traces + Annotation-Queues; rescore pipeline; two-project Langfuse strategy; prompt-store cleanup) — cataloged in CHANGELOG.md v0.15.0, each with its own commit in `git log v0.14.0..v0.15.0` |

When moving a card here: fill this table AND leave the lane row visible in
the Key Kanban table only if the card is still open; closed cards live ONLY
here (the table above holds open work, the archive holds the record).
