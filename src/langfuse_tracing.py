"""Langfuse tracing for the prompt-iterative eval mirror.

The mirror eval runners (``scripts/eval/run_langfuse_*_eval.py``) execute the
SAME tasks, data, and deterministic logic scorers as their Braintrust
counterparts, but trace into a SEPARATE Langfuse environment: a dedicated
project (own ``pk-lf-*``/``sk-lf-*`` keys in ``langfuse.env``) with every
trace additionally tagged by ``LANGFUSE_ENVIRONMENT``.

Design (follows the Langfuse SDK v4 best practices)
---------------------------------------------------
- One Langfuse trace per evaluated document. The trace id is DETERMINISTIC
  (sha256 of the stable filename, a valid W3C 32-char lowercase-hex id) so a
  re-run overwrites/updates the same traces — mirroring Braintrust's stable
  per-row identity.
- The root observation is a ``span`` whose ``input`` (filename, expected
  subtype, run metadata) becomes the trace input; the composite output is
  attached with ``span.update(output=...)`` before the context exits.
- ``propagate_attributes`` stays open across the whole per-document section so
  ``session_id`` (experiment name), ``environment`` (separate-env tag), and
  ``tags`` (project, prompt version) land on the trace AND every child
  observation.
- The LangChain call is nested under the trace via the official Langfuse
  ``CallbackHandler`` (``langfuse.langchain``) created inside the trace
  context — LLM generations, model name, token usage, and costs are captured
  automatically as child observations.
- The deterministic logic scorers (exact_match, subtype_accuracy,
  subtype_accuracy_equiv, confidence) are logged per trace as NUMERIC scores
  via ``client.create_score`` — the SAME scoring semantics the Braintrust
  runner computes locally (Langfuse runs are never charged against scored-run
  quotas).
- Graceful degradation: if Langfuse is disabled (no keys), unreachable, or a
  trace fails, every call becomes a no-op and the evaluation runs identically
  on the local defaults (see the contract in ``src/prompts.py``).
- ``flush()``/``shutdown()`` are always called before the run exits
  (short-lived script — buffered traces are lost otherwise).
"""

from __future__ import annotations

import hashlib
import structlog
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from src.langfuse_config import LangfuseConfig, load_langfuse_config

logger = structlog.get_logger(__name__)

TRACE_ID_LENGTH = 32


def deterministic_trace_id(filename: str, session_id: str = "") -> str:
    """Return a stable Langfuse trace id for a document within an experiment.

    W3C trace ids are 32-char lowercase hex strings; a sha256 of the stable
    CUAD stem (scoped by the experiment's session id) satisfies that while
    keeping the SAME contract on the SAME trace across runs and resumptions
    OF THE SAME EXPERIMENT. Different experiments (different session ids) on
    the same corpus get disjoint traces — a re-run updates its own traces in
    place instead of merging observations across experiments.
    """
    seed = f"{session_id}|{filename}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:TRACE_ID_LENGTH]


@dataclass
class TraceHandle:
    """Per-document trace handle yielded by :meth:`LangfuseTracer.trace_document`.

    ``handler`` is the LangChain callback handler to attach to the agent call
    (``None`` when tracing is disabled — the pipeline then runs untraced).
    ``set_output`` / ``score`` are no-ops when disabled or on client errors.
    """

    trace_id: str
    handler: Any = None
    disabled: bool = False
    _span: Any = None
    _client: Any = None

    def set_output(self, output: Any) -> None:
        """Attach the composite output to the document's root observation.

        In the v4 observations-first model the root observation's input/output
        are the trace input/output, so updating the span is sufficient.
        """
        if self.disabled or self._span is None:
            return
        try:
            self._span.update(output=output)
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_trace_output_failed", trace_id=self.trace_id)

    def score(self, name: str, value: float, comment: str = "",
              observation_id: str | None = None) -> None:
        """Log one deterministic logic score against the document's trace.

        ``observation_id`` pins the score to a specific observation (e.g. an
        agent's span) instead of the whole trace — the per-agent task scores
        (sorter, contracts_specialist) attach to their own spans.
        """
        if self.disabled or self._client is None:
            return
        try:
            kwargs = {
                "trace_id": self.trace_id,
                "name": name,
                "value": value,
                "data_type": "NUMERIC",
                "comment": comment,
            }
            if observation_id:
                kwargs["observation_id"] = observation_id
            self._client.create_score(**kwargs)
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_score_failed", trace_id=self.trace_id, name=name)


@dataclass
class AgentHandle:
    """Per-agent observation handle yielded by :meth:`LangfuseTracer.agent_observation`.

    The handle carries the agent span's ``observation_id`` so its designated
    task scores (exact_match/subtype_accuracy/... for the sorter,
    overall_extraction_score/field_presence/... for the specialist) attach to
    the agent's OWN observation — that is what makes per-agent performance
    metrics derivable over time in Langfuse.
    """

    trace_id: str
    observation_id: str = ""
    handler: Any = None
    disabled: bool = False
    _span: Any = None
    _client: Any = None

    def set_output(self, output: Any) -> None:
        """Attach the agent's composite result to its observation."""
        if self.disabled or self._span is None:
            return
        try:
            self._span.update(output=output)
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_agent_output_failed", trace_id=self.trace_id)

    def score(self, name: str, value: float, comment: str = "") -> None:
        """Log one deterministic logic score against the AGENT's observation."""
        if self.disabled or self._client is None or not self.observation_id:
            return
        try:
            self._client.create_score(
                trace_id=self.trace_id,
                observation_id=self.observation_id,
                name=name,
                value=value,
                data_type="NUMERIC",
                comment=comment,
            )
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_agent_score_failed",
                           trace_id=self.trace_id, name=name)


class LangfuseTracer:
    """Wraps the Langfuse client for one eval run (one document per trace)."""

    def __init__(
        self,
        config: LangfuseConfig | None = None,
        session_id: str = "",
        tags: list[str] | None = None,
        trace_name: str = "subtype_classification",
    ):
        self._config = config or load_langfuse_config()
        self._session_id = session_id or self._config.project
        self._tags = list(tags or [])
        self._trace_name = trace_name
        self._client: Any = None
        self.disabled = not (
            self._config.public_key and self._config.secret_key and self._config.base_url
        )
        if self.disabled:
            logger.info("langfuse_tracing_disabled", reason="missing LANGFUSE keys")

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    def _ensure_client(self) -> None:
        """Lazily construct the Langfuse client (singleton).

        Imported AFTER the environment is loaded (``load_langfuse_config`` ran
        in ``__init__``) — importing Langfuse before env vars are loaded would
        initialize it with missing/wrong credentials.
        """
        if self._client is not None or self.disabled:
            return
        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self._config.public_key,
                secret_key=self._config.secret_key,
                host=self._config.base_url,
            )
        except Exception:  # noqa: BLE001 - degrade to no-op tracing
            logger.warning("langfuse_init_failed", exc_info=True)
            self.disabled = True
            self._client = None

    def flush(self) -> None:
        """Flush queued trace/score events (blocking) before the run ends."""
        if self.disabled or self._client is None:
            return
        try:
            self._client.flush()
        except Exception:  # noqa: BLE001
            logger.warning("langfuse_flush_failed")

    def shutdown(self) -> None:
        """Shut the client down (flush + close background workers)."""
        if self.disabled or self._client is None:
            return
        try:
            self._client.shutdown()
        except Exception:  # noqa: BLE001
            logger.warning("langfuse_shutdown_failed")

    # ------------------------------------------------------------------
    # Per-document tracing
    # ------------------------------------------------------------------

    @contextmanager
    def trace_document(
        self,
        filename: str,
        expected: Any = None,
        metadata: dict | None = None,
    ) -> Iterator[TraceHandle]:
        """Open ONE Langfuse trace for a document; yields its :class:`TraceHandle`.

        Usage::

            with tracer.trace_document(filename, expected, meta) as handle:
                result = sorter.classify_json(text, callbacks=[handle.handler])
                handle.set_output(composite)
                handle.score("subtype_accuracy", 1.0)

        The ``propagate_attributes`` scope stays open across the whole ``with``
        block so ``session_id`` / ``environment`` / ``tags`` reach the trace
        AND the nested LLM generation created by the callback handler.
        """
        trace_id = deterministic_trace_id(filename, self._session_id)
        handle = TraceHandle(trace_id=trace_id, disabled=True)
        if self.disabled:
            yield handle
            return
        self._ensure_client()
        if self._client is None:
            yield handle
            return

        try:
            from langfuse import propagate_attributes
            from langfuse.langchain import CallbackHandler

            trace_input = {"filename": filename, "expected": expected, **(metadata or {})}
            with self._client.start_as_current_observation(
                as_type="span",
                name=self._trace_name,
                trace_context={"trace_id": trace_id},
                input=trace_input,
            ) as span:
                with propagate_attributes(
                    session_id=self._session_id,
                    environment=self._config.environment,
                    tags=[self._config.project, *self._tags],
                ):
                    handler = CallbackHandler()
                    handle = TraceHandle(
                        trace_id=trace_id,
                        handler=handler,
                        disabled=False,
                        _span=span,
                        _client=self._client,
                    )
                    try:
                        yield handle
                    finally:
                        # Span (and trace) close with the context manager.
                        pass
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_trace_failed", filename=filename, exc_info=True)
            yield TraceHandle(trace_id=trace_id, disabled=True)

    @contextmanager
    def agent_observation(
        self,
        agent_name: str,
        metadata: dict | None = None,
    ) -> Iterator[AgentHandle]:
        """Open ONE per-agent observation nested under the current trace.

        Must be called INSIDE a :meth:`trace_document` block. The observation
        is a SPAN named after the agent (e.g. ``sorter``,
        ``contracts_specialist``); the LangChain ``CallbackHandler`` created
        inside nests the agent's LLM generation under it, and
        :meth:`AgentHandle.score` attaches the agent's designated task scores
        to the agent's own observation.

        Usage::

            with tracer.trace_document(filename, expected) as trace:
                with tracer.agent_observation("sorter", {"prompt_version": ...}) as sorter:
                    result = sorter_agent.classify_json(text, callbacks=[sorter.handler])
                    sorter.score("subtype_accuracy", 1.0)
                with tracer.agent_observation("contracts_specialist", {...}) as specialist:
                    ...
        """
        disabled = AgentHandle(trace_id="", disabled=True)
        if self.disabled or self._client is None:
            yield disabled
            return
        try:
            from langfuse import propagate_attributes
            from langfuse.langchain import CallbackHandler

            trace_id = self._client.get_current_trace_id()
            with self._client.start_as_current_observation(
                as_type="span",
                name=agent_name,
                input=dict(metadata or {}),
                metadata={"agent": agent_name, **(metadata or {})},
            ) as span:
                with propagate_attributes(tags=[f"agent:{agent_name}"]):
                    handler = CallbackHandler()
                handle = AgentHandle(
                    trace_id=trace_id,
                    observation_id=getattr(span, "id", "") or "",
                    handler=handler,
                    disabled=False,
                    _span=span,
                    _client=self._client,
                )
                try:
                    yield handle
                finally:
                    # The span closes with the context manager.
                    pass
        except Exception:  # noqa: BLE001 - observability must never break the run
            logger.warning("langfuse_agent_span_failed",
                           agent=agent_name, exc_info=True)
            yield disabled
