# llm-entity-extraction — Experiment Log Wiki

**The prompt-experiment loop for the llm-mailroom legal document pipeline.**

This repo measures how well prompt versions classify legal documents and
extract entities, **one prompt at a time**. Every run produces one append-only
record in `reports/experiment_log.jsonl`, a fully expanded section in
`reports/experiment_log.md`, and a filterable **interactive site** served by
GitHub Pages:

> ## [**Open the experiment-log site**](https://exios66.github.io/llm-entity-extraction/)
>
> score trends, cost-vs-quality scatter, failure-mode stacked bars, prompt
> diffs, and same-surface A/B guardrails — every chart point opens its run.

## Quick links

| Page | What it covers |
|---|---|
| [Getting-Started](Getting-Started) | setup, first eval, the experiment loop |
| [Architecture](Architecture) | repo layout, data flow, agents |
| [Eval-Runners](Eval-Runners) | every eval runner, flags, matrices |
| [Langfuse-Traces](Langfuse-Traces) | how to read the Langfuse trace graphs — node-by-node, chunked examples |
| [Phoenix-Tracing](Phoenix-Tracing) | the local Phoenix trace sink + the resume / checkpoint / queue / cache cost-efficiency configuration |
| [Annotation-Queues](Annotation-Queues) | the HITL review loop — low-performing extraction traces and failed sorter classifications, enqueued for human annotation |
| [Experiment-Log](Experiment-Log) | the JSONL log, the markdown renderer, the site |
| [Scoring](Scoring) | every metric, where it is computed, how to read it |
| [Site](Site) | the visualization site: views, charts, interactions |
| [Release-Process](Release-Process) | changelog, versioning, tags, GH Pages sync |
| [Taxonomy](Taxonomy.yml) | `config/taxonomy.yaml` reference |
| [FAQ](FAQ) | common questions |

**Knowledge graph** — an interactive graphify map of this codebase (agents,
prompts, scripts, tests as queryable nodes) lives at
[llm-entity-extraction-graph](https://exios66.github.io/llm-entity-extraction-graph/)
— build artifact, never committed here; rebuild with `graphify . --code-only`.
Sister-repo relationships are mapped in
[`docs/sister-repos.md`](https://github.com/Exios66/llm-entity-extraction/blob/main/docs/sister-repos.md).

## The core idea

1. **Sync corpora** (CUAD, LegalBench) into Braintrust datasets.
2. **Run ONE prompt version** through the vendored agents (sorter,
   specialists, judge) via OpenRouter.
3. **Score deterministically** — never LLM-graded: field-type-aware content
   scores, bootstrap CIs, cost estimates.
4. **Log it** — JSONL + markdown + the GH Pages site, automatically.
5. **Compare on the same surface** — dataset fingerprint + seed + sample
   size, with bootstrap significance, never bare accuracy deltas.

The sorter and contracts-specialist prompts validated here are vendored into
**llm-mailroom** (`llm-mailroom/langchain_agents/`, byte-locked against this
repo's commit `3a03d5c`) — the experiment log is the evidence base for which
prompt versions are in production.
