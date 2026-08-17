# `data/judgments/` — post-hoc LLM-judge calibration records

**Status:** gitignored (local only)

Calibration records from the offline judge pass — the JudgeAgent's
classification/completeness/correctness verdicts versus the deterministic
scorer, appended one line per reviewed document.

## Contents

| Pattern | What it holds |
|---|---|
| `<experiment>.jsonl` | Judge-vs-deterministic rows for one experiment |

## Writers

- `scripts/reporting/judge_experiment.py` → `data/judgments/<experiment>.jsonl`
- `scripts/eval/run_extraction_eval.py` (the optional `--judge` pass) appends
  to `data/judgments/<exp>.jsonl`

## Related paths

- Judge agent: `agents/judge_agent.py`
- Deterministic scorer: `llm_dojo_scoring.field_scoring` (via the
  `src/field_scoring.py` re-export shim)
