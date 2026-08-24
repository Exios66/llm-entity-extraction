# Annotation Queues — Human-in-the-Loop Review

The experiment cycle is prompt-iteration-first; the **HITL annotation
queue** closes the loop with human review. `scripts/eval/run_annotation_queue.py`
filters the llm-dojo mirror's traces and enqueues the ones worth a human's
eyes into a Langfuse **annotation queue** (`PENDING` items), where reviewers
score each trace in the Langfuse UI. Annotations land as scores on the
traces — the labeled misses for the next prompt iteration.

## The loop

1. **`build`** — scan the llm-dojo traces of one pipeline task, rank them,
   and enqueue the failures/low performers as `PENDING` items (idempotent:
   the queue is created once by name, already-enqueued traces are never
   re-enqueued).
2. **Review** — open the printed review URL; each queue item opens its
   trace: predicted output vs GT, per-field scores, the agent span, and
   per-chunk generations (see [Langfuse-Traces](Langfuse-Traces) for the
   graph reader).
3. **Annotate** — score the trace in the UI against the queue's score
   config (`annotation-verdict`: correct / partial / incorrect).
4. **Audit** — `status` lists the queue with per-trace scores, failure
   flags, prompt versions, and review URLs.

## Two tasks, one queue

The Langfuse Hobby plan allows **one annotation queue per project**, so the
llm-dojo project shares a single queue (`entity-extraction-low-performers`)
between the two pipeline tasks. `status --task <task>` filters the items by
trace name, so each review flow stays separate.

```bash
# Extraction pipeline: traces whose overall_extraction_score < 0.85
python scripts/eval/run_annotation_queue.py build --dry-run --threshold 0.85
python scripts/eval/run_annotation_queue.py build --threshold 0.85

# Sorter pipeline: FAILED classifications (primary class, subtype, or both)
python scripts/eval/run_annotation_queue.py build --task subtype --dry-run
python scripts/eval/run_annotation_queue.py build --task subtype

# Audit either queue view
python scripts/eval/run_annotation_queue.py status                 # extraction items
python scripts/eval/run_annotation_queue.py status --task subtype  # sorter items
```

| Flag | Meaning |
|---|---|
| `--task extraction` (default) | threshold mode — enqueue traces with `overall_extraction_score` < `--threshold` (0.85) |
| `--task subtype` | failure mode — enqueue traces where the primary class (`doc_type`), the contract subtype (CUAD folder), or both FAILED, from the sorter's output composite (`doc_type_ok`/`subtype_ok`); both-failures lead |
| `--dry-run` | scan + rank only, no writes |
| `--limit N` | cap the batch (worst first) |
| `--since-days N` | only traces newer than N days (default 30) |
| `--queue-name` | override the queue (default per task) |

## What the filter reads

- **Extraction**: the trace output composite written by
  `run_langfuse_extraction_eval.py` (`trace_handle.set_output`), ranking on
  the same `overall_extraction_score` the task scorer attached — zero extra
  API calls.
- **Sorter**: `subtype_classification` traces (session-scoped to
  `*_subtype_langfuse`, prompt-scoped to `sorter_*`); failure flags come
  from `output.sorter.doc_type_ok` / `subtype_ok`. A doc-type failure
  always fails the subtype too (`subtype_ok` requires `doc_type_ok`).

## Hardening notes (from the live setup)

- The public list endpoints return score **ids** (strings) — the ranking
  uses the trace output composite; `status` reads scores via the bulk
  **v3 scores** endpoint (cursor-paginated, `subject` field group).
- 429 rate limits are retried with the server's `retryAfterSeconds`.
- The queue auto-creates its `annotation-verdict` categorical score config
  when none is passed (the API requires ≥1 config id).

## Repo references

- `scripts/eval/run_annotation_queue.py` — the tool (client, task
  registry, selection logic)
- `tests/test_annotation_queue.py` — network-free tests (fake Langfuse API)
- AGENTS.md "Command cheatsheet" — the HITL commands
- [Eval-Runners](Eval-Runners) — the mirror runners that produce the traces
- [Langfuse-Traces](Langfuse-Traces) — how to read the trace graphs a
  reviewer clicks through
