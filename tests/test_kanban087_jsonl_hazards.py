"""KANBAN-087: line-boundary hazard guards for Hub-bound JSONL (network-free).

Literal U+2028/U+2029/NEL inside JSON strings are LEGAL JSON, but any loader
that parses batches via str.splitlines() (the HF datasets-server worker does)
treats them as record breaks INSIDE a row -> shredded invalid fragments ->
DatasetGenerationError "Expected object or value" on mailroom-cuad-contracts-
full (16 literal U+2028 chars in ONE CUAD doc_text, 2026-08-23 human report).
export_bt_to_hf.py must therefore escape the hazard set at write time; these
pins keep that guard from silently regressing. Local `datasets` loads such a
file happily (bytes.splitlines() ignores U+2028), so a green local load proves
NOTHING — the pins below simulate the worker's parse shape instead.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.datasets.export_bt_to_hf import (  # noqa: E402
    LINE_BOUNDARY_HAZARDS,
    sanitize_line_boundary_chars,
)


def test_hazard_set_covers_the_splitlines_family():
    assert set(LINE_BOUNDARY_HAZARDS) == {"\u2028", "\u2029", "\x85"}


def test_all_hazards_escaped_at_write_shape():
    rec = {"input": {"doc_text": "a b cd"}}
    line = sanitize_line_boundary_chars(json.dumps(rec, ensure_ascii=False))
    for ch in LINE_BOUNDARY_HAZARDS:
        assert ch not in line, f"raw hazard {ch!r} survived"
    assert "\\u2028" in line and "\\u2029" in line and "\\u0085" in line


def test_roundtrip_lossless():
    rec = {"input": {"doc_text": "line sep   para"}, "expected": {"n": 42}}
    fixed = sanitize_line_boundary_chars(json.dumps(rec, ensure_ascii=False))
    assert json.loads(fixed) == rec  # \uXXXX escapes decode to identical values


def test_worker_parse_shape_one_record_stays_one_piece():
    rec = {"doc_text": "before after"}
    raw = json.dumps(rec, ensure_ascii=False)
    assert len(raw.splitlines()) == 2          # UNSAFE: worker shreds into 2 pieces
    safe = sanitize_line_boundary_chars(raw)
    assert len(safe.splitlines()) == 1         # SAFE: one record, one piece
    assert json.loads(safe) == rec


def test_incident_shape_16_separators_in_one_doc_text():
    doc_text = ("master clause " + " " + "tail ") * 16  # 16 U+2028, line-73 shape
    rec = {"id": "x", "input": {"doc_text": doc_text}}
    safe = sanitize_line_boundary_chars(json.dumps(rec, ensure_ascii=False))
    assert len(safe.splitlines()) == 1
    assert json.loads(safe)["input"]["doc_text"] == doc_text


def test_exporter_write_path_wraps_dumps_with_sanitizer():
    src = (REPO_ROOT / "scripts" / "datasets" / "export_bt_to_hf.py").read_text(
        encoding="utf-8"
    )
    hits = re.findall(
        r"rows_out\.append\(\s*sanitize_line_boundary_chars\(\s*json\.dumps\(rec",
        src,
    )
    assert len(hits) == 1, "exporter writer must wrap json.dumps with the sanitizer"
