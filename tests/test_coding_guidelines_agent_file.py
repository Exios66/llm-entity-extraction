"""Mechanics pins for the Karpathy coding-guidelines doctrine (KANBAN-075).

Network-free: reads repo files from disk only. These pins fail loudly if a
future edit silently drops a load-bearing mechanic from AGENTS.md or breaks
doc <-> provenance-sidecar consistency.

Pin-authoring conventions (KANBAN-066): normalize whitespace before
substring checks (multi-line markdown prose wraps unpredictably); assert
full canonical phrases exactly as written; keep every literal in this file
identical to the one in the artifact it pins.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
SIDECAR = REPO_ROOT / ".opencode" / "agents" / "CODING_GUIDELINES_PROVENANCE.md"

SECTION_HEADING = "## Coding guidelines (adapted from Karpathy)"
PRINCIPLE_HEADINGS = [
    "Think before coding",
    "Simplicity first",
    "Surgical changes",
    "Goal-driven execution",
]
PRECEDENCE_PHRASE = "the house workflow wins"
UPSTREAM_URL = "https://github.com/multica-ai/andrej-karpathy-skills"
UPSTREAM_PIN = "2c606141936f1eeef17fa3043a72095b4765b9c2"
SIDECAR_RELATIVE_PATH = ".opencode/agents/CODING_GUIDELINES_PROVENANCE.md"
ADAPTED_NOT_VENDORED = "ADAPTED, NOT VENDORED"

# Verbatim upstream sentences that MUST NOT appear (adaptation, not copy).
UPSTREAM_VERBATIM_FORBIDDEN = [
    "Don't assume. Don't hide confusion. Surface tradeoffs.",
    "No features beyond what was asked.",
    "If you write 200 lines and it could be 50, rewrite it.",
]


def _norm(text: str) -> str:
    return " ".join(text.split())


def _agents() -> str:
    return _norm(AGENTS_MD.read_text(encoding="utf-8"))


def _sidecar() -> str:
    return _norm(SIDECAR.read_text(encoding="utf-8"))


def test_agents_md_has_guidelines_section():
    text = _agents()
    assert SECTION_HEADING in text


def test_all_four_principles_present_in_order():
    text = _agents()
    positions = [text.find(h) for h in PRINCIPLE_HEADINGS]
    assert all(p != -1 for p in positions), f"missing principle(s): {positions}"
    assert positions == sorted(positions), "principles out of canonical order"


def test_precedence_clause_survived():
    """House workflow outranks the guidelines where they touch."""
    assert PRECEDENCE_PHRASE in _agents()


def test_section_sits_between_code_conventions_and_testing_rules():
    raw = _agents()
    anchors = ["## Code conventions", SECTION_HEADING, "## Testing rules"]
    positions = [raw.find(a) for a in anchors]
    assert all(p != -1 for p in positions)
    assert positions == sorted(positions)


def test_upstream_url_and_pin_pinned_in_both_files():
    agents_text, sidecar_text = _agents(), _sidecar()
    for needle in (UPSTREAM_URL, UPSTREAM_PIN):
        assert needle in agents_text, f"{needle} missing from AGENTS.md"
        assert needle in sidecar_text, f"{needle} missing from sidecar"


def test_agents_md_points_at_sidecar_path():
    assert SIDECAR_RELATIVE_PATH in _agents()


def test_sidecar_declares_adapted_not_vendored():
    assert ADAPTED_NOT_VENDORED in _sidecar()


def test_sidecar_documents_resync_protocol():
    sidecar_text = _sidecar()
    assert "Re-sync protocol" in sidecar_text
    assert "git clone --depth 1 https://github.com/multica-ai/andrej-karpathy-skills" in sidecar_text


def test_no_verbatim_upstream_sentences_vendored():
    text = _agents()
    for sentence in UPSTREAM_VERBATIM_FORBIDDEN:
        assert _norm(sentence) not in text, f"upstream sentence vendored verbatim: {sentence!r}"
