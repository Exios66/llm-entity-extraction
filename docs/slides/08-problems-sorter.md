# 08 — Problems: sorter prompt iterations

---

## The question

The sorter classifies every document into a doc_type plus one of **25
contract subtypes** (the CUAD folders). The iterations v5→v9 were a series
of *"why does the model misroute this family?"* investigations. This deck
catalogs the problems those iterations were chasing — the companion deck
[09-fixes-sorter](09-fixes-sorter.md) documents what fixed each one.

---

## 1. The family space is near-synonymous by design

25 subtypes overlap in machinery: reseller and distributor agreements are
structurally identical; maintenance and license agreements share service
grants; development agreements carry license/franchise machinery; affiliate
deals look like joint ventures. Two documents can be *defensibly* routed to
different families by different readers, so a strict single-label
evaluation is harsh by construction.

**Measured effect:** the subtype eval reports strict accuracy *and*
family-level equivalence accuracy; `SUBTYPE_EQUIVALENCES` recognizes
reseller↔distributor, maintenance↔license, development↔license,
affiliate↔joint_venture as defensible family routing. Strict stays the
discriminating signal; equiv recognizes the honest part of the loss.

## 2. Titles vs operative sections — the title-wins problem

The recurring failure shape: a document whose **title** names one family
but whose **operative machinery** belongs to another, and the model split
along whichever side it trusted:

- "CO-PROMOTION / COLOGUARD / PROMOTION AND DISTRIBUTION" agreements with
  marketing/distribution machinery → routed to marketing/distributor
  (a 6-error cluster in v6/v7).
- Outsourcing-titled agreements whose outsourced services ARE manufacturing
  → routed to manufacturing (2 errors at v8).
- "Franchise Development Agreement" with a Section 2 grant-of-rights →
  development machinery, but franchise by title.
- "Intellectual Property Agreement" structured as a license grant or
  containing a joint-venture section → routed to license / joint_venture.
- "Development Agreement" titled documents with license or franchise
  structures for the developed materials.

The corpus files these documents under one folder and the ground truth
follows the folder — the model had no rule telling it **which side wins**.

## 3. Development vs collaboration / license / franchise structures

"Collaborative Development and Commercialization Agreement" and
"Collaborative Research, Development and Commercialization Agreement"
carry development machinery (joint research program, joint steering
committee, development plan, milestones, trial timelines) wrapped in
collaboration governance (JSC/JPT). The model read the governance and
routed to collaboration; the corpus files them under development. The
reverse confusion: a "Development Agreement" whose operative section is a
"Grant of License" for the developed materials → license.

**Measured effect:** development→collaboration/license/franchise = 5
errors at v7; development→collab 5→0 and ip→license/joint_venture 3→0
after the v8 rules.

## 4. Hybrid titles are genuinely ambiguous

"Distribution and Development Agreement" can plausibly be either family —
there is no single correct answer for every hybrid. The evaluation treats
it as a routing decision with a *defensible* resolution (the equivalence
families), and the confusion matrix shows which hybrids recur.

## 5. Under-deliberation: reasoning effort

25 near-synonymous families need actual deliberation, and the sorter's
default reasoning effort was too low to separate them reliably. When the
eval harness tested a higher setting on the same surface, strict accuracy
moved **+4.6pp on the 200-doc stratified sample** — a setting problem, not
a prompt-content problem.

## 6. Plateau and revision confounds (the 0.95 question)

The sorter never reached its 0.95-strict target, and the investigation
found two confounds:

1. **Corpus revision drift** — the 0.9436-era v6 numbers lived on an
   OLDER corpus revision (fingerprint `2e1fe4b7`); on the current
   revision (`fb9f939d`) v6 itself scores 0.8683. The "regression" was a
   harder ground truth, not a worse model.
2. **Sample-size non-monotonicity** — v9 scored 0.8872 / 0.9259 / 0.9116
   across 195 / 243 / 509 docs; the full-set number is the stable
   estimate.

The residual after v9: **18 fails, all 1-off (no cluster > 2)** — a long
tail, not a fixable family confusion. ~0.93 is the practical plateau on
this corpus revision; 0.95 needs tail-sampling iterations (per-error-class
rules on the long tail) or a corpus re-baseline.

---

## The lesson

The sorter's failures were **routing-rule problems**, not comprehension
problems: title-vs-machinery conflicts, over-broad family definitions, and
a too-low reasoning budget. Each iteration's rule set was derived from the
exact failure rows of the previous run (data-backed), and every A/B ran on
the **same surface** (same dataset fingerprint + seed + sample) so the
deltas were comparable.

*Next: [09-fixes-sorter](09-fixes-sorter.md) — what fixed each of these.*
