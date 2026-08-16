# Docclass sorter completed + QWEN 3.7-flash benchmark on the merged docclass task

**Research question:** With all three docclass corpora (CUAD contracts, MAUD
merger agreements, S-1 corporate records) merged into one dataset, what is the
completed docclass sorter prompt — and what does the QWEN 3.7-flash benchmark
on the merged + added-complexity task look like?

**Companions:** `memos/sorter_v13.md` (the shared sorter frontier), KANBAN-033
board card, `CHANGELOG.md [Unreleased]`, runs `qwen3.7-flash_sorter_docclass_v3_docclass_ab30`,
`qwen3.7-flash_sorter_docclass_v3_docclass_full676`,
`qwen3.7-flash_sorter_docclass_vision_v0_docclass_vpilot`.

## Answer, Response, + Summary of Results

**Short answer:** The completed docclass sorter prompt is **`sorter_docclass_v3`** —
the Phase 3.5 merge of the two validated single-change lessons (rule 34
embedded-records scope guard + rule 35 RRA-exhibit convention) on the v0 base.
Same-surface A/B confirms it ties the v2 winner (exact 0.8000, doc_type 1.0000,
fp `d3d7b335…`) with zero regressions while carrying rule 34's logic repair.
The **QWEN 3.7-flash benchmark on the merged 676-doc task is doc_type 0.9926 /
subclass 0.5808 / exact 0.8905 (0 errors, ≈$0.47)** — with the caveat that
81% of subclass misses are ground-truth gaps, not model error. The vision arm
(the added complexity) is established: `sorter_docclass_vision_v0` +
`--input-mode vision-primary` pilot: 5/5 vision rows + 3/3 text-fallback rows
all correct.

## Results

### 1. The merged docclass corpus (ONE dataset)

| Source | Rows | doc_type | subclass GT |
|---|---|---|---|
| `mailroom-cuad-contracts-full` (Braintrust) | 509 | contract | — (subtype surface) |
| `data/maud/contracts.jsonl` | 152 | merger_agreement | all_cash 57 / other 57 / all_stock 24 / mixed_cash_stock 13 / mixed_cash_stock_election 1 |
| `data/s1_corporate_records/corporate-records.jsonl` | 15 | corporate_record | articles_of_incorporation 8 / rights_instrument 6 / bylaws 1 |
| **Merged** (`data/datasets/docclass_merged.jsonl`) | **676** | — | — |

Built deterministically by `scripts/datasets/build_docclass_merged.py`
(corpus order, then filename; reproducible fingerprint `5602b71f…`); mirrored
to Langfuse as ONE dataset `mailroom-docclass` (676 items) + all docclass
prompts (v0..v3 + vision) synced to llm-dojo.

**Same-surface note:** the @30 A/B surface (fp `d3d7b335…`) samples from the
pre-merge `docclass_mixed_dump.jsonl`; the merged file's richer metadata and
sorted order make it a new canonical surface (its own fp). Comparisons stay
within their own surface.

### 2. Prompt iteration: v1/v2 A/B and the v3 merge

Surface: stratified-30 seed 42, fp `d3d7b335…`, qwen3.7-flash, temp 0.1,
reasoning medium. Same prompts, same rows — v0 control = the anchor.

| Version | doc_type | subclass | exact | failures | note |
|---|---|---|---|---|---|
| v0 (control) | 0.8333 | 0.5000 | 0.6667 | 10 | 5 EX-4.x doc_type misses + 5 subclass |
| v1 (rule 34) | 0.8333 | 0.5000 | 0.6667 | 10 | rule-34 target not in sample (logic repair) |
| v2 (rule 35) | **1.0000** | 0.7000 | **0.8000** | 6 | 5/5 EX-4.x recovered, rule-35 reasoning pinned |
| **v3 (34+35)** | **1.0000** | 0.7000 | **0.8000** | 6 | **failure set byte-identical to v2** |

The 6 remaining failures are ground-truth artifacts on both surfaces: 3 MAUD
consideration GT gaps (contract_59/50/114 — model reads an explicit cash
price where MAUD has no answer; GT "other") and 3 S-1 streamer-detection
artifacts (specimen certificate, RRA, bylaws mislabeled
articles_of_incorporation). No prompt rule fixes mislabeled GT — flagged for
the data side.

### 3. QWEN 3.7-flash benchmark on the merged task (full 676)

Run `qwen3.7-flash_sorter_docclass_v3_docclass_full676` (fp `5602b71f…`,
temp 0.1, reasoning medium, 0 errors, 12.9M tokens, ≈$0.47):

- **doc_type 0.9926** — per-class: contract 0.994 / corporate_record 1.0 /
  merger_agreement 0.987 (5 misses: 2 contract→corporate_record, 1
  contract→correspondence, 2 merger_agreement→contract).
- **subclass 0.5808** — 69 misses, decomposed:
  - **56/69 (81%) = MAUD GT-gap cluster**: GT "other" (streamer fallback — no
    Type-of-Consideration answer) where the model reads an explicit
    consideration (27 all_cash / 16 all_stock / 11 mixed_cash_stock / 2
    mixed_cash_stock_election). Defensible/correct reads against missing GT.
  - 4 = S-1 GT artifacts (articles_of_incorporation labels on specimen
    certificates / RRAs / bylaws).
  - ~9 = genuine consideration near-misses (all_cash↔all_stock↔mixed).
- **exact 0.8905.**

**Interpretation:** the subclass dimension is the task's resolution-limited
metric right now — its headline is dragged by GT gaps, not prompt errors. The
doc_type headline (0.9926) is the clean model-quality read on the merged
task. Fixing the subclass metric = data-side work (MAUD consideration
backfill + S-1 label repair), not prompt iteration.

### 4. Vision-primary arm (added complexity)

`sorter_docclass_vision_v0` (vision twin of v3: 7 classes, rules 31–35,
`<subclass>` tag, UNREADABLE sentinel, `## Output format` split) + runner
`--input-mode vision|vision-primary` (`--pdf-dir` filename-stem matching,
`--vision-pages all|first`, per-row input_mode + fallback_reason + vision
usage accounting). Agent vision path extended to the docclass schema with
strict 6-class backward compatibility (byte-identical legacy contract).

Pilot `qwen3.7-flash_sorter_docclass_vision_v0_docclass_vpilot` (8 rows, 5
CUAD PDFs page-1 vision + 3 no-PDF rows, ≈$0.005): **5/5 vision rows
classified from images (contract, conf 0.95×4 + 0.5×1), 3/3 text-fallback
rows correct (no_pages) — doc_type 1.0, exact 0.875.** The vision-primary
path is validated end-to-end; a full-pages vision benchmark (all pages,
larger sample) is the natural follow-on at higher cost.

### 5. Concurrency scaling (speed/efficiency)

`src/evaluation.py::resolve_concurrency` — auto worker count scales with the
sample (8 + n/25, cap 32) until diminishing returns/rate limits; explicit
`--max-concurrency N` wins. `call_with_rate_limit_retry` — exponential
backoff + jitter on transient 429s (wired into the four langfuse runners;
effective workers + retries recorded per run). Full-676 benchmark ran at the
default 8 before this landed; the surface now scales to 32 for future
runs.

*Sources:* `reports/experiment_log.jsonl` runs above; `data/datasets/docclass_merged.jsonl`;
`src/prompts.py` SORTER_DOCCLASS_PROMPT_V0/V1/V2/V3 + SORTER_DOCCLASS_VISION_PROMPT_V0;
`scripts/datasets/build_docclass_merged.py`; `scripts/eval/sync_langfuse_datasets.py --docclass`;
`scripts/eval/run_langfuse_docclass_eval.py --input-mode`; `src/evaluation.py`.

## What questions or uncertainties remain?

- **Subclass metric ceiling:** until the MAUD consideration GT is backfilled
  (57 "other" rows) and the S-1 streamer labels are repaired, subclass
  accuracy stays a GT-bound metric (~0.81 of its misses are label gaps). The
  data-side card is the unlock.
- **Vision full benchmark:** the pilot used page-1 only (`--vision-pages
  first`); a full-pages `--vision-pages all` benchmark on a larger sample
  (with merger_agreement + corporate_record PDFs once MAUD/S-1 PDFs are
  retained) is the next benchmark arm.
- **Noise floor on the merged surface:** the full-676 run is the first
  measurement; an identical-prompt rerun would bound the surface's noise band
  for future A/Bs.
