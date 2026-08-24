"""KANBAN-072 regression guards: the clause-category registry must stay
character-exact against CUAD's canonical category_descriptions.csv.

The original registry carried fluent paraphrases under a "verbatim" label —
~30 of 41 CUAD texts deviated from the primary source, including a
volume_restriction entry that actually described price_increase_consent.
These network-free guards vendor the canonical CSV as the oracle and make
label drift impossible again.
"""

import csv
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "config" / "clause_categories.yaml"
CANON_CSV = REPO_ROOT / "tests" / "fixtures" / "cuad_category_descriptions.csv"

EXPECTED_CUAD = 41
EXPECTED_MAUD = 8


def _load_canonical():
    canon = {}
    with open(CANON_CSV, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or not row[0].startswith("Category:") or row[0].startswith(
                "Category (incl"
            ):
                continue
            cat = row[0][len("Category:"):].strip()
            desc = row[1][len("Description:"):].strip() if len(row) > 1 else ""
            fmt = row[2][len("Answer Format:"):].strip() if len(row) > 2 else ""
            canon[cat] = {"desc": desc, "fmt": fmt}
    return canon


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def test_registry_shape():
    doc = yaml.safe_load(REGISTRY.read_text())
    cats = doc["categories"]
    assert len(cats) == EXPECTED_CUAD + EXPECTED_MAUD
    maud = [n for n in cats if "class_id" not in cats[n] or cats[n]["class_id"] is None]
    assert len(maud) == EXPECTED_MAUD


def test_cuad_verbatim_questions_are_char_exact():
    canon = _load_canonical()
    canon_n = {_norm(k): k for k in canon}
    doc = yaml.safe_load(REGISTRY.read_text())
    cuad = [n for n in doc["categories"] if n in canon_n or _norm(n) in canon_n]
    assert len(cuad) == EXPECTED_CUAD
    for name in cuad:
        spec = doc["categories"][name]
        c = canon[canon_n[_norm(name)]]
        assert spec["verbatim_question"].strip() == c["desc"], (
            f"{name}: verbatim_question drifted from canonical CUAD description"
        )


def test_answer_types_follow_canonical_format():
    canon = _load_canonical()
    canon_n = {_norm(k): k for k in canon}
    doc = yaml.safe_load(REGISTRY.read_text())
    for name, spec in doc["categories"].items():
        key = canon_n.get(_norm(name))
        if key is None:
            continue  # MAUD side has no canonical format column yet
        expected = "yes_no" if canon[key]["fmt"].lower() == "yes/no" else "general_info"
        assert spec["answer_type"] == expected, name


def test_agent_inquiry_templates_present():
    doc = yaml.safe_load(REGISTRY.read_text())
    tpl = doc["agent_inquiry_templates"]
    assert set(tpl) >= {"change_of_control", "mae_clause_scope",
                        "contract_amendment_restrictions"}
    for name, t in tpl.items():
        assert t["prompt"], name
        assert t["target_dataset"] in {"CUAD", "MAUD", "CUAD / MAUD"}, name


def test_no_known_mislabelled_entry():
    """The smoking gun from reconciliation: volume_restriction's old 'verbatim'
    text actually described price_increase_consent. Pin the canonical text."""
    doc = yaml.safe_load(REGISTRY.read_text())
    vq = doc["categories"]["volume_restriction"]["verbatim_question"]
    assert vq.startswith("Is there a fee increase or consent requirement")
