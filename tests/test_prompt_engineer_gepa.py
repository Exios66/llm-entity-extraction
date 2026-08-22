"""Network-free consistency pins for the prompt-engineer agent's GEPA mechanics.

KANBAN-066: the GEPA facts encoded in .opencode/agents/prompt-engineer.md are
source-derived from gepa-ai/gepa @ b265bf9 (pinned in
PROMPT_ENGINEER_GEPA_PROVENANCE.md). These tests fail when either file is
edited so the mechanics drift from the pin or from each other.
"""

from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parents[1] / ".opencode" / "agents"
AGENT_FILE = AGENTS_DIR / "prompt-engineer.md"
PROVENANCE_FILE = AGENTS_DIR / "PROMPT_ENGINEER_GEPA_PROVENANCE.md"

GEPA_PIN = "b265bf9ca77fd8e8d82039d9f74911b8780fe1ce"

ACCEPTANCE_CLASSES = ["StrictImprovementAcceptance", "ImprovementOrEqualAcceptance"]
SELECTOR_CLASSES = [
    "ParetoCandidateSelector",
    "CurrentBestCandidateSelector",
    "EpsilonGreedyCandidateSelector",
    "TopKParetoCandidateSelector",
]
COMPONENT_SELECTORS = ["RoundRobinReflectionComponentSelector", "AllReflectionComponentSelector"]
FRONTIER_TYPES = ['"instance"', '"objective"', '"hybrid"', '"cartesian"']
MERGE_FACTS = ["use_merge=False", "max_merge_invocations=5", "merge_val_overlap_floor=5", ">= max(parents)"]
WORKFLOW_FACTS = [
    "EpochShuffledBatchSampler",
    "skip_perfect_score=True",
    "reflection_lm",
    "Actionable Side Information",
]
GOVERNED_WORKFLOW_MARKERS = [
    "PROMPT_VERSIONS",
    "Same-surface comparisons only",
    "--chunked",
    "noise floor",
    "MESSAGE_BOARD.md",
]
PROVENANCE_SOURCE_FILES = [
    "src/gepa/strategies/acceptance.py",
    "src/gepa/strategies/candidate_selector.py",
    "src/gepa/strategies/component_selector.py",
    "src/gepa/proposer/merge.py",
    "src/gepa/core/state.py",
    "src/gepa/api.py",
]


def test_files_exist():
    assert AGENT_FILE.is_file(), f"missing {AGENT_FILE}"
    assert PROVENANCE_FILE.is_file(), f"missing {PROVENANCE_FILE}"


def test_agent_frontmatter_pins_upstream_commit():
    text = AGENT_FILE.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "agent file must keep its YAML frontmatter"
    assert GEPA_PIN in text, "frontmatter must carry the gepa-ai/gepa commit pin"
    assert "mode: all" in text
    for tool in ("read: true", "grep: true", "glob: true", "bash: true", "edit: true", "write: true"):
        assert tool in text, f"agent tools block lost {tool}"


def test_acceptance_semantics_present():
    text = AGENT_FILE.read_text(encoding="utf-8")
    for cls in ACCEPTANCE_CLASSES:
        assert cls in text, f"acceptance criterion missing: {cls}"
    assert "sum(child subsample scores) > sum(parent subsample scores)" in text
    assert "acceptance gate" in text.lower()


def test_candidate_selection_strategies_present():
    text = AGENT_FILE.read_text(encoding="utf-8")
    for cls in SELECTOR_CLASSES:
        assert cls in text, f"candidate selector missing: {cls}"
    assert "not always the current best" in text


def test_component_selection_present():
    text = " ".join(AGENT_FILE.read_text(encoding="utf-8").split())
    for cls in COMPONENT_SELECTORS:
        assert cls in text, f"component selector missing: {cls}"
    assert "ONE prompt component per iteration" in text


def test_frontier_types_present():
    text = AGENT_FILE.read_text(encoding="utf-8")
    assert 'frontier_type' in text
    for ft in FRONTIER_TYPES:
        assert ft in text, f"frontier type missing: {ft}"
    assert "get_pareto_front_mapping" in text


def test_merge_preconditions_present():
    text = AGENT_FILE.read_text(encoding="utf-8")
    for fact in MERGE_FACTS:
        assert fact in text, f"merge fact missing: {fact}"
    assert "Common ancestry" in text
    assert "VALIDATION SUPPORT" in text


def test_workflow_machinery_present():
    text = AGENT_FILE.read_text(encoding="utf-8")
    for fact in WORKFLOW_FACTS:
        assert fact in text, f"workflow fact missing: {fact}"


def test_governed_workflow_preserved():
    text = AGENT_FILE.read_text(encoding="utf-8")
    for marker in GOVERNED_WORKFLOW_MARKERS:
        assert marker in text, f"governed-workflow marker dropped during rewrite: {marker}"


def test_provenance_pin_and_sources():
    text = PROVENANCE_FILE.read_text(encoding="utf-8")
    assert GEPA_PIN in text
    assert "https://github.com/gepa-ai/gepa" in text
    assert "Apache-2.0" in text
    assert "2026-08-21" in text
    for src in PROVENANCE_SOURCE_FILES:
        assert src in text, f"provenance missing consulted source: {src}"
    assert "git clone" in text, "provenance must carry a re-sync recipe"


def test_agent_and_provenance_consistent():
    agent = AGENT_FILE.read_text(encoding="utf-8")
    prov = PROVENANCE_FILE.read_text(encoding="utf-8")
    shared = ACCEPTANCE_CLASSES + SELECTOR_CLASSES + COMPONENT_SELECTORS
    for name in shared:
        assert (name in agent) == (name in prov), (
            f"{name} appears in only one of agent file / provenance; update both together"
        )


def test_no_vendored_gepa_code():
    for path in (AGENT_FILE, PROVENANCE_FILE):
        text = path.read_text(encoding="utf-8")
        assert "Copyright (c) 2025 Lakshya" not in text.split("Re-sync")[0] or path == PROVENANCE_FILE
        assert "def should_accept" not in text, "no upstream source code may be vendored"
