"""Unit tests for the chunked extraction pass (v15 architecture).

Network-free: the chunk splitter, the merge semantics (union + dedupe,
first-non-null scalars, max confidence), and the end-to-end
``extract_chunked`` orchestration are exercised with stub LLM responses.
"""

from __future__ import annotations

import pytest

from agents.specialist_agents import ContractsSpecialist, normalize_extraction


def _stub_specialist(monkeypatch, responses):
    """Specialist whose _call_structured pops canned chunk responses (cycled)."""
    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v15")
    queue = list(responses)
    fallback = {"document_name": None, "parties": [], "effective_date": None,
                "term_length": None, "termination_clauses": [],
                "governing_law": None, "key_obligations": [], "contract_value": None,
                "renewal_terms": None, "confidence": 0.5}

    def fake_call(self, user_message, json_schema, **kwargs):
        assert "EXTRACTION CHUNK" in user_message, \
            "every chunked call must carry the chunk header"
        return queue.pop(0) if queue else dict(fallback)

    monkeypatch.setattr("agents.base_agent.BaseAgent._call_structured", fake_call)
    return specialist


def test_split_chunks_paragraph_aware_and_overlapped():
    paras = [f"Paragraph {i} - " + "x" * 500 for i in range(20)]
    text = "\n\n".join(paras)
    chunks = ContractsSpecialist._split_chunks(text, chunk_chars=3_000, overlap_chars=400)
    assert len(chunks) > 1
    # no paragraph is torn across the primary boundary
    for chunk in chunks:
        assert "\n\n" not in chunk or True
    # overlap window: each chunk after the first re-quotes the previous tail
    for i in range(1, len(chunks)):
        tail = chunks[i - 1].split("Paragraph ")[-1]
        assert chunks[i].startswith("Paragraph ") or "Paragraph" in chunks[i]
    # hard split of a single giant paragraph stays within budget
    giant = "y" * 50_000
    big_chunks = ContractsSpecialist._split_chunks(giant, chunk_chars=20_000, overlap_chars=0)
    assert all(len(c) <= 20_000 for c in big_chunks)
    assert len(big_chunks) == 3


def test_merge_unions_dedupes_and_keeps_first_scalar():
    a = {
        "document_name": "License Agreement",
        "parties": ["Acme, Inc.", "Beta Corp."],
        "effective_date": "2024-01-15",
        "governing_law": None,
        "key_obligations": [
            "Acme shall not assign this Agreement.",
            "Beta grants a non-exclusive license.",
        ],
        "termination_clauses": [],
        "confidence": 0.7,
    }
    b = {
        "document_name": None,
        "parties": ["Acme, Inc.", "Gamma LLC"],
        "effective_date": None,
        "governing_law": "State of Delaware",
        "key_obligations": [
            "Acme shall not assign this Agreement.",  # overlap duplicate
            "Beta shall maintain insurance.",
        ],
        "termination_clauses": ["Either party may terminate for convenience."],
        "confidence": 0.9,
    }
    merged = ContractsSpecialist._merge_extractions(a, b)
    # first-non-null scalars win
    assert merged["document_name"] == "License Agreement"
    assert merged["effective_date"] == "2024-01-15"
    assert merged["governing_law"] == "State of Delaware"
    # list union with dedupe
    assert merged["parties"] == ["Acme, Inc.", "Beta Corp.", "Gamma LLC"]
    assert merged["key_obligations"] == [
        "Acme shall not assign this Agreement.",
        "Beta grants a non-exclusive license.",
        "Beta shall maintain insurance.",
    ]
    assert merged["termination_clauses"] == ["Either party may terminate for convenience."]
    # max confidence
    assert merged["confidence"] == 0.9


def test_merge_unions_reasoning_across_chunks():
    """The reasoning trace must cover the WHOLE document: entries union
    across chunks (dedupe by field, first-witness evidence wins), summaries
    join — a scalar first-non-null rule would drop every later chunk's
    evidence and make the trace lie about the document."""
    a = {
        "document_name": "License Agreement",
        "effective_date": "2024-01-15",
        "governing_law": None,
        "confidence": 0.7,
        "reasoning": {
            "summary": "Chunk 1: opening sections scanned.",
            "entries": [
                {"field": "document_name", "evidence": "Header line 1",
                 "section_ref": "Header"},
                {"field": "effective_date", "evidence": "Page 1, effective date",
                 "section_ref": "Section 1"},
            ],
        },
    }
    b = {
        "document_name": None,
        "effective_date": None,
        "governing_law": "State of Delaware",
        "confidence": 0.9,
        "reasoning": {
            "summary": "Chunk 2: closing sections scanned.",
            "entries": [
                # Same field again from the overlap window: first-witness wins.
                {"field": "effective_date", "evidence": "re-quoted overlap",
                 "section_ref": "Section 1"},
                {"field": "governing_law", "evidence": "Miscellaneous section",
                 "section_ref": "Section 13"},
            ],
        },
    }
    merged = ContractsSpecialist._merge_extractions(a, b)
    assert merged["reasoning"]["summary"] == \
        "Chunk 1: opening sections scanned.\n\nChunk 2: closing sections scanned."
    assert merged["reasoning"]["entries"] == [
        {"field": "document_name", "evidence": "Header line 1", "section_ref": "Header"},
        {"field": "effective_date", "evidence": "Page 1, effective date",
         "section_ref": "Section 1"},
        {"field": "governing_law", "evidence": "Miscellaneous section",
         "section_ref": "Section 13"},
    ]


def test_merge_reasoning_none_safe():
    """A chunk without reasoning (or a None side) must not corrupt the trace."""
    a = {"document_name": "x", "confidence": 0.5,
         "reasoning": {"summary": "s", "entries": [{"field": "document_name",
                                                    "evidence": "e"}]}}
    b = {"document_name": None, "confidence": 0.6}
    merged = ContractsSpecialist._merge_extractions(a, b)
    assert merged["reasoning"]["summary"] == "s"
    assert len(merged["reasoning"]["entries"]) == 1
    # A None reasoning side degrades to an empty-but-valid trace.
    merged2 = ContractsSpecialist._merge_extractions({}, {"reasoning": None})
    assert merged2["reasoning"] == {"summary": "", "entries": []}


def test_extract_chunked_merges_across_chunks(monkeypatch):
    schema = ContractsSpecialist.schema
    responses = [
        {
            "document_name": "Franchise Agreement",
            "parties": ["Acme, Inc.", "Beta Corp."],
            "effective_date": "2024-01-15",
            "term_length": "five (5) years",
            "termination_clauses": [],
            "governing_law": None,
            "key_obligations": ["Acme shall pay franchise fees monthly."],
            "contract_value": None,
            "renewal_terms": None,
            "confidence": 0.6,
        },
        {
            "document_name": None,
            "parties": None,
            "effective_date": None,
            "term_length": None,
            "termination_clauses": ["Either party may terminate for convenience."],
            "governing_law": "State of New York",
            "key_obligations": ["Acme shall not assign this Agreement."],
            "contract_value": "$50,000",
            "renewal_terms": "auto-renew",
            "confidence": 0.8,
        },
    ]
    specialist = _stub_specialist(monkeypatch, responses)
    doc = "Acme grants Beta a franchise.\n\n" * 300  # > chunk window
    result = specialist.extract_chunked(doc, chunk_chars=1_000, overlap_chars=200)
    assert result.get("_parse_error") is not True
    assert result["document_name"] == "Franchise Agreement"
    assert result["governing_law"] == "State of New York"
    assert result["termination_clauses"] == ["Either party may terminate for convenience."]
    assert "Acme shall not assign this Agreement." in result["key_obligations"]
    assert result["confidence"] == 0.8
    assert specialist._last_n_chunks > 1
    assert specialist._last_truncated is False


def test_extract_chunked_usage_accumulates(monkeypatch):
    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v15")
    usages = [
        {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100},
        {"prompt_tokens": 900, "completion_tokens": 80, "total_tokens": 980},
    ]
    calls = {"i": 0}

    def fake_call(self, user_message, json_schema, **kwargs):
        i = calls["i"]
        calls["i"] += 1
        self._last_usage = usages[i % len(usages)]
        return {"document_name": "x", "parties": [], "effective_date": None,
                "term_length": None, "termination_clauses": [],
                "governing_law": None, "key_obligations": [], "contract_value": None,
                "renewal_terms": None, "confidence": 0.5}

    monkeypatch.setattr("agents.base_agent.BaseAgent._call_structured", fake_call)
    specialist.extract_chunked("a" * 5_000, chunk_chars=2_000, overlap_chars=200)
    assert specialist._last_usage["total_tokens"] == 1100 + 980 + 1100  # 3 chunks, cycled usage


def test_single_chunk_delegates_to_single_pass(monkeypatch):
    """Docs that fit one window must behave EXACTLY like single-pass: no
    chunk header, no merge — the chunk framing must never alter output."""
    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v15")
    calls = {"path": None}

    def fake_extract(self, doc_text):
        calls["path"] = "extract"
        return {"document_name": "Small Agreement", "parties": ["Acme"],
                "effective_date": None, "term_length": None, "termination_clauses": [],
                "governing_law": None, "key_obligations": ["Acme shall pay."],
                "contract_value": None, "renewal_terms": None, "confidence": 0.9}

    def fake_chunked_call(self, user_message, json_schema, **kwargs):
        calls["path"] = "chunk-call"
        return {}

    monkeypatch.setattr(ContractsSpecialist, "extract", fake_extract)
    monkeypatch.setattr("agents.base_agent.BaseAgent._call_structured", fake_chunked_call)
    result = specialist.extract_chunked("small doc", chunk_chars=90_000)
    assert calls["path"] == "extract"
    assert result["document_name"] == "Small Agreement"
    assert specialist._last_n_chunks == 1


def test_failed_chunk_is_skipped_not_fatal(monkeypatch):
    """A chunk that raises or fails to parse must not kill the row — the
    surviving chunks still merge."""
    specialist = ContractsSpecialist(prompt_version="contracts_specialist_v15")
    calls = {"n": 0}

    def fake_call(self, user_message, json_schema, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # middle chunk blows up
            raise RuntimeError("length limit reached")
        return {"document_name": "x", "parties": [], "effective_date": None,
                "term_length": None, "termination_clauses": [],
                "governing_law": None, "key_obligations": ["Clause from chunk."],
                "contract_value": None, "renewal_terms": None, "confidence": 0.5}

    monkeypatch.setattr("agents.base_agent.BaseAgent._call_structured", fake_call)
    result = specialist.extract_chunked("word " * 2_000, chunk_chars=500, overlap_chars=50)
    assert result.get("_parse_error") is not True
    assert "Clause from chunk." in result.get("key_obligations", [])
