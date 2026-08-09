"""Shared Braintrust environment configuration loader.

Reads the Braintrust org/project/dataset/experiment configuration from
``braintrust.env`` (the single source of truth for the mailroom-eval experiments),
falling back to ``.env`` for any variable the file does not set.

Every experiment/report/dataset script in ``scripts/`` calls
:func:`load_braintrust_config` so org/project/dataset/model can be adjusted in
one place. Command-line flags in the individual scripts still override the
config values per run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ORG_ID = "b0eea81a-56db-4be2-91a9-bbe17ab6d648"
DEFAULT_PROJECT_NAME = "mailroom-eval"
DEFAULT_PROJECT_ID = "02fb28b9-60e2-40b6-a68a-b72ee0b237ad"
DEFAULT_DATASET_PROJECT = "mailroom-eval"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
DEFAULT_API_BASE = "https://api.braintrust.dev"


@dataclass(frozen=True)
class BraintrustConfig:
    """Resolved Braintrust configuration for the current environment."""

    org_id: str
    project_id: str
    project_name: str
    dataset_project: str
    model: str
    api_base: str
    escalation_model: str = ""
    api_key: str = ""
    data_api_key: str = ""


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
    except ImportError:
        pass


def _resolve(env_file: str | Path) -> dict:
    """Load braintrust.env (if present) then .env and return resolved values."""
    env_file = Path(env_file)
    if env_file.exists():
        _load_dotenv(env_file)
    _load_dotenv(Path(".env"))

    def get(name: str, default: str) -> str:
        value = os.environ.get(name)
        return value if value not in (None, "") else default

    return {
        "org_id": get("BRAINTRUST_ORG_ID", DEFAULT_ORG_ID),
        "project_id": get("BRAINTRUST_PROJECT_ID", DEFAULT_PROJECT_ID),
        "project_name": get("BRAINTRUST_PROJECT_NAME", DEFAULT_PROJECT_NAME),
        "dataset_project": get("BRAINTRUST_DATASET_PROJECT", DEFAULT_DATASET_PROJECT),
        "model": get("BRAINTRUST_MODEL", DEFAULT_MODEL),
        "api_base": get("BRAINTRUST_API_BASE", DEFAULT_API_BASE),
        "escalation_model": get("BRAINTRUST_ESCALATION_MODEL", ""),
        "api_key": get("BRAINTRUST_API_KEY", ""),
        "data_api_key": get("DATA_BRAINTRUST_KEY", ""),
    }


def load_braintrust_config(env_file: str | Path = "braintrust.env") -> BraintrustConfig:
    """Load and resolve the Braintrust configuration (main account)."""
    return BraintrustConfig(**_resolve(env_file))


def load_agent_config(env_file: str | Path = "braintrust.env") -> BraintrustConfig:
    """Load and resolve the **agent** Braintrust account configuration.

    Reads AGENT_BRAINTRUST_API_KEY plus optional AGENT_BRAINTRUST_* overrides.
    Every field not explicitly overridden falls back to the main account's
    resolved value.
    """
    base = _resolve(env_file)

    def get(name: str, default: str) -> str:
        value = os.environ.get(name)
        return value if value not in (None, "") else default

    return BraintrustConfig(
        org_id=get("AGENT_BRAINTRUST_ORG_ID", base["org_id"]),
        project_id=get("AGENT_BRAINTRUST_PROJECT_ID", base["project_id"]),
        project_name=get("AGENT_BRAINTRUST_PROJECT_NAME", base["project_name"]),
        dataset_project=get("AGENT_BRAINTRUST_DATASET_PROJECT", base["dataset_project"]),
        model=base["model"],
        api_base=get("AGENT_BRAINTRUST_API_BASE", base["api_base"]),
        escalation_model=get("AGENT_BRAINTRUST_ESCALATION_MODEL", base["escalation_model"]),
        api_key=get("AGENT_BRAINTRUST_API_KEY", ""),
        data_api_key=base["data_api_key"],
    )
