#!/usr/bin/env python3
"""KANBAN-084 pins — docclass-pilot + docclass-merged v5 mechanics.

Network-free guards over the pilot sampler / v5 fusion contracts:
- the pilot blind config carries NO answer keys (leak-proof separation)
- GT surface = legacy enrichment keys ∪ InsuranceClaimExtraction keys
- the stratified draw is deterministic, covers every stratum, respects quota
  and preserves the family split column
- the family split rule stays single-sourced (v5 imports assign_split,
  never forks it)
- claims ground truth is promoted OUT of metadata (never rides blind-side)
"""

from __future__ import annotations

import pathlib
import sys

_repo_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))

from scripts.datasets.build_docclass_merged import (  # noqa: E402
    assign_split as family_assign_split,
)
from scripts.datasets.build_docclass_v5 import (  # noqa: E402
    CLAIM_GT_KEYS,
    EXPECTED_SHARDS,
    assign_split as v5_assign_split,
)
from scripts.datasets.build_docclass_pilot import (  # noqa: E402
    BLIND_KEYS,
    GT_SCALAR_KEYS,
    stratified_draw,
)


# --- separation of concerns -------------------------------------------------


def test_blind_keys_carry_no_answer_keys():
    forbidden = {"expected", "expected_subclass"} | set(GT_SCALAR_KEYS)
    assert BLIND_KEYS.isdisjoint(forbidden)


def test_gt_surface_is_legacy_union_insurance():
    assert {"label_evidence", "content_topic", "sentiment_score"} <= set(GT_SCALAR_KEYS)
    assert set(CLAIM_GT_KEYS) <= set(GT_SCALAR_KEYS)
    # every InsuranceClaimExtraction taxonomy field is represented
    assert {"claim_number", "policy_number", "insurer", "insured_party",
            "claim_type", "date_of_loss", "date_filed", "claimed_amount",
            "adjuster", "damages_description", "coverage_determination",
            "denial_reasons", "supporting_documents"} == set(CLAIM_GT_KEYS)


def test_family_split_rule_is_single_sourced():
    # v5 imports the rule rather than forking it (identity, not equality-of-output)
    assert v5_assign_split is family_assign_split


def test_source_shard_pins_are_complete():
    expected = {"default_train.parquet", "default_test.parquet",
                "gt_train.parquet", "gt_test.parquet",
                "claims_train.parquet", "claims_test.parquet"}
    assert expected == set(EXPECTED_SHARDS)
    for name, (size, sha) in EXPECTED_SHARDS.items():
        assert size > 0 and len(sha) == 16, f"bad pin: {name}"


# --- deterministic stratified draw ------------------------------------------


def _synthetic_v5() -> list[dict]:
    """Three strata with sizes 1 / 3 / 7 across two doc types."""
    rows = []
    specs = [("contract", "Alpha", 7), ("contract", "Beta", 3),
             ("correspondence", "memo", 1)]
    fn_counter = 0
    for dt, sub, n in specs:
        for i in range(n):
            fn_counter += 1
            fn = f"{dt}-{sub}-{fn_counter:03d}.txt"
            rows.append({
                "filename": fn,
                "doc_text": f"text {fn}",
                "prompt": "",
                "expected": dt,
                "expected_subclass": sub,
                # exercise BOTH split values inside big strata
                "split": family_assign_split(fn),
                "gt_fields": {"label_evidence": None},
                "metadata": {"k": str(fn_counter)},
            })
    return rows


def test_draw_is_quota_and_coverage_exact():
    rows = _synthetic_v5()
    drawn = stratified_draw(rows, quota=2)
    by_stratum: dict[tuple[str, str], int] = {}
    for r in drawn:
        key = (r["expected"], r["expected_subclass"])
        by_stratum[key] = by_stratum.get(key, 0) + 1
    assert by_stratum == {("contract", "Alpha"): 2,
                          ("contract", "Beta"): 2,
                          ("correspondence", "memo"): 1}
    assert len({r["filename"] for r in drawn}) == len(drawn)


def test_draw_is_deterministic_and_content_addressed():
    rows = _synthetic_v5()
    assert ([r["filename"] for r in stratified_draw(rows, 2)] ==
            [r["filename"] for r in stratified_draw(rows, 2)])
    # selection follows ascending sha256(filename) WITHIN each stratum
    import hashlib
    alpha = sorted((r for r in rows if r["expected_subclass"] == "Alpha"),
                   key=lambda r: hashlib.sha256(r["filename"].encode()).hexdigest())
    got = sorted((r for r in stratified_draw(rows, 2)
                  if r["expected_subclass"] == "Alpha"),
                 key=lambda r: r["filename"])
    want = sorted(alpha[:2], key=lambda r: r["filename"])
    assert [r["filename"] for r in got] == [r["filename"] for r in want]


def test_draw_preserves_split_column():
    rows = _synthetic_v5()
    splits = {r["filename"]: r["split"] for r in rows}
    for r in stratified_draw(rows, 3):
        assert r["split"] == splits[r["filename"]]
        assert r["split"] in ("train", "test")


# --- KANBAN-084 subclass canon ----------------------------------------------

from scripts.datasets.build_docclass_merged import (  # noqa: E402
    CONTRACT_SUBCLASS_CANON,
    normalize_contract_subclass,
)


def test_canon_merges_duplicate_cuad_spellings():
    # singular/plural drift collapses onto the dominant sibling form
    assert normalize_contract_subclass("Affiliate Agreement") == "Affiliate_Agreements"
    assert normalize_contract_subclass("Endorsement Agreement") == "Endorsement"
    # case/space insensitive on the lookup side
    assert normalize_contract_subclass(" affiliate  agreement ") == "Affiliate_Agreements"


def test_canon_is_identity_for_canonical_and_distinct_buckets():
    assert normalize_contract_subclass("Affiliate_Agreements") == "Affiliate_Agreements"
    assert normalize_contract_subclass("Endorsement") == "Endorsement"
    # deliberately-distinct buckets must NEVER be merged
    for kept in ("Joint Venture", "Joint Venture _ Filing",
                 "mixed_cash_stock", "mixed_cash_stock_election",
                 "demand", "attorney_demand"):
        assert normalize_contract_subclass(kept) == kept


def test_gt_surface_carries_clause_keys():
    assert {"cuad_clause_labels", "maud_clause_labels"} <= set(GT_SCALAR_KEYS)
    # and the leak guard picks them up automatically (blind ∩ GT = ∅)
    forbidden = {"expected", "expected_subclass"} | set(GT_SCALAR_KEYS)
    assert BLIND_KEYS.isdisjoint(forbidden)
