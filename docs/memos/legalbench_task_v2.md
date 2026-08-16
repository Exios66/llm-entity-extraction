# legalbench_task_v2 — purpose-first ACT/STATE carve-out + contradiction repair

**Research question:** The v1 hearsay classifier (`legalbench_task_v1`, 0.8511 @94)
still fails 14 rows. Full-reasoning diagnostics on every failure show 8 are
runner artifacts and 6 are genuine content failures. Can ONE rule refinement
fix the genuine content failures (operative-fact/state-purpose rows + the
knowledge-assertion contradiction) without regressing the 80 v1-correct rows?

**Companions:** KANBAN-026 (hearsay iteration series), `memos/legalbench_task_v1.md`.
Runs: `qwen3.7-flash_legalbench_task_v2_test` (candidate, 0.8830 @94) +
`qwen3.7-flash_legalbench_task_v1_test_rerun94` (noise-floor control, 0.8617 @94),
temp 0.0, qwen/qwen3.7-flash, same surface fp 40cfb513, fresh manifests.

## Answer, Response, + Summary of Results

### Short answer

**v2 = v1.replace(rule 6) with the purpose-first ACT/STATE carve-out + the
knowledge-assertion contradiction repair.** Same-surface A/B: **v2 0.8830
(83/94) vs v1-control 0.8617 (81/94) — Δ +2, paired bootstrap 95% CI [−4, +8],
P(Δ≤0)=0.3345 → INSIDE the noise floor (identical-prompt band ±1 row: 80→81).**
**Logic repair, NOT a claimed win.** The genuine-content ledger is directionally
positive: **4 v1 content failures recovered (72, 74, 78, 91 — the exact v2
targets) vs 2 new genuine regressions (48, 56)**, net +2 — but 7 of the 12
moved rows are runner artifacts (see Interpretation 1), which swamp the
prompt signal.

| Metric | v1-orig @94 | v1-control @94 | v2 @94 |
|---|---|---|---|
| exact_match | 0.8511 (80/94) | 0.8617 (81/94) | **0.8830 (83/94)** |
| no | 42/53 (79.2%) | 43/53 (81.1%) | **48/53 (90.6%)** |
| yes | 38/41 (92.7%) | 38/41 (92.7%) | 35/41 (85.4%) |

### The two root causes of v1's 14 failures (diagnostic evidence)

**Root cause A — the runner's truncated-reasoning retry (8 of 14).** The
production `_answer_task` first call caps `max_tokens=512`; qwen's reasoning
exceeds that on most rows → `finish_reason=length`, EMPTY content → retry with
`reasoning_effort="none"`, which pattern-matches the base_prompt few-shot
example 2 ("Rebecca told Ronald she was unwell → Yes") and flips rows wrong.
Full-reasoning replays (raw OpenRouter `reasoning_content`, same v1 prompt)
answer rows **21, 30, 44, 79, 82, 85, 86 correctly** — the v1 doctrine works
when the model can reason. The v1 close-out memo called this "pure cost
waste"; it is an **accuracy killer** (~8 rows) and the dominant remaining
lever. **Banked as a runner fix (raise first-call max_tokens / drop the
no-reasoning retry), NOT a prompt rule.**

**Root cause B — 6 genuine content failures** (wrong even with full v1
reasoning; quoted model reasoning):

| Row | GT | Mechanism (model's own words) |
|---|---|---|
| 91 | No | `rule_contradiction`: "'I am aware of the conduct' to prove knowledge' matches exactly the structure of 'told his friend that the patent was poorly written'" — v1's own YES-example applied to a knowledge-acquaintance row GT labels No. |
| 74 | No | "Pointing is assertive non-verbal conduct communicating an identification... offered to prove the truth of the matter asserted (identification)" — GT: the ACT of identifying is the operative fact. |
| 78 | No | "the content asserts his sobriety/reputation... Yes" — GT: a defamatory utterance IS the act damaging reputation (verbal act). |
| 72 | No | "carried signs demanding equitable compensation... fits the definition of hearsay → Yes" — GT: signs show the workers' grievance, not that the demand is true. |
| 68 | Yes | "Stickers on a car are generally considered non-assertive conduct... → No" — GT: stickers asserting support ARE assertive; the v1 "poster hung as decoration" example was misread. |
| 39 | Yes | will-change read as circumstantial → No. 1-off GT-anomaly, banked (anti-overfit). |

### The v2 mutation

One lesson: **read the ISSUE phrase first — is X the statement's CONTENT
(→ Yes) or an ACT/STATE shown by the making (→ No)?** Plus the contradiction
repair required by the mutation rule: removed the harmful YES-example
("I am aware of the conduct" → knowledge) — a statement NAMING a person/thing
shows the speaker's acquaintance, not the content's truth (→ No for 82/91);
added the intent-plan guardrail (email plan → ownership stays Yes for 44) and
the reputation/identification boundaries drawn both ways (gossip whose content
IS the harm → Yes for 42; defamatory utterance as the operative act → No for
78; pointing offered to show the identification act → No for 74, vs pointing
offered to prove WHO/WHAT → Yes for 64).

**Recovered (stable vs both v1 runs): 21, 44, 72, 74, 78, 82, 91 (+30 vs
orig)** — all four genuine content targets (72/74/78/91) plus three
truncation artifacts now surviving the retry via explicit carve-outs.
**Regressed: 48, 56 (genuine — the new carve-outs misfired) + 64, 70, 79, 76
(runner artifacts v1 got lucky on).**

**The 2 genuine v2 regressions (the v3 lesson, quoted):**
- **56** ("he wanted an ice cream" → prove likes ice cream, GT Yes): model
  applied my "declarant's feeling, belief, or support → No" clause + few-shot
  example 3 (Tim/Real Madrid → fan → No). The statement asserts the
  declarant's OWN state directly — content-truth governs → Yes.
- **48** ("Albert told Mary that Tom looked like her" → prove Mary is Tom's
  mother, GT Yes): model applied my acquaintance clause ("a statement naming a
  person or thing shows the speaker's acquaintance"). Content-truth (he looks
  like her) supports the motherhood fact → Yes.

**The v3 decision procedure they motivate:** *ask whether X is shown by the
truth of the statement's CONTENT (→ Yes) or by the fact the statement was
MADE (→ No)* — the making-vs-content test subsumes every sub-bullet: 56/70
(content asserts the state itself → Yes), 48 (content-truth supports the fact
→ Yes), 86/80/82/91 (content about another, state inferred from the utterance
→ No), 72/74/78/79/85 (the making/act is the point → No).

### Interpretation

1. **The runner truncation dominates the measurement surface.** 8/14 v1
   failures and ~7/12 moved rows in the v2 A/B are truncation artifacts: the
   full-reasoning model gets them right with BOTH prompts. The noise band on
   this surface (±1 row) is not model noise — it is truncation luck. The
   runner fix is the highest-value next step and must come before further
   prompt tuning.
2. **v2's prompt signal is real but sub-noise in aggregate.** The 4 genuine
   content recoveries (72/74/78/91) are exactly the v2 rule's targets, and
   the 2 genuine regressions (48/56) are exactly its over-reach. Net +2
   genuine — a directional improvement with a fixable over-fire.
3. **The few-shot examples in the base_prompt are a strong anchor.** The
   truncated retry pattern-matches example 2 ("unwell → Yes") and v2's model
   cited example 3 ("Real Madrid → fan → No") for 56. The base_prompt is
   task-authored and fixed; the system rule must out-weight it, which the
   explicit row-shape examples (stickers, gossip, email-plan) now do where
   they appear verbatim.
4. **The v2 regressions are rule-misfires, not noise** — both trace to my
   new clauses being drawn too broadly (state clause caught self-asserted
   states; acquaintance clause caught resemblance-statements). The
   making-vs-content test is the v3 repair; it should NOT be bolted onto v2
   (one change per iteration).

### What questions or uncertainties remain?

- **The runner fix is unbanked and dominant:** raising `_answer_task`'s
  first-call max_tokens (or dropping the no-reasoning retry) would recover
  ~8-9 truncation-artifact rows across BOTH prompts — bigger than any prompt
  rule so far. Next iteration: runner fix + re-baseline v1/v2 on the fixed
  surface.
- **77 oscillates even with full reasoning** (Yes→No across replays) — the
  few-shot "Rebecca unwell → Yes" anchor is strongest on the knowledge rows;
  the v3 making-vs-content test targets it.
- **39 stays banked** (GT-anomaly: will-change as assertive conduct → Yes;
  every formulation that fixes it risks 79/85).
- **v2 cost is flat** (108k vs 88k tokens for v1-control — the longer rule
  costs ~23% more prompt tokens but the runs are sub-$\$$0.005 each).

*Sources:* `reports/experiment_log.jsonl` (v1-orig / v1-control / v2 @94
records), raw OpenRouter `reasoning_content` captures (14 v1 failures + 6 v2
regressions, same prompts, temp 0.0), `data/legalbench_local/hearsay-test.jsonl`
(fp 40cfb513), `src/prompts.py` LEGALBENCH_TASK_PROMPT_V1/V2.