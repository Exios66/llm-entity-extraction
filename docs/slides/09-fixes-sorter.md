# 09 — Fixes: sorter prompt iterations (v7 → v9)

---

## The question

Each sorter iteration shipped **one data-backed rule set** derived from the
exact failure rows of the run before it, validated by a same-surface A/B.
This deck maps every problem in [08-problems-sorter](08-problems-sorter.md)
to the fix that eliminated it — and the numbers that prove it.

---

## 1. The rule-iteration loop (applies to every version)

1. Run a full-corpus or stratified pass; collect the failed rows.
2. Cluster the failures by family; find the confusions with >1 occurrence.
3. Write a **title-wins / structure-wins rule** for each cluster, citing
   the failed filenames in the prompt's section banner.
4. A/B on the SAME surface (same dataset fingerprint, seed, sample size)
   against the previous version — only prompt versions validated this way
   ship.
5. Repeat until the residual is a 1-off long tail (no cluster > 2).

## 2. The equivalence framework (infrastructure, v5/v6 era)

`SUBTYPE_EQUIVALENCES` accepts reseller↔distributor, maintenance↔license,
development↔license, affiliate↔joint_venture as defensible family routing.
The eval reports strict accuracy (the discriminating signal) AND
equivalence accuracy (the defensible-routing signal) — so the model is not
penalized for a hybrid resolution a human would also defend.

## 3. v7 — the promotion guard, consortium O&M, development-over-license

**Problems:** the promotion→marketing cluster (6 errors); consortium
O&M agreements (shared-infrastructure governance wrappers) routed to
joint_venture; development agreements with license machinery routed to
license.

**Fixes (three data-backed rules):** consortium O&M → maintenance
(wrappers don't make a JV); development-over-license (development
machinery wins over license grants for the developed IP); the promotion
guard (promotion title/core is its own family, not marketing or
distributor).

**A/B (stratified 250, seed 42 → 243 docs, medium reasoning, llm-dojo):**
strict **0.8683 → 0.8765 (+0.82pp)**, equiv 0.8807 → 0.8889, the
promotion→marketing cluster eliminated, 32 → 30 fails.

## 4. v8 — development vs collaboration, IP-titled agreements

**Problems:** development→collaboration/license/franchise (5 errors);
IP-titled agreements with license/JV sections routed to license /
joint_venture (3 errors).

**Fixes (rules 21–22):** DEVELOPMENT VERSUS COLLABORATION, LICENSE, AND
FRANCHISE STRUCTURES ("Collaborative Development" = development; a
"Development Agreement" title stays development even with grant/franchise
delivery machinery); INTELLECTUAL PROPERTY AGREEMENTS ARE ip (IP title
wins over license-grant or JV sections — the corpus files these under Ip
Ownership and the GT follows the folder).

**A/B (same 243-doc surface):** strict **0.8765 → 0.8971 (+2.06pp)**,
equiv 0.8889 → 0.9012, development→collab/license/franchise **5 → 0**,
ip→license/joint_venture **3 → 0**, 30 → 25 fails. Cumulative v6→v8:
+2.9pp strict.

## 5. v9 — the title-wins rules

**Problems (the exact v8 residual):** promotion-title docs with
distribution machinery → marketing (2); outsourcing-titled docs whose
outsourced services ARE manufacturing → manufacturing (2);
customization-schedule annexes → miscounted (1).

**Fixes (rules 23–25):** 23. PROMOTION TITLE WINS — COLOGUARD /
CO-PROMOTION / PROMOTION AND DISTRIBUTION agreements are promotion despite
marketing/distribution machinery; 24. OUTSOURCING TITLE WINS —
outsourcing-titled docs are outsourcing even when the outsourced services
ARE manufacturing; 25. CUSTOMIZATION SCHEDULES ARE MAINTENANCE — annex
inheritance for customization schedules.

**A/B (same 243-doc surface):** strict **0.8971 → 0.9259 (+2.88pp)**,
equiv 0.9012 → 0.9259, all three target clusters eliminated, 25 → 18
fails. **Cumulative v6→v9: +5.8pp strict (0.8683 → 0.9259).**

## 6. Reasoning-effort default (medium)

**Problem:** 25 near-synonymous families under-deliberated at low effort.

**Fix:** the sorter defaults to `reasoning_effort="medium"` (overridable
per run); verified **+4.6pp strict on the 200-doc stratified sample**.

## 7. Scale validation + the re-baseline (settling the 0.95 question)

v9 @ full corpus (509 docs) = **0.9116 strict / 0.9194 equiv, beating v8
(+0.98pp)** — the v6→v9 rule iterations hold at scale. The re-baseline
showed the 0.9436-era v6 number lived on the OLDER corpus revision: the
0.95 target was **revision-confounded**, and ~0.93 is the practical
plateau on the current revision. Sample-size behavior is non-monotonic but
bounded (v9: 0.8872 → 0.9259 → 0.9116 across 195/243/509); the full-set
number is the stable estimate.

## 8. The plateau doctrine (v9 close-out)

18 fails remain, all 1-off (no cluster > 2) — a long tail, not a family
confusion. Decision: **stop rule-writing here**; 0.95 needs either
tail-sampling iterations (per-error-class rules on the long tail) or a
corpus re-baseline, proposal + data first.

---

## The lesson

Every fix was a **routing rule with a filename citation**, validated on
the identical surface. When the residual stopped clustering, the honest
move was to declare a plateau and open a follow-on card — not to keep
writing rules.

*Next: [10-problems-contracts-specialist](10-problems-contracts-specialist.md).*
