"""Unit tests for the Langfuse tracing layer (no network, stubbed client).

Covers: config resolution, deterministic trace ids, graceful no-op when
Langfuse is disabled, per-document trace/score capture through a stub client,
and the BaseAgent callback forwarding that nests the LLM call under the trace.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest

from agents.sorter_agent import SORTER_SCHEMA, SorterAgent
from src.langfuse_config import load_langfuse_config
from src.langfuse_tracing import LangfuseTracer, deterministic_trace_id


# ---------------------------------------------------------------------------
# Stub Langfuse client
# ---------------------------------------------------------------------------


class StubSpan:
    """Mimics the span returned by ``start_as_current_observation``."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.updates = []
        self.id = "obs-span"

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class StubLangfuse:
    """Records every trace/score/flush call the tracer makes."""

    def __init__(self):
        self.spans = []
        self.scores = []
        self.flush_calls = 0
        self.shutdown_calls = 0
        self.current_trace_id = "0123456789abcdef0123456789abcdef"

    def start_as_current_observation(self, **kwargs):
        span = StubSpan(**kwargs)
        span.id = f"obs-{len(self.spans)}"
        self.spans.append(span)
        return span

    def create_score(self, **kwargs):
        self.scores.append(kwargs)

    def get_current_trace_id(self):
        return self.current_trace_id

    def flush(self):
        self.flush_calls += 1

    def shutdown(self):
        self.shutdown_calls += 1


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


@pytest.fixture
def stub_langfuse(monkeypatch):
    """Stub the Langfuse SDK so no client is ever constructed/contacted."""
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")
    return stub


@pytest.fixture
def lf_env(monkeypatch, tmp_path):
    """Deterministic Langfuse env for tests (repo langfuse.env never read)."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("LANGFUSE_PROJECT", "llm-mailroom-experiments")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "llm-mailroom-experiments")
    return tmp_path / "missing.env"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_config_from_env(lf_env):
    cfg = load_langfuse_config(lf_env)
    assert cfg.public_key == "pk-test"
    assert cfg.secret_key == "sk-test"
    assert cfg.base_url == "https://example.invalid"
    assert cfg.project == "llm-mailroom-experiments"
    assert cfg.environment == "llm-mailroom-experiments"


def test_config_missing_keys_disables_tracer(monkeypatch, tmp_path):
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(name, "")
    tracer = LangfuseTracer(config=load_langfuse_config(tmp_path / "missing.env"))
    assert tracer.disabled is True


# ---------------------------------------------------------------------------
# Trace ids
# ---------------------------------------------------------------------------


def test_deterministic_trace_id():
    tid = deterministic_trace_id("Monsanto - Agreement.pdf")
    # W3C trace id: 32 lowercase hex chars.
    assert len(tid) == 32
    assert all(c in "0123456789abcdef" for c in tid)
    assert tid == deterministic_trace_id("Monsanto - Agreement.pdf")
    assert tid != deterministic_trace_id("Other - Agreement.pdf")
    # Session scoping: the same document in DIFFERENT experiments gets a
    # DIFFERENT trace id (no cross-experiment observation merging), while the
    # same experiment stays stable across re-runs.
    assert deterministic_trace_id("doc_a.txt", "exp_1") == \
           deterministic_trace_id("doc_a.txt", "exp_1")
    assert deterministic_trace_id("doc_a.txt", "exp_1") != \
           deterministic_trace_id("doc_a.txt", "exp_2")


# ---------------------------------------------------------------------------
# Per-document tracing through the stub client
# ---------------------------------------------------------------------------


def test_trace_document_captures_output_and_scores(stub_langfuse, lf_env):
    tracer = LangfuseTracer(config=load_langfuse_config(lf_env), session_id="exp_1",
                            tags=["prompt:sorter_v5"])
    with tracer.trace_document("doc_a.txt", "license", {"prompt_version": "sorter_v5"}) as handle:
        assert not handle.disabled
        assert handle.handler == "stub-handler"
        handle.set_output({"sorter": {"doc_type": "contract"}})
        handle.score("exact_match", 1.0, comment="doc_type == contract")
        handle.score("subtype_accuracy", 0.0)

    span = stub_langfuse.spans[0]
    assert span.kwargs["as_type"] == "span"
    assert span.kwargs["name"] == "subtype_classification"
    assert span.kwargs["trace_context"]["trace_id"] == deterministic_trace_id("doc_a.txt", "exp_1")
    assert span.kwargs["input"]["filename"] == "doc_a.txt"
    assert span.kwargs["input"]["expected"] == "license"
    assert span.kwargs["input"]["prompt_version"] == "sorter_v5"
    assert span.updates[-1] == {"output": {"sorter": {"doc_type": "contract"}}}

    assert len(stub_langfuse.scores) == 2
    first = stub_langfuse.scores[0]
    assert first["trace_id"] == deterministic_trace_id("doc_a.txt", "exp_1")
    assert first["name"] == "exact_match"
    assert first["value"] == 1.0
    assert first["data_type"] == "NUMERIC"
    assert first["comment"] == "doc_type == contract"


def test_trace_document_graceful_noop_when_disabled(monkeypatch, tmp_path):
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(name, "")
    tracer = LangfuseTracer(config=load_langfuse_config(tmp_path / "missing.env"))
    with tracer.trace_document("doc_a.txt", "license") as handle:
        assert handle.disabled
        assert handle.handler is None
        handle.set_output({"sorter": {}})  # must not raise
        handle.score("exact_match", 1.0)  # must not raise
    tracer.flush()  # must not raise
    tracer.shutdown()  # must not raise


def test_trace_failure_degrades_to_noop(stub_langfuse, lf_env, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("client unavailable")

    monkeypatch.setattr("langfuse.langchain.CallbackHandler", boom)
    tracer = LangfuseTracer(config=load_langfuse_config(lf_env))
    with tracer.trace_document("doc_b.txt", "license") as handle:
        assert handle.disabled
        handle.score("exact_match", 1.0)  # no-op, no raise


def test_flush_and_shutdown(stub_langfuse, lf_env):
    tracer = LangfuseTracer(config=load_langfuse_config(lf_env))
    with tracer.trace_document("doc_c.txt", "license"):
        pass
    tracer.flush()
    tracer.shutdown()
    assert stub_langfuse.flush_calls == 1
    assert stub_langfuse.shutdown_calls == 1


# ---------------------------------------------------------------------------
# Per-agent observations (sorter / contracts_specialist designated tasks)
# ---------------------------------------------------------------------------


def test_agent_observation_nests_under_trace(stub_langfuse, lf_env):
    tracer = LangfuseTracer(config=load_langfuse_config(lf_env))
    with tracer.trace_document("doc_a.txt", "license") as trace_handle:
        with tracer.agent_observation("sorter", {"prompt_version": "sorter_v6"}) as agent:
            assert not agent.disabled
            assert agent.handler == "stub-handler"
            agent.set_output({"doc_type": "contract"})
            agent.score("subtype_accuracy", 1.0)
            trace_handle.set_output({"composite": True})

    # Root span + one nested agent span.
    assert len(stub_langfuse.spans) == 2
    agent_span = stub_langfuse.spans[1]
    assert agent_span.kwargs["name"] == "sorter"
    assert agent_span.kwargs["as_type"] == "span"
    assert agent_span.kwargs["metadata"]["agent"] == "sorter"
    assert agent_span.kwargs["metadata"]["prompt_version"] == "sorter_v6"
    assert agent_span.updates[-1] == {"output": {"doc_type": "contract"}}

    # The agent's task score attaches to the AGENT's observation id.
    score = stub_langfuse.scores[0]
    assert score["name"] == "subtype_accuracy"
    assert score["value"] == 1.0
    assert score["data_type"] == "NUMERIC"
    assert score["observation_id"] == agent_span.id
    assert score["trace_id"] == stub_langfuse.current_trace_id


def test_agent_observation_disabled_and_failure_are_noops(stub_langfuse, lf_env, monkeypatch):
    # Client failure inside the agent span degrades to a disabled handle.
    def boom(**kwargs):
        raise RuntimeError("client unavailable")

    monkeypatch.setattr("langfuse.langchain.CallbackHandler", boom)
    tracer = LangfuseTracer(config=load_langfuse_config(lf_env))
    with tracer.trace_document("doc_b.txt", "license"):
        with tracer.agent_observation("sorter", {}) as agent:
            assert agent.disabled
            agent.set_output({})  # must not raise
            agent.score("exact_match", 1.0)  # must not raise

    # Disabled tracer: agent observation is a pure no-op.
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.setenv(name, "")
    tracer2 = LangfuseTracer(config=load_langfuse_config(lf_env))
    assert tracer2.disabled is True
    with tracer2.trace_document("doc_c.txt", "license"):
        with tracer2.agent_observation("sorter", {}) as agent:
            assert agent.disabled
            agent.score("exact_match", 1.0)  # must not raise


# ---------------------------------------------------------------------------
# BaseAgent callback forwarding (LangChain handler -> agent call)
# ---------------------------------------------------------------------------


def test_structured_call_forwards_callbacks(mocker):
    """The agent's chain.invoke must receive the Langfuse handler in config."""
    import agents.base_agent as ba

    captured = {}

    class FakeChain:
        def invoke(self, payload, config=None):
            captured["config"] = config
            return {"raw": None, "parsed": {"doc_type": "contract"}, "parsing_error": None}

    class FakePrompt:
        @staticmethod
        def from_messages(messages):
            return FakePrompt()

        def __or__(self, other):
            return FakeChain()

    mocker.patch.object(ba.ChatPromptTemplate, "from_messages",
                        staticmethod(FakePrompt.from_messages))

    sorter = SorterAgent(prompt_version="sorter_v1", callbacks=["langfuse-handler"])
    result = sorter._call_structured("text", SORTER_SCHEMA)
    assert result["doc_type"] == "contract"
    assert captured["config"] == {"callbacks": ["langfuse-handler"]}

    plain = SorterAgent(prompt_version="sorter_v1")
    plain._call_structured("text", SORTER_SCHEMA)
    assert captured["config"] is None
