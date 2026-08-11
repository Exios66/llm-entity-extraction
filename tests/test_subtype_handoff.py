"""Unit tests for the subtype-scoped chained handoff cue
(``build_subtype_handoff``) — the narrowed field scope the specialist is
cued with once the sorter predicts a class + subclass."""

from __future__ import annotations

from src.cuad_ground_truth import SUBTYPE_CUAD_FOLDERS, build_subtype_handoff


def test_subtype_folders_reverse_of_sorter_aliases():
    """Every sorter alias resolves to a subtype whose folder list is complete
    against the CUAD type-exclusion table (so the cue is data-complete)."""
    from agents.sorter_agent import CONTRACT_SUBTYPE_KEYS, _SUBTYPE_ALIASES

    from src.cuad_ground_truth import CUAD_TYPE_EXCLUDED_CATEGORIES, TYPE_ALIASES

    for folder, key in _SUBTYPE_ALIASES.items():
        assert key in SUBTYPE_CUAD_FOLDERS, f"folder {folder} -> {key} missing"
        folders = SUBTYPE_CUAD_FOLDERS[key]
        assert folders, f"{key} has no CUAD folders"
        for resolved in folders:
            assert resolved in CUAD_TYPE_EXCLUDED_CATEGORIES, \
                f"folder {resolved} missing from the type-exclusion table"
    # The singular "Affiliate Agreement" alias resolves through TYPE_ALIASES.
    assert TYPE_ALIASES["Affiliate Agreement"] in SUBTYPE_CUAD_FOLDERS["affiliate"]
    assert set(SUBTYPE_CUAD_FOLDERS) == set(CONTRACT_SUBTYPE_KEYS) | {"other"}


def test_build_subtype_handoff_license():
    cue = build_subtype_handoff("license")
    assert "license agreement family" in cue
    # License_Agreements excludes only 4 categories; the license-grant family
    # is expected and must be cued.
    assert "key_obligations" in cue
    assert "License Grant" in cue
    # Never-applicable categories are listed as not-expected.
    assert "Not expected in this family" in cue


def test_build_subtype_handoff_narrow_scope():
    # Non_Compete_Non_Solicit carries only a small slice of the 41 categories;
    # the cue must list its applicable categories and warn the specialist
    # against inventing license-grant machinery.
    cue = build_subtype_handoff("non_compete_no_solicit")
    assert "Non-Compete" in cue
    assert "Exclusivity" in cue
    assert "Not expected in this family" in cue
    assert "License Grant" in cue  # listed in the NOT-expected line
    not_expected = cue.split("Not expected in this family")[1]
    assert "License Grant" in not_expected


def test_build_subtype_handoff_unknown_and_other():
    # The fallback subtype produces NO cue (no narrowing).
    assert build_subtype_handoff("other") == ""
    assert build_subtype_handoff(None) == ""
    assert build_subtype_handoff("banana") == ""


def test_build_subtype_handoff_multifolder_key():
    # endorsement covers Endorsement + Endorsement Agreement folders — the
    # union of their applicable categories is cued.
    cue = build_subtype_handoff("endorsement")
    assert "endorsement agreement family" in cue
    assert "Not expected in this family" in cue
    # The union is wider than either folder alone (Endorsement Agreement
    # excludes more categories than Endorsement).
    assert "Affiliate License-Licensor" in cue


def test_build_subtype_handoff_contains_schema_fields():
    cue = build_subtype_handoff("transportation")
    for field in ("parties", "effective_date", "governing_law", "termination_clauses"):
        assert field in cue, f"{field} missing from transportation cue"
