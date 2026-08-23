# Docclass iteration round 2 — v4/v5/v6, scoring depth, and the v6 text champion

**Research question:** With the full-676 failure set and the merged corpus in
hand, what does the next docclass prompt iteration yield — and how deep are
the scoring/logging metrics for the new classes and subclasses?

**Companions:** `memos/docclass_v3_merged_benchmark.md` (round 1), KANBAN-033
board card, runs `qwen3.7-flash_sorter_docclass_{v3,v4,v5,v6}_docclass_*`,
`src/tracing.py` (Langfuse-primary directive).

## Answer, Response, + Summary of Results

**Short answer:** The full-676 failure set decomposes into three mechanisms;
one round of candidates (v4 rule 36, v5 rule 37, v6 rule 36-sharpened) shows
that **only the sharpened M&A-package rule survives the noise-floor test**:
the v3 identical-prompt rerun reproduced the headline exactly (0.8905 =
0.8905), and **v6 = 0.8935 with 0 regressions, 2 rule-pinned recoveries, and
subclass +1.19pp → the new docclass text champion (strictly dominates v3)**.
The scoring layer was also brought to subtype-surface depth: bootstrap CIs on
every headline, per-subclass accuracy tables with support, equivalence-aware
subclass scoring, and a renderer that finally shows the subclass dimension.

## Results

### 1. Full-676 failure decomposition (the reflection)

| Cluster | Rows | Mechanism | Fixable? |
|---|---|---|---|
| C1 M&A-package machinery | contract_2 (APM+CVRs), contract_33 (TRANSACTION AGREEMENT) | rule-31 title enumeration gap + rule-35 over-fire on registration-rights machinery | yes — rule 36 |
| C2 agreement-package composition | FEDERATED (POA leading a services-agreement exhibit) | rule 32/33 over-fire on record text inside an agreement package | yes — rule 37 |
| C3 GT/text artifacts | UNITEDNATIONAL (press-release-only text), OLDAPI (certificate-only text) | the extracted text IS the annex, not the parent agreement; model reads are defensible | no — data side (KANBAN-038) |

### 2. The candidates and the A/B ladder

- **v4** = v3 + rule 36 (M&A package machinery governs ancillary instruments;
  rule-35 own-title scope guard). Recovered contract_2 deterministically in
  diag30 (2/2 runs, rule-36 reasoning pinned) but NOT contract_33 — the
  model's own reasoning showed it second-guessing rule 31's title list.
- **v5** = v3 + rule 37 (agreement packages: record/certificate text inside a
  package doesn't change the class). No replicated signal on the diagnostic
  surface (recovered OLDAPI once, not twice) — dropped.
- **v6** = v3 + rule 36 SHARPENED (rule-31 title list declared illustrative;
  multi-agreement files governed by the primary agreement) — the v4 lesson
  sharpened by contract_33's hesitation evidence.

**Diagnostic surface A/B** (30 rows incl. all target rows + controls, fp
`946ac1c4`, bootstrap CIs): v3 exact 0.5667 [0.40, 0.73] / v4 0.6000 [0.43,
0.77] / v5 0.5667 [0.40, 0.73] — **all deltas inside the CIs**; the targeted
rows are high-variance (contract_2 flips between v3 runs; OLDAPI flips) → no
candidate measurable on this surface alone.

**Full-676 A/B with noise control** (fp `5602b71f`, qwen3.7-flash, temp 0.1):

| Metric | v3 control | v3 rerun (noise) | v6 |
|---|---|---|---|
| exact | 0.8905 | **0.8905** (= control) | **0.8935** |
| doc_type | 0.9926 | 0.9926 | **0.9941** (5→4 misses) |
| subclass | 0.5808 | 0.5749 | **0.5868** (all_cash 0.877→0.912) |
| exact CI | — | [0.8669, 0.9142] | [0.8698, 0.9157] |
| failures | 74 | 74 | **72** |

- The identical-prompt rerun reproduced the headline **exactly** — the merged
  surface's aggregate noise floor ≈ 0.000, so the +0.0030 (2 rows) is a
  deterministic-looking gain, not drift.
- **Recovered (2, zero regressions):** contract_62 — the embedded-bylaws
  rule-34 target that still failed at scale under v3 (rule 36's package
  language fired) — and contract_71 (all_cash read via the
  consideration-machinery clause).
- **Residual:** contract_33 persists — the model hallucinates an RRA title on
  the truncated 1 MB document (tail's RRA signature blocks anchor the read);
  truncation/model-bound, documented not prompt-fixed.

**Verdict: v6 strictly dominates v3** (same cost, 0 regressions, +2 rows,
subclass +1.19pp) → promoted as the docclass text champion.

### 3. Scoring depth — the new classes/subclasses measured like the subtypes

- **Bootstrap 95% CIs** on doc_type/subclass/exact headlines (per-row binary
  scores, `src/bootstrap.py`).
- **Per-subclass accuracy + support** (e.g. full-676: all_cash 0.877/57,
  all_stock 0.917/24, mixed 0.923/13, articles_of_incorporation 0.5/8 —
  the GT-bound rows visible per subclass now).
- **`subclass_accuracy_equiv`** (+ per-row `subclass_ok_equiv` +
  `equiv_recovered` list): `DOC_SUBCLASS_EQUIVALENCES` — mixed_cash_stock ↔
  mixed_cash_stock_election, dimension-scoped (a consideration key never
  equates to a record key). Doc-type-gated like the subtype surface's equiv.
- **Input-mode split counts** per run (text / vision / text_fallback) and the
  renderer's docclass branch (per-document tables now show doc_subclass,
  expected subclass, equiv flag, input mode; per-subclass section).

### 4. Tracing: Langfuse primary, local Phoenix fallback

`src/tracing.py::resolve_tracer()` — the human directive's flip, wired into
all four langfuse runners; verified live (full-676 runs report
`tracing_backend=langfuse`, llm-dojo). Also fixed a latent fixture gap (the
langfuse subtype smoke previously selected Phoenix when PHOENIX_TRACING was
unset — the new default exercises the Langfuse stub as intended).

*Sources:* `reports/experiment_log.jsonl` runs above; `src/prompts.py`
SORTER_DOCCLASS_PROMPT_V4/V5/V6; `agents/sorter_agent.py`
DOC_SUBCLASS_EQUIVALENCES; `src/tracing.py`; `scripts/eval/run_langfuse_docclass_eval.py`.

## What questions or uncertainties remain?

- **contract_33**: the hallucinated-RRA read on the truncated doc is the
  clearest model-bound residual; a larger input budget or a
  first-title-wins reinforcement is the potential unblock (next iteration).
- **Noise floor**: one identical-prompt rerun reproduced 0.8905 exactly; a
  second rerun would bound the band properly.
- **Subclass metric**: still GT-bound (56/69 misses are MAUD "other"-fallback
  rows) — the KANBAN-038 data-side backfill is the real unlock.
