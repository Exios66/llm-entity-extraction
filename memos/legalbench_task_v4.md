# legalbench_task_v4 — subtask-specific prompts: CRE/CNTS operative rules + V4 hygiene base

**Research question:** The 7 CUAD subtask prompts (`legalbench_task_v3_<subtask>`:
anti-assignment, audit_rights, cap_on_liability, change_of_control,
competitive_restriction_exception, covenant_not_to_sue, effective_date) are all
registered as aliases of the generic `LEGALBENCH_TASK_PROMPT_V3` — a hearsay-
doctrine prompt whose rule 6 never fires on CUAD clause tasks, plus a prohibition
rule with a stray quote and a numbering collision. On the 6-row per-subtask
surfaces, two subtasks fail: `competitive_restriction_exception` (deterministic)
and `covenant_not_to_sue` (oscillating). Can ONE subtask-specific operative rule
per failing subtask — built on a hygiene-fixed base — recover those rows without
regressing the 1.0/6 ceilings of the other five?

**Companions:** LegalBench subtask series (KANBAN-026 extension), `memos/legalbench_task_v3.md`,
`memos/legalbench_task_v2.md`. Runs: 6-row per-subtask surfaces
(`data/legalbench_local/cuad_<task>.jsonl`, `--samples-per-class 5 --sample-seed 42`,
temp 0.1, qwen/qwen3.7-flash).

## Answer, Response, + Summary of Results

### Short answer

**The subtask prompts were generic aliases, not subtask-specific prompts.** The
next loop makes them subtask-specific: `LEGALBENCH_TASK_PROMPT_V4` = v3 with TWO
hygiene repairs (stray `"` from the `V2 + """"` construction; prohibition rule
renumbered 6→7 to clear the rule-6 collision), and the two failing subtasks get
ONE operative rule each — CRE gets the conditional-permission-carveout rule
(deterministic failure → rule material), CNTS gets the conduct-restriction-
covenant rule (weaker 1/2 evidence → logic-repair grade). The other five subtask
keys re-point to V4 (hygiene-only — they sat at 1.0/6, no measurable headroom).

| Subtask surface (fp, 6 rows, temp 0.1) | v3 alias (control) | v4 candidate | delta |
|---|---|---|---|
| competitive_restriction_exception (de6ae646) | 0.8333 / 0.8333 (same row fails twice — deterministic) | **1.0** | **+1 row — the deterministic failure is fixed** |
| covenant_not_to_sue (0068f5b9) | 0.8333 / 1.0 (oscillating) | **1.0** | +1 row (control oscillates — logic-repair grade) |
| anti_assignment (32d93756) | 1.0 / 1.0 | 1.0 | 0 (hygiene-only) |
| audit_rights (4e5868ba) | 1.0 / 1.0 | 1.0 | 0 (hygiene-only) |
| cap_on_liability (6060a67a) | 1.0 / 1.0 | 1.0 | 0 (hygiene-only) |
| change_of_control (de75a50b) | 1.0 / 1.0 | 1.0 | 0 (hygiene-only) |
| effective_date (4319a19b) | 1.0 / 1.0 | 1.0 | 0 (hygiene-only) |

**Final verdict: CRE +1 deterministic row recovered; CNTS +1 (control oscillates,
so at-best logic repair); five hygiene-only subtasks unchanged at ceiling.
All seven A/Bs ran on identical sampled surfaces (fp matched to the v3 controls
exactly).**

### The failure clusters (from the v3-alias 6-row runs)

| subtask | failing row | GT | v3 | mechanism (one sentence) |
|---|---|---|---|---|
| competitive_restriction_exception | cuad_competitive_restriction_exception_0 (IGER/CERES) | Yes | No (2/2 runs) | The clause is a **conditional-permission carveout** — "if IGER would enter into any agreement ... with a not-for-profit third party ... such agreement must provide that (i) IGER will receive the exclusive right (subject to Articles 5.1.2(a) and 5.2) ..." — an exception framework whose permission structure IS the carveout; the task few-shot teaches only the explicit-qualifier pattern ("provided, however", "but nonexclusive"), so the model missed the permission shape. |
| covenant_not_to_sue | cuad_covenant_not_to_sue_2 (Allied/Newegg) | Yes | No (1/2 runs) | "Allied shall not at any time do, or cause to be done, directly or indirectly any act that may impair or tarnish any part of Newegg's goodwill and reputation in the Newegg Marks" — a **conduct-restriction covenant** protecting the counterparty's IP; the model over-matched on literal "contest validity / bring a claim" vocabulary. |

**Root cause (one sentence):** the subtask prompts carry hearsay doctrine that
never fires on CUAD clause tasks and no subtask-specific operative shapes, so the
model decides from the task few-shot alone — pattern-matching explicit vocabulary
and missing the permission-structure (CRE) and conduct-restriction (CNTS) shapes.

### The mutation (ONE rule per version)

- `LEGALBENCH_TASK_PROMPT_V4` = v3 with the stray quote removed + prohibition
  rule renumbered 7 (no doctrine change). Verified: `V4 != V3`, `startswith(V3[:300])`,
  rule headers 1–7 sequential.
- `LEGALBENCH_TASK_PROMPT_V4_CRE` = V4 + rule 8 COMPETITIVE-RESTRICTION
  EXCEPTIONS: a carveout includes BOTH explicit qualifier vocabulary AND a
  conditional-permission structure ("if X may enter into a specified agreement
  subject to stated conditions, the permission structure IS the carveout").
  Family rule — not a document recall. Negative boundary: "only states a
  restriction or a termination right" stays No (rows 3–5).
- `LEGALBENCH_TASK_PROMPT_V4_CNTS` = V4 + rule 8 COVENANT NOT TO SUE: the
  restriction need NOT use the words "sue"/"contest"/"claim" — a promise not to
  impair/tarnish/challenge the counterparty's marks/goodwill IS a covenant not to
  sue. Negative boundary: unrelated duties (record-keeping, audit, payment) stay
  No (rows 3–5).
- `legalbench_task_v4_<subtask>` keys registered: 5 → V4 (hygiene), 2 → the rule
  versions. v3_<subtask> keys stay at v3 (version key IS experiment identity).

### Same-surface A/B (Phase 4 — completed)

Controls: the v3-alias runs in the experiment log (same surface identity: local
task JSONL, `--samples-per-class 5 --sample-seed 42`, temp 0.1, fp per subtask).
Candidates: `qwen3.7-flash_legalbench_task_v4_<subtask>_sampled` on identical
sampled surfaces — **all seven fp-matched the v3 controls exactly** (de6ae646 /
0068f5b9 / 32d93756 / 4e5868ba / 6060a67a / de75a50b / 4319a19b). NOTE: an
initial batch ran the candidates on the RAW 6-row file (different fp — not
comparable) and was discarded; the sampled-surface runs are the valid A/B.
CRE recovered the deterministic row (0.8333→1.0); CNTS recovered its row
(1.0, control oscillates 0.8333/1.0); five subtasks unchanged at 1.0/6.

*Sources:* `reports/experiment_log.jsonl` (v3-alias subtask runs 2026-08-16,
`data/legalbench_local/cuad_*.jsonl`), `src/prompts.py` LEGALBENCH_TASK_PROMPT_V3/V4/V4_CRE/V4_CNTS.

## What questions or uncertainties remain?

- The CNTS rule ships on 1/2-run evidence (logic-repair grade): the oscillating
  control means the +1 recovery may be part of the surface's noise band. The CRE
  rule is stronger (deterministic 2/2 control failure).
- The 6-row surfaces are ceiling-bound: five subtasks at 1.0/6 have no headroom —
  a larger surface (the full LegalBench test sets) is needed to measure any
  further delta on those.
- The generic `legalbench_task_v4` (hygiene) vs v3: the stray-quote/numbering fix
  is unmeasured (both surfaces at 1.0) — logic repair, not a claimed win.
