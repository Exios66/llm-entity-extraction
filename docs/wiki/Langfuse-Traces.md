# Langfuse Traces — How to Read the Graph

The Langfuse **mirror** (`llm-mailroom-experiments` project) records **one
trace per document** for every Langfuse-backed run (`run_langfuse_*_eval.py`).
This page explains what every node in the trace graph is, what it costs, and
how to read the graphs — including the much longer **chunked** examples —
without getting lost in the plumbing.

## The short version

> **Count the `GENERATION` nodes.** That is the number of LLM calls the
> document actually made (≈ number of chunks processed). Every other node is
> zero-cost structural bookkeeping from LangChain's auto-instrumentation —
> there to show you *how* the chain was executed, not to add work.

A single-chunk document shows **14 nodes** (the trace root + 13
observations), of which exactly **one** is a model call. A 2-chunk document
shows **24 nodes** — the same subtree repeated once per chunk, **two** model
calls. The graph is long before it completes because the runnable tree is
emitted as the chain executes, not after.

## The three layers

Every trace graph is built from three layers, and each layer is created by
different code:

| Layer | Creator | Nodes | Cost |
|---|---|---|---|
| 1. Trace + task span | `src/langfuse_tracing.py` (`trace_document` / `agent_observation`) | `TRACE` root, `SPAN contract_entity_extraction`, `SPAN contracts_specialist` | 0 tokens, ~ms |
| 2. LangChain runnable tree | the `CallbackHandler` from `langfuse.langchain` (wired inside `trace_document`) | the `CHAIN`s + `GENERATION` | only the `GENERATION` costs tokens |
| 3. The model call | `agents/base_agent.py` `_call_structured` → `llm.with_structured_output(...)` | `GENERATION ChatOpenAI` | **all** the tokens |

Layer 2 is the source of the "too many nodes" feeling: one call to
`with_structured_output(json_schema, method="json_schema", include_raw=True)`
expands into ~10 runnable nodes, each of which gets its own observation.

## Node-by-node reference (single-chunk document)

Verified against trace
`223a8357bd59854f2ebab543f8341a31` (v21 run, one window, 10,567 tokens).
The graph, top to bottom:

```
TRACE  (root — the document; filename / expected / composite scores live here)
└── SPAN   contract_entity_extraction           ~12ms    0 tok   ← repo tracer (layer 1)
    └── SPAN   contracts_specialist             ~12ms    0 tok   ← repo tracer; task scores attach here
        └── CHAIN RunnableSequence               ~7ms    0 tok   ← the prompt|structured chain
            ├── CHAIN ChatPromptTemplate         0ms    0 tok   ← prompt assembly (system+user messages)
            ├── CHAIN RunnableParallel<raw>      ~7ms    0 tok   ← include_raw=True wrapper
            │   └── GENERATION ChatOpenAI        ~7ms 10567 tok ← THE ONLY LLM CALL
            ├── CHAIN RunnableWithFallbacks      0ms    0 tok   ← parser-failure retry wrapper
            └── CHAIN RunnableAssign<parsed,parsing_error>      0ms 0 tok ← attaches parse results
                └── CHAIN RunnableParallel<parsed,parsing_error> 0ms 0 tok
                    ├── CHAIN RunnableSequence   0ms    0 tok
                    │   ├── CHAIN RunnableLambda 0ms    0 tok   ← parse-invoke lambda
                    │   └── CHAIN JsonOutputParser 0ms   0 tok  ← the JSON schema parser
                    └── CHAIN RunnableLambda     0ms    0 tok   ← error capture (parsing_error)
```

| Node | What it represents | Cost | Read it as |
|---|---|---|---|
| `TRACE` (root) | One document in the eval | — | The document: filename, expected GT, composite scores |
| `SPAN contract_entity_extraction` | The per-document task span opened by `trace_document` | 0 tok | The task boundary; input carries filename/expected/metadata |
| `SPAN contracts_specialist` | The per-agent observation opened by `agent_observation` | 0 tok | **The agent** — task scores (field scores, verified precision, category presence) attach to this node's output |
| `CHAIN RunnableSequence` | The chain `prompt | llm.with_structured_output(...)` from `_call_structured` | 0 tok | The whole structured call as one unit |
| `CHAIN ChatPromptTemplate` | Message assembly (system prompt + `{text}` document) | 0 tok | Which prompt version ran — click to see the messages |
| `CHAIN RunnableParallel<raw>` | `include_raw=True` wrapper that keeps the raw `AIMessage` next to the parse | 0 tok | "This subtree produces the raw output" |
| `GENERATION ChatOpenAI` | **The actual model call** (qwen3.7-flash via OpenRouter) | **all tokens** | Latency, input/output tokens, cost, the raw response |
| `CHAIN RunnableWithFallbacks` | Fallback chain for parsing retries (RunnableLambda fallback → JsonOutputParser) | 0 tok | Will only do work if the first parse fails |
| `CHAIN RunnableAssign<parsed,parsing_error>` | Adds `parsed` and `parsing_error` keys to the raw output dict | 0 tok | The include_raw result contract |
| `CHAIN RunnableParallel<parsed,parsing_error>` | Runs the parser and the error-capture lambda concurrently | 0 tok | Branch 1 = parse, branch 2 = error capture |
| `CHAIN RunnableSequence` + `RunnableLambda` | Parse invocation wrapper | 0 tok | Executes the JSON parser |
| `CHAIN JsonOutputParser` | The schema-validated JSON parser | 0 tok | Converts the model text to the structured dict |
| `CHAIN RunnableLambda` (error capture) | Captures `parsing_error` when parsing fails | 0 tok | Non-zero only on malformed output |

**Why `parsed,parsing_error` and `<raw>`?** `_call_structured` uses
`include_raw=True`, so the chain returns `{"raw": AIMessage, "parsed": ...,
"parsing_error": ...}`. The `RunnableAssign`/`RunnableParallel` nodes are
that contract made visible. If the model's JSON fails to parse, the
`RunnableLambda` error-capture node is the one that records why.

## The chunked graph (2 windows — verified example)

For documents longer than one window, `extract_chunked`
(`agents/specialist_agents.py`) splits the text on paragraph boundaries
into overlapping windows (**90k chars, 8k overlap**), extracts **each window
with its own chain invocation**, then merges. The graph is simply the
single-chunk tree **repeated once per chunk**, all under the same
`contracts_specialist` span:

Verified against trace `cd289ad2bb92892b19e4c626fc6e44cc` (v18 run,
24 observations, **2 generations**, 26,934 + 21,666 tokens):

```
TRACE
└── SPAN contract_entity_extraction
    └── SPAN contracts_specialist
        ├── CHAIN RunnableSequence                    ← window 1
        │   ├── ChatPromptTemplate
        │   ├── RunnableParallel<raw>
        │   │   └── GENERATION ChatOpenAI  26,934 tok ← call 1 (window 1)
        │   ├── RunnableAssign<parsed,parsing_error>
        │   │   └── RunnableParallel<parsed,parsing_error>
        │   │       ├── RunnableSequence → RunnableLambda + JsonOutputParser
        │   │       └── RunnableLambda
        │   └── RunnableWithFallbacks
        └── CHAIN RunnableSequence                    ← window 2
            ├── ChatPromptTemplate
            ├── RunnableParallel<raw>
            │   └── GENERATION ChatOpenAI  21,666 tok ← call 2 (window 2)
            ├── RunnableWithFallbacks
            └── RunnableAssign<parsed,parsing_error>
                └── RunnableParallel<parsed,parsing_error>
                    ├── RunnableSequence → RunnableLambda + JsonOutputParser
                    └── RunnableLambda
```

What this means:

- **Each `CHAIN RunnableSequence` subtree = one window.** The chunk header
  ("EXTRACTION CHUNK 1 OF 2 — …") appears in that subtree's prompt messages.
- **The merge happens outside the graph.** The union-with-dedupe / first
  non-null scalar / max-confidence logic runs in `extract_chunked` *after*
  the last window — you will not see a "merge" node; the merged result is
  what the `contracts_specialist` span's output holds.
- **A failed chunk does not abort.** If a window's call raises or fails to
  parse, its subtree shows an error but the surviving chunks still merge —
  the `n_chunks`/`failed` counts are in the span output.
- **Node counts scale with windows:** 1 window → 13 observations (+ trace
  root); 2 windows → 24; 4 windows → ~46 (the v18 run's histogram: 40 docs
  with 1 generation, 7 with 2, 3 with 4).

## How to read a graph fast

1. **Collapse to generations.** Use the filter/list view, type `GENERATION`:
   every node is one model call with its tokens and latency — that is the
   whole cost story.
2. **Look for the agent span's output, not the runnable tree.** Click
   `contracts_specialist` (or `sorter`, `judge` in chained traces) — the
   per-agent task scores and the merged output are attached there.
3. **Prompt verification.** Open any `ChatPromptTemplate` node to confirm
   which prompt version, chunk header, and handoff context actually reached
   the model.
4. **Errors.** Exceptions surface on the `GENERATION` or the
   `RunnableLambda` error-capture node (and on the agent span when the chunk
   is skipped) — everything else staying at 0ms/0 tok is normal.
5. **Chained runs.** In `run_langfuse_chained_eval.py` traces you get
   sibling agent spans (`sorter` then `contracts_specialist`), each with its
   own subtree — same reading rules, one subtree per agent call.

## Repo references

- `src/langfuse_tracing.py` — trace/span/score lifecycle (`trace_document`,
  `agent_observation`, per-agent task scores)
- `agents/base_agent.py:230` (`_call_structured`) — the
  `prompt | with_structured_output(..., include_raw=True)` chain whose
  expansion produces the runnable tree
- `agents/specialist_agents.py:178` (`extract_chunked`) — windowing,
  per-window invocation, merge semantics
- `scripts/eval/run_langfuse_extraction_eval.py` — the runner that opens the
  per-document trace (`--chunked --chunk-chars 90000 --chunk-overlap 8000`)
- See [Architecture](Architecture) for the data flow, [Scoring](Scoring) for
  what the task scores mean, and [Eval-Runners](Eval-Runners) for the
  Langfuse mirror commands. Low-performing / failed traces are enqueued for
  human review via [Annotation-Queues](Annotation-Queues).
