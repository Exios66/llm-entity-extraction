"""Shared eval-run tracer resolution: Langfuse PRIMARY, local Phoenix fallback.

The human directive (2026-08-16) flips the previous Phoenix-first default:
every ``run_langfuse_*_eval.py`` runner traces to **Langfuse** (the llm-dojo
project, keys in ``langfuse.env``) whenever its keys are configured, and
falls back to the **local Arize Phoenix server** (OpenTelemetry,
``http://localhost:6006/v1/traces``) when Langfuse is unavailable — never
silently untraced. The resolver returns the tracer plus the backend label and
tracing metadata that land in the experiment-log record, so every runner
reports the same shape.

``prefer="phoenix"`` preserves the pre-directive order for callers that
explicitly opt into the local-first behavior (none of the langfuse runners
use it today).
"""

from __future__ import annotations

import os
from dataclasses import replace

from src.langfuse_config import load_langfuse_config
from src.langfuse_tracing import LangfuseTracer
from src.phoenix_tracing import PhoenixTracer

LANGFUSE_BACKEND = "langfuse"
PHOENIX_BACKEND = "phoenix"


def resolve_tracer(
    session_id: str,
    trace_name: str,
    tags: list[str] | None = None,
    *,
    prefer: str = LANGFUSE_BACKEND,
    lf_project: str | None = None,
    lf_environment: str | None = None,
) -> tuple[object, str, dict]:
    """Resolve the eval-run tracer: Langfuse primary, local Phoenix fallback.

    Args:
        session_id: The experiment/session name (traces group under it).
        trace_name: Per-document trace name (e.g. "docclass_classification").
        tags: Trace tags (prompt version + model slug).
        prefer: "langfuse" (default — Langfuse first, Phoenix fallback) or
            "phoenix" (the pre-directive local-first order).
        lf_project / lf_environment: Langfuse overrides (--lf-* flags).

    Returns:
        ``(tracer, tracing_backend, tracing_meta)`` where ``tracing_meta`` is
        the record-shaped dict for the experiment log (endpoint/service for
        Phoenix; project/environment/base_url for Langfuse; both carry
        session_id + trace_name + disabled).
    """
    if prefer == LANGFUSE_BACKEND:
        lf_config = load_langfuse_config()
        if lf_project:
            lf_config = replace(lf_config, project=lf_project)
        if lf_environment:
            lf_config = replace(lf_config, environment=lf_environment)
        lf_tracer = LangfuseTracer(
            config=lf_config,
            session_id=session_id,
            tags=tags,
            trace_name=trace_name,
        )
        if not lf_tracer.disabled:
            return (
                lf_tracer,
                LANGFUSE_BACKEND,
                {
                    "project": lf_config.project,
                    "environment": lf_config.environment,
                    "base_url": lf_config.base_url,
                    "session_id": session_id,
                    "trace_name": trace_name,
                    "disabled": False,
                },
            )
        # Langfuse unavailable -> local Phoenix server fallback.
        phoenix_tracer = PhoenixTracer(session_id=session_id, tags=tags,
                                       trace_name=trace_name)
        return (
            phoenix_tracer,
            PHOENIX_BACKEND,
            {
                "endpoint": os.environ.get(
                    "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
                "service_name": os.environ.get(
                    "PHOENIX_SERVICE_NAME", "llm-entity-extraction"),
                "session_id": session_id,
                "trace_name": trace_name,
                "disabled": phoenix_tracer.disabled,
            },
        )

    # prefer="phoenix": local-first order (pre-directive behavior).
    phoenix_tracer = PhoenixTracer(session_id=session_id, tags=tags,
                                   trace_name=trace_name)
    if not phoenix_tracer.disabled:
        return (
            phoenix_tracer,
            PHOENIX_BACKEND,
            {
                "endpoint": os.environ.get(
                    "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
                "service_name": os.environ.get(
                    "PHOENIX_SERVICE_NAME", "llm-entity-extraction"),
                "session_id": session_id,
                "trace_name": trace_name,
                "disabled": False,
            },
        )
    lf_config = load_langfuse_config()
    if lf_project:
        lf_config = replace(lf_config, project=lf_project)
    if lf_environment:
        lf_config = replace(lf_config, environment=lf_environment)
    lf_tracer = LangfuseTracer(config=lf_config, session_id=session_id,
                               tags=tags, trace_name=trace_name)
    return (
        lf_tracer,
        LANGFUSE_BACKEND,
        {
            "project": lf_config.project,
            "environment": lf_config.environment,
            "base_url": lf_config.base_url,
            "session_id": session_id,
            "trace_name": trace_name,
            "disabled": lf_tracer.disabled,
        },
    )
