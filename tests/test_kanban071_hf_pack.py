"""KANBAN-071: network-free pins for the LegalBench-full pack + docclass-merged
publishing tooling.

Pins by SOURCE INSPECTION (no network, no Hub calls at test time): the pack
builder's verbatim-TSV + honest-enrichment contract, and the publisher's
byte-proof verification discipline. Staging-data assertions are skipped when
the gitignored data/hf_export/ directory is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "scripts" / "datasets" / "build_legalbench_full_pack.py"
PUBLISHER = REPO_ROOT / "scripts" / "datasets" / "publish_kanban071.py"
STAGING = REPO_ROOT / "data" / "hf_export"


def _src(path: Path) -> str:
    assert path.exists(), f"missing {path}"
    return path.read_text(encoding="utf-8")


# --- builder: verbatim upstream + honest enrichment -----------------------

def test_builder_preserves_upstream_tsv_bytes():
    src = _src(BUILDER)
    # single source of truth: fetch/discovery helpers come from the streamer
    assert "from scripts.datasets.stream_legalbench_tasks_to_bt import" in src
    assert "fetch_task_file" in src
    # upstream TSVs land byte-exact (write_bytes of the fetched bytes)
    assert 'write_bytes(train_raw.encode("utf-8"))' in src


def test_builder_enrichment_never_rewrites_labels():
    src = _src(BUILDER)
    # audit flags ride along on the row; the LB answer itself is untouched
    assert "category_audit" in src
    assert "never rewritten" in src


def test_builder_join_key_unifies_lb_document_name_and_cuad_title():
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from scripts.datasets.build_legalbench_full_pack import contract_key

    # LB ships trailing ".PDF"; CUAD_v1.json titles don't; case differs.
    lb = "ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT AGREEMENT.PDF"
    cuad = "ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT AGREEMENT"
    assert contract_key(lb) == contract_key(cuad)
    assert contract_key("Foo Bar.PDF") == "foo bar"


# --- publisher: KANBAN-069 verification discipline ------------------------

def test_publisher_verifies_blob_oids_against_hub_tree():
    src = _src(PUBLISHER)
    assert "git_blob_sha1" in src                # per-file git-style sha1
    assert "blob_id" in src                      # compared to the Hub tree


def test_publisher_verifies_docclass_lfs_sha256():
    src = _src(PUBLISHER)
    assert "hub_lfs_sha256" in src
    assert 'verified' in src                     # explicit verdict in summary


def test_publisher_defaults_to_lucius_morningstar():
    src = _src(PUBLISHER)
    assert 'HF_USERNAME' in src and "Lucius-Morningstar" in src


# --- staging evidence (skipped when gitignored exports are absent) --------


def _summary() -> dict | None:
    p = STAGING / "KANBAN071_PUBLISH_SUMMARY.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def test_publish_summary_records_green_verification():
    import pytest

    s = _summary()
    if s is None:
        pytest.skip("data/hf_export/ absent (gitignored)")
    pack = s.get("pack")
    if pack is None:
        pytest.skip("pack record pending regeneration (--only pack)")
    assert pack.get("files_missing_on_hub") == 0
    assert pack.get("blob_oid_mismatches") == 0
    assert pack.get("aggregates_roundtrip_ok") is True
    docclass = s.get("docclass") or {}
    assert docclass.get("verified") is True
    assert docclass.get("local_sha256") == docclass.get("hub_lfs_sha256")


def test_enrichment_report_totals_are_complete_and_honest():
    p = STAGING / "legalbench_full" / "ENRICHMENT_REPORT.json"
    if not p.exists():
        import pytest

        pytest.skip("pack staging absent (gitignored)")
    totals = json.loads(p.read_text())["totals"]
    # allowlisted keys only — a new key must be added here deliberately
    assert set(totals) == {
        "train_exact", "train_fuzzy", "train_span_unmatched",
        "train_unknown_contract", "train_audit_agree", "train_audit_suspect",
    }
    # every enriched cuad_* row lands in exactly one disposition — no silent
    # drops (cross-checked against index.jsonl's per-task row counts)
    dispositions = sum(totals.get(k, 0) for k in
                       ("train_exact", "train_fuzzy", "train_unknown_contract",
                        "train_span_unmatched"))
    idx = [json.loads(l) for l in (STAGING / "legalbench_full" / "index.jsonl").open()]
    cuad_rows = sum(r["rows_train"] for r in idx if r["task"].startswith("cuad_"))
    assert dispositions == cuad_rows
    # audited rows are a subset of located rows (agree+suspect+mismatch may
    # double-count into exact/fuzzy — that's by design, audit rides on match)
    audited = sum(totals.get(k, 0) for k in
                  ("train_audit_agree", "train_audit_suspect", "train_audit_mismatch"))
    located = totals.get("train_exact", 0) + totals.get("train_fuzzy", 0)
    assert audited <= located
