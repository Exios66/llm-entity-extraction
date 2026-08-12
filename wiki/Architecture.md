# Architecture

## What is being measured

**llm-mailroom** — a LangGraph pipeline that processes legal documents through
specialist LLM agents (classify → extract → report → archive). This repo is
the **prompt experiment loop** for that pipeline: it measures how well prompt
versions classify legal documents and extract entities, one prompt at a time.

## Repo layout

```
agents/                  LangChain agents (sorter, specialists, judge)
config/taxonomy.yaml     doc classes, field types, agent->model mapping, thresholds
src/                     core modules (see src/README.md)
scripts/
  datasets/              HF corpus -> Braintrust dataset streamers
  eval/                  the eval runners (see Eval-Runners)
  reporting/             markdown log renderer + report helpers
  site/                  GH Pages site data builder
  release.py             semver release automation
tests/                   network-free suite (see tests/README.md)
reports/                 the experiment log (JSONL + rendered markdown)
docs/                    the site (index.html, assets/, data/) — /docs on main
wiki/                    this wiki (synced to the GitHub wiki by wiki/sync-wiki.sh)
```

## Data flow

```
HF/GitHub corpora ──stream_cuad/legalbench──▶ Braintrust datasets
                                                  │
local PDFs ──--pdf-dir──┐                        │ load_braintrust_dataset()
                         ▼                        ▼
               run_*_eval.py ──▶ LangChain agent ──▶ OpenRouter LLM
                    │                                │
                    │                 setup_langchain() traces spans
                    ▼                                ▼
             deterministic scoring          Braintrust experiment
             (src/field_scoring.py)              │
                    │                             │
                    ▼                             ▼
   data/manifests/*.jsonl ◀── resumable ──  report_generator / confusion_matrix
                    │
                    ▼
   reports/experiment_log.{jsonl,md}   (append-only; md rebuilt by render script)
                    │
                    ▼
   docs/data/* (index, meta, runs/, trends.json, prompts.json) ──▶ GH Pages site
```

## Agents

| Agent | File | Role |
|---|---|---|
| `BaseAgent` | `agents/base_agent.py` | ChatOpenAI (OpenRouter) + structured output + vision + head/tail truncation + `_last_usage` |
| `SorterAgent` | `agents/sorter_agent.py` | doc-type + contract-subtype classification (text + image), `SUBTYPE_EQUIVALENCES` |
| specialists | `agents/specialist_agents.py` | per-class field extraction + shared JSON schemas + `handoff_context` |
| `JudgeAgent` | `agents/judge_agent.py` | LLM-as-a-judge (classification/completeness/correctness) |

The sorter receives **full documents** — either the full extracted text
(100k-char hard cap; past it, a HEAD + TAIL window where term/termination/
renewal/governing-law/signatures live) or the complete PDF page set in one
call (vision mode).

## Langfuse mirror

A separate Langfuse project (`llm-mailroom-experiments`, keys in
`langfuse.env`) mirrors runs trace-by-trace: one trace per document,
session-scoped deterministic ids, one span per agent with its designated task
scores attached. `run_langfuse_*_eval.py` runners share the same logging path
(`tracing_backend="langfuse"` in the record).
