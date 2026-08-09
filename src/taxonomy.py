"""Taxonomy loader — single source of truth for doc classes, agents, thresholds.

Reads ``config/taxonomy.yaml`` (the same task specification used by the
llm-mailroom sibling repo). Every evaluation loop, judge, and report derives
its classes/fields/agent mappings from this file so a taxonomy change is a
YAML edit, not a code change.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = REPO_ROOT / "config" / "taxonomy.yaml"

DEFAULT_TAXONOMY: dict = {
    "doc_classes": [
        {"key": "contract", "label": "Contract / Agreement",
         "description": "Formal agreements between parties: M&A, vendor, employment, NDAs, etc."},
        {"key": "corporate_record", "label": "Corporate Record",
         "description": "Bylaws, resolutions, board minutes, cap table entries, incorporation docs"},
        {"key": "due_diligence", "label": "Due Diligence",
         "description": "Checklists, disclosure schedules, diligence memos, risk assessments"},
        {"key": "correspondence", "label": "Correspondence",
         "description": "Letters, emails, memos, notices between parties or with regulators"},
        {"key": "compliance_filing", "label": "Compliance Filing",
         "description": "SEC filings, state registrations, regulatory submissions, annual reports"},
        {"key": "court_opinion", "label": "Court Opinion",
         "description": "Judicial opinions and orders: published decisions, memorandum opinions, rulings"},
    ],
    "agents": {
        "sorter": {"provider": "openrouter", "model": "qwen/qwen3.7-flash",
                   "temperature": 0.1, "max_tokens": 2048, "max_input_chars": 12000},
        "judge": {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash",
                  "temperature": 0.1, "max_tokens": 2048, "reasoning_effort": "none"},
    },
}


@lru_cache(maxsize=1)
def load_taxonomy(path: str | Path | None = None) -> dict:
    """Load and cache the taxonomy YAML (falls back to DEFAULT_TAXONOMY)."""
    path = Path(path) if path else TAXONOMY_PATH
    if not path.exists():
        return dict(DEFAULT_TAXONOMY)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    for key, value in DEFAULT_TAXONOMY.items():
        data.setdefault(key, value)
    return data


def doc_class_keys() -> list[str]:
    """Ordered doc class keys from the taxonomy."""
    return [d["key"] for d in load_taxonomy().get("doc_classes", [])]


def doc_class_labels() -> dict[str, str]:
    """Map doc class key -> human label."""
    return {d["key"]: d.get("label", d["key"]) for d in load_taxonomy().get("doc_classes", [])}


def agent_config(agent_name: str) -> dict:
    """Return the taxonomy config dict for an agent (empty dict if absent)."""
    return dict(load_taxonomy().get("agents", {}).get(agent_name, {}))


def doc_class_by_key(key: str) -> dict | None:
    """Return the taxonomy entry for a doc class key (None if unknown)."""
    for d in load_taxonomy().get("doc_classes", []):
        if d["key"] == key:
            return d
    return None
