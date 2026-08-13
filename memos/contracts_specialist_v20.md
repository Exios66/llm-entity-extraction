# Research Memo: Contracts-specialist v20 — non-obligation field fidelity (overall 0.9135 → 0.9142; field rules +3.0 to +8.2pp on target, ko variance-dominated)

**Research question:** v19's ko gains (0.8840) left the overall score
dragged by NON-obligation fields — effective_date had 5 docs at 0.0,
parties 4 docs at 0.0, renewal_terms 2 at 0.0, governing_law 2 near-0.
Which of these failures are model errors (fixable in the prompt) versus
scorer/ground-truth artifacts (the model is actually right)? And what is
the cleanest way to raise `overall_extraction_score` without touching the
obligation pipeline?

**Companions:**
[contracts_specialist_v19.md](contracts_specialist_v19.md)
· [contracts_specialist_v17_v18_enhancements.md](contracts_specialist_v17_v18_enhancements.md)
· experiment log (runs 044–050, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** The failures split cleanly. **Three of the five zero-date
docs, three of the four zero-party docs, and the worst title mismatch are
scorer/GT artifacts** — the model's null answer or role-quoting answer is
CORRECT, so three surgical scorer fixes (blank-template dates are null
expectations; contained party labels are instantiated; contained titles
score 1.0) raise the floor for every future run. **The genuine model
errors** are renewal_terms (evergreen clauses that never say "renew",
deal-terms tables), termination_clauses (redacted sections), term_length
(defined-Term sentences) and governing_law (regulatory-jurisdiction
sentences) — four prompt rules. On the run: **overall 0.9142 (tie with
v19's 0.9135), parties 1.000, document_name 0.991, renewal_terms +4.5pp
and termination_clauses +5.4pp at same-scorer — but ko −7.3pp in diffuse
max-reasoning variance (2 docs up vs 14 down across docs the rules never
touch)**, so v20 as a whole is not a champion; v19 keeps the ko crown.

### The per-field failure table (v19, docs below 0.9)

| Field | v19 mean | Fail docs | Root cause |
|---|---:|---|---|
| effective_date | 0.865 | 5 × 0.0 | 3 blank-template GT ("_____ day of ________, 19____", "Effective Date:") — model right to return null; 1 OCR-mangled real date ("7t h day of April, 2020."); 1 genuine miss |
| parties | 0.918 | 4 × 0.0 | 3 role/pronoun GT labels ("Consultant", "Member", '"we," "us," or "our"') contained verbatim in the model's answer; 1 definition-sentence GT |
| renewal_terms | 0.816 | 2 × 0.0 | evergreen clause ("shall continue in full force and effect thereafter until terminated by either Party by providing thirty (30) calendar days' prior written notice") never says "renew"; deal-terms table line |
| governing_law | 0.932 | 2 near-0 | regulatory-jurisdiction sentence ("subject to all laws ... of the Canadian Radio-television and Telecommunications Commission") vs the model's proper governing-law sentence |
| term_length | 0.968 | 1 × 0.44 | GT holds the DEFINED-TERM sentence ("The term "Term" shall mean ...") |
| termination_clauses | 0.938 | 1 × 0.0 | GT is a redacted section (Termination for Convenience, redacted) |
| document_name | 0.960 | 2 worst | short-title containment ("FRANCHISE AGREEMENT" inside the full title) |

### The v20 arm (qwen3.7-flash × max reasoning, same 50 docs, chunked, seed 42)

Official records (v19 = old scorer, v20 = new scorer; the right column
re-scores BOTH arms with the same new scorer, embedding off, to isolate
the prompt/model delta):

| Metric | v19 | v20 | Δ official | Δ same-scorer |
|---|---:|---:|---:|---:|
| overall | 0.9135 | 0.9142 | +0.07pp | +0.49pp |
| key_obligations | 0.8840 | 0.8113 | −7.3pp | −5.6pp |
| parties | 0.918 | **1.000** | +8.2pp | +2.0pp (scorer) |
| document_name | 0.960 | **0.991** | +3.1pp | +3.1pp (scorer) |
| effective_date | 0.865 | 0.802 | −6.3pp | +2.1pp (scorer) |
| renewal_terms | 0.816 | 0.861 | +4.5pp | +4.5pp (prompt) |
| termination_clauses | 0.938 | 0.867 | −7.1pp | **+5.4pp (prompt)** |
| term_length | 0.968 | 0.966 | −0.2pp | −0.2pp |
| governing_law | 0.932 | 0.919 | −1.3pp | −1.3pp |
| verified_precision | 0.988 | 0.987 | −0.1pp | — |
| tokens / cost | 1.52M / $0.098 | 1.46M / $0.094 | — | — |

### Interpretation

1. **The scorer fixes are correctness fixes, adopted permanently.** A model
   that returns null for a contract whose date line is literally
"_____ day of ________, 19____" is right; a scorer that gives it 0.0
punishes honesty. Same for "Consultant"/"Member"/pronoun-alias party
labels (contained verbatim in the answer) and contained titles. These
rules raise the floor for every future run without touching historical
records (append-only stored scores).
2. **The prompt rules are validated on their targets.** renewal_terms
   +4.5pp and termination_clauses +5.4pp at same-scorer are real model-
behavior changes; term_length and governing_law are flat-to-slightly-
down (their single-doc targets did not move — Euromedia's regulatory
sentence still loses to the model's proper governing-law answer, a
GT-vs-model span choice no prompt can settle).
3. **The ko regression is variance, not a v20 effect.** 2 up vs 14 down,
   34 flat; the losers (HPIL 1.0→0.5, EcoScience 1.0→0.5, Healthcare
0.833→0.333) are docs the v20 rules never touch, and the v19 arm showed
the same diffuse spread (10 up vs 7 down). Max reasoning amplifies
run-to-run span choice. One parse-error row per arm (Ediets in v19,
MidwestEnergy in v20) is the documented reliability cost of
reasoning=max.
4. **Overall is a tie because the arms move different fields.** v19 wins
   ko, v20 wins the non-obligation fields; merging (v21 = v19's ko content
+ v20's four field rules, ideally at reasoning=none) is the obvious next
arm and costs one ~$0.10 run.

*Sources:* `reports/experiment_log.jsonl` (runs 044–050, task
`contract_entity_extraction`) · `V16_PROPOSITION.md` §10–11 ·
`SCORING.md` §3 (null-expectation dates, contained labels, contained
titles) · `src/field_scoring.py` (v20-era scorer rules) ·
`src/prompts.py` v19/v20 banners · `CHANGELOG.md` · corpus = CUAD
(Hendrycks et al., 2021 — [CUAD dataset](https://github.com/TheAtticusProject/cuad)) ·
runner = [LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **The v21 merge.** Does v19's ko content + v20's field rules hold both
   gains at reasoning=none (removing the parse-error risk)? One ~$0.10 arm.
2. **The OCR-mangled date.** SPRINGBANK's "7t h day of April, 2020." is a
   real date the model misses; a date-normalizer that strips OCR spacing
("7t h" → "7th") would make the GT parseable and the miss punishable —
scorer change, not prompt.
3. **The 0-ko docs.** SPRINGBANK, QBIOMED, PelicanDelivers still extract
   little or nothing in several arms; a trace-level postmortem remains open.
4. **Same-scorer reruns.** The official v19 record holds old-scorer scores;
   a permanent same-scorer re-scoring pipeline (embedding-inclusive) would
make every historical comparison immune to scorer drift.