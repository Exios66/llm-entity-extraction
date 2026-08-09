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
    },
    title="ClassificationOutput",
)


class SorterAgent(BaseAgent):
    """Classifies legal documents into mailroom document types.

    Two classification paths share the same output contract
    (``{"doc_type", "confidence", "reasoning"}``):

    - ``classify_json`` / ``classify`` — text documents (full extracted
      markdown text; truncation only past the hard safety cap).
    - ``classify_image`` — document page images (RVL-CDIP-style vision
      pipeline) using the versioned vision prompt (``sorter_vision_v0``).
    """

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

    # ------------------------------------------------------------------
    # Vision path (RVL-CDIP-style image classification)
    # ------------------------------------------------------------------

    def classify_image(self, image_base64: str, image_format: str = "png") -> dict:
        """Classify a document PAGE IMAGE with a vision model (qwen).

        Uses the versioned vision prompt (``sorter_vision_v0``): the intro
        (checks + scratchpad procedure) goes in the system message, the output
        contract + worked examples go in the image-bearing user message —
        the same split RVL-CDIP applies (``## Output format`` marker).

        Returns the SAME contract as ``classify_json``:
        ``{"doc_type", "confidence", "reasoning"}``.
        """
        from src.classifier import (
            clean_prediction,
            extract_confidence,
            extract_reasoning,
        )
        from src.openrouter_utils import split_prompt

        prompt_text = get_prompt(self.prompt_version)
        system_text, user_text = split_prompt(prompt_text)
        if not system_text:
            system_text, user_text = prompt_text, "Classify the document in this image."

        raw = self._call_vision(
            system_prompt=system_text,
            user_text=user_text,
            image_base64=image_base64,
            image_format=image_format,
            temperature=0.1,
            max_tokens=self._max_tokens,
        )

        doc_type = clean_prediction(raw)
        if doc_type not in DOC_CLASS_KEYS:
            logger.error("sorter_vision_invalid_label", raw_label=doc_type)
            doc_type = "correspondence"

        confidence = extract_confidence(raw)
        if confidence is None:
            confidence = 0.5

        reasoning = extract_reasoning(raw)
        logger.info("classified_vision", doc_type=doc_type, confidence=confidence)
        return {"doc_type": doc_type, "confidence": confidence, "reasoning": reasoning}

    def classify_document(self, pages_base64: list[str], image_format: str = "png") -> dict:
        """Classify a FULL PDF document in ONE vision call.

        Every rendered page of the PDF is sent to the model in a single request
        (``_call_vision_multi``) — one classification per document, so the
        model reads the entire agreement (recitals, sections, exhibits,
        signature pages) before deciding. Returns the standard contract:
        ``{"doc_type", "confidence", "reasoning"}``.
        """
        from src.classifier import (
            clean_prediction,
            extract_confidence,
            extract_reasoning,
        )
        from src.openrouter_utils import split_prompt

        if not pages_base64:
            return {"doc_type": "correspondence", "confidence": 0.0,
                    "reasoning": "no page images"}

        prompt_text = get_prompt(self.prompt_version)
        system_text, user_text = split_prompt(prompt_text)
        if not system_text:
            system_text, user_text = prompt_text, "Classify the document in these page images."

        raw = self._call_vision_multi(
            system_prompt=system_text,
            user_text=user_text,
            images=[(b64, image_format) for b64 in pages_base64],
            temperature=0.1,
            max_tokens=self._max_tokens,
        )

        doc_type = clean_prediction(raw)
        if doc_type not in DOC_CLASS_KEYS:
            logger.error("sorter_vision_invalid_label", raw_label=doc_type)
            doc_type = "correspondence"

        confidence = extract_confidence(raw)
        if confidence is None:
            confidence = 0.5

        reasoning = extract_reasoning(raw)
        logger.info("classified_document", doc_type=doc_type, pages=len(pages_base64),
                    confidence=confidence)
        return {"doc_type": doc_type, "confidence": confidence, "reasoning": reasoning}

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
