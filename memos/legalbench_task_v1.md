# legalbench_task_v1 — hearsay doctrine in the system prompt

**Research question:** The LegalBench `hearsay` task classifier (`legalbench_task_v0`
via `--prompt-mode task`) scores 0.7766–0.7872 on the 94-row test surface. What
single prompt rule — stated as doctrine the model can follow — fixes the largest
failure cluster without regressing the 71 correct rows?

**Companions:** KANBAN-026 (hearsay iteration series), `memos/sorter_v12.md`,
`memos/contracts_specialist_v31.md`. Runs: `qwen3.7-flash_legalbench_task_v0_test`
(+`_classification_langfuse_test`), 4 fresh @94 runs, temp 0.0, qwen/qwen3.7-flash.

## Answer, Response, + Summary of Results

### Short answer

v0's system prompt is output-format-only — it tells the model *how* to answer but
*not what hearsay is*. The task's one-line definition lives only in the user-side
base_prompt, and the model's own priors decide the hard cases. 18 rows fail
deterministically (wrong in all 4 runs). The failures split into two mirror-image
clusters plus one carve-out miss:

| Cluster | Rows (stable) | GT | Model | Mechanism (one sentence) |
|---|---|---|---|---|
| A. purpose-test misses | 47,76,77,78,79,80,82,85,86 (9) + flips 83,91 | No | Yes | Statement offered to prove effect-on-listener / declarant state-of-mind (not the truth of the asserted matter); model calls it hearsay anyway. |
| B. statement-scope escapes | 39,50,58,61,68,69,71,94 (8) + flip 52 | Yes | No | Party's own statement (58 "I am the boss here"), assertive non-verbal conduct (68 stickers, 69 head-shake), written statements (61/71 emails), verbal-act (94 agency, 50 planning) all wrongly treated as not-hearsay. |
| C. in-court carve-out | 23 (1) + flip 26 | No | Yes | Statement made in court / relayed testimony; model misses the in-court-not-hearsay carve-out. |

The 5 oscillating rows (26,6,52,83,91) define the surface's noise floor: band ≈
±1 row (73↔74, i.e. exact 0.7766↔0.7872). A candidate delta is meaningful only
outside that band.

**Mutation `legalbench_task_v1`** = `LEGALBENCH_TASK_PROMPT_V0.replace(...)` adding
ONE hearsay-doctrine rule to the system prompt:

> The classic hearsay definition governs when the question asks about hearsay: an
> out-of-court statement (words, writings, or assertive non-verbal conduct such as
> a nod, head-shake, or pointing) offered to prove the truth of the matter it
> asserts IS hearsay — including a party's own statement (party admissions are
> exceptions to admissibility, not to the hearsay definition).
> A statement offered for a purpose OTHER than the truth of what it asserts is NOT
> hearsay: e.g. to show the effect on the listener (that they were told, knew, had
> notice, or were provoked), or to show the declarant's state of mind. Statements
> made in court (under oath, subject to cross-examination) are not hearsay.

Data-motivated target: clusters A+B+C = 18 stable + up to 4 flips, vs a
regression scan of all 71 correct rows showing no predicted flip (all correct No
rows are either non-assertive conduct, in-court, or effect-on-listener purposes;
all correct Yes rows are statements offered for truth).

**Verification plan (Phase 4):** surgical prompt tests → `--dry-run` →
sample-5 pilot (same seed 42) → same-surface A/B @94 (fresh manifest) →
paired bootstrap CI vs the champion band.

### Interpretation

1. **The dominant root cause is absent doctrine, not model weakness.** The model
   gets 76/94 right with zero legal instruction in the system prompt — it knows
   basic hearsay. The failures are concentrated where the definitional test needs
   explicit statement: purpose (A), statement scope (B), in-court (C).
2. **Cluster A is the largest and the cleanest to fix.** The "effect on the
   listener / state of mind" purpose is textbook non-hearsay. Every A-row quotes
   an out-of-court statement whose truth is NOT the point — the point is that the
   listener was told (47 Jane knew, 76 Vincent provoked, 82 Patty knew, 85 Mary at
   the mall) or the declarant's feeling (80 Dylan's ill feeling, 86 Anne's
   support) or circumstantial fact of utterance (79 Gerald alive, 83 Arthur knew
   English).
3. **Cluster B is the mirror failure.** The model finds escape hatches — party
   admission, non-verbal conduct, "verbal act" — and calls statements non-hearsay.
   Each B-row's statement IS offered for the truth of what it asserts (58 boss,
   68 support, 69 knife-purchase denial, 94 agency).
4. **The in-court cluster (C) is small but shares the fix.** A doctrine rule that
   names the in-court carve-out handles 23/26 without a separate mutation.
5. **Doctrine belongs in the system prompt, not the base_prompt.** The base_prompt
   is task-authored (LegalBench) and fixed; the system prompt is the versioned,
   iterable artifact. That is exactly the knob the GEPA loop turns.

### What questions or uncertainties remain?

- Does the model over-apply the new doctrine and flip any correct effect-on-
  listener rows to Yes? The 71-row regression scan says no on paper; the A/B
  resolves it.
- The verbal-act boundary (94 agency, 50 planning) is genuinely arguable in
  evidence law — the GT labels them hearsay, so the rule states the GT position.
  If the A/B shows 94/50 still wrong, the rule wording needs sharpening there,
  not the GT.
- Runner-level: the first `_answer_task` call burns ~512 reasoning tokens and is
  truncated (finish_reason=length, empty content) before a clean 1-token retry —
  pure cost waste, prompt-independent. Tracked as a follow-on card, not this
  mutation.

*Sources:* `reports/experiment_log.jsonl` (4 v0 @94 records),
`data/legalbench_local/hearsay-test.jsonl` (94 rows + base_prompt),
Langfuse llm-dojo `legalbench_task_classification` traces (per-row outputs,
usage), `src/prompts.py` LEGALBENCH_TASK_PROMPT_V0,
`scripts/eval/run_classification_eval.py::_answer_task`.
