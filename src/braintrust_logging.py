"""Run-sink configuration: which observability backends are active.

The repo's default run sink is Langfuse (``run_langfuse_*_eval.py`` mirrors)
+ LangSmith (``LANGSMITH_TRACING`` env) + the local repo experiment log.
Braintrust is read-only — it still hosts the eval datasets (free) but
experiment/span logging is DISABLED by default so runs never consume the
Braintrust plan's scored-run / log-byte quota. Set ``BRAINTRUST_LOGGING=enabled``
to opt back into Braintrust experiment + span logging (e.g. a legacy manifest
resume or a one-off Braintrust-side A/B).
"""

from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "enabled", "yes", "on"}


def braintrust_logging_enabled() -> bool:
    """Return True when Braintrust experiment/span logging should run.

    Reads ``BRAINTRUST_LOGGING`` (default: ``disabled``). Braintrust datasets
    are always readable (``load_braintrust_dataset``) — this flag only gates
    the *sink*: ``setup_langchain`` and ``braintrust.Eval``.
    """
    return os.environ.get("BRAINTRUST_LOGGING", "disabled").strip().lower() in _TRUE_VALUES


def langsmith_enabled() -> bool:
    """Return True when LangChain LLM calls auto-trace to LangSmith.

    Reads ``LANGSMITH_TRACING`` (default: ``false``).
    """
    return os.environ.get("LANGSMITH_TRACING", "false").strip().lower() in _TRUE_VALUES
