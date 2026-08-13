# Research Memo: v23 — worked-example set v2 (the residual-34 spans; ko 0.8374 best @none, 42 spans recovered)

**Companions:** [contracts_specialist_v22.md](contracts_specialist_v22.md)
· [contracts_specialist_v21.md](contracts_specialist_v21.md) ·
experiment log (runs 044–055, task `contract_entity_extraction`) ·
[experiment-log site](https://exios66.github.io/llm-entity-extraction/)

---

## Answer, Response, + Summary of Results

**Result: ko 0.8374 (best none-reasoning arm; trend 0.8168 → 0.8294 →
0.8374), 42 of the target spans recovered at token level vs 31 lost,
overall 0.9315 (v22's 0.9512 stays the overall champion — v23's
effective_date 0.917 / verified_precision 0.973 dips are same-surface
variance, CI .893-.960 overlaps).**

The v23 design surfaced a real defect in the v19 example set: the
"Sekisui shall not deface ... trade names" NEGATIVE was over-broad — it
suppressed GT-labeled mark-OWNERSHIP-USE restrictions (Ritter) and mark
non-tarnishment (ARMSTRONGFLOORING) alongside the intended hygiene
duties. The fix disambiguates the classes, and the recovered spans confirm
it (Ritter supply commitment, PHREESIA assignment, Phasebio
additional-insured all recovered at token level). ko at reasoning=none is
climbing back toward v18's 0.8535; the 0.8840 peak remains a
max-reasoning outcome. Open: a v23×max arm (≈$0.10) is the remaining
question if the ko priority outweighs cost.
