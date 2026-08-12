# `agents/` — the LangChain agents under test

| Agent | File | Role |
|---|---|---|
| `BaseAgent` | `base_agent.py` | ChatOpenAI (OpenRouter) + `with_structured_output` + vision + head/tail truncation + `_last_usage` + retry contract |
| `SorterAgent` | `sorter_agent.py` | doc-type + contract-subtype classification (text + image); `DOC_CLASSES`, `CONTRACT_SUBTYPES`, `SUBTYPE_EQUIVALENCES`, `classify_json(subtype_focus=)` |
| specialists | `specialist_agents.py` | per-class field extraction with shared JSON schemas; `handoff_context` (the sorter's subtype cue) prepended in `extract()` |
| `JudgeAgent` | `judge_agent.py` | LLM-as-a-judge: `judge_classification`, `judge_extraction_correctness`, `judge_completeness` |

The agents are the unit under test: prompt version = experiment identity.
When a prompt changes, it needs a NEW version key in `src/prompts.py` —
never mutate a string after it has run. The eval-validated versions are
vendored byte-for-byte into llm-mailroom's `langchain_agents/` (verified
against this repo's commit `3a03d5c`).
