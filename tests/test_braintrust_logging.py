"""Run-sink gate: Braintrust logging defaults OFF, LangSmith flag passthrough.

The repo's primary run sink is Langfuse + LangSmith + the local experiment
log; Braintrust is read-only (dataset hosting) and its experiment/span logging
is opt-in via ``BRAINTRUST_LOGGING=enabled`` so runs never consume the
Braintrust plan's scored-run / log-byte quota.
"""

from __future__ import annotations

from src.braintrust_logging import braintrust_logging_enabled, langsmith_enabled


def test_braintrust_logging_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("BRAINTRUST_LOGGING", raising=False)
    assert braintrust_logging_enabled() is False


def test_braintrust_logging_enabled_values(monkeypatch):
    for value in ("enabled", "true", "1", "yes", "on", "TRUE", " Enabled "):
        monkeypatch.setenv("BRAINTRUST_LOGGING", value)
        assert braintrust_logging_enabled() is True, value


def test_braintrust_logging_disabled_values(monkeypatch):
    for value in ("disabled", "false", "0", "no", "off", ""):
        monkeypatch.setenv("BRAINTRUST_LOGGING", value)
        assert braintrust_logging_enabled() is False, value


def test_langsmith_enabled_defaults_to_false(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert langsmith_enabled() is False


def test_langsmith_enabled_true(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert langsmith_enabled() is True
