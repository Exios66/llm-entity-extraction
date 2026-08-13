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

---

## Addendum 2 (2026-08-13): v23×max + the infrastructure fixes

**v23 × reasoning=max: ko 0.8510 (best since v19's 0.8840), 50/50 rows
(zero parse errors), ellipsis 18.7% (lowest of the max arms), overall
0.9363 (CI .899-.964), verified_precision 0.974, $0.103.** Within 3.3pp of
the v19 peak without its 1/50 parse-error risk or −2.3pp overall penalty.
The ko-justified production arm: **v23×max**; the overall champion stays
**v22×none (0.9512)**.

Three infrastructure items closed alongside:
1. **Same-scorer pipeline** (`scripts/reporting/rescore_manifests.py`):
   re-scores historical manifests with the current scorer (no-embedding
   pass; `--auto-50` for the v13→v23 series; report →
   `reports/same_scorer_scores.json`). String-level view shows the v19+
   arms lean harder on the embedding rescue (official ko 0.83-0.85 vs
   string 0.38-0.43) — the same-scorer view makes history drift-proof.
2. **Langfuse prompt-store cleanup**: the version-scoped delete 404s on
   this instance, but delete-all + re-sync left every prompt at exactly
   one version with clean production/latest labels (verified).
3. **0-ko docs corrected**: SPRINGBANK/QBIOMED/PelicanDelivers have ZERO
   obligation-family GT spans (QBIOMED = Schedule 13G joint filing) — ko
   is None (excluded) in every arm, not 0.0; the earlier "0-ko" framing
   was a token-level-audit artifact. Scope note: PelicanDelivers emits 11
   payment-milestone items (general duties, outside the family scope) —
   harmless without GT but a compliance observation.

*Open:* the 30-span residual at token level (span-choice divergence);
v24 would need annotator-grain boundary examples rather than clause-class
examples.
