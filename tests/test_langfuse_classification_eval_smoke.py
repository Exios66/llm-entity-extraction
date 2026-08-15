"""End-to-end smoke test of the LANGFUSE MIRROR doc-type classification eval
(no network, no LLM): one sorter observation per row with the sorter's
designated task scores, and the repo experiment log record tagged
``tracing_backend: langfuse``."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from tests.test_langfuse_tracing import StubLangfuse


@contextmanager
def _fake_propagate_attributes(**kwargs):
    yield


@pytest.fixture
def fake_langfuse_classification(monkeypatch):
    stub = StubLangfuse()
    monkeypatch.setattr("langfuse.Langfuse", lambda **kwargs: stub)
    monkeypatch.setattr("langfuse.propagate_attributes", _fake_propagate_attributes)
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", lambda: "stub-handler")

    calls = {"sorter": 0}

    def fake_classify_json(self, doc_text):
        calls["sorter"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.95, "reasoning": "an agreement"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_json", fake_classify_json)
    stub.calls = calls
    return stub


def _dataset_row():
    return {
        "input": {"doc_text": "This Agreement between Acme and Beta is a license agreement.",
                  "filename": "cuad_doc_01.txt", "expected": "contract",
                  "metadata": {"category": "License_Agreements"}},
        "expected": "contract",
        "filename": "cuad_doc_01.txt",
        "doc_text": "This Agreement between Acme and Beta is a license agreement.",
        "metadata": {"category": "License_Agreements"},
    }


def test_langfuse_classification_loop_wiring(fake_langfuse_classification, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    rc = runner.main_with_args([
        "--dataset", "mailroom-cuad-contracts",
        "--prompt-version", "sorter_v6",
        "--experiment-name", "smoke_langfuse_classification",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert fake_langfuse_classification.calls["sorter"] == 1
    names = [s.kwargs["name"] for s in fake_langfuse_classification.spans]
    assert names == ["doc_type_classification", "sorter"]

    # The sorter's designated task scores attach to ITS observation.
    agent_scores = {s["name"]: s["value"] for s in fake_langfuse_classification.scores
                    if s.get("observation_id") == "obs-1"}
    assert set(agent_scores) == {"exact_match", "confidence"}
    assert agent_scores["exact_match"] == 1.0
    assert agent_scores["confidence"] == 0.95

    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "sorter_classification"
        assert record["prompt_version"] == "sorter_v6"
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["parameters"]["input_mode"] == "text"
        assert record["scores"]["exact_match"] == 1.0
        assert record["scores"]["per_class_accuracy"]["contract"] == 1.0


def test_langfuse_classification_dry_run(fake_langfuse_classification, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_dataset_row()])
    rc = runner.main_with_args(["--dataset", "mailroom-cuad-contracts", "--dry-run"])
    assert rc == 0
    assert fake_langfuse_classification.calls["sorter"] == 0


def _hearsay_row():
    return {
        "input": {"doc_text": "On the issue of whether David is fast, the fact that David "
                              "set a high school track record.",
                  "prompt": "Q: {{text}} Is there hearsay?\nA:",
                  "filename": "hearsay_0.txt",
                  "metadata": {"task": "hearsay", "slice": "Non-assertive conduct",
                               "valid_classes": ["No", "Yes"]}},
        "expected": "No",
        "filename": "hearsay_0.txt",
        "doc_text": "On the issue of whether David is fast, the fact that David set a "
                    "high school track record.",
        "prompt": "Q: {{text}} Is there hearsay?\nA:",
        "metadata": {"task": "hearsay", "slice": "Non-assertive conduct",
                     "valid_classes": ["No", "Yes"]},
    }


def test_langfuse_task_mode_wiring(fake_langfuse_classification, monkeypatch, tmp_path):
    """--prompt-mode task answers the row's task question via _answer_task and
    attaches the answer's exact_match to a ``legalbench_task`` observation."""
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_hearsay_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    answered = {}

    def fake_answer_task(sorter, input_data, valid_classes, prompt_version):
        answered["prompt"] = input_data["prompt"]
        answered["valid_classes"] = valid_classes
        answered["prompt_version"] = prompt_version
        return {"doc_type": "No", "confidence": 1.0, "reasoning": "no statement"}

    monkeypatch.setattr(runner, "_answer_task", fake_answer_task)

    rc = runner.main_with_args([
        "--dataset", "mailroom-lb-hearsay",
        "--prompt-mode", "task",
        "--valid-classes", "Yes,No",
        "--prompt-version", "legalbench_task_v0",
        "--experiment-name", "smoke_langfuse_hearsay",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert answered == {
        "prompt": _hearsay_row()["prompt"],
        "valid_classes": ["No", "Yes"],
        "prompt_version": "legalbench_task_v0",
    }
    assert fake_langfuse_classification.calls["sorter"] == 0
    names = [s.kwargs["name"] for s in fake_langfuse_classification.spans]
    assert names == ["legalbench_task_classification", "legalbench_task"]

    agent_scores = {s["name"]: s["value"] for s in fake_langfuse_classification.scores
                    if s.get("observation_id") == "obs-1"}
    assert set(agent_scores) == {"exact_match", "confidence"}
    assert agent_scores["exact_match"] == 1.0

    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "task_classification"
        assert record["prompt_version"] == "legalbench_task_v0"
        assert record["parameters"]["prompt_mode"] == "task"
        assert record["parameters"]["valid_classes"] == "Yes,No"
        assert record["parameters"]["tracing_backend"] == "langfuse"
        assert record["scores"]["exact_match"] == 1.0
        assert record["scores"]["per_class_accuracy"]["no"] == 1.0


def test_langfuse_task_mode_requires_valid_classes(fake_langfuse_classification, monkeypatch, tmp_path):
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_hearsay_row()])
    with pytest.raises(SystemExit) as exc:
        runner.main_with_args(["--dataset", "mailroom-lb-hearsay",
                               "--prompt-mode", "task"])
    assert exc.value.code == 2


def test_langfuse_task_mode_invalid_prediction(fake_langfuse_classification, monkeypatch, tmp_path):
    """A task answer outside the valid classes becomes an error row, not a crash."""
    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    monkeypatch.setattr("scripts.eval.run_langfuse_classification_eval.load_braintrust_dataset",
                        lambda *a, **k: [_hearsay_row()])
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    monkeypatch.setattr(runner, "_answer_task",
                        lambda *a, **k: {"doc_type": "Maybe", "confidence": 0.0})

    rc = runner.main_with_args([
        "--dataset", "mailroom-lb-hearsay",
        "--prompt-mode", "task",
        "--valid-classes", "Yes,No",
        "--experiment-name", "smoke_langfuse_hearsay_bad",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0  # the bad row counts as a failure, the run completes
    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["n_error"] == 1
        assert record["scores"]["failure"] == 1.0


def test_langfuse_task_mode_task_dataset(fake_langfuse_classification, monkeypatch, tmp_path):
    """``--task-dataset`` feeds the local JSONL the streamer's ``--local-dump``
    writes, bypassing Braintrust entirely (its writes are billing-blocked)."""
    import scripts.eval.run_langfuse_classification_eval as runner

    row = _hearsay_row()
    jsonl = tmp_path / "hearsay-test.jsonl"
    jsonl.write_text(json.dumps({
        "filename": row["filename"], "doc_text": row["doc_text"],
        "prompt": row["prompt"], "expected": row["expected"],
        "metadata": row["metadata"],
    }) + "\n")

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")
    monkeypatch.setattr(runner, "_answer_task",
                        lambda *a, **k: {"doc_type": "No", "confidence": 1.0})

    rc = runner.main_with_args([
        "--task-dataset", str(jsonl),
        "--prompt-mode", "task",
        "--valid-classes", "Yes,No",
        "--prompt-version", "legalbench_task_v0",
        "--experiment-name", "smoke_langfuse_hearsay_local",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert fake_langfuse_classification.calls["sorter"] == 0
    names = [s.kwargs["name"] for s in fake_langfuse_classification.spans]
    assert names == ["legalbench_task_classification", "legalbench_task"]

    for line in open(tmp_path / "exp.jsonl"):
        record = json.loads(line)
        assert record["task"] == "task_classification"
        assert record["scores"]["exact_match"] == 1.0
        assert record["data_source"]["source"].endswith("hearsay-test.jsonl")


def test_langfuse_classification_pdf_dir(fake_langfuse_classification, monkeypatch, tmp_path):
    """``--pdf-dir`` wires the LOCAL corpus into the Langfuse mirror: a nested
    CUAD tree is discovered recursively, each PDF is classified by the VISION
    sorter (one trace per document), and the repo record carries
    ``input_mode: vision`` — with zero Braintrust involvement."""

    import scripts.eval.run_langfuse_classification_eval as runner

    monkeypatch.setattr(runner, "require_env", lambda *names: tuple("fake-key" for _ in names))
    pdfs = tmp_path / "corpus"
    nested = pdfs / "CUAD_v1" / "full_contract_pdf" / "Part_II" / "License_Agreements"
    nested.mkdir(parents=True)
    (nested / "alpha.pdf").write_bytes(b"fake-pdf-a")

    def fake_pdf_to_png(pdf_bytes, page_num=0, target_size=(1024, 1024)):
        if page_num >= 2:
            raise ValueError("no more pages")
        return b"\x89PNG-page" + bytes([page_num])

    monkeypatch.setattr("src.image_utils.pdf_to_png_bytes", fake_pdf_to_png)
    vision_calls = {"n": 0}

    def fake_classify_document(self, pages_base64, image_format="png"):
        vision_calls["n"] += 1
        return {"doc_type": "contract", "contract_subtype": "license",
                "confidence": 0.9, "reasoning": "full document"}

    monkeypatch.setattr("agents.sorter_agent.SorterAgent.classify_document",
                        fake_classify_document)
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")

    rc = runner.main_with_args([
        "--pdf-dir", str(pdfs),
        "--prompt-version", "sorter_vision_v0",
        "--experiment-name", "smoke_langfuse_pdf_dir",
        "--experiment-log", str(tmp_path / "exp.jsonl"),
        "--manifest", str(tmp_path / "manifest.jsonl"),
    ])
    assert rc == 0

    assert vision_calls["n"] == 1  # one PDF -> one full-document vision call
    names = [s.kwargs["name"] for s in fake_langfuse_classification.spans]
    assert names == ["doc_type_classification", "sorter"]

    records = [json.loads(line) for line in open(tmp_path / "exp.jsonl")]
    assert len(records) == 1
    record = records[0]
    assert record["task"] == "sorter_classification"
    assert record["parameters"]["input_mode"] == "vision"
    assert record["parameters"]["vision_pages"] == "all"
    assert record["parameters"]["tracing_backend"] == "langfuse"
    assert record["data_source"]["source"] == "local"
    assert record["scores"]["exact_match"] == 1.0
    assert record["results"][0]["filename"] == "alpha.pdf"
