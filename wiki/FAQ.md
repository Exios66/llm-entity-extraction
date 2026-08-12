# FAQ

**Q: Why is accuracy different between two runs of the same prompt?**
A: They likely ran on different surfaces — dataset, seed, or sample size.
Only same-surface comparisons (identical `dataset_fingerprint` + `seed` +
`n_samples`) are meaningful; the site's "Δ vs best" enforces this, and
bootstrap CIs tell you when a gap is just noise.

**Q: Why is `cost_total_usd` $0.00 but the site shows an estimate?**
A: OpenRouter usage payloads carry no cost field, so runs record $0.00 from
usage. The site computes deterministic estimates from token counts × verified
per-model prices (`src/cost_models.py`), and shows real billed totals when
you rebuild with `--openrouter-csv openrouter_activity.csv`.

**Q: Why does the markdown log look different after `render_experiment_log.py`?**
A: The md is DERIVED whole from the JSONL — it always reflects every record,
in order. Never hand-edit it.

**Q: Can I compare a 50-doc run to a 509-doc run?**
A: No. Deltas across different samples are meaningless (this is exactly how
the v0.13.0 "regression" got misread). Compare only same-surface runs, and
let the bootstrap delta CI decide significance.

**Q: What is `--handoff-scope ground_truth`?**
A: The chained error-propagation ablation: the specialist ALSO extracts the
same docs cued with the ground-truth subtype. `scores.ablation` splits sorter
routing loss from specialist error.

**Q: What is the judge-calibration tracker?**
A: With `--judge`, every ambiguous-band row's LLM verdict is compared to the
deterministic score (`scores.judge_calibration`): agree rate + lenient/strict
lean — before trusting the judge more broadly.

**Q: How do I add a new prompt version?**
A: Add the constant + register it in `PROMPT_VERSIONS` (`src/prompts.py`).
The version key IS the experiment identity. NEVER edit a prompt string after
it has run — a changed prompt needs a new version key.

**Q: How does the wiki stay in sync?**
A: `wiki/` is version-controlled here; `./wiki/sync-wiki.sh` pushes it to the
public GitHub wiki.

**Q: Where does the GH Pages site come from?**
A: `docs/` on `main` — rebuilt with `scripts/site/build_site.py`, deployed on
every push, no Actions runners.
