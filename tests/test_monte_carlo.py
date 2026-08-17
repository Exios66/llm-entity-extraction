"""Tests for the Monte Carlo simulation suite (KANBAN-046).

Network-free: the suite is driven by a tiny synthetic corpus written into a
tmp dir (the corpus schema produced by ``monte_carlo_corpus.py``), so the
helper units and every scenario script run without the real experiment log.

The real-corpus runs are covered by the committed ``reports/monte_carlo/*``
outputs, which the reproducibility test below regenerates when the experiment
log is present.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from src.monte_carlo import (  # noqa: E402
    bootstrap,
    confidence_score,
    decoy_mentioned,
    draw_committee,
    majority_margin,
    normalize_dist,
    paired_delta_bootstrap,
    reasoning_mentions_label,
    shannon_entropy,
    task_label_vocabulary,
    uncertainty_phrases,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_normalize_dist_and_entropy():
    dist = normalize_dist({"a": 3, "b": 1})
    assert dist["a"] == pytest.approx(0.75)
    assert dist["b"] == pytest.approx(0.25)
    assert shannon_entropy({"a": 1.0}) == 0.0
    assert 0.0 <= shannon_entropy(dist, normalized=True) <= 1.0
    assert shannon_entropy({}) == 0.0


def test_majority_margin_and_committee():
    assert majority_margin({"a": 1.0}) == 1.0
    assert majority_margin({"a": 0.6, "b": 0.4}) == pytest.approx(0.2)
    assert majority_margin({}) == 0.0
    rng = random.Random(7)
    winner = draw_committee({"a": 1.0}, 5, rng)
    assert winner == "a"
    assert draw_committee({}, 3, rng) == ""


def test_bootstrap_helpers():
    values = [1.0] * 40 + [0.0] * 10
    stat = bootstrap(values, lambda v: sum(v) / len(v), n_boot=500, seed=1)
    assert stat["estimate"] == pytest.approx(0.8)
    assert stat["ci_lo"] <= stat["estimate"] <= stat["ci_hi"]
    delta = paired_delta_bootstrap([1.0] * 30 + [-1.0] * 5, n_boot=500, seed=1)
    assert delta["mean"] > 0.0
    assert delta["p_win"] > 0.9


def test_uncertainty_and_confidence():
    assert uncertainty_phrases("not sure about this one")
    assert not uncertainty_phrases("")
    assert not uncertainty_phrases(None)
    assert confidence_score({"a": 1.0}, near_miss_signal=False, uncertainty=False) == 1.0
    low = confidence_score({"a": 0.5, "b": 0.5}, near_miss_signal=True, uncertainty=True)
    high = confidence_score({"a": 0.5, "b": 0.5}, near_miss_signal=False, uncertainty=False)
    assert low < high


def test_vocabulary_and_decoy_detection():
    subtypes = task_label_vocabulary("subtype_classification")
    assert "marketing" in subtypes and len(subtypes) == 25
    docclasses = task_label_vocabulary("docclass_classification")
    assert "merger_agreement" in docclasses
    assert task_label_vocabulary("no_such_task") == ()
    assert decoy_mentioned("classified as development, not license", "license")
    assert not decoy_mentioned("classified as development", "license")
    assert reasoning_mentions_label("Development agreement with license grants",
                                    "license")


# ---------------------------------------------------------------------------
# Scenario scripts on a tiny synthetic corpus
# ---------------------------------------------------------------------------

def _synthetic_corpus() -> list[dict]:
    """A small corpus exercising every scenario path: shared docs across two
    prompt versions, a confused pair, a failure row, and a near-miss trace."""
    rows = []
    doc_a = "contract_alpha"
    doc_b = "contract_beta"
    for prompt in ("sorter_v9", "sorter_v13"):
        for doc, expected, predicted, ok, conf, reasoning in (
            (doc_a, "marketing", "marketing", True, 0.95,
             "Titled Marketing Agreement; operates as marketing, not agency"),
            (doc_b, "development", "development", True, 0.90,
             "Development agreement; the license grants are ancillary"),
            (doc_b, "development", "development", True, 0.92,
             "Development contract with license provisions"),
            ("contract_gamma", "agency", "agency", True, 0.80,
             "Agency agreement; not marketing despite co-branding"),
        ):
            rows.append({
                "task": "subtype_classification",
                "experiment_name": f"qwen_sorter_{prompt}_run",
                "model": "qwen/qwen3.7-flash",
                "prompt_version": prompt,
                "dataset": "mailroom-cuad-contracts-full",
                "temperature": 0.1,
                "reasoning_effort": "medium",
                "tracing_backend": "langfuse",
                "filename": doc, "predicted": predicted, "expected": expected,
                "correct": ok, "confidence": conf, "reasoning": reasoning,
                "failure_mode": None, "status": "completed", "error": "",
                "tokens": {}, "cost_usd": None,
            })
    # a confusion failure row (development -> license) + a non-completed row
    rows.append({
        "task": "subtype_classification", "experiment_name": "qwen_sorter_v13_run",
        "model": "qwen/qwen3.7-flash", "prompt_version": "sorter_v13",
        "dataset": "mailroom-cuad-contracts-full", "temperature": 0.1,
        "reasoning_effort": "medium", "tracing_backend": "langfuse",
        "filename": "contract_delta", "predicted": "license", "expected": "development",
        "correct": False, "confidence": 0.6,
        "reasoning": "Development-ish but license grants dominate",
        "failure_mode": "family_confusion", "status": "completed", "error": "",
        "tokens": {}, "cost_usd": None,
    })
    rows.append({
        "task": "subtype_classification", "experiment_name": "qwen_sorter_v13_run",
        "model": "qwen/qwen3.7-flash", "prompt_version": "sorter_v13",
        "dataset": "mailroom-cuad-contracts-full", "temperature": 0.1,
        "reasoning_effort": "medium", "tracing_backend": "langfuse",
        "filename": "contract_epsilon", "predicted": "", "expected": "marketing",
        "correct": False, "confidence": None, "reasoning": "",
        "failure_mode": None, "status": "error", "error": "Connection error",
        "tokens": {}, "cost_usd": None,
    })
    return rows


def _write_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus.jsonl"
    with corpus.open("w", encoding="utf-8") as fh:
        for row in _synthetic_corpus():
            fh.write(json.dumps(row) + "\n")
    return corpus


@pytest.fixture()
def synthetic_corpus(tmp_path):
    return _write_corpus(tmp_path)


def _run_script(name: str, corpus: Path, out: Path, *extra: str) -> int:
    import importlib

    module = importlib.import_module(f"scripts.reporting.{name}")
    return module.main_with_args(["--corpus", str(corpus), "--out-dir", str(out),
                                  *extra])


def test_ensemble_scenario(synthetic_corpus, tmp_path):
    out = tmp_path / "out"
    assert _run_script("monte_carlo_ensemble", synthetic_corpus, out,
                       "--task", "subtype_classification",
                       "--k-list", "1,3,5", "--n-sim", "40") == 0
    assert (out / "ensemble-voting-subtype_classification.md").exists()
    assert (out / "escalation-subtype_classification.md").exists()
    assert (out / "escalation_candidates-subtype_classification.txt").exists()


def test_prompt_ablation_scenario(synthetic_corpus, tmp_path):
    out = tmp_path / "out"
    assert _run_script("monte_carlo_prompt_ablation", synthetic_corpus, out,
                       "--task", "subtype_classification", "--min-shared", "2") == 0
    report = (out / "prompt-ablation-subtype_classification.md").read_text()
    assert "sorter_v9" in report and "sorter_v13" in report


def test_failures_scenario(synthetic_corpus, tmp_path):
    out = tmp_path / "out"
    assert _run_script("monte_carlo_failures", synthetic_corpus, out,
                       "--n-sim", "500") == 0
    report = (out / "failure-pipeline.md").read_text()
    assert "Fitted per-attempt probabilities" in report


def test_exemplars_scenario(synthetic_corpus, tmp_path):
    out = tmp_path / "out"
    assert _run_script("monte_carlo_exemplars", synthetic_corpus, out,
                       "--task", "subtype_classification",
                       "--max-exemplars", "2") == 0
    assert (out / "exemplars-subtype_classification.md").exists()


def test_verify_scenario(synthetic_corpus, tmp_path):
    out = tmp_path / "out"
    assert _run_script("monte_carlo_verify", synthetic_corpus, out,
                       "--task", "subtype_classification", "--alpha", "0.3") == 0
    plan = (out / "verify-subtype_classification.md").read_text()
    assert "run_langfuse_subtype_eval.py" in plan
    assert "--dry-run" in plan


def _gepa_winner_corpus() -> list[dict]:
    """A corpus with a clear champion (sorter_v13 strictly beats sorter_v9 on
    18 of 20 shared docs) so the champion-contender branch is exercised with a
    bootstrap CI that excludes zero."""
    rows = []
    n_docs = 20
    for prompt, correct_upto in (("sorter_v9", 2), ("sorter_v13", n_docs)):
        for i in range(1, n_docs + 1):
            ok = i <= correct_upto
            rows.append({
                "task": "subtype_classification",
                "experiment_name": f"qwen_sorter_{prompt}_run",
                "model": "qwen/qwen3.7-flash",
                "prompt_version": prompt,
                "dataset": "mailroom-cuad-contracts-full",
                "temperature": 0.1,
                "reasoning_effort": "medium",
                "tracing_backend": "langfuse",
                "filename": f"d{i}",
                "predicted": "development" if ok else "license",
                "expected": "development",
                "correct": ok,
                "confidence": 0.95 if ok else 0.6,
                "reasoning": "Development agreement with license grants"
                             if ok else "License grants dominate",
                "failure_mode": None if ok else "family_confusion",
                "status": "completed", "error": "",
                "tokens": {}, "cost_usd": None,
            })
    return rows


def test_gepa_scenario(synthetic_corpus, tmp_path):
    """The GEPA champion-contender layer runs on a synthetic corpus and emits
    the full + half-corpus pilot reports (KANBAN-049)."""
    out = tmp_path / "out"
    assert _run_script("monte_carlo_gepa", synthetic_corpus, out,
                       "--task", "subtype_classification",
                       "--min-shared", "1", "--n-boot", "100",
                       "--sample", "0.5") == 0
    report = (out / "gepa-champion-contender-subtype_classification-sample50%.md").read_text()
    assert "## Full-corpus selection" in report
    assert "## Half-corpus pilot" in report
    assert "Document-count sweep" in report
    assert ("Plateau" in report) or ("MC champion contender" in report)


def test_gepa_selects_clear_winner(tmp_path):
    """With a strictly-better version on the shared docs, the MC layer names
    the champion (the non-plateau branch)."""
    corpus = tmp_path / "corpus.jsonl"
    with corpus.open("w", encoding="utf-8") as fh:
        for row in _gepa_winner_corpus():
            fh.write(json.dumps(row) + "\n")
    out = tmp_path / "out"
    assert _run_script("monte_carlo_gepa", corpus, out,
                       "--task", "subtype_classification",
                       "--min-shared", "1", "--n-boot", "100") == 0
    report = (out / "gepa-champion-contender-subtype_classification.md").read_text()
    assert "MC champion contender: `sorter_v13`" in report
    assert "sorter_v13" in report.split("## Half-corpus pilot")[0]


def test_corpus_builder_smoke(tmp_path, monkeypatch):
    """The corpus builder runs over the real experiment log (when present) and
    emits the canonical corpus + summary; skipped when the log is absent."""
    log = REPO_ROOT / "reports" / "experiment_log.jsonl"
    if not log.exists():
        pytest.skip("experiment log absent")
    from scripts.reporting import monte_carlo_corpus as mc

    monkeypatch.setattr(mc, "EXPERIMENT_LOG", log)
    monkeypatch.setattr(mc, "MANIFESTS_DIR", REPO_ROOT / "data" / "manifests")
    out = tmp_path / "mc"
    assert mc.main_with_args(["--out-dir", str(out)]) == 0
    assert (out / "corpus.jsonl").exists()
    summary = (out / "corpus-summary.md").read_text()
    assert "Rows by task" in summary


def test_reports_monte_carlo_are_current():
    """The committed reports/monte_carlo scenario outputs must regenerate from
    the current corpus without drift (derived artifacts, never hand-edited).

    Uses the exact parameterization the committed outputs were generated with
    (the scenario defaults), so drift is detected rather than regenerated away.
    """
    corpus = REPO_ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
    if not corpus.exists():
        pytest.skip("monte carlo corpus absent (gitignored)")
    import tempfile

    import scripts.reporting.monte_carlo_ensemble as ensemble
    import scripts.reporting.monte_carlo_failures as failures
    import scripts.reporting.monte_carlo_gepa as gepa
    import scripts.reporting.monte_carlo_prompt_ablation as ablation

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        ensemble.main_with_args(["--corpus", str(corpus), "--out-dir", str(out),
                                 "--task", "subtype_classification"])
        ablation.main_with_args(["--corpus", str(corpus), "--out-dir", str(out),
                                 "--task", "subtype_classification"])
        failures.main_with_args(["--corpus", str(corpus), "--out-dir", str(out)])
        gepa.main_with_args(["--corpus", str(corpus), "--out-dir", str(out),
                             "--task", "subtype_classification", "--sample", "0.5"])
        for name in ("ensemble-voting-subtype_classification.md",
                     "escalation-subtype_classification.md",
                     "prompt-ablation-subtype_classification.md",
                     "prompt-ablation-classes-subtype_classification.md",
                     "failure-pipeline.md",
                     "gepa-champion-contender-subtype_classification-sample50%.md"):
            committed = REPO_ROOT / "reports" / "monte_carlo" / name
            if not committed.exists():
                continue
            fresh = out / name
            if fresh.exists():
                assert fresh.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8"), (
                    f"{name} drifted from the committed copy — rerun the scenario script"
                )