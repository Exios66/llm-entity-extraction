# Research Memo: Contracts-specialist v17→v18 — the family-fidelity catalog (key_obligations 0.7755 → 0.8535, +7.8pp)

**Research question:** After the v15 chunking enhancement reached 0.913
overall, `key_obligations` still sat at **0.7755** on the same 50-doc
surface. The residual error had been decomposed into unmatched predicted
items (331) and uncovered GT spans (162). Two candidate levers remained:
output **grain** (how the item boundaries are phrased — v16/v17) and
family **scope** (what operative shapes the prompt's family enumeration
covers — v18). Which one actually closes the gap, and is v18 adoptable
under the A/B decision rule?

**Companions:** [entity_extraction_improvements.md](entity_extraction_improvements.md)
· [subtype_classification_improvements.md](subtype_classification_improvements.md)
· experiment log (task `contract_entity_extraction`, runs 044–046) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Short answer:** The segmentation lever is **exhausted at the prompt
layer** — three different grain instructions (v15 sentences, v16 fragments,
v17 length-anchored) all converge on the same ~0.62–0.65 matched-span
ceiling, and a post-hoc audit refutes the containment hypothesis outright
(0 of 160 unmatched GT spans are token-contained in any predicted item).
The real residual was **family-scope mismatch**: the prompt's terse
26-family name list did not enumerate the operative clause shapes the CUAD
annotators label (pricing formulas, shelf-life/quality spans, IP
prosecution elections), so the model faithfully excluded them under the
"general payment obligations are NOT expected items" rule. **v18 replaces
the name list with a CUAD-mirror catalog** — one entry per obligation
category with its clause shapes, and an exclusion rule narrowed to true
general duties with a WHERE-IT-SITS guard — and delivers **key_obligations
0.7755 → 0.8535 (+7.8pp)** with overall at **0.9230** (series best, 95% CI
0.891–0.949). Decision rule met (ko ≥ +3pp, no field regressed > 2pp):
**v18 is the new champion.**

| Metric | v15 | v18 | Δ |
|---|---|---|---|
| key_obligations | 0.7755 | **0.8535** | **+7.8pp** |
| overall | 0.9129 | **0.9230** | +1.0pp |
| alignment precision | 0.650 | 0.619 | −3pp |
| verified_precision | 0.994 | 0.991 | −0.3pp |

> **Verdict:** grain is exhausted; scope was the lever — the CUAD-mirror catalog is the champion change.


### The four-arm A/B (same 50 docs, chunked, seed 42, Langfuse llm-dojo)

Every arm runs the identical surface — the deltas are directly comparable.

| Metric | v15 | v16 (fragments) | v17 (length-anchored) | v18 (catalog) |
|---|---:|---:|---:|---:|
| key_obligations | 0.7755 | 0.7816 | 0.7726 | **0.8535** |
| overall | 0.9129 | 0.8859 | 0.9074 | **0.9230** |
| 95% CI (overall) | 0.881–0.942 | 0.840–0.926 | 0.874–0.937 | **0.891–0.949** |
| parties | 0.940 | 0.900 | 0.920 | 0.940 |
| effective_date | 0.896 | 0.854 | 0.883 | 0.883 |
| term_length | 0.979 | 0.953 | 0.953 | 0.979 |
| governing_law | 0.934 | 0.934 | 0.954 | 0.934 |
| items (median words) | 1021 (48) | 1292 (26) | 1083 (27) | 1118 (25) |
| matched GT spans | 664 | 707 | 627 | 692 |
| alignment precision | 0.650 | 0.547 | 0.579 | 0.619 |
| verified_precision | 0.994 | 0.970 | 0.994 | 0.991 |

### What each iteration actually changed

1. **v16 — the fragment contract (NOT adopted).** Items were re-specified
   as atomic 4–20-word verbatim fragments with preamble/riders stripped
("During the Term of this Agreement,", "Except as otherwise set forth
herein," are not part of the fragment). It halved median item length
(48 → 26 words) and recovered +43 GT spans — but over-fragmented to
**1292 items vs 826 GT spans (+56%)** and alignment precision *fell*
(0.650 → 0.547). ko +0.6pp, overall **−2.7pp**, parties −4.0pp,
effective_date −4.2pp. Rejected under the decision rule.
2. **v17 — the length anchor (NOT adopted).** The grain instruction was
   re-anchored to the GT span length itself (10–25 words, target ~15–20;
strip preamble but keep operative qualifiers, never split below span
grain). Items 1083 (median 27 words) — but matched spans **fell to 627,
below v15's 664**, alignment precision 0.579, ko 0.7726 (−0.3pp vs
v15). Rejected.
3. **The decisive finding — three grains, one ceiling.** Sentences (48w),
   fragments (26w), length-anchored (27w): the model's boundary choices do
not converge on the annotator's regardless of how grain is phrased. The
segmentation lever is exhausted at the prompt layer.
4. **The post-hoc audit — containment REFUTED, scope implicated.**
   **0 of 160** unmatched v15 GT spans are token-contained (≥0.7) in any
predicted item — these are genuine content omissions, not embedded
fragments. Family breakdown of the 160: license grant 40, minimum
commitment 12, IP ownership 10, anti-assignment 9, audit rights 6,
revenue sharing 6, cap liability 5, post-termination 5, exclusivity 5,
insurance 4, other 51. The mechanism is scope-fidelity: pricing-formula
spans ("The price that Sekisui shall pay for the Reagent Kits Products
shall be based upon a formula…"), shelf-life/quality spans, and
IP-prosecution-election spans ("In the event that Qualigen elects not to
prosecute or maintain…") are labeled in CUAD but the terse family names
("price restrictions", "IP ownership") do not enumerate those shapes —
the model excludes them *as instructed*.
5. **v18 — the family-fidelity catalog (ADOPTED).** The 26-family comma
   list is replaced by a catalog mirroring `CUAD_CATEGORIES` 1:1: each of
the 26 obligation families gets its operative clause shapes derived
from the 160-span decomposition (cap-on-liability consequential-damages
waivers, license grants phrased "right and license … for the territory
of", minimum guarantees/royalties, audit deficiency remedies, insurance
coverage lists, IP-prosecution elections, family-term definitions). The
exclusion rule narrows to true general duties, with a WHERE-IT-SITS
guard so family clauses inside indemnity/damages sections still count.
v17's length-anchored grain is kept unchanged.

### Family-level recovery (token-level, the 160 v15-missed spans vs v18)

30 of 160 originally-missed spans now match at ≥0.6 token overlap
(embedding-rescue matching recovers further — that is why scored ko rose
7.8pp):

| Family | spans recovered | Family | spans recovered |
|---|---:|---|---:|
| cap liability | +8 | price restriction | +1 |
| IP ownership | +4 | volume restriction | +1 |
| license grant | +4 | insurance | +1 |
| post-termination | +2 | no-solicit | +1 |
| minimum commitment | +2 | audit rights | +1 |
| revenue sharing | +1 | anti-assignment | +1 |

Worked confirmation — **Penntex** (Transportation Agreement, 0 liability
items in v15 despite a labeled cap-on-liability span) now emits the
"NO PARTY SHALL BE LIABLE FOR CONSEQUENTIAL, INCIDENTAL, PUNITIVE,
EXEMPLARY OR INDIRECT DAMAGES" clause verbatim. Still missing at token
level: 131 spans, largest family **license grant (36)** — the shapes still
do not enumerate every grant phrasing.

### Interpretation

1. **Scope beats grain, empirically.** All three grain arms sit under
   alignment precision 0.65; the only arm that moved ko materially changed
*what counts as an obligation*, not *how items are cut*. The +7.8pp is
recovered content, not recovered matching.
2. **The containment-credit scorer idea is closed.** 0/160 spans embedded
   ⇒ no scoring change could have helped — the SCORING.md discussion is
empirically settled until the content itself is found.
3. **Doc-level motion is broad, not surgical.** At raw token level 17 docs
   improved and 19 worsened between v17 and v18; the +7.8pp scored gain is
the net of the embedding rescue on recovered content (Ritter +0.43,
Phasebio +0.34, EmbarkCom +0.32 on the matched-ratio axis). Three docs
remain at ko 0.0 in both arms (SPRINGBANKPHARMACEUTICALS EX-9, QBIOMED
EX-99.1 joint filing, PelicanDelivers EX-10.3).
4. **Fidelity is preserved.** verified_precision 0.991 (v18) vs 0.994
   (v15) — the catalog added recall without hallucination; schema_valid
1.0, category_presence 0.911 (best on the surface).
5. **Cost is the honest trade.** The catalog adds enumeration, not input —
   tokens/doc 17.8k (v17) → 19.9k (v18), +11%, still 0 truncated docs.

*Sources:* `reports/experiment_log.jsonl` (runs 044–046, task
`contract_entity_extraction`) · `src/prompts.py` v16/v17/v18 banners ·
`V16_PROPOSITION.md` §8–9 (decomposition, decision rule, recovery audit) ·
`CHANGELOG.md` (v18 adoption) · corpus = CUAD (Hendrycks et al., 2021 —
[CUAD dataset](https://github.com/TheAtticusProject/cuad)) · runner =
[LangGraph](https://langchain-ai.github.io/langgraph/) on
[OpenRouter](https://openrouter.ai/)

---

## What questions or uncertainties remain?

1. **The residual license-grant gap.** 36 of the 131 still-missing spans
   are license grants — the next iteration (v19) should supply worked
positive/negative span examples per family instead of prose shapes,
measured against this same surface.
2. **The 0-ko docs.** SPRINGBANKPHARMACEUTICALS, QBIOMED, PelicanDelivers
   extract nothing in either arm — a failure mode no family rule touches;
worth a direct trace-level postmortem.
3. **Model capability, now gated OPEN.** With scope-fidelity fixed at the
   prompt layer, a v18 × {deepseek-v4-flash, deepseek-v4-pro} sweep on the
same 50 docs quantifies how much of the residual 131-span gap is
model-bound — the input for the llm-mailroom vendor decision.
4. **Doc-level scatter.** Why does raw token-level matching worsen on 19
   docs while scored ko improves? The embedding-rescue interaction with
the new shapes is not yet decomposed.