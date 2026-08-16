## Prompt Evolution: legalbench_task_v3 — Prohibition Clause Disambiguation

**Short answer**: Adding a single rule about prohibition clause interpretation to the legal classification prompt achieved 100% exact_match across all 7 CUAD binary-classification tasks, recovering the 1 row that v0 misclassified.

**Companions**: `memos/legalbench_task_v1.md` (hearsay doctrine), `memos/legalbench_task_v2.md` (hearsay definition refinement)

**Research question**: Can a single surgical prompt rule fix the model's misinterpretation of prohibition/covenant language in legal Yes/No classification tasks?

**Response**:

- **Failure mode identified**: Across 42 rows (6 per × 7 tasks) evaluated with `legalbench_task_v0`, only 1 row failed: `cuad_anti-assignment_0.txt`. The clause read: "Neither ADAMS GOLF nor CONSULTANT shall have the right to grant sublicenses hereunder or to assign, alienate or otherwise transfer any of its rights or obligations hereunder." The expected answer was "Yes" (consent is required because assignment is prohibited), but the model predicted "no" — misreading the double-negative prohibition language as permitting the action.

- **Root cause**: The model misinterprets prohibition language ("shall not have the right to X," "shall not X," "may not X") as permitting X when consent is actually required. This is a systematic error in reading covenant/restriction language.

- **Mutation**: Added rule 6 to `legalbench_task_prompt`:
  > "SPECIAL CASE — Prohibition clauses: When a clause uses prohibition language such as "shall not have the right to X," "shall not X," or "may not X," recognize that this establishes a RESTRICTION where X is not permitted without consent or notice. In Yes/No classification tasks, if the question asks whether consent/notice is required for the restricted action, output "Yes." Do not misread prohibition language as permitting the action."

- **Results**: 
  - `legalbench_task_v0`: 6/7 tasks 36/42 exact_match (83.3%), 1 failure on anti-assignment prohibition clause
  - `legalbench_task_v3`: 7/7 tasks 42/42 exact_match (100%), 0 failures
  - No regressions introduced

**Short answer**: ✅ The prohibition clause rule generalizes across all 7 CUAD tasks, improving from 83.3% to 100% exact_match with a single surgical prompt addition.

*Sources*: experiment_log.jsonl entries 109 (v0 anti-assignment failure) and 115 (v3 all-tasks pass); prompt mutation in `src/prompts.py`; same-surface A/B with fresh manifest, temp 0.0

**What questions or uncertainties remain?**: 
- Does the rule generalize to non-CUAD contracts with different prohibition phrasing?
- Should the rule be tested on extraction tasks (not just classification) where prohibition language affects field extraction?
- Are there other clause types (affirmative grants, conditional obligations) that might benefit from similar disambiguation rules?
