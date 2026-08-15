# 07 — Reading the experiment log (without being misled)

---

## Where the data lives

| Artifact | What it is | Rebuild command |
|---|---|---|
| `reports/experiment_log.jsonl` | **Source of truth** — one JSON line per run, append-only, never rewritten | — (written by the runners) |
| `reports/experiment_log.md` | Derived, fully expanded markdown | `python scripts/reporting/render_experiment_log.py` |
| GH Pages site `docs/` | Filterable viewer (`https://exios66.github.io/llm-entity-extraction/`) | `python scripts/site/build_site.py` |

**Never hand-edit the md log or docs/data** — they are derived; regenerate
them.

---

## Anatomy of one run record (JSONL line)

```json
{
  "experiment_name": "qwen3.7-flash_contracts_specialist_v22_extraction_langfuse_50",
  "model": "qwen3.7-flash",
  "prompt_version": "contracts_specialist_v22",
  "data_source": {"dataset": "...", "dataset_fingerprint": "fb9f939d", "master_labels": "..."},
  "parameters": {"sample": 50, "seed": 42, "reasoning_effort": "none", ...},
  "tokens": {"prompt_tokens": ..., "cost_total_usd": ...},
  "scores": {
    "overall_extraction_score": 0.9512, "overall_extraction_score_ci": [..],
    "per_field": {...}, "verified_precision": ..., "hallucination_rate": ...,
    "diagnostics": { ... deck-04 numbers ... }
  },
  "results": [ { per-document: predicted, field_scores, entity_list_audit, reasoning } ]
}
```

The **markdown section** renders all of this as tables: metadata, data
source, parameters, tokens, scores, **run-level diagnostics**, per-document
results, document × field scoring matrices, factuality audit, CUAD category
presence, confusion matrices, model outputs — and for subtype runs,
per-class accuracy + failed-classification insights with full reasoning.

---

## The site, mapped to this deck

| Site view | Contains |
|---|---|
| Dashboard | per-task stat cards, filterable runs table (sample-size aware) |
| Run detail | banded metric cards, score composition, per-field scores, **Run-level diagnostics card**, per-document results |
| Trace (`#/run/N/doc/i`) | one document: verdicts, reasoning, interpreted extraction scores, factuality audit |
| Group views (`#/task/`, `#/prompt/`, `#/model/`) | aggregates + grouped-by tables |

Every headline score carries a Wilson/bootstrap 95% CI with n; the **Δ vs
best** column is colored only when statistically significant.

---

## The 5 reading rules (the anti-misleading checklist)

1. **Same surface only** — dataset fingerprint + seed + sample size must
   match to compare runs. `reports/same_scorer_scores.json` keeps the
   50-doc series comparable across scorer changes.
2. **Sample size first** — n=5 → CI ±27pp; n=509 → ±2.2pp. A 0.94-vs-0.88
   gap on 5 docs is noise.
3. **Read the composition, not just the headline** — 0.95 overall with
   `verified_precision` 0.6 means a lot of fabricated content scored by
   coverage. Diagnostics exist for this.
4. **Support sizes with every MAE/R²** — `date_n_pairs = 2` is a hint,
   500 is a fact.
5. **Name → identity** — `{model}_{prompt_version}[_suffix]`. Re-running a
   name suffixes the experiment in Braintrust; the suffixed one holds the
   newer run.

---

## Quick log queries

```bash
# Headlines + timestamps
python - <<'PY'
import json
for line in open("reports/experiment_log.jsonl"):
    r = json.loads(line)
    print(r["experiment_name"], r["scores"].get("overall_extraction_score")
          or r["scores"].get("exact_match"), r["timestamp"])
PY

# Diagnostics from the latest extraction run
python - <<'PY'
import json
runs = [json.loads(l) for l in open("reports/experiment_log.jsonl")
        if json.loads(l)["task"] == "contract_entity_extraction"]
d = runs[-1]["scores"].get("diagnostics") or {}
print(runs[-1]["experiment_name"])
for k in ("list_f1", "date_mae_days", "date_r2", "duration_mae_days",
          "span_count_signed_mean", "field_exact_rate"):
    print(f"  {k}: {d.get(k)}")
PY
```

---

## If a number looks wrong

1. Check the **git snapshot** on the record (`record.git.commit`) — scorer
   drift changes old numbers; rescore with `scripts/reporting/rescore_manifests.py`
   when a scorer rule changes.
2. Check the **dataset fingerprint** — a different corpus revision is not
   comparable (the 0.95-era v6 numbers lived on an OLDER corpus revision).
3. Check the **support size** — thin pairs, few docs.
4. Then suspect the prompt/runner, not the scorer: the scoring is
   deterministic by design; Braintrust only mirrors local composites.

## End of decks

Back to [index](README.md) · Full formulas: `SCORING.md`
