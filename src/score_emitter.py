"""Score-emitter bridge — connects pipeline runs to the KANBAN-061 registry
layer (llm-dojo-scoring v0.5.0 ``registry`` / ``bundles`` / ``emitter`` /
``pruning``).

Thin by design: the package owns definitions, routing, and storage. This
module only adapts THIS repo's run records to the unified emitter:

- ``build_emitter()`` — local JSONL manifest sink (``reports/scores_manifest.jsonl``)
  plus an optional Langfuse sink (only when ``langfuse=True`` AND credentials
  resolve; otherwise the sink is inert — never fatal).
- ``emit_run_scores()`` — emit a dict of computed metric values for one
  agent/run; registry-unknown names are skipped (returned, never silently
  dropped) so new KPIs surface as registry work, not lost scores.
- ``dashboard_names()`` / ``headline_names()`` — what a dashboard panel for
  an agent shows (tier-capped bundle intersection).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_dojo_scoring.emitter import Emitter, LangfuseSink, LocalManifestSink
from llm_dojo_scoring.pruning import dashboard_metrics, headline_metrics

from src.env_utils import load_env

__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "build_emitter",
    "emit_run_scores",
    "dashboard_names",
    "headline_names",
]

DEFAULT_MANIFEST_PATH = Path("reports/scores_manifest.jsonl")


def build_emitter(
    manifest_path: str | Path | None = None,
    *,
    langfuse: bool = False,
) -> Emitter:
    """Emitter with a local manifest sink; optional Langfuse when asked for.

    ``langfuse=True`` still yields a working emitter when credentials are
    missing — the LangfuseSink simply reports itself unavailable.
    """
    load_env()
    sinks: list[Any] = [LocalManifestSink(manifest_path or DEFAULT_MANIFEST_PATH)]
    if langfuse:
        sinks.append(LangfuseSink())
    return Emitter(sinks=sinks)


def emit_run_scores(
    emitter: Emitter,
    agent: str,
    run_id: str,
    metrics: dict[str, Any],
    *,
    doc_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """Emit ``{metric_name: value}`` for one agent/run.

    Returns ``(emitted, skipped)`` — skipped names are either unknown to the
    registry (fail-fast philosophy stops at the emitter, not the pipeline)
    or ``None``-valued.
    """
    emitted: list[str] = []
    skipped: list[str] = []
    for name, value in metrics.items():
        try:
            emitter.registry.get(name)
        except KeyError:
            skipped.append(name)
            continue
        if value is None:
            skipped.append(name)
            continue
        emitter.emit_score(
            agent,
            doc_id=doc_id,
            metric_name=name,
            value=value,
            metadata=metadata or {},
            run_id=run_id,
        )
        emitted.append(name)
    return emitted, skipped


def dashboard_names(agent: str) -> list[str]:
    """Default dashboard panel for an agent (T0+T1 bundle intersection)."""
    return dashboard_metrics(agent)


def headline_names(agent: str) -> list[str]:
    """Strictly T0 — the one-number-per-agent view."""
    return headline_metrics(agent)
