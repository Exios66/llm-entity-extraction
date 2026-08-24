# Phoenix Local Trace Sink

The default, local-first observability sink for every eval run — a single
process, SQLite-backed Arize Phoenix server that receives OpenTelemetry spans
as they are produced, with **no cloud subscription, no quota, and no Docker
stack**. This page documents the sink itself and the **resume / checkpoint /
queue / cache** configurations that keep runs efficient without burning cost.

## Why a local sink

The pipeline previously leaned on cloud trace sinks (Langfuse, Braintrust,
LangSmith) for every run. Those are retained — Langfuse remains the **primary**
trace sink for the `run_langfuse_*_eval.py` runners when its keys are
configured, and LangSmith auto-traces every LangChain LLM call when enabled —
but the **default local Phoenix server** is the workhorse:

- **Apache/Elastic-licensed**, runs as a single local process.
- **SQLite/in-memory storage** — no external database, no multi-service stack.
- **OpenTelemetry-native** — spans pour in via OTLP HTTP (`/v1/traces`).
- **Discard-by-delete** — finished batches are discarded by deleting the DB
  file; nothing accrues, nothing is billed.

The local sink means experiment iteration is free of cloud-trace quotas and
per-byte billing; the experiment log (`reports/experiment_log.{jsonl,md}`) is
the durable, version-controlled record, and Phoenix is the poke-around window.

## Data flow

```
eval runner (run_langfuse_*_eval.py)
  │  resolve_tracer(session_id, trace_name, tags)     [src/tracing.py]
  ▼
Langfuse keys configured? ──yes──▶ LangfuseTracer (llm-dojo project)
  │ no                                              (tracing_backend="langfuse")
  ▼
PhoenixTracer ──▶ OTLP HTTP ──▶ local Phoenix server  (tracing_backend="phoenix")
  │                                  │ SQLite store, http://localhost:6006
  └─ PHOENIX_TRACING=disabled ──▶ no-op tracer (runs identically, zero overhead)
```

`resolve_tracer()` returns `(tracer, tracing_backend, tracing_meta)`; the
backend label and metadata (endpoint / service / project / session) land in
the experiment-log record, so **the log always reports which sink fired**.
`prefer="phoenix"` keeps the pre-directive local-first order for explicit
opt-in.

Every LangChain LLM call can additionally auto-trace to **LangSmith**
(`LANGSMITH_TRACING=true`) and to **Langfuse** (the llm-dojo project) — these
are opt-in mirrors that coexist with the Phoenix sink.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PHOENIX_TRACING` | `enabled` | Master switch. `disabled` → no-op tracer. |
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | OTLP HTTP endpoint of the Phoenix server. |
| `PHOENIX_SERVICE_NAME` | — | OpenTelemetry service name for the spans. |
| `PHOENIX_PROJECT` | — | Phoenix project/session tag for run grouping. |
| `PHOENIX_SESSION` | — | Session tag (defaults to the experiment name). |
| `LANGCHAIN_TRACING_V2` | `true` | Enables LangChain's OpenTelemetry instrumentation so LLM calls emit spans. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | Points the OTel exporter at Phoenix (same as `PHOENIX_ENDPOINT`). |

All live values live in `config/environments/.env` (gitignored; template in
`.env.example`). Real shell env vars always win over the dotenv files.

## Running it

```bash
# Phoenix runs as a single local process; start it once per machine:
python -m phoenix.server.main serve          # serves the UI + OTLP receiver
# UI: http://localhost:6006  ·  OTLP receiver: http://localhost:6006/v1/traces

# Then run evals as usual — spans pour in automatically when PHOENIX_TRACING
# is enabled and the server is up:
python scripts/eval/run_langfuse_subtype_eval.py --dry-run          # confirm the plan first
python scripts/eval/run_langfuse_subtype_eval.py --stratified 250 --seed 42 --sorter-prompt-version sorter_v13
```

Inspect traces in the UI, then **discard the batch** when done by deleting the
DB file (SQLite/in-memory — nothing persists by default and nothing bills).

## Resume, checkpoint, queue & cache — the cost-efficiency configuration

"Solidify and cement" the configurations that make long runs cheap to re-run
and impossible to double-pay for.

### Resume — the manifest checkpoint

Every `run_*_eval.py` / `run_langfuse_*_eval.py` runner accepts
`--manifest <path>` (`src/evaluation.py::ManifestStore`, thread-safe JSONL):

- The **first line is a run header**; subsequent lines are append-only row
  states. The last state per filename is authoritative.
- A manifest is reusable **only when its metadata matches the current
  evaluation exactly** (dataset fingerprint, model, prompt version,
  tracing backend) — a mismatch makes the resume invalid **by design**.
- Completed rows are skipped on re-run (no re-paid LLM calls); interrupted
  runs resume exactly where they left off.

**Never resume a stale manifest**: cached rows that predate a scorer or prompt
change are invalid — use a fresh manifest path (`data/manifests/*.jsonl`).

### Checkpoint — the experiment log

The experiment log itself is the durable checkpoint:

- `reports/experiment_log.jsonl` is **append-only** — one JSON line per run,
  never rewritten.
- `reports/experiment_log.md` is **derived** and rebuilt whole by
  `scripts/reporting/render_experiment_log.py` — never hand-edited.
- Path overrides: `EXPERIMENT_LOG_PATH` / `EXPERIMENT_LOG_MD_PATH` env vars or
  `--experiment-log` (tests redirect to tmp dirs).

### Queue — the HITL annotation queue

`scripts/eval/run_annotation_queue.py` mirrors the llm-dojo Langfuse project
into a review queue (network-free against a fake Langfuse stand-in in tests):

- `build --task extraction --threshold 0.85` — enqueue low-performing
  extraction traces as PENDING.
- `build --task subtype` — enqueue failed sorter doc_type/subtype
  classifications.
- `status` — queue items + scores + trace URLs.
- `--dry-run` scans and ranks **without writing** — never enqueue blind.

### Cache — embeddings & usage accounting

- The semantic embedding rescue prefers the **local `all-MiniLM-L6-v2`
  sentence-transformers model** (free, offline, reproducible); the paid
  OpenRouter embedding fallback triggers only when the local model is absent.
- **Manifest-replayed rows carry no usage** — token/cost summaries count only
  rows with usage (`rows_with_usage`), so a resumed run never double-bills.

### Cost gates

- `--dry-run` on any runner prints the plan (dataset, sample, prompt version,
  experiment name) before a single LLM call.
- `assert_production_run()` (**`src/env_utils.py`**) HARD-REFUSES dry-runs and
  pilot-scale samples (fewer than 100 rows, or less than the full dataset)
  when the externally-funded `--research-funding-key` is used — external
  funding pays only for fully-ready production runs.
- Deterministic field-type-aware scoring means re-scoring a manifest
  (`scripts/reporting/rescore_manifests.py`) is free — no LLM re-run.

## Testing

All tests are **network-free**: Phoenix tracing degrades to a no-op when
`PHOENIX_TRACING=disabled` or the server is unreachable, and the tracing
resolution order + record metadata are pinned by `tests/test_tracing.py` and
the langfuse/annotation-queue tests (fake API stand-ins). A run with no
observability configured behaves identically to one with full tracing.