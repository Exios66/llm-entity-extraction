# Getting Started

## Prerequisites

- Python 3.10+ (tested on 3.13)
- An [OpenRouter](https://openrouter.ai) API key (the eval LLM gateway)
- Optional but recommended: `pip install sentence-transformers` for the local
  embedding rescue (free, offline)

## Setup

```bash
git clone https://github.com/Exios66/llm-entity-extraction
cd llm-entity-extraction
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # agents/src/config importable from any codebase
cp config/environments/braintrust.env.example config/environments/braintrust.env   # Braintrust org/project keys
cp config/environments/.env.example config/environments/.env                       # OPENROUTER_API_KEY (+ Langfuse keys for mirrors)
```

## Your first run

```bash
# 1) Sync the CUAD corpus into Braintrust (one time)
python scripts/datasets/stream_cuad_to_bt.py --text-only --dry-run   # preview
python scripts/datasets/stream_cuad_to_bt.py --text-only

# 2) Run a cheap classification eval (ONE prompt version at a time)
python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
    --prompt-version sorter_v0 --limit 5

# 3) Rebuild the derived artifacts + the site
python scripts/reporting/render_experiment_log.py
python scripts/site/build_site.py
node tests/assets/site_render_audit.js     # headless render audit

# 4) Commit + push (this updates the GH Pages site — /docs is served from main)
git add reports/ docs/data
git commit -m "EXPERIMENT: <name>"
git push origin main
```

## The loop (one prompt at a time)

1. **Diagnose with data** — read the last runs in `reports/experiment_log.md`
   (or the [site](https://exios66.github.io/llm-entity-extraction/)):
   per-field scores, confusion matrices, failure insights, cost.
2. **Change ONE thing** — a new prompt version (constant + `PROMPT_VERSIONS`
   entry in `src/prompts.py`). The version key IS the experiment identity;
   never mutate a prompt after it has run.
3. **Unit-test** — `python -m pytest tests/ -q` before spending money.
4. **Dry-run** — `--dry-run` on the runner to confirm the plan.
5. **Cheap pilot** — same seed as previous runs for direct comparison
   (`--sample 5 --seed 42`).
6. **A/B on identical rows** — `evaluate_prompt_version.py --prompt-a A
   --prompt-b B`; the delta carries a bootstrap CI + significance verdict.
7. **Full-sample when meaningful** — same-sample comparisons are the ONLY
   valid accuracy comparisons.
8. **Log & document** — verify the JSONL record, regenerate the md + site,
   commit with its `[Unreleased]` changelog entry (see
   [Release-Process](Release-Process)).

## Mirror into llm-mailroom

The synced copy lives at `llm-mailroom/docs/reports/experiments/experiment_log.md`.
After upstream pushes, llm-mailroom re-syncs:

```bash
cd ../llm-mailroom
PYTHONPATH=src python -c "from legalbench.experiment_log import regenerate, default_log_path; regenerate(default_log_path())"
```
