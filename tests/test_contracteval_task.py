"""Network-free tests for the directly-mirrored ContractEval task (KANBAN-052).

Covers: the data-builder (category extraction from the CUAD question template,
SQuAD->pairs/contracts parsing, stable fingerprint) and the
``run_langfuse_contracteval_eval.py`` runner end-to-end with a mocked LLM and
stubbed Langfuse — one experiment-log record (task=contracteval) carrying the
ContractEval rubric scores (F1/F2/Jaccard/false-nr) + per-category breakdown.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from tests.test_langfuse_tracing import StubLangfuse

ANTI = "NEITHER PARTY SHALL, WITHOUT THE PRIOR WRITTEN CONSENT OF THE OTHER PARTY, ASSIGN THIS AGREEMENT"


# ---------------------------------------------------------------------------
# Data builder (scripts/datasets/build_contracteval_testset.py)
# ---------------------------------------------------------------------------


def _synthetic_test_json():
    """A minimal SQuAD-style test.json with 2 contracts / 3 qas (one negative)."""
    return {
        "data": [
            {
                "title": "ACME - Supply Agreement",
                "paragraphs": [{
                    "context": "FULL CONTRACT A TEXT",
                    "qas": [
                        {"id": "acme__Document Name", "question":
                         'Highlight the parts (if any) of this contract related to "Document Name" '
                         'that should be reviewed by a lawyer. Details: X',
                         "answers": [{"text": "SUPPLY CONTRACT", "answer_start": 14}],
                         "is_impossible": False},
                        {"id": "acme__Anti-Assignment", "question":
                         'Highlight the parts (if any) of this contract related to "Anti-Assignment" '
                         'that should be reviewed by a lawyer. Details: Y',
                         "answers": [{"text": ANTI, "answer_start": 0}],
                         "is_impossible": False},
                    ],
                }],
            },
            {
                "title": "BETA - Master Services Agreement",
                "paragraphs": [{
                    "context": "FULL CONTRACT B TEXT",
                    "qas": [
                        {"id": "beta__Non-Compete", "question":
                         'Highlight the parts (if any) of this contract related to "Non-Compete" '
                         'that should be reviewed by a lawyer. Details: Z',
                         "answers": [], "is_impossible": True},
                    ],
                }],
            },
        ]
    }


def test_builder_category_of_parses_cuad_question(tmp_path):
    from scripts.datasets.build_contracteval_testset import _category_of
    assert _category_of(
        'Highlight the parts (if any) of this contract related to "Anti-Assignment" '
        'that should be reviewed by a lawyer. Details: ...') == "Anti-Assignment"
    assert _category_of('... "Governing Law" ...') == "Governing Law"
    assert _category_of("no quotes") == ""


def test_builder_parse_test_rows(tmp_path):
    from scripts.datasets.build_contracteval_testset import parse_test_rows
    (tmp_path / "test.json").write_text(json.dumps(_synthetic_test_json()))
    rows, contracts = parse_test_rows(tmp_path / "test.json")
    assert len(rows) == 3
    assert contracts == {"ACME - Supply Agreement": "FULL CONTRACT A TEXT",
                         "BETA - Master Services Agreement": "FULL CONTRACT B TEXT"}
    by_id = {r["id"]: r for r in rows}
    assert by_id["acme__Anti-Assignment"]["category"] == "Anti-Assignment"
    assert by_id["acme__Anti-Assignment"]["label_spans"] == [ANTI]
    assert by_id["beta__Non-Compete"]["label_spans"] == []
    assert by_id["beta__Non-Compete"]["n_labels"] == 0
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)  # deterministic order


def test_builder_fingerprint_stable(tmp_path):
    from scripts.datasets.build_contracteval_testset import _fingerprint
    (tmp_path / "test.json").write_text(json.dumps(_synthetic_test_json()))
    from scripts.datasets.build_contracteval_testset import parse_test_rows
    rows, contracts = parse_test_rows(tmp_path / "test.json")
    assert _fingerprint(rows, contracts) == _fingerprint(rows, contracts)
    assert len(_fingerprint(rows, contracts)) == 64


# ---------------------------------------------------------------------------
# Runner smoke (run_langfuse_contracteval_eval.py) — mocked LLM, no network
# ---------------------------------------------------------------------------


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


class _FakePhoenixTracer:
    """Stand-in for the Phoenix tracer: records traces, no network."""

    def __init__(self, **kwargs):
        self.disabled = False

    @contextmanager
    def trace_document(self, filename, expected=None, metadata=None):
        yield _FakePhoenixHandle()

    @contextmanager
    def agent_observation(self, agent_name, metadata=None):
        yield _FakePhoenixHandle()

    def flush(self):
        pass

    def shutdown(self):
        pass


class _FakePhoenixHandle:
    disabled = False
    handler = None

    def set_output(self, output):
        pass

    def score(self, name, value, comment=""):
        pass


@pytest.fixture
def fake_contracteval_env(monkeypatch, tmp_path):
    """Synthetic pairs+contracts + mocked LLM + stubbed Langfuse."""
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    # Mocked LLM: verbatim-quote the positive label, else "No related clause."
    def fake_call_llm(self, user_message, system_prompt=None, temperature=None,
                      max_tokens=None, reasoning_effort=None):
        self._last_usage = {"prompt_tokens": 5, "completion_tokens": 5,
                            "total_tokens": 10, "cost": 0.0}
        if "Anti-Assignment" in user_message:
            return ANTI
        return "No related clause."

    monkeypatch.setattr("agents.sorter_agent.SorterAgent._call_llm", fake_call_llm)

    pairs_path = tmp_path / "pairs.jsonl"
    contracts_path = tmp_path / "contracts.jsonl"
    with contracts_path.open("w") as fh:
        for title, context in [("ACME - Supply Agreement", "FULL CONTRACT A TEXT"),
                               ("BETA - Master Services Agreement", "FULL CONTRACT B TEXT")]:
            fh.write(json.dumps({"title": title, "context": context}) + "\n")
    with pairs_path.open("w") as fh:
        for row in [
            {"id": "acme__Document Name", "title": "ACME - Supply Agreement",
             "category": "Document Name", "question": "Document Name question",
             "label_spans": ["SUPPLY CONTRACT"], "n_labels": 1},
            {"id": "acme__Anti-Assignment", "title": "ACME - Supply Agreement",
             "category": "Anti-Assignment", "question": "Anti-Assignment question",
             "label_spans": [ANTI], "n_labels": 1},
            {"id": "beta__Non-Compete", "title": "BETA - Master Services Agreement",
             "category": "Non-Compete", "question": "Non-Compete question",
             "label_spans": [], "n_labels": 0},
        ]:
            fh.write(json.dumps(row) + "\n")

    return {"stub": stub, "pairs": pairs_path, "contracts": contracts_path}


def test_runner_smoke_contracteval(fake_contracteval_env, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_contracteval_eval as runner

    monkeypatch.setattr("scripts.eval.run_langfuse_contracteval_eval.resolve_openrouter_key",
                        lambda *a, **k: "fake-key")
    rc = runner.main_with_args([
        "--task-dataset", str(fake_contracteval_env["pairs"]),
        "--contracts", str(fake_contracteval_env["contracts"]),
        "--prompt-version", "contracteval_v0",
        "--model", "qwen/qwen3.7-flash",
        "--experiment-name", "smoke_contracteval",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
        "--max-concurrency", "2",
    ])
    assert rc == 0

    records = [json.loads(line) for line in open(tmp_path / "exp.jsonl")]
    assert len(records) == 1
    record = records[0]
    assert record["task"] == "contracteval"
    assert record["prompt_version"] == "contracteval_v0"
    assert record["parameters"]["tracing_backend"] == "langfuse"
    assert record["parameters"]["faithful_full_context"] is True
    assert record["data_source"]["n_pairs"] == 3
    assert record["data_source"]["n_contracts"] == 2

    s = record["scores"]
    assert s["n_pairs"] == 3
    assert s["n_positive"] == 2
    # Anti-Assignment TP; Document Name FN (mocked output mismatches label); Non-Compete TN.
    assert s["tp"] == 1
    assert s["fn"] == 1
    assert s["tn"] == 1
    assert s["fp"] == 0
    assert s["recall"] == pytest.approx(0.5)
    assert "per_category" in s
    assert s["per_category"]["Anti-Assignment"]["tp"] == 1
    assert s["per_category"]["Non-Compete"]["tn"] == 1

    by_id = {r["id"]: r for r in record["results"]}
    assert by_id["acme__Anti-Assignment"]["classification"] == "TP"
    assert by_id["beta__Non-Compete"]["classification"] == "TN"
    assert by_id["acme__Document Name"]["classification"] == "FN"

    # Langfuse: one trace + one observation per pair, both named "contracteval"
    # (trace_name default) = 3 pairs x 2 spans.
    names = [sp.kwargs["name"] for sp in fake_contracteval_env["stub"].spans]
    assert names.count("contracteval") == 6
    # The ContractEval observation scores are attached per pair.
    assert any(sc["name"] == "classification" for sc in fake_contracteval_env["stub"].scores)
    assert any(sc["name"] == "jaccard" for sc in fake_contracteval_env["stub"].scores)


def test_runner_smoke_contracteval_phoenix_backend(fake_contracteval_env, monkeypatch, tmp_path):
    """--tracing-backend phoenix: the run resolves the Phoenix tracer (no
    Langfuse), records tracing_backend=phoenix, and dispatches pairs grouped
    by contract (cache-friendly) while scoring identically."""
    import scripts.eval.run_langfuse_contracteval_eval as runner

    monkeypatch.setattr("scripts.eval.run_langfuse_contracteval_eval.resolve_openrouter_key",
                        lambda *a, **k: "fake-key")
    monkeypatch.setattr(
        "scripts.eval.run_langfuse_contracteval_eval.resolve_tracer",
        lambda *a, **k: (_FakePhoenixTracer(), "phoenix",
                         {"endpoint": "http://localhost:6006/v1/traces",
                          "session_id": "smoke_ce_phoenix", "trace_name": "contracteval",
                          "disabled": False}))

    instances: list = []
    orig_sorter = runner.SorterAgent

    def recording_sorter(*args, **kwargs):
        inst = orig_sorter(*args, **kwargs)
        instances.append(inst)
        return inst

    monkeypatch.setattr("scripts.eval.run_langfuse_contracteval_eval.SorterAgent",
                        recording_sorter)

    rc = runner.main_with_args([
        "--task-dataset", str(fake_contracteval_env["pairs"]),
        "--contracts", str(fake_contracteval_env["contracts"]),
        "--prompt-version", "contracteval_v0",
        "--model", "qwen/qwen3.7-flash",
        "--tracing-backend", "phoenix",
        "--experiment-name", "smoke_ce_phoenix",
        "--experiment-log", str(tmp_path / "exp_phoenix.jsonl"),
        "--manifest", str(tmp_path / "manifest_phoenix.jsonl"),
        "--max-concurrency", "2",
    ])
    assert rc == 0

    records = [json.loads(line) for line in open(tmp_path / "exp_phoenix.jsonl")]
    assert len(records) == 1
    record = records[0]
    assert record["parameters"]["tracing_backend"] == "phoenix"
    assert record["parameters"]["tracing"]["endpoint"] == "http://localhost:6006/v1/traces"

    s = record["scores"]
    assert s["tp"] == 1 and s["fn"] == 1 and s["tn"] == 1 and s["fp"] == 0

    # Cache-friendly dispatch: the two ACME pairs run consecutively (contract
    # grouped, id order within the contract).
    titles = [r["title"] for r in record["results"]]
    assert titles == ["ACME - Supply Agreement", "ACME - Supply Agreement",
                      "BETA - Master Services Agreement"]
    assert record["results"][0]["id"] == "acme__Anti-Assignment"
    assert record["results"][1]["id"] == "acme__Document Name"

    # The paper's plain-call convention: no sorter reasoning effort leaks in.
    assert instances and all(inst._reasoning_effort is None for inst in instances)


def test_report_contracteval(tmp_path):
    """The report script reads task=contracteval records and tabulates them vs
    the full 19-model Table III reference."""
    record = {
        "type": "experiment", "task": "contracteval",
        "experiment_name": "qwen3.7-flash_contracteval_v0_contracteval_langfuse",
        "model": "qwen/qwen3.7-flash", "prompt_version": "contracteval_v0",
        "timestamp": "2026-08-17T23:00:00Z",
        "scores": {
            "n_pairs": 3, "n_positive": 2, "tp": 1, "tn": 1, "fp": 0, "fn": 1,
            "accuracy": 0.6667, "precision": 1.0, "recall": 0.5, "f1": 0.6667,
            "f2": 0.5556, "jaccard_mean": 0.5, "jaccard_median": 0.5,
            "no_related_rate": 0.3333, "false_no_related_rate": 0.5,
            "false_no_related_rate_paper": 0.0008,
            "per_category": {"Anti-Assignment": {"n_pairs": 1, "n_positive": 1,
                              "tp": 1, "tn": 0, "fp": 0, "fn": 0, "accuracy": 1.0,
                              "precision": 1.0, "recall": 1.0, "f1": 1.0,
                              "f2": 1.0, "jaccard_mean": 1.0}},
        },
    }
    log = tmp_path / "exp.jsonl"
    log.write_text(json.dumps(record) + "\n")

    import scripts.reporting.run_contracteval_report as reporter
    rc = reporter.main_with_args(["--experiment-log", str(log)])
    assert rc == 0

    md = tmp_path / "report.md"
    rc = reporter.main_with_args(["--experiment-log", str(log), "--output", str(md)])
    assert rc == 0
    text = md.read_text()
    assert "# Directly-mirrored ContractEval benchmark" in text
    assert "gpt-4.1 | 0.641 | 0.672 | 0.472 | 0.071" in text  # Table III reference
    assert "qwen3.7-flash v0 | 3 | 2 | 0.667" in text
    assert "## Per-category breakdown" in text
    assert "Anti-Assignment" in text
