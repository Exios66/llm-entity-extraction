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


def _figure_footer_overlaps(fig, ax=None):
    """Renderer-based collision scan: any figure text whose extent crosses the
    axes bottom edge (the x labels / tick labels / legend live there) counts
    as an overlap. Returns the offending texts' content."""
    import matplotlib

    # Figures created outside pyplot management carry a bare FigureCanvasBase
    # (no get_renderer); attach an Agg canvas so the collision scan can render.
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    canvas = fig.canvas
    if not hasattr(canvas, "get_renderer"):
        canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    if ax is None:
        ax = fig.axes[0]
    ax_bottom = ax.get_window_extent(renderer=renderer).y0
    hits = []
    for t in fig.texts:
        b = t.get_window_extent(renderer=renderer)
        if b.y1 > ax_bottom - 0.5:  # text rises into the axes/label region
            hits.append(t.get_text())
    return hits


@pytest.mark.skipif(
    not (REPO_ROOT / "data" / "cuad_pdfs" / "CUAD_v1.json").exists(),
    reason="CUAD corpus absent (gitignored) — download_cuad_pdfs first",
)
def test_eda_figure_citations_stay_in_their_footer_band(tmp_path):
    """The dataset-citation footer must never overlap axes labels / legends
    (regression guard for the footer-band rework): the CUAD figures are
    rendered into a tmp dir and scanned for footer text that rises into the
    axes region."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from scripts.eda import explore_cuad as ec

    ec.FIG = tmp_path / "cuad_figs"
    ec.FIG.mkdir(parents=True, exist_ok=True)
    captured = []
    orig = ec._add_citation

    def probe(fig, ax, note=""):
        orig(fig, ax, note)  # real footer band + layout
        captured.append(fig)

    ec._add_citation = probe
    try:
        ec.make_figures(ec.analyze())
    finally:
        ec._add_citation = orig
    plt.close("all")

    assert len(captured) >= 10, f"expected 10 CUAD figures, got {len(captured)}"
    offenders = {}
    for fig in captured:
        text = _figure_footer_overlaps(fig)
        if text:
            offenders[fig] = [t[:60] for t in text]
    assert not offenders, f"citation overlapping axes/labels on {len(offenders)} figure(s)"


@pytest.mark.skipif(
    not all(p.exists() for p in _REQUIRED),
    reason="corpus dumps absent (gitignored)",
)
def test_pipeline_sources_figure_citations_stay_in_their_footer_band(tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from scripts.eda import explore_pipeline_sources as eps

    captured = []
    orig = eps._add_citation

    def probe(fig, note=""):
        orig(fig, note)  # real footer band + layout
        captured.append(fig)

    eps._add_citation = probe
    try:
        for name, (analyze, _r, _f, make_figs) in eps._SOURCES.items():
            figdir = tmp_path / name / "figures"
            figdir.mkdir(parents=True, exist_ok=True)
            make_figs(analyze(), figdir)
    finally:
        eps._add_citation = orig
    plt.close("all")

    assert len(captured) >= 7, f"expected 7 pipeline-source figures, got {len(captured)}"
    offenders = [t[:60] for fig in captured for t in _figure_footer_overlaps(fig)]
    assert not offenders, f"citation overlapping axes/labels: {offenders}"