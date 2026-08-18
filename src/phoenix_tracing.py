"""Arize Phoenix tracing — local OpenTelemetry-native default.

Phoenix is Apache/Elastic-licensed, runs as a single local process with SQLite/
in-memory storage, and is OpenTelemetry-native. It ingests spans as they are
produced with no Docker/multi-service stack, and the DB file can be deleted
when a batch is done — ideal for pour-in, poke-around, discard workflows.

Design
------
- One OpenTelemetry TracerProvider is lazily initialised per process.
- The provider emits spans over OTLP HTTP to the Phoenix endpoint
  (``PHOENIX_ENDPOINT``, default ``http://localhost:6006/v1/traces``).
- ``trace_document`` opens a ROOT span per evaluated document (name =
  ``trace_name``) carrying session id, tags, filename, expected value and the
  caller's metadata as span attributes; ``agent_observation`` opens a child
  span under it. Outputs and deterministic logic scores are recorded on the
  spans as events (``set_output`` / ``score``), so Phoenix holds the SAME
  per-document data shape the Langfuse mirror records.
- Best-effort ``OpenAIInstrumentor`` (openinference-instrumentation-openai,
  already a dependency) instruments the OpenAI SDK used by the LangChain
  agents, so every LLM call lands as a nested span with the full prompt,
  response and token usage — captured under the agent span via context
  propagation. Instrumentation failure only degrades to manual spans; it
  never breaks a run.
- The tracer is a no-op when PHOENIX_TRACING is disabled or when provider
  initialisation failed — evaluation runs identically without observability.
- ``flush()``/``shutdown()`` force-flush the batch processor WITHOUT shutting
  the provider down (a shutdown would permanently disable the process's
  tracer); batch spans are exported on flush or on a later exit.
"""

from __future__ import annotations

import json
import os
import structlog
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = structlog.get_logger(__name__)

_TRUE_VALUES = {"1", "true", "enabled", "yes", "on"}


def phoenix_enabled() -> bool:
    """Return True when Phoenix tracing should be active.

    Reads PHOENIX_TRACING (default: enabled). When disabled the module
    degrades to a no-op tracer so runs are unaffected.
    """
    return os.environ.get("PHOENIX_TRACING", "enabled").strip().lower() in _TRUE_VALUES


def _instrument_openai() -> None:
    """Best-effort OpenInference instrumentation of the OpenAI SDK.

    The LangChain agents call OpenRouter through langchain-openai, which uses
    the OpenAI SDK under the hood; instrumenting it emits one span per LLM
    call (model, token usage, latency, output) nested under the current agent
    span. ``hide_input_text`` drops the FULL request payload from the spans —
    the ContractEval contexts run up to 300k chars each and would otherwise
    balloon the local Phoenix SQLite DB; the bounded question/output/scores
    stay on the manual document + agent spans.
    """
    try:
        from openinference.instrumentation import TraceConfig
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument(config=TraceConfig(hide_input_text=True))
        logger.info("phoenix_openai_instrumented")
    except Exception:  # noqa: BLE001 - observability must never break the run
        logger.warning("phoenix_openai_instrument_failed", exc_info=True)


def _init_opentelemetry() -> Any | None:
    """Initialise OpenTelemetry SDK with Phoenix OTLP exporter.

    Returns the tracer provider or None on failure / disabled.
    """
    if not phoenix_enabled():
        logger.info("phoenix_tracing_disabled", reason="PHOENIX_TRACING not enabled")
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        endpoint = os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
        service_name = os.environ.get("PHOENIX_SERVICE_NAME", "llm-entity-extraction")
        resource = Resource.create({"service.name": service_name})

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("phoenix_tracing_initialized", endpoint=endpoint, service=service_name)
        _instrument_openai()
        return provider
    except Exception:  # noqa: BLE001
        logger.warning("phoenix_tracing_init_failed", exc_info=True)
        return None


# Initialise once per process
_provider = _init_opentelemetry()

_TRACER_NAME = "llm-entity-extraction"


def _tracer() -> Any | None:
    """Return the module's OTel tracer, or None when tracing is disabled."""
    if _provider is None:
        return None
    try:
        from opentelemetry import trace

        return trace.get_tracer(_TRACER_NAME)
    except Exception:  # noqa: BLE001
        return None


def _set_attributes(span: Any, attributes: dict[str, Any]) -> None:
    """Set span attributes from a dict, skipping unusable values."""
    for key, value in attributes.items():
        if value is None:
            continue
        try:
            span.set_attribute(key, value)
        except Exception:  # noqa: BLE001 - one bad attribute must not kill the span
            logger.warning("phoenix_attribute_failed", key=key, exc_info=True)


def _annotation_attributes(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten collected scores into OpenInference ``annotations.*`` attributes.

    Phoenix ingests feedback attached via the flattened ``annotations``
    semantic convention (``annotations.{index}.{field}`` — name/score/label/
    annotator_kind/explanation) and renders them as span annotations, so each
    scored entry is filterable as correct/incorrect in the Phoenix UI.
    """
    attributes: dict[str, Any] = {}
    for index, annotation in enumerate(annotations):
        prefix = f"annotations.{index}"
        for key, value in annotation.items():
            if value is None:
                continue
            attributes[f"{prefix}.{key}"] = value
    return attributes


@dataclass
class TraceHandle:
    """Document-level span handle (name = the tracer's trace_name)."""

    trace_id: str
    disabled: bool = True
    handler: Any | None = None
    _span: Any = None
    _annotations: list[dict[str, Any]] = field(default_factory=list)

    def set_output(self, output: Any) -> None:
        """Record the document's composite output as a span event."""
        if self.disabled or self._span is None:
            return
        try:
            self._span.add_event(
                "output",
                {"payload": json.dumps(output, default=str)[:200_000]},
            )
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_output_event_failed", trace_id=self.trace_id)

    def score(self, name: str, value: float, comment: str = "",
              observation_id: str | None = None) -> None:
        """Record one deterministic logic score as a span event + annotation."""
        if self.disabled or self._span is None:
            return
        try:
            self._span.add_event("score", {
                "name": name, "value": str(value), "comment": comment,
            })
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_score_event_failed", trace_id=self.trace_id, name=name)
        self._annotations.append({
            "name": name,
            "score": float(value),
            "label": "correct" if value >= 0.5 else "incorrect",
            "annotator_kind": "CODE",
            "explanation": comment,
        })


@dataclass
class AgentHandle:
    """Agent-level span handle (nested under the document span)."""

    trace_id: str
    observation_id: str = ""
    disabled: bool = True
    handler: Any | None = None
    _span: Any = None
    _annotations: list[dict[str, Any]] = field(default_factory=list)

    def set_output(self, output: Any) -> None:
        """Record the agent's result as a span event."""
        if self.disabled or self._span is None:
            return
        try:
            self._span.add_event(
                "output",
                {"payload": json.dumps(output, default=str)[:200_000]},
            )
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_agent_output_failed", trace_id=self.trace_id)

    def score(self, name: str, value: float, comment: str = "") -> None:
        """Record one deterministic logic score as a span event + annotation."""
        if self.disabled or self._span is None:
            return
        try:
            self._span.add_event("score", {
                "name": name, "value": str(value), "comment": comment,
            })
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_agent_score_failed",
                           trace_id=self.trace_id, name=name)
        self._annotations.append({
            "name": name,
            "score": float(value),
            "label": "correct" if value >= 0.5 else "incorrect",
            "annotator_kind": "CODE",
            "explanation": comment,
        })


class PhoenixTracer:
    """Phoenix tracer mirroring the LangfuseTracer API surface.

    ``trace_document`` opens a ROOT span per document; ``agent_observation``
    opens a child span under it. Outputs and scores are recorded as span
    events; the OpenAI SDK instrumentation adds nested LLM-call spans.
    """

    def __init__(self, session_id: str = "", tags: list[str] | None = None,
                 trace_name: str = "evaluation"):
        self.session_id = session_id or os.environ.get("PHOENIX_SESSION", "default")
        self.tags = tags or []
        self.trace_name = trace_name
        self.disabled = not phoenix_enabled() or _provider is None

    def flush(self) -> None:
        """Force-export buffered spans without disabling the provider."""
        if self.disabled or _provider is None:
            return
        try:
            _provider.force_flush()
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_flush_failed")

    def shutdown(self) -> None:
        """Final flush before the process exits (provider stays reusable)."""
        self.flush()

    @contextmanager
    def trace_document(self, filename: str, expected: Any = None,
                       metadata: dict | None = None) -> Iterator[TraceHandle]:
        """Open a document-level ROOT span; yields its :class:`TraceHandle`.

        The span carries session id, tags, filename, expected value and the
        caller's metadata as attributes (question, category, prompt version,
        model, ...), so Phoenix holds the same per-document data shape as the
        Langfuse mirror.
        """
        trace_id = f"phoenix-{self.session_id}-{filename}"
        handle = TraceHandle(trace_id=trace_id, disabled=True)
        otel_tracer = _tracer()
        if self.disabled or otel_tracer is None:
            yield handle
            return
        attributes: dict[str, Any] = {
            "session_id": self.session_id,
            "tags": ",".join(self.tags),
            "filename": filename,
            "expected": expected,
        }
        for key, value in (metadata or {}).items():
            attributes[key] = value
        with otel_tracer.start_as_current_span(self.trace_name,
                                               attributes=attributes) as span:
            handle = TraceHandle(trace_id=trace_id, disabled=False, _span=span)
            try:
                yield handle
            finally:
                _set_attributes(span, _annotation_attributes(handle._annotations))
                # The start_as_current_span context manager ends the span.
                pass

    @contextmanager
    def agent_observation(self, agent_name: str,
                          metadata: dict | None = None) -> Iterator[AgentHandle]:
        """Open an agent-level span NESTED under the current document span.

        Must be called INSIDE a :meth:`trace_document` block — the span is a
        child of the current span via OTel context propagation, and the
        instrumented OpenAI SDK call nests under it in turn.
        """
        handle = AgentHandle(trace_id="", disabled=True)
        otel_tracer = _tracer()
        if self.disabled or otel_tracer is None:
            yield handle
            return
        attributes: dict[str, Any] = {"agent": agent_name}
        for key, value in (metadata or {}).items():
            attributes[key] = value
        with otel_tracer.start_as_current_span(agent_name,
                                               attributes=attributes) as span:
            handle = AgentHandle(trace_id="", observation_id=getattr(span, "context", None),
                                 disabled=False, _span=span)
            try:
                yield handle
            finally:
                _set_attributes(span, _annotation_attributes(handle._annotations))
                # The start_as_current_span context manager ends the span.
                pass


def init_phoenix_tracing(service_name: str | None = None, endpoint: str | None = None) -> None:
    """Explicit initialisation helper for scripts that want to control startup.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _provider
    if _provider is not None:
        return
    if service_name:
        os.environ["PHOENIX_SERVICE_NAME"] = service_name
    if endpoint:
        os.environ["PHOENIX_ENDPOINT"] = endpoint
    # Re-initialise
    _provider = _init_opentelemetry()