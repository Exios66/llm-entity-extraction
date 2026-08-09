"""SorterAgent — Legal Document Classification Agent (LangChain).

Classifies documents into one of the 6 mailroom document types with confidence
scoring. The system prompt is loaded BY VERSION from ``src.prompts`` so the
evaluation loops can test exactly one prompt version per Braintrust experiment.
"""

from __future__ import annotations

import structlog
from agents.base_agent import BaseAgent, build_structured_schema
from src.prompts import get_prompt

logger = structlog.get_logger(__name__)

DOC_CLASSES = [
    {"key": "contract", "label": "Contract / Agreement", "description": "Formal agreements between parties: M&A, vendor, employment, NDAs, etc."},
    {"key": "corporate_record", "label": "Corporate Record", "description": "Bylaws, resolutions, board minutes, cap table entries, incorporation docs"},
    {"key": "due_diligence", "label": "Due Diligence", "description": "Checklists, disclosure schedules, diligence memos, risk assessments"},
    {"key": "correspondence", "label": "Correspondence", "description": "Letters, emails, memos, notices between parties or with regulators"},
    {"key": "compliance_filing", "label": "Compliance Filing", "description": "SEC filings, state registrations, regulatory submissions, annual reports"},
    {"key": "court_opinion", "label": "Court Opinion", "description": "Judicial opinions and orders: published decisions, memorandum opinions, rulings"},
]

DOC_CLASS_KEYS = [d["key"] for d in DOC_CLASSES]

SORTER_SCHEMA = build_structured_schema(
    {
        "doc_type": {"type": "string", "enum": DOC_CLASS_KEYS},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string"},
    }
)


class SorterAgent(BaseAgent):
    """Classifies legal documents into mailroom document types."""

    agent_name = "sorter"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        prompt_version: str = "sorter",
    ):
        super().__init__(model=model, api_key=api_key)
        self.prompt_version = prompt_version

    def system_prompt(self) -> str:
        base_prompt = get_prompt(self.prompt_version)
        if "{{doc_type_descriptions}}" not in base_prompt:
            return base_prompt
        doc_type_descriptions = "\n".join(
            f"- {d['key']}: {d['label']} — {d['description']}"
            for d in DOC_CLASSES
        )
        return base_prompt.replace("{{doc_type_descriptions}}", doc_type_descriptions)

    def classify(self, doc_text: str) -> tuple[str, float, str]:
        """Classify a document and return (doc_type, confidence, reasoning).

        Args:
            doc_text: The full text content of the document.

        Returns:
            Tuple of (doc_type key, confidence 0-1, reasoning string).
        """
        truncated = self.truncate_input(doc_text)
        result = self._call_structured(
            f"Classify this legal document:\n\n{truncated}",
            json_schema=SORTER_SCHEMA,
            temperature=0.1,
        )

        if result.get("_parse_error"):
            logger.error("sorter_parse_error")
            return ("correspondence", 0.3, "parse error — defaulting to correspondence")

        doc_type = result.get("doc_type", "correspondence")
        if doc_type not in DOC_CLASS_KEYS:
            doc_type = "correspondence"
        try:
            confidence = float(result.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        reasoning = result.get("reasoning", "")

        logger.info("classified", doc_type=doc_type, confidence=confidence)
        return (doc_type, confidence, reasoning)

    def classify_json(self, doc_text: str) -> dict:
        """Classify and return the raw structured dict (used by eval loops)."""
        truncated = self.truncate_input(doc_text)
        result = self._call_structured(
            f"Classify this legal document:\n\n{truncated}",
            json_schema=SORTER_SCHEMA,
            temperature=0.1,
        )
        if result.get("_parse_error"):
            return {"doc_type": "correspondence", "confidence": 0.3, "reasoning": "parse error"}
        return result

    def re_evaluate(self, doc_text: str, previous_result: dict) -> tuple[str, float, str]:
        """Re-evaluate a document after low-confidence classification.

        Args:
            doc_text: The full text content.
            previous_result: Dict with keys 'doc_type', 'confidence', 'reasoning'.

        Returns:
            Updated (doc_type, confidence, reasoning).
        """
        prompt = f"""RE-EVALUATION REQUESTED

Previous classification attempt produced low confidence. Please re-analyze this document more carefully.

Previous result:
- Assigned class: {previous_result.get('doc_type', 'unknown')}
- Confidence: {previous_result.get('confidence', 0)}
- Previous reasoning: {previous_result.get('reasoning', 'N/A')}

Document text:
{doc_text}

Provide your best classification with justification."""

        result = self._call_structured(prompt, json_schema=SORTER_SCHEMA, temperature=0.1)

        if result.get("_parse_error"):
            return (previous_result.get("doc_type", "correspondence"), 0.3, "re-evaluation parse error")

        doc_type = result.get("doc_type", previous_result.get("doc_type", "correspondence"))
        try:
            confidence = float(result.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        return (doc_type, confidence, result.get("reasoning", ""))
