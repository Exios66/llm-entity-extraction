"""Shared JSONL line-boundary safety helpers (KANBAN-088).

Extracted verbatim from scripts/datasets/export_bt_to_hf.py (KANBAN-087) so
every Hub-bound / line-oriented writer in the family shares ONE definition.

Why this exists: the Hugging Face Hub worker parses uploaded .json* files with
str.splitlines(), which treats U+2028 / U+2029 / NEL as record breaks INSIDE a
row — structurally-valid JSONL shreds into invalid fragments while local
datasets loads stay green (the KANBAN-087 incident). Escape the hazards at
write time; json.loads decodes them back losslessly at read time.
"""

LINE_BOUNDARY_HAZARDS = {
    "\u2028": "\\u2028",  # LINE SEPARATOR
    "\u2029": "\\u2029",  # PARAGRAPH SEPARATOR
    "\x85": "\\u0085",    # NEL (str.splitlines boundary on some platforms)
}


def sanitize_line_boundary_chars(text: str) -> str:
    """Escape str.splitlines() hazard characters so one JSONL record can never
    be split mid-row by a line-oriented parser. Lossless: json.loads decodes
    the escapes back to the original characters."""
    for ch, esc in LINE_BOUNDARY_HAZARDS.items():
        text = text.replace(ch, esc)
    return text


def safe_jsonl_line(obj, **dumps_kwargs) -> str:
    """One canonical way to emit a JSONL row: ASCII-safe dumps + sanitation.

    Defaults to ``ensure_ascii=True`` so ``json.dumps`` can never emit raw
    U+2028/U+2029/NEL in the first place (belt); ``sanitize_line_boundary_chars``
    remains as the guard for explicit opt-outs like ``ensure_ascii=False``
    (suspenders) and for callers that pass pre-serialized text. Callers that
    need non-ASCII bytes verbatim must opt out explicitly:
    ``safe_jsonl_line(obj, ensure_ascii=False)``.
    """
    import json

    dumps_kwargs.setdefault("ensure_ascii", True)
    return sanitize_line_boundary_chars(json.dumps(obj, **dumps_kwargs))
