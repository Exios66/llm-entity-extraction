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


# --- KANBAN-073: docclass schema v2 (subclasses + filenames on every row) --

BUILDER_DOCCLASS = REPO_ROOT / "scripts" / "datasets" / "build_docclass_merged.py"
DOCCLASS_DUMP = REPO_ROOT / "data" / "datasets" / "docclass_merged.jsonl"


def test_docclass_builder_refuses_partial_null_schema():
    src = _src(BUILDER_DOCCLASS)
    # contracts get their subclass from CUAD's own grouping + real file names
    assert 'metadata.get("category")' in src
    assert 'pdf_path' in src and 'rsplit("/", 1)' in src
    # refuse-to-write guard: a single null would crash the Hub viewer
    assert "refusing to" in src and "expected_subclass" in src


def test_publisher_docclass_guard_blocks_partial_null_uploads():
    src = _src(PUBLISHER)
    # pre-upload mirror of the builder guard — this bug class never ships
    assert "refusing to upload a" in src
    assert 'r.get("expected_subclass")' in src and 'r.get("filename")' in src


def test_docclass_dump_schema_v2_no_null_label_columns():
    import pytest

    if not DOCCLASS_DUMP.exists():
        pytest.skip("data/datasets/docclass_merged.jsonl absent (gitignored)")
    rows = [json.loads(l) for l in DOCCLASS_DUMP.open(encoding="utf-8") if l.strip()]
    assert len(rows) == 700
    # the Hub-viewer killer: every row carries non-empty string labels
    for i, r in enumerate(rows):
        assert str(r.get("filename") or "").strip(), f"row {i}: empty filename"
        assert str(r.get("expected_subclass") or "").strip(), \
            f"row {i}: empty expected_subclass"
    # prefix-inference pin: the FIRST batch must already be fully typed
    assert all(r["expected_subclass"] for r in rows[:20])
    # contract rows carry CUAD's own grouping as their subclass
    contracts = [r for r in rows if r["expected"] == "contract"]
    assert contracts and all(r["expected_subclass"] for r in contracts)
    assert len({r["expected_subclass"] for r in contracts}) >= 25


def test_docclass_manifest_records_schema_v2_coverage():
    import pytest

    p = DOCCLASS_DUMP.parent / "docclass_merged.manifest.json"
    if not p.exists():
        pytest.skip("docclass manifest absent (gitignored)")
    m = json.loads(p.read_text())
    assert m.get("schema_version") == 2
    cov = m.get("subclass_coverage") or {}
    assert cov.get("rows_with_nonempty_filename") == m.get("rows") == 700
    assert cov.get("rows_with_nonempty_subclass") == 700
    assert cov.get("contract_groups", 0) >= 25
