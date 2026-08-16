"""Unit tests for the research-funding-key resolution + production gate.

Network-free: keys are faked via conftest or per-test monkeypatching; the
runner-level gate smoke test mocks the dataset loader and the resolver.
"""

from __future__ import annotations

from argparse import ArgumentParser

import pytest

from src.env_utils import (
    PRODUCTION_RUN_MIN_ROWS,
    RESEARCH_FUNDING_KEY_ENV,
    add_research_funding_flag,
    assert_production_run,
    resolve_openrouter_key,
)


def test_resolve_default_key(monkeypatch):
    """Without the flag, the normal OPENROUTER_API_KEY is used."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-normal-key")
    assert resolve_openrouter_key(research_funding=False) == "sk-or-normal-key"


def test_resolve_funding_key(monkeypatch):
    """With the flag, the externally-funded key is required."""
    monkeypatch.setenv(RESEARCH_FUNDING_KEY_ENV, "sk-or-funding-key")
    assert resolve_openrouter_key(research_funding=True) == "sk-or-funding-key"
    # Without the flag the funding key is never consulted.
    monkeypatch.delenv("RESEARCH_FUNDING_OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-normal-key")
    assert resolve_openrouter_key(research_funding=False) == "sk-or-normal-key"


def test_resolve_funding_key_missing(monkeypatch):
    """The funding key must be configured explicitly — no silent fallback."""
    monkeypatch.setenv(RESEARCH_FUNDING_KEY_ENV, "")
    with pytest.raises(SystemExit):
        resolve_openrouter_key(research_funding=True)


def test_resolve_default_key_missing(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(SystemExit):
        resolve_openrouter_key(research_funding=False)


def test_gate_inert_without_flag():
    """Without the flag the gate never fires — even on dry-runs."""
    assert assert_production_run(False, dry_run=True, selected_rows=0, total_rows=509) is None


def test_gate_refuses_dry_run():
    """A dry-run pays for no LLM calls — external funding must not be touched."""
    with pytest.raises(SystemExit, match="FULLY READY PRODUCTION RUNS"):
        assert_production_run(True, dry_run=True, selected_rows=509, total_rows=509)


def test_gate_refuses_pilot_sample():
    """Pilot-scale samples are refused with the row floor named."""
    with pytest.raises(SystemExit, match="only 50/509 rows"):
        assert_production_run(True, dry_run=False, selected_rows=50, total_rows=509)


def test_gate_accepts_production_scale(capsys):
    """Full-scale runs pass and print the funding banner."""
    assert_production_run(True, dry_run=False, selected_rows=509, total_rows=509)
    assert RESEARCH_FUNDING_KEY_ENV in capsys.readouterr().out


def test_gate_accepts_full_dataset_below_floor():
    """A dataset smaller than the floor counts as production when run whole."""
    assert_production_run(True, dry_run=False, selected_rows=42, total_rows=42)
    assert PRODUCTION_RUN_MIN_ROWS == 100


def test_gate_respects_custom_floor():
    assert_production_run(True, dry_run=False, selected_rows=300, total_rows=2000,
                          min_rows=250) is None
    with pytest.raises(SystemExit, match="only 200/2000 rows"):
        assert_production_run(True, dry_run=False, selected_rows=200, total_rows=2000,
                              min_rows=250)


def test_flag_registers_on_parser():
    """The flag parses on any runner parser and defaults to off."""
    parser = ArgumentParser()
    add_research_funding_flag(parser)
    assert parser.parse_args(["--research-funding-key"]).research_funding_key is True
    assert parser.parse_args([]).research_funding_key is False


def test_subtype_runner_gate_smoke(monkeypatch, tmp_path):
    """The gate fires inside the runner BEFORE any LLM call; without the flag
    a pilot run proceeds as before."""
    import scripts.eval.run_subtype_eval as runner

    rows = [
        {
            "input": {"doc_text": f"Agreement {i}", "filename": f"doc_{i}.txt",
                      "expected": "contract", "metadata": {"category": "License_Agreements"}},
            "expected": "contract",
            "filename": f"doc_{i}.txt",
            "doc_text": f"Agreement {i}",
            "metadata": {"category": "License_Agreements"},
        }
        for i in range(150)
    ]
    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr(runner, "resolve_openrouter_key", lambda *a, **k: "fake-funding-key")
    monkeypatch.setattr("scripts.eval.run_subtype_eval.load_braintrust_dataset",
                        lambda *a, **k: [dict(r) for r in rows])

    def fake_classify_json(self, doc_text):
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "license agreement"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)

    common = ["--dataset", "mailroom-cuad-contracts",
              "--sorter-prompt-version", "sorter_v3",
              "--experiment-name", "smoke_gate",
              "--project-id", "proj-test-0000",
              "--experiment-log", str(tmp_path / "exp.jsonl")]

    # Funding flag + pilot sample -> hard refusal.
    with pytest.raises(SystemExit, match="FULLY READY PRODUCTION RUNS"):
        runner.main_with_args(common + ["--sample", "5", "--research-funding-key"])

    # Funding flag + dry-run -> hard refusal.
    with pytest.raises(SystemExit, match="FULLY READY PRODUCTION RUNS"):
        runner.main_with_args(common + ["--dry-run", "--research-funding-key"])

    # Without the flag, the same pilot runs normally.
    rc = runner.main_with_args(common + ["--sample", "5"])
    assert rc == 0
