# Correspondence sorter v3 — demand speech-act (KANBAN-103)

**Research question:** Does overriding the v2 Hub phrase lexicon (rule 46)
with a speech-act test (rule 47: this message itself demands that the
recipient pay / cure / cease / arbitrate) recover true demand /
attorney_demand without treating IT FINAL NOTICE, draft-requests, news
clips, or "we could send a demand letter" as demand — on the same pinned
200-row Enron filename manifest plus `--gt-overrides`?

**Companions:** parent memos
[sorter_docclass_correspondence_v0.md](sorter_docclass_correspondence_v0.md),
[sorter_docclass_correspondence_v1.md](sorter_docclass_correspondence_v1.md),
[sorter_docclass_correspondence_v2.md](sorter_docclass_correspondence_v2.md);
overrides `data/gt/enron_correspondence_label_overrides.jsonl`; reserved
run `qwen3.7-flash_sorter_docclass_correspondence_v3_enron200_s42`.

## Answer, Response, + Summary of Results

**Short answer:** A/B not yet run.

Parent frontier (already measured, frozen v2):

| version | subclass | demand | attorney_demand | surface | note |
|---|---|---|---|---|---|
| v0 | 0.400 | 0/25 | 0/3 | enron200 s42 | baseline |
| v1 | 0.465 | 0/25 | 0/3 | same | claimed win, CI +1.5–+12.0pp |
| v2 | 0.485 | 3/25 | 1/3 | same | pool-accept, CI includes 0 |
| v2 attyall | 0.5124 | — | 1/4 | n=201 | different surface |

Reserved child: `sorter_docclass_correspondence_v3` on
`data/manifests/enron_corr200_s42_filenames.jsonl` +
`--gt-overrides data/gt/enron_correspondence_label_overrides.jsonl`,
model `qwen/qwen3.7-flash`. Do not invent scores.

### Interpretation

1. **Parent lesson 46 is the broken Hub convention.** The official
   labeler fires on any demand-marker phrase in the writer's own text.
   Most Hub-demand rows are not speech-act demands.
2. **v3 is one GEPA mutation:** rule 47 overrides rule 46. demand = this
   message performs the demand; attorney_demand = that act AND a
   lawyer/law-firm is the author/sender. `max_tokens` stays 2048.
3. **Acceptance is unmeasured** until the reserved same-surface A/B
   lands. This memo is a proposal stub.

*Sources:* v0/v1/v2/attyall parent memos; Hub override file; audited
demand bodies motivating rule 47.

## What questions or uncertainties remain?

- Same-surface paired CI vs v2 (and vs v1) once the reserved run lands.
- Whether speech-act tightness regresses the 3/25 phrase-lexicon hits v2
  recovered, or only drops the false positives the overrides already
  demote.
- Parse-burn `other` (21 rows at max_tokens 2048) is out of scope for
  this iteration.
