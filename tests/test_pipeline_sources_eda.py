"""Smoke tests for the pipeline-sources EDA script (KANBAN-045).

Network-free: the script only reads the local (gitignored) corpus dumps under
``data/`` and writes markdown + PNG figures to an output directory. The suite
skips when the source data files are absent (fresh clone — the corpus is
gitignored and must be streamed down first).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_REQUIRED = [
    REPO_ROOT / "data" / "maud" / "contracts.jsonl",
    REPO_ROOT / "data" / "maud" / "classification.jsonl",
    REPO_ROOT / "data" / "s1_corporate_records" / "corporate-records.jsonl",
    REPO_ROOT / "data" / "datasets" / "docclass_merged.jsonl",
    REPO_ROOT / "data" / "legalbench_local" / "hearsay.jsonl",
]


@pytest.mark.skipif(
    not all(p.exists() for p in _REQUIRED),
    reason="corpus dumps absent (gitignored) — stream data first",
)
def test_pipeline_sources_eda_writes_all_suites(tmp_path):
    from scripts.eda.explore_pipeline_sources import main_with_args

    rc = main_with_args(["--source", "all", "--out", str(tmp_path), "--no-figures"])
    assert rc == 0
    for name in ("maud", "s1", "docclass", "legalbench"):
        report = tmp_path / name / "report.md"
        findings = tmp_path / name / "findings.md"
        assert report.exists(), f"{name} report missing"
        assert findings.exists(), f"{name} findings missing"
        assert report.read_text(encoding="utf-8").strip(), f"{name} report empty"


@pytest.mark.skipif(
    not (REPO_ROOT / "data" / "maud" / "contracts.jsonl").exists(),
    reason="MAUD dumps absent (gitignored)",
)
def test_pipeline_sources_eda_figures(tmp_path):
    from scripts.eda.explore_pipeline_sources import main_with_args

    rc = main_with_args(["--source", "maud", "--out", str(tmp_path)])
    assert rc == 0
    figs = sorted((tmp_path / "maud" / "figures").glob("*.png"))
    assert len(figs) >= 3, f"expected MAUD figures, got {figs}"


def test_pipeline_sources_eda_reports_are_reproducible():
    """The committed data/eda/<source>/ reports must regenerate identically
    from the current corpus (the reports are derived, never hand-edited)."""
    if not all(p.exists() for p in _REQUIRED):
        pytest.skip("corpus dumps absent (gitignored)")
    import tempfile

    from scripts.eda.explore_pipeline_sources import main_with_args

    with tempfile.TemporaryDirectory() as td:
        main_with_args(["--source", "all", "--out", td, "--no-figures"])
        for name in ("maud", "s1", "docclass", "legalbench"):
            committed = REPO_ROOT / "data" / "eda" / name / "report.md"
            if not committed.exists():
                continue
            fresh = Path(td) / name / "report.md"
            assert fresh.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8"), (
                f"{name} report drifted from the committed copy — rerun the EDA script"
            )