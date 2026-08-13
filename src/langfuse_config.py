"""Shared Langfuse environment configuration loader.

Reads the Langfuse host/project/keys from ``langfuse.env`` (the dedicated
gitignored file for the SEPARATE prompt-experiment environment — never the
primary project's keys), falling back to ``.env`` and real shell environment
variables (shell wins, matching ``braintrust_config`` semantics).

Every mirror eval runner (``scripts/eval/run_langfuse_*_eval.py``) calls
:func:`load_langfuse_config` so the host/project/environment can be adjusted
in one place; command-line flags still override per run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://us.cloud.langfuse.com"
# The prompt-iteration experiment environment: ALL eval runs trace to
# llm-dojo (the keys in langfuse.env route there; the label below rides on
# every trace). Other projects (e.g. the primary llm-mailroom environment)
# stay reachable by passing --env-file with that project's keys to
# scripts/eval/sync_langfuse_prompts.py — prompt iterations are synced
# between projects by that script, never by re-pointing the experiment
# traces.
DEFAULT_PROJECT = "llm-dojo"
DEFAULT_ENVIRONMENT = "llm-dojo"


@dataclass(frozen=True)
class LangfuseConfig:
    """Resolved Langfuse configuration for the current environment."""

    base_url: str
    public_key: str
    secret_key: str
    project: str
    environment: str


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
    except ImportError:
        pass


def load_langfuse_config(env_file: str | Path = "langfuse.env") -> LangfuseConfig:
    """Load and resolve the Langfuse configuration (separate experiment env).

    Reads ``langfuse.env`` first, then ``.env`` (like ``env_utils.load_env``);
    existing shell environment variables always win. A missing ``langfuse.env``
    is fine — the tracer degrades to a no-op unless keys are present.
    """
    env_file = Path(env_file)
    if env_file.exists():
        _load_dotenv(env_file)
    _load_dotenv(Path(".env"))

    def get(name: str, default: str = "") -> str:
        value = os.environ.get(name)
        return value if value not in (None, "") else default

    base_url = get("LANGFUSE_BASE_URL") or get("LANGFUSE_HOST", DEFAULT_BASE_URL)
    return LangfuseConfig(
        base_url=base_url.rstrip("/"),
        public_key=get("LANGFUSE_PUBLIC_KEY"),
        secret_key=get("LANGFUSE_SECRET_KEY"),
        project=get("LANGFUSE_PROJECT", DEFAULT_PROJECT),
        environment=get("LANGFUSE_ENVIRONMENT", DEFAULT_ENVIRONMENT),
    )
