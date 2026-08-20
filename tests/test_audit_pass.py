"""Unit tests for the runner-level audit pass (KANBAN-060).

Network-free: ``_call_structured`` is monkeypatched so the audit method runs
its windowing, feedback rendering, usage accumulation, and union merge logic
without any LLM call.
"""

from __future__ import annotations

import pytest

from agents.specialist_agents import ContractsSpecialist, AUDIT_SCHEMA


@pytest.fixture
def specialist():
    return ContractsSpecialist(model="mock", api_key="sk-mock")


def _extraction(obligations=None, entries=None):
    return {
        "reasoning": {
            "summary": "scanned",
            "entries": entries or [
                {"field": "Exclusivity", "evidence": "LICENSEE grants exclusivity.",
                 "section_ref": "Section 2"},
            ],
        },
        "parties": ["Acme"],
        "effective_date": "2024-01-15",
        "term_length": None,
        "termination_clauses": [],
        "governing_law": "Delaware",
        "key_obligations": obligations or ["LICENSEE grants exclusivity."],
        "contract_value": None,
        "renewal_terms": None,
        "confidence": 0.8,
    }


def test_audit_merges_missing_clauses_union(specialist, monkeypatch):
    """The audit's missing clauses append to key_obligations as a union with
    normalized dedupe, each with a canonical-tagged reasoning entry; already-
    quoted clauses are never duplicated; nothing is removed."""
    calls = {}

    def fake_call(self, user_message, json_schema, temperature=None):
        calls["schema"] = json_schema
        calls["message"] = user_message
        assert "Exclusivity" in user_message  # feedback lists already-quoted
        assert "AUDIT PASS" in user_message  # audit block appended after text
        return {"missing_obligations": [
            {"category": "Covenant Not To Sue",
             "clause": "NEITHER PARTY SHALL ASSERT CLAIMS AGAINST THE OTHER."},
            {"category": "Exclusivity",
             "clause": "licensee grants exclusivity."},  # normalized-dupe of existing
        ]}

    monkeypatch.setattr(ContractsSpecialist, "_call_structured", fake_call)

    extraction = _extraction()
    merged = specialist.audit_extraction("window text", extraction)

    assert calls["schema"]["title"] == "AuditOutput"
    assert "missing_obligations" in calls["schema"]["properties"]
    obligations = merged["key_obligations"]
    assert obligations == [
        "LICENSEE grants exclusivity.",
        "NEITHER PARTY SHALL ASSERT CLAIMS AGAINST THE OTHER.",
    ]
    fields = [e["field"] for e in merged["reasoning"]["entries"]]
    assert fields == ["Exclusivity", "Covenant Not To Sue"]
    assert merged["reasoning"]["entries"][-1]["section_ref"] == "audit-pass"
    assert merged["parties"] == ["Acme"]  # untouched
    assert merged["effective_date"] == "2024-01-15"  # untouched


def test_audit_empty_result_is_noop(specialist, monkeypatch):
    """An honest empty answer leaves the extraction byte-identical."""
    monkeypatch.setattr(ContractsSpecialist, "_call_structured",
                        lambda self, m, json_schema, temperature=None: {"missing_obligations": []})
    extraction = _extraction()
    merged = specialist.audit_extraction("window text", extraction)
    assert merged == extraction


def test_audit_parse_error_skipped_never_fatal(specialist, monkeypatch):
    """A failed/parse-error audit call is skipped, not fatal; the extraction
    is returned unchanged."""
    monkeypatch.setattr(ContractsSpecialist, "_call_structured",
                        lambda self, m, json_schema, temperature=None: {"_parse_error": True})
    extraction = _extraction()
    merged = specialist.audit_extraction("window text", extraction)
    assert merged == extraction


def test_audit_multi_window_sums_usage(specialist, monkeypatch):
    """Per-window audit calls accumulate usage ON TOP of the extraction's own
    usage; _last_usage carries the summed extract + audit totals."""
    doc = "\n\n".join(f"Section {i} paragraph." + "x" * 300 for i in range(1, 20))
    usage_counter = {"calls": 0}

    def fake_call(self, user_message, json_schema, temperature=None):
        usage_counter["calls"] += 1
        self._last_usage = {"prompt_tokens": 1000, "completion_tokens": 100,
                            "total_tokens": 1100, "cost": 0.001}
        return {"missing_obligations": []}

    monkeypatch.setattr(ContractsSpecialist, "_call_structured", fake_call)
    specialist._last_usage = {"prompt_tokens": 500, "completion_tokens": 50,
                              "total_tokens": 550, "cost": 0.0005}

    extraction = _extraction()
    merged = specialist.audit_extraction(doc, extraction, chunk_chars=1_000,
                                         overlap_chars=200)
    assert usage_counter["calls"] > 1  # multi-window -> per-window audit calls
    assert merged == extraction
    assert specialist._last_usage["prompt_tokens"] >= 500 + 1000 * usage_counter["calls"]
    assert specialist._last_usage["cost"] >= 0.0005 + 0.001 * usage_counter["calls"]


def test_audit_single_window_uses_whole_text(specialist, monkeypatch):
    """Documents under the chunk size get ONE audit call over the whole text,
    with the extraction call's exact user-message prefix (the provider prefix-
    cache consolidation: the re-read shares the extraction call's byte-
    identical prefix and is billed at the cached-token rate)."""
    calls = []

    def fake_call(self, user_message, json_schema, temperature=None):
        calls.append(user_message)
        return {"missing_obligations": []}

    monkeypatch.setattr(ContractsSpecialist, "_call_structured", fake_call)
    specialist.audit_extraction("short text under the window", _extraction(),
                                chunk_chars=90_000, overlap_chars=8_000)
    assert len(calls) == 1
    assert calls[0].startswith(
        "Extract fields from this contracts document:\n\nshort text under the window")
    assert "AUDIT PASS" in calls[0]


def test_audit_prefix_is_byte_identical_to_extraction(specialist, monkeypatch):
    """The cache consolidation, verified: the audit call's user message must
    START with the extraction call's user message byte-for-byte, so the shared
    prefix (system prompt + layout + window text) hits the provider's
    automatic context cache and the text re-read is not re-billed in full."""
    messages = {}

    def fake_call(self, user_message, json_schema, temperature=None):
        messages.setdefault(json_schema.get("title", "?"), user_message)
        return {"missing_obligations": []}

    monkeypatch.setattr(ContractsSpecialist, "_call_structured", fake_call)
    doc = "\n\n".join(f"Section {i} of the agreement." for i in range(1, 12))
    extraction = specialist.extract(doc)
    specialist.audit_extraction(doc, extraction, chunk_chars=90_000, overlap_chars=8_000)

    extract_msg = messages.get("StructuredOutput")
    audit_msg = messages.get("AuditOutput")
    assert extract_msg is not None and audit_msg is not None
    assert audit_msg.startswith(extract_msg)
    assert len(audit_msg) > len(extract_msg)  # audit block appended after text


def test_audit_schema_contract():
    """The audit output schema demands category + clause per entry."""
    item = AUDIT_SCHEMA["properties"]["missing_obligations"]["items"]
    assert set(item["required"]) == {"category", "clause"}
    assert AUDIT_SCHEMA["required"] == ["missing_obligations"]


def test_audit_rejects_unlabeled_entries(specialist, monkeypatch):
    """Entries missing a category or clause are dropped, not merged."""
    monkeypatch.setattr(ContractsSpecialist, "_call_structured",
                        lambda self, m, json_schema, temperature=None: {
                            "missing_obligations": [
                                {"category": "Audit Rights", "clause": "Acme may audit."},
                                {"category": "", "clause": "no category"},
                                {"category": "Insurance", "clause": "  "},
                                "not a dict",
                            ]})
    extraction = _extraction()
    merged = specialist.audit_extraction("Acme may audit.", extraction)
    assert merged["key_obligations"] == [
        "LICENSEE grants exclusivity.",
        "Acme may audit.",
    ]
    assert merged["reasoning"]["entries"][-1]["field"] == "Audit Rights"