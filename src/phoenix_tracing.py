"""Arize Phoenix tracing — local OpenTelemetry-native default.

Phoenix is Apache/Elastic-licensed, runs as a single local process with SQLite/
in-memory storage, and is OpenTelemetry-native. It ingests spans as they are
produced with no Docker/multi-service stack, and the DB file can be deleted
when a batch is done — ideal for pour-in, poke-around, discard workflows.

Design
------
- One OpenTelemetry TracerProvider is lazily initialised per process.
- LangChain's OpenTelemetry integration emits spans for LLM calls, which
  Phoenix ingests via OTLP HTTP.
- The tracer is a no-op when PHOENIX_TRACING is disabled or when the
  environment variable PHOENIX_ENABLED is false — evaluation runs identically
  without observability overhead.
- The module exposes a simple ``init_phoenix_tracing`` helper and a
  ``PhoenixTracer`` context manager that mirrors the Langfuse API surface
  (trace_document / agent_observation) for minimal code churn in eval runners.
- Default endpoint: http://localhost:6006/v1/traces (Phoenix's OTLP HTTP
  receiver). Override with PHOENIX_ENDPOINT.
- Default project / session tagging via PHOENIX_PROJECT / PHOENIX_SESSION.
"""

from __future__ import annotations

import os
import structlog
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

logger = structlog.get_logger(__name__)

_TRUE_VALUES = {"1", "true", "enabled", "yes", "on"}

def phoenix_enabled() -> bool:
    """Return True when Phoenix tracing should be active.

    Reads PHOENIX_TRACING (default: enabled). When disabled the module
    degrades to a no-op tracer so runs are unaffected.
    """
    return os.environ.get("PHOENIX_TRACING", "enabled").strip().lower() in _TRUE_VALUES


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
        return provider
    except Exception:  # noqa: BLE001
        logger.warning("phoenix_tracing_init_failed", exc_info=True)
        return None


# Initialise once per process
_provider = _init_opentelemetry()


@dataclass
class TraceHandle:
    """Minimal handle compatible with LangfuseTracer interface.

    In Phoenix mode the handle is a no-op for scoring/output attachment —
    spans are emitted by LangChain's OpenTelemetry instrumentation.
    """
    trace_id: str
    disabled: bool = True
    handler: Any | None = None

    def set_output(self, output: Any) -> None:
        return

    def score(self, name: str, value: float, comment: str = "", observation_id: str | None = None) -> None:
        return


@dataclass
class AgentHandle:
    trace_id: str
    observation_id: str = ""
    disabled: bool = True
    handler: Any | None = None

    def set_output(self, output: Any) -> None:
        return

    def score(self, name: str, value: float, comment: str = "") -> None:
        return


class PhoenixTracer:
    """Lightweight Phoenix tracer that mirrors LangfuseTracer API.

    Real span emission is handled by OpenTelemetry instrumentation; this
    class provides the context-manager API used by eval runners so they can
    run with Phoenix as the default backend without code changes.
    """

    def __init__(self, session_id: str = "", tags: list[str] | None = None, trace_name: str = "evaluation"):
        self.session_id = session_id or os.environ.get("PHOENIX_SESSION", "default")
        self.tags = tags or []
        self.trace_name = trace_name
        self.disabled = not phoenix_enabled() or _provider is None

    def flush(self) -> None:
        if self.disabled or _provider is None:
            return
        try:
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            # Force flush via service shutdown
            _provider.shutdown()
        except Exception:  # noqa: BLE001
            logger.warning("phoenix_flush_failed")

    def shutdown(self) -> None:
        self.flush()

    @contextmanager
    def trace_document(self, filename: str, expected: Any = None, metadata: dict | None = None) -> Iterator[TraceHandle]:
        """Open a document-level tracing scope.

        Phoenix spans are generated automatically by LangChain instrumentation;
        this context manager only provides a compatible handle.
        """
        trace_id = f"phoenix-{self.session_id}-{filename}"
        handle = TraceHandle(trace_id=trace_id, disabled=self.disabled)
        try:
            yield handle
        finally:
            pass

    @contextmanager
    def agent_observation(self, agent_name: str, metadata: dict | None = None) -> Iterator[AgentHandle]:
        """Open an agent-level tracing scope.

        No-op beyond API compatibility; OpenTelemetry creates spans for the
        LLM calls automatically.
        """
        handle = AgentHandle(trace_id="", disabled=self.disabled)
        try:
            yield handle
        finally:
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
