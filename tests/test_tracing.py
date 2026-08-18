"""Unit tests for the shared tracer resolver (src/tracing.py).

Langfuse PRIMARY with the local Phoenix server as fallback (human
directive 2026-08-16): no network — the Langfuse client and Phoenix tracer
are stubbed; only the selection order + record metadata are exercised.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def fake_clients(monkeypatch):
    """Stub Langfuse + Phoenix tracers so the resolver runs without a network
    (the Langfuse client itself is constructed lazily inside LangfuseTracer,
    which is replaced wholesale)."""

    class FakeTracer:
        def __init__(self, session_id="", tags=None, trace_name="evaluation", **kwargs):
            self.session_id = session_id
            self.tags = tags or []
            self.trace_name = trace_name
            # Mirror LangfuseTracer's disabled semantics ONLY when constructed
            # with a Langfuse config (the resolver's Phoenix fallback branch
            # constructs PhoenixTracer WITHOUT config -> enabled by default).
            config = kwargs.get("config")
            if config is not None:
                self.disabled = not bool(
                    config.public_key and config.secret_key and config.base_url
                )
            else:
                self.disabled = False

        def flush(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr("src.tracing.PhoenixTracer", FakeTracer)
    monkeypatch.setattr("src.tracing.LangfuseTracer", FakeTracer)
    return FakeTracer


def test_resolve_tracer_langfuse_primary_when_keys_present(fake_clients, monkeypatch):
    """With Langfuse keys configured, the resolver picks Langfuse (the
    directive's primary sink), not the local Phoenix server."""
    from src.tracing import LANGFUSE_BACKEND, resolve_tracer

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-fake")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-fake")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_PROJECT", "llm-dojo")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "llm-dojo")

    tracer, backend, meta = resolve_tracer("exp_test", "docclass_classification",
                                           tags=["prompt:sorter_docclass_v3", "qwen"])
    assert backend == LANGFUSE_BACKEND
    assert meta["project"] == "llm-dojo"
    assert meta["session_id"] == "exp_test"
    assert meta["disabled"] is False


def test_resolve_tracer_phoenix_fallback_when_langfuse_missing(fake_clients, monkeypatch):
    """No Langfuse keys -> the LOCAL Phoenix server is the fallback sink."""
    from src.langfuse_config import LangfuseConfig
    from src.tracing import PHOENIX_BACKEND, resolve_tracer

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    # The loader reads langfuse.env (file) too — stub it so the test is
    # independent of any locally-configured key file.
    monkeypatch.setattr(
        "src.tracing.load_langfuse_config",
        lambda env_file=None: LangfuseConfig(
            base_url="https://us.cloud.langfuse.com",
            public_key="", secret_key="", project="llm-dojo", environment="llm-dojo"),
    )

    tracer, backend, meta = resolve_tracer("exp_test", "docclass_classification")
    assert backend == PHOENIX_BACKEND
    assert meta["endpoint"]  # local server endpoint
    assert meta["session_id"] == "exp_test"
    assert meta["disabled"] is False


def test_resolve_tracer_prefer_phoenix_preserves_old_order(fake_clients, monkeypatch):
    """prefer='phoenix' keeps the pre-directive local-first order for callers
    that explicitly opt in."""
    from src.tracing import PHOENIX_BACKEND, resolve_tracer

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-fake")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-fake")

    tracer, backend, meta = resolve_tracer("exp_test", "t", prefer="phoenix")
    assert backend == PHOENIX_BACKEND
