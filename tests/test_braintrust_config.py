"""Tests for Braintrust config loading (env-only, no network)."""

from src.braintrust_config import (
    BraintrustConfig,
    load_agent_config,
    load_braintrust_config,
)


def test_load_braintrust_config_from_env():
    cfg = load_braintrust_config(env_file="/nonexistent/env/file")
    assert isinstance(cfg, BraintrustConfig)
    assert cfg.org_id == "org-test-0000"
    assert cfg.project_id == "proj-test-0000"
    assert cfg.project_name == "mailroom-eval-test"
    assert cfg.dataset_project == "mailroom-eval-test"
    assert cfg.model == "qwen/qwen3.7-flash"
    assert cfg.api_key == "sk-test-braintrust-fake-key"


def test_load_braintrust_config_defaults():
    import os

    cfg = load_braintrust_config(env_file="/nonexistent/env/file")
    assert cfg.api_base == "https://api.braintrust.dev"
    assert cfg.escalation_model == ""


def test_agent_config_falls_back_to_main():
    import os

    os.environ.pop("AGENT_BRAINTRUST_API_KEY", None)
    cfg = load_agent_config(env_file="/nonexistent/env/file")
    assert cfg.org_id == "org-test-0000"
    assert cfg.project_id == "proj-test-0000"
    assert cfg.api_key == ""


def test_agent_config_overrides(monkeypatch):
    monkeypatch.setenv("AGENT_BRAINTRUST_API_KEY", "sk-agent-key")
    monkeypatch.setenv("AGENT_BRAINTRUST_ORG_ID", "org-agent")
    cfg = load_agent_config(env_file="/nonexistent/env/file")
    assert cfg.api_key == "sk-agent-key"
    assert cfg.org_id == "org-agent"
    assert cfg.project_id == "proj-test-0000"  # not overridden -> falls back
