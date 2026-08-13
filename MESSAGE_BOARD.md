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

| Card | Status | Task (summary) | Owner | Updated | Target release | CHANGELOG / evidence |
|---|---|---|---|---|---|---|
| KANBAN-004 | `backlog` | **Extraction next arm (v24 candidate)** — attack the 30-span residual: span-choice/boundary divergence at token level (v18-matched spans still missed; ko ~0.85 ceiling at reasoning=none). Diagnostic first: classify the 30 misses (boundary-shift vs abbreviation vs wrong-span) before writing prompt rules. | unclaimed | 2026-08-12 | v0.16.0 | `V16_PROPOSITION.md` §14.3/§15.1; `reports/same_scorer_scores.json` |
| KANBAN-005 | `backlog` | **Mirror sync → llm-mailroom (partial done)** — v0.15.0 experiment-log mirror re-synced into llm-mailroom (`75d6fa0` DOCS SYNC). REMAINING: (a) sync the 58-run log incl. the v7 A/B, (b) sync the v22/v23 champion prompts into the llm-mailroom Langfuse project (`sync_langfuse_prompts.py --env-file langfuse-llm-mailroom.env`), (c) full-pipeline validation runs in llm-mailroom-experiments per the production-config decision (ties to KANBAN-008). | unclaimed | 2026-08-12 | v0.16.0 | AGENTS.md "Langfuse projects" / "Mirror sync"; llm-mailroom `docs/reports/experiments/experiment_log.md` |
| KANBAN-006 | `backlog` | **HITL annotation queue processing** — tooling DONE (score-config support landed `ca20d17`: get_or_create_annotation_config + default score-config in `run_annotation_queue.py`, FakeLangfuse tests). REMAINING: adjudicate the pending llm-dojo queue items (extraction < 0.85 + sorter failure queue) and feed corrections into the next prompt iteration. | unclaimed | 2026-08-12 | v0.16.0 | `scripts/eval/run_annotation_queue.py status`; `tests/test_annotation_queue.py`; wiki `Annotation-Queues.md` |
| KANBAN-008 | `backlog` | **v23×max ko arm — production decision** — ko 0.8510 @ 2.6× cost, 0 parse errors vs v22×none 0.9512 overall. Decide the recommended production config (or split: overall arm vs ko arm) and record it in README/AGENTS docs. | unclaimed | 2026-08-12 | v0.16.0 | `V16_PROPOSITION.md` §15.1; memo `contracts_specialist_v23.md` |
| KANBAN-009 | `backlog` | **Score-drift hygiene** — extend the same-scorer rescore pipeline beyond the 50-doc series if a scorer rule changes again; keep `reports/same_scorer_scores.json` current per run. | unclaimed | 2026-08-12 | v0.16.0 | `scripts/reporting/rescore_manifests.py`; `tests/test_rescore_manifests.py` |
| KANBAN-011 | `backlog` | **Post-v23 model sweep (gated OPEN)** — run v22/v23 prompts × {deepseek-v4-flash, deepseek-v4-pro} on the same 50 docs to quantify the remaining model-bound segmentation gap (the v18 sweep proved scope-fidelity is model-agnostic; confirm the ko 0.85→0.89 plateau closes at the newest prompts). | unclaimed | 2026-08-12 | v0.16.0 | memo `model_sweep_v18.md`; `V16_PROPOSITION.md` §9.3/§15 |
| KANBAN-012 | `backlog` | **sorter_v8 — next classification iteration** — remaining confusion clusters from the v7 243-doc A/B (32→30 fails): development→collaboration/license/franchise (5), outsourcing→manufacturing (2), affiliate→marketing (2), ip→license (2, new). Data-backed rules first (per-cluster error quotes), then the same-surface A/B; target strict > 0.90 on the current corpus revision (fb9f939d). | unclaimed | 2026-08-12 | `[Unreleased]` → v0.16.0 | `V16_PROPOSITION.md` §16.2–16.3; `reports/experiment_log.jsonl` run `qwen3.7-flash_sorter_v7_subtype_langfuse` |
| KANBAN-013 | `backlog` | **Corpus-revision effect quantification** — v6 rerun on a 195-doc draw of the CURRENT corpus revision (fb9f939d) to isolate revision-shift vs prompt-gain (the 0.9436-era v6 numbers sit on fingerprint 2e1fe4b7 and are not comparable); needed before any >0.95 sorter claim. | unclaimed | 2026-08-12 | v0.16.0 | `V16_PROPOSITION.md` §16.3 |
| KANBAN-014 | `backlog` | **v0.16.0 release** — `release.py --bump`, convert `[Unreleased]` (sorter_v7 A/B + memos polish) → v0.16.0, pyproject 0.15.0→0.16.0, site data regen + render audit, `release.py --check` (full test suite), tag + push + GitHub release with notes, wiki sync (`./wiki/sync-wiki.sh`). | unclaimed | 2026-08-12 | v0.16.0 | AGENTS.md "Release workflow"; CHANGELOG `[Unreleased]` |
| KANBAN-015 | `backlog` | **Cross-corpus subtype pilot** — validate sorter_v7's corpus-convention rules on a non-SEC/non-CUAD corpus (LegalBench MAUD agreements): do the O&M/development/promotion rules transfer, or are they CUAD-filing-specific? | unclaimed | v0.17.0 | subtype memo "What questions…?" #1; `memos/subtype_classification_improvements.md` |
| KANBAN-016 | `backlog` | **Long-doc chunking confirmation subset** — targeted subset of the 100k+-char contracts (Antares, MOELIS, Phasebio-class) to confirm the chunking completeness guarantee directly on at least one specialist arm. | unclaimed | v0.17.0 | memo `entity_extraction_improvements.md` #1 |
| KANBAN-017 | `backlog` | **OCR-mangled date normalizer** — SPRINGBANK's "7t h day of April, 2020." is a real GT date the model misses; a normalization step ("7t h"→"7th") makes the GT parseable and the date miss punishable; add scorer/normalizer unit tests. | unclaimed | v0.17.0 | memo `contracts_specialist_v20.md` #2 |
| KANBAN-018 | `backlog` | **sorter_v7 research memo** — the A/B landed without its memo (repo convention: memo in the same commit as the finding). Write `memos/sorter_v7_classification_improvements.md` (research-question format, scorecard table + Verdict callout, V16 §16 cross-ref). | unclaimed | v0.16.0 | AGENTS.md "Research memos"; CHANGELOG `[Unreleased]` sorter_v7 entry |
| KANBAN-019 | `backlog` | **Sorter vision re-eval on the current corpus revision** — `sorter_vision_v0/v1` have no runs on revision fb9f939d (only 2 classification runs total, on the old corpus); re-A/B vision vs text on the new revision before trusting vision in the pipeline. | unclaimed | v0.17.0 | `src/prompts.py` vision block; `reports/experiment_log.jsonl` (vision coverage) |

**Sweep rule:** when a release ships, re-target every non-done card to the
new `[Unreleased]` version and move landed cards to the Archive. (Last sweep:
2026-08-12 — v0.16.0 prep — KANBAN-003/010 archived below; KANBAN-001/002/007
archived at the previous sweep.)

## Discussion board

Dated, append-only log. Newest entry goes at the TOP. Format:
`**YYYY-MM-DD — <agent/human> — <card ref(s)>** <what happened / decision / question / blocker>`. No editing history.

- **2026-08-12 — opencode — full-state sweep (KANBAN-003/010 done; +KANBAN-012…019)** Board
  resynced to the current repo state (working tree clean, HEAD `cbb5b93`):
  **KANBAN-003 archived** — the sorter_v7 243-doc A/B completed (strict
  0.8765, +0.82pp; promotion cluster eliminated; run 58; changelog entry in
  place) but the >0.95 target was NOT met → spawned KANBAN-012 (v8 cluster
  iteration) + KANBAN-013 (corpus-revision effect). **KANBAN-010 archived** —
  `costs` meta restored in `docs/data/meta.json` (openrouter activity CSV).
  **KANBAN-005/006 updated** with partial-done tooling (llm-mailroom mirror
  synced `75d6fa0`; annotation-queue score-config support `ca20d17`).
  New backlog cards from the repo's own open questions: KANBAN-012 sorter_v8,
  KANBAN-013 revision-effect, KANBAN-014 v0.16.0 release, KANBAN-015 cross-
  corpus pilot, KANBAN-016 long-doc subset, KANBAN-017 OCR-date normalizer,
  KANBAN-018 v7 research memo, KANBAN-019 vision re-eval. Claim before
  starting; v0.16.0 release (KANBAN-014) needs KANBAN-012/013/018 decided
  first (or explicitly deferred).
- **2026-08-12 — opencode — governance** Timestamp discipline enforced
  repo-wide: AGENTS.md now carries the explicit "Agent message board" section
  — mandatory lifecycle (claim → lane-change → blocked → completion, each
  with `YYYY-MM-DD` timestamps; **update your Kanban entry and move it to
  the correct status BEFORE declaring any task, objective, or experimental
  run finished**) plus explicit best practices (one owner per card, append-
  only discussion, visible reopenings, archive-as-audit-trail, semver sweep,
  commit references, conflict rule). The board table gained the `Updated`
  column so every status carries its timestamp. All agents must read
  AGENTS.md §"Agent message board" and MESSAGE_BOARD.md "How to use this
  board" at the start of every session.
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
| KANBAN-003 | `[Unreleased]` → v0.16.0 (2026-08-12) | `cbb5b93` EXPERIMENT: sorter v7 A/B | **v7 WINS the 243-doc same-surface A/B**: strict 0.8683→0.8765 (+0.82pp), equiv 0.8807→0.8889 (+0.82pp), promotion→marketing cluster 6→0, fails 32→30. Caveat landed honestly: current corpus revision (fb9f939d) is harder than the 0.9436-era (2e1fe4b7) — strict >0.95 NOT met; follow-ons KANBAN-012/013. Run 58, changelog `[Unreleased]` entry, `V16_PROPOSITION.md` §16 |
| KANBAN-010 | `[Unreleased]` → v0.16.0 (2026-08-12) | `cbb5b93` (site data regen) | **OpenRouter cost accounting restored**: `docs/data/meta.json` `costs` block present again — source `openrouter_activity_2026-08-11.csv` (api_key "Laptop v3", export 2026-08-09→08-10, per_run coverage ×425 calls incl. embeddings); the cumulative-cost card renders from the current regen |
| KANBAN-007 | v0.15.0 (2026-08-12) | tag `v0.15.0` → `4b6ad5f`; commits `93eb938`, `0a4051e`, `0afdf2e` | Release finalized: changelog dedup-repaired, tag pushed, GitHub release with dedicated notes published; `release.py --check` green (303 tests) |
| KANBAN-002 | v0.16.0 prep (2026-08-12) | `ac156a5` MESSAGE BOARD: land the dirty tree + board sweep | Dirty tree landed: experiment log regen (57 runs), site data regen, `sorter_v7` registration + test, AGENTS.md board governance, changelog `[Unreleased]` entry for sorter_v7 |
| KANBAN-001 | v0.16.0 prep (2026-08-12) | `ac156a5` | `SORTER_PROMPT_V7` constant + `PROMPT_VERSIONS["sorter_v7"]` + `test_sorter_v7_data_backed_rules` landed (18 prompt tests green). Evaluation tracked in KANBAN-003 |
| *(v0.15.0 content)* | v0.15.0 (2026-08-12) | tag `v0.15.0` | All v0.15.0 changelog entries (v18 sweep → v19 → v20 → v21 → v22 → v23 → v23×max; scorer fixes; annotation queues ×2; memos tab + 6 memos; wiki Langfuse-Traces + Annotation-Queues; rescore pipeline; two-project Langfuse strategy; prompt-store cleanup) — cataloged in CHANGELOG.md v0.15.0, each with its own commit in `git log v0.14.0..v0.15.0` |

When moving a card here: fill this table AND leave the lane row visible in
the Key Kanban table only if the card is still open; closed cards live ONLY
here (the table above holds open work, the archive holds the record).
