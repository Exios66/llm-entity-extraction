"""Base agent class — LangChain-powered LLM helpers with structured output.

Every mailroom agent is a small LangChain Runnable wrapper: a ``ChatOpenAI``
instance pointed at OpenRouter (or any OpenAI-compatible endpoint via
``OPENROUTER_BASE_URL``) composed with prompt templates and optional JSON
schema parsing.

Design notes
------------
- Prompts are loaded by version from ``src.prompts`` so the evaluation loops
  can test exactly ONE prompt version per Braintrust experiment.
- Structured calls use ``with_structured_output`` (JSON schema) so specialists
  and the sorter emit strict JSON that Braintrust scorers can rely on.
- All calls are traced to Braintrust via ``braintrust.integrations.langchain``
  when the eval runners call ``setup_langchain`` first (they always do).
"""

from __future__ import annotations

import json
import structlog
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.openrouter_utils import OPENROUTER_BASE_URL

logger = structlog.get_logger(__name__)


def build_structured_schema(
    properties: dict,
    required: list[str] | None = None,
    additional_properties: bool = False,
) -> dict:
    """Build a JSON schema dict for structured output."""
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties.keys()),
        "additionalProperties": additional_properties,
    }


class BaseAgent(ABC):
    """Abstract base class for all mailroom agents (LangChain runnables)."""

    agent_name: str

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or "qwen/qwen3.7-flash"
        self.api_key = api_key or ""
        self._max_tokens = 4096
        self._max_input_chars = 25000
        self._temperature = 0.1
        self._reasoning_effort = None
        self._llm: ChatOpenAI | None = None
        self._last_usage: dict | None = None

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt string."""
        ...

    # ------------------------------------------------------------------
    # LangChain plumbing
    # ------------------------------------------------------------------

    def llm(self) -> ChatOpenAI:
        """Lazily build the LangChain ``ChatOpenAI`` client.

        Uses the OpenRouter base URL so any OpenAI-compatible endpoint
        (Ollama, vLLM) can be swapped in via ``OPENROUTER_BASE_URL``.
        """
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.model,
                api_key=self.api_key or None,
                base_url=OPENROUTER_BASE_URL,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                timeout=120,
                max_retries=3,
            )
            if self._reasoning_effort:
                self._llm.extra_body = {"reasoning": {"effort": self._reasoning_effort}}
        return self._llm

    def truncate_input(self, text: str) -> str:
        """Truncate document text to configured input budget."""
        if len(text) <= self._max_input_chars:
            return text
        return (
            text[: self._max_input_chars]
            + f"\n\n[... document truncated, {len(text)} total chars ...]"
        )

    # ------------------------------------------------------------------
    # Completion helpers
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        user_message: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        """Plain text completion via the LangChain chain.

        Args:
            user_message: The user-facing message content.
            system_prompt: System prompt (defaults to self.system_prompt()).
            temperature: Sampling temperature (defaults to self._temperature).
            max_tokens: Max output tokens (defaults to self._max_tokens).
            reasoning_effort: Reasoning effort level for Qwen models.

        Returns:
            The model's response text.
        """
        llm = self.llm()
        if temperature is not None or max_tokens is not None:
            llm = llm.bind(
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens or self._max_tokens,
            )
        if reasoning_effort:
            llm = llm.bind(extra_body={"reasoning": {"effort": reasoning_effort}})

        system = system_prompt or self.system_prompt()
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", "{text}")]
        )
        chain = prompt | llm | StrOutputParser()

        logger.info("llm_call", agent=self.agent_name, model=self.model)
        content = chain.invoke({"text": user_message})
        logger.info("llm_response", agent=self.agent_name, length=len(content))
        return content

    def _call_structured(
        self,
        user_message: str,
        json_schema: dict,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Structured JSON extraction via ``with_structured_output``.

        Args:
            user_message: User message containing the document text.
            json_schema: JSON schema dict describing expected output structure.
            system_prompt: Override system prompt.
            temperature: Sampling temperature.
            max_tokens: Max output tokens.

        Returns:
            Parsed JSON dict, or {"_raw": raw_text, "_parse_error": True} on failure.
        """
        llm = self.llm()
        if temperature is not None or max_tokens is not None:
            llm = llm.bind(
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens or self._max_tokens,
            )
        try:
            structured = llm.with_structured_output(
                json_schema, method="json_schema", include_raw=True
            )
        except Exception:  # pragma: no cover - older SDKs fall back to prompting
            structured = llm.with_structured_output(json_schema, method="function_calling", include_raw=True)

        system = system_prompt or self.system_prompt()
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", "{text}")]
        )
        chain = prompt | structured

        logger.info("llm_structured_call", agent=self.agent_name, model=self.model)
        raw_out: Any = chain.invoke({"text": user_message})

        # include_raw=True returns {"raw": AIMessage, "parsed": ..., "parsing_error": ...}
        if isinstance(raw_out, dict):
            message = raw_out.get("raw")
            result = raw_out.get("parsed")
            parsing_error = raw_out.get("parsing_error")
        else:
            message = getattr(raw_out, "raw", None)
            result = getattr(raw_out, "parsed", None)
            parsing_error = getattr(raw_out, "parsing_error", None)

        # Capture usage/cost from the raw AIMessage for the Braintrust cost scorer.
        if message is not None:
            usage = getattr(message, "usage_metadata", None) or (message.response_metadata or {}).get("usage") or {}
            self._last_usage = {
                "prompt_tokens": usage.get("input_tokens") or usage.get("prompt_tokens") or 0,
                "completion_tokens": usage.get("output_tokens") or usage.get("completion_tokens") or 0,
                "total_tokens": usage.get("total_tokens") or 0,
                "cost": (message.response_metadata or {}).get("cost"),
            }
        else:
            self._last_usage = None

        if result is None and parsing_error is not None:
            logger.error("structured_output_parse_error", agent=self.agent_name, error=str(parsing_error))
            raw_text = ""
            if message is not None:
                raw_text = message.content if isinstance(message.content, str) else ""
            return {"_raw": raw_text, "_parse_error": True}

        if not isinstance(result, dict):
            try:
                result = result.model_dump()
            except AttributeError:
                logger.error("structured_output_unparseable", agent=self.agent_name)
                return {"_raw": str(result), "_parse_error": True}

        logger.info("llm_structured_response", agent=self.agent_name, keys=list(result.keys()))
        return result
