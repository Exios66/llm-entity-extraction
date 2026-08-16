# `data/manifests/` — resumable eval-run checkpoints

**Status:** gitignored (local only)

JSONL checkpoints written by the eval runners via `--manifest`. Each line
records one processed document so a rerun resumes where it left off instead of
re-paying LLM calls.

## Contents

| Pattern | Runner |
|---|---|
| `subtype_*.jsonl` | `run_langfuse_subtype_eval.py` / `run_subtype_eval.py` |
| `extract_*.jsonl` | `run_extraction_eval.py` / `run_langfuse_extraction_eval.py` |
| `chained_*.jsonl` | `run_chained_eval.py` / `run_langfuse_chained_eval.py` |
| `classification_*.jsonl` | `run_langfuse_classification_eval.py` |
| `docclass_*.jsonl` | `run_langfuse_docclass_eval.py` |

## Notes

- The checkpoint header must match the rerun's metadata exactly (dataset
  fingerprint, model, prompt version) — a mismatch invalidates the resume by
  design. Cached rows predating a scorer change must NOT be resumed; use a
  fresh manifest.
- Manifest-replayed rows carry no usage, so token/cost summaries count only
  rows with usage.

## Related paths

- Manifest scoring tooling: `scripts/reporting/score_extraction_manifest.py`,
  `scripts/reporting/rescore_manifests.py`.
