"""Network-free tests for the HITL annotation queue builder.

The Langfuse public API is exercised through a fake HTTP layer; selection,
ranking, idempotency, and the CLI wiring are asserted against deterministic
payloads. Never touches the network.
"""

from __future__ import annotations

import json
import time

import pytest

import scripts.eval.run_annotation_queue as tool
from scripts.eval.run_annotation_queue import (
    AnnotationQueueClient,
    select_failures,
    select_low_performers,
)


def _sorter_trace(trace_id: str, doc_type_ok: bool, subtype_ok: bool,
                  session: str = "qwen3.7-flash_sorter_v6_subtype_langfuse",
                  version: str = "sorter_v6", filename: str | None = None,
                  timestamp: str = "2026-08-12T19:50:39.000Z") -> dict:
    return {
        "id": trace_id,
        "name": "subtype_classification",
        "timestamp": timestamp,
        "sessionId": session,
        "input": {
            "filename": filename or f"sort_{trace_id}.txt",
            "prompt_version": version,
            "model": "qwen/qwen3.7-flash",
            "expected": "license",
        },
        "scores": ["score-id"],
        "output": {"sorter": {
            "doc_type": "contract", "contract_subtype": "license",
            "expected_subtype": "license", "confidence": 0.94,
            "doc_type_ok": doc_type_ok, "subtype_ok": subtype_ok,
            "subtype_ok_equiv": subtype_ok, "failure_mode": None,
        }},
    }


def _trace(trace_id: str, score: float | None, session: str = "qwen_contracts_specialist_v18_extraction_langfuse_50",
           version: str = "contracts_specialist_v18",
           filename: str | None = None, timestamp: str = "2026-08-12T19:50:39.000Z") -> dict:
    return {
        "id": trace_id,
        "name": "contract_entity_extraction",
        "timestamp": timestamp,
        "sessionId": session,
        "input": {
            "filename": filename or f"doc_{trace_id}.txt",
            "prompt_version": version,
            "model": "qwen/qwen3.7-flash",
        },
        # the list endpoint returns score ids (strings), not objects
        "scores": [] if score is None else ["score-id"],
        "output": ({"overall_score": score, "field_presence": 1.0,
                    "category_presence": 0.9, "overall_verified_precision": 1.0}
                   if score is not None else {}),
    }


class FakeLangfuse:
    """In-memory Langfuse public API stand-in."""

    def __init__(self) -> None:
        self.traces: list[dict] = []
        self.queues: list[dict] = []
        self.items: list[dict] = []
        self.score_configs: list[dict] = []
        self.project = {"name": "llm-dojo", "id": "pj-dojo"}
        self.calls: list[str] = []

    def handle(self, method: str, path: str, params: dict | None,
               json_body: dict | None) -> dict:
        self.calls.append(f"{method} {path}")
        parts = [p for p in path.split("/") if p]
        if path == "traces":
            flt = json.loads((params or {}).get("filter", "[]"))
            rows = self.traces
            for cond in flt:
                col, op, value = cond["column"], cond["operator"], cond["value"]
                if col == "name" and op == "=":
                    rows = [t for t in rows if t.get("name") == value]
                elif col == "timestamp" and op == ">=":
                    rows = [t for t in rows if t.get("timestamp", "") >= value]
            return {"data": rows, "meta": {"totalItems": len(rows), "totalPages": 1}}
        if path == "annotation-queues" and method == "GET":
            return {"data": self.queues, "meta": {"totalItems": len(self.queues)}}
        if path == "annotation-queues" and method == "POST":
            queue = {"id": f"q-{len(self.queues)}", "name": json_body["name"],
                     "description": json_body.get("description"),
                     "scoreConfigIds": json_body.get("scoreConfigIds", [])}
            self.queues.append(queue)
            return queue
        if parts[0] == "annotation-queues" and method == "GET" and len(parts) == 2:
            queue_id = parts[1]
            status = (params or {}).get("status")
            rows = [i for i in self.items if i.get("queueId") == queue_id
                    and (status is None or i.get("status") == status)]
            return {"data": rows, "meta": {"totalItems": len(rows)}}
        if parts[0] == "annotation-queues" and method == "GET" and parts[2:] == ["items"]:
            queue_id = parts[1]
            status = (params or {}).get("status")
            rows = [i for i in self.items if i.get("queueId") == queue_id
                    and (status is None or i.get("status") == status)]
            return {"data": rows, "meta": {"totalItems": len(rows)}}
        if parts[0] == "v3" and parts[1] == "scores":
            name = (params or {}).get("name")
            rows = []
            for trace in self.traces:
                out = trace.get("output") or {}
                if name == "overall_extraction_score" and out.get("overall_score") is not None:
                    rows.append({"subject": {"traceId": trace["id"]},
                                 "name": name, "value": out["overall_score"]})
                elif name in ("exact_match", "subtype_accuracy",
                              "subtype_accuracy_equiv", "confidence"):
                    sorter = out.get("sorter") or {}
                    if not sorter:
                        continue
                    value = {"exact_match": 1 if sorter.get("doc_type_ok") else 0,
                             "subtype_accuracy": 1 if sorter.get("subtype_ok") else 0,
                             "subtype_accuracy_equiv": 1 if sorter.get("subtype_ok_equiv") else 0,
                             "confidence": sorter.get("confidence", 0.0)}[name]
                    rows.append({"subject": {"traceId": trace["id"]},
                                 "name": name, "value": value})
            return {"data": rows, "meta": {"totalItems": len(rows)}}
        if parts[0] == "score-configs" and method == "GET":
            return {"data": self.score_configs}
        if parts[0] == "score-configs" and method == "POST":
            cfg = {"id": f"sc-{len(self.score_configs)}",
                   "name": json_body["name"], "dataType": json_body["dataType"],
                   "categories": json_body.get("categories", [])}
            self.score_configs.append(cfg)
            return cfg
        if parts[0] == "annotation-queues" and method == "POST" and parts[2:] == ["items"]:
            item = {"id": f"i-{len(self.items)}", "queueId": parts[1],
                    "objectId": json_body["objectId"], "objectType": json_body["objectType"],
                    "status": json_body.get("status", "PENDING")}
            self.items.append(item)
            return item
        if parts[0] == "projects":
            return {"data": [self.project]}
        if parts[0] == "traces" and len(parts) == 2:
            trace_id = parts[1]
            for t in self.traces:
                if t["id"] == trace_id:
                    out = t.get("output") or {}
                    full = dict(t)
                    full["scores"] = ([] if not out else [
                        {"name": "overall_extraction_score",
                         "value": out["overall_score"]}])
                    return full
            return {}
        raise AssertionError(f"unexpected request: {method} {path} {params} {json_body}")


@pytest.fixture
def fake_client(monkeypatch):
    stub = FakeLangfuse()
    original = tool.AnnotationQueueClient
    created = {"client": None}

    class FakeClient(original):
        def __init__(self, base_url, public_key, secret_key, timeout=60):
            created["client"] = self
            self.base_url = "https://us.cloud.langfuse.com"
            self._stub = stub
            self._timeout = timeout

        def _request(self, method, path, params=None, json_body=None):
            return stub.handle(method, path, params, json_body)

    monkeypatch.setattr(tool, "AnnotationQueueClient", FakeClient)
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
                 "LANGFUSE_PROJECT", "LANGFUSE_ENVIRONMENT"):
        monkeypatch.setenv(name, f"fake-{name}")
    stub.project = {"name": "fake-LANGFUSE_PROJECT", "id": "pj-dojo"}
    return stub


# ----------------------------------------------------------------------
# Selection logic
# ----------------------------------------------------------------------


def test_select_low_performers_orders_worst_first():
    ranked = [
        {"trace": _trace("t1", 0.92), "score": 0.92},
        {"trace": _trace("t2", 0.61), "score": 0.61},
        {"trace": _trace("t3", 0.84), "score": 0.84},
        {"trace": _trace("t4", 0.86), "score": 0.86},
        {"trace": _trace("t5", None), "score": None},
    ]
    low = select_low_performers(ranked, "overall_extraction_score", 0.85, None)
    assert [r["trace"]["id"] for r in low] == ["t2", "t3"]
    low_bounded = select_low_performers(ranked, "overall_extraction_score", 0.85, 1)
    assert [r["trace"]["id"] for r in low_bounded] == ["t2"]
    with_unscored = select_low_performers(
        ranked, "overall_extraction_score", 0.85, None, include_unscored=True)
    assert [r["trace"]["id"] for r in with_unscored] == ["t2", "t3", "t5"]


def test_score_value_missing_and_latest():
    trace = _trace("t1", 0.90)
    trace["scores"] = [{"name": "overall_extraction_score", "value": 0.90}]
    assert AnnotationQueueClient.score_value(trace, "overall_extraction_score") == 0.90
    assert AnnotationQueueClient.score_value(_trace("t2", None), "overall_extraction_score") is None


def test_composite_score_from_trace_output():
    trace = _trace("t1", 0.9129)
    assert AnnotationQueueClient.composite_score(trace, "overall_extraction_score") == 0.9129
    assert AnnotationQueueClient.composite_score(trace, "field_presence") == 1.0
    assert AnnotationQueueClient.composite_score(_trace("t2", None),
                                                 "overall_extraction_score") is None


def test_keep_for_pipeline_scopes_to_extraction_runs():
    good = _trace("t1", 0.9, session="qwen_contracts_specialist_v18_extraction_langfuse_50")
    assert AnnotationQueueClient.keep_for_pipeline(good, "extraction_langfuse", "contracts_specialist")
    chained = _trace("t2", 0.9, session="qwen_chained_v6_v18_langfuse_5")
    assert not AnnotationQueueClient.keep_for_pipeline(chained, "extraction_langfuse", "contracts_specialist")
    wrong_prompt = _trace("t3", 0.9, session="qwen_contracts_specialist_v18_extraction_langfuse_50",
                          version="sorter_v6")
    assert not AnnotationQueueClient.keep_for_pipeline(wrong_prompt, "extraction_langfuse", "contracts_specialist")


def test_trace_review_url():
    url = tool.trace_review_url("https://us.cloud.langfuse.com", "pj-1", "tr-2")
    assert url == "https://us.cloud.langfuse.com/project/pj-1/traces/tr-2"


# ----------------------------------------------------------------------
# CLI wiring (fake API)
# ----------------------------------------------------------------------


def test_build_dry_run_writes_nothing(fake_client, monkeypatch, capsys):
    stub = fake_client
    stub.traces = [
        _trace("t1", 0.9129), _trace("t2", 0.7712), _trace("t3", 0.8399),
        _trace("t4", 0.9901),
    ]
    rc = tool.main_with_args(["build", "--dry-run", "--since-days", "60",
                              "--threshold", "0.85"])
    assert rc == 0
    assert not stub.items
    assert not stub.queues
    out = capsys.readouterr().out
    assert "would enqueue" in out
    assert "t2" in out and "t3" in out and "t1" not in out


def test_build_enqueues_low_performers_idempotently(fake_client, capsys):
    stub = fake_client
    stub.traces = [
        _trace("t1", 0.9129), _trace("t2", 0.7712), _trace("t3", 0.8399),
    ]
    rc = tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60",
                              "--queue-name", "entity-extraction-low-performers"])
    assert rc == 0
    assert [q["name"] for q in stub.queues] == ["entity-extraction-low-performers"]
    enqueued = {i["objectId"] for i in stub.items}
    assert enqueued == {"t2", "t3"}
    assert all(i["objectType"] == "TRACE" and i["status"] == "PENDING"
               for i in stub.items)
    out = capsys.readouterr().out
    assert "newly enqueued : 2" in out
    assert "review at" in out and "pj-dojo" in out

    # second run: same selection, nothing new enqueued
    rc = tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60",
                              "--queue-name", "entity-extraction-low-performers"])
    assert rc == 0
    assert len(stub.items) == 2
    assert "already present: 2" in capsys.readouterr().out


def test_build_nothing_below_threshold(fake_client, capsys):
    stub = fake_client
    stub.traces = [_trace("t1", 0.95), _trace("t2", 0.91)]
    rc = tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60"])
    assert rc == 0
    assert not stub.queues and not stub.items
    assert "nothing to enqueue" in capsys.readouterr().out


def test_build_excludes_other_pipelines(fake_client):
    stub = fake_client
    stub.traces = [
        _trace("t1", 0.50, session="qwen_sorter_v6_subtype_langfuse_200"),
        _trace("t2", 0.50),
    ]
    rc = tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60"])
    assert rc == 0
    assert [i["objectId"] for i in stub.items] == ["t2"]


def test_status_lists_pending_with_scores(fake_client, capsys):
    stub = fake_client
    stub.traces = [_trace("t1", 0.77), _trace("t2", 0.91)]
    tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60"])
    # simulate the human having processed one item
    stub.items[0]["status"] = "PROCESSED"
    rc = tool.main_with_args(["status", "--queue-name", "entity-extraction-low-performers"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(pending: 0, processed: 1)" in out or "(pending: 1, processed: 0)" in out
    assert "PROCESSED" in out
    assert "pj-dojo" in out


def test_status_queue_missing(fake_client, capsys):
    rc = tool.main_with_args(["status", "--queue-name", "does-not-exist"])
    assert rc == 1
    assert "queue not found" in capsys.readouterr().out


# ----------------------------------------------------------------------
# Sorter subtype task (failure mode)
# ----------------------------------------------------------------------


def test_sorter_failure_flags_from_composite():
    both = AnnotationQueueClient.sorter_failure(
        _sorter_trace("t1", doc_type_ok=False, subtype_ok=False))
    assert both == {"doc_type_failed": True, "subtype_failed": True}
    subtype_only = AnnotationQueueClient.sorter_failure(
        _sorter_trace("t2", doc_type_ok=True, subtype_ok=False))
    assert subtype_only == {"doc_type_failed": False, "subtype_failed": True}
    ok = AnnotationQueueClient.sorter_failure(
        _sorter_trace("t3", doc_type_ok=True, subtype_ok=True))
    assert ok == {"doc_type_failed": False, "subtype_failed": False}
    assert AnnotationQueueClient.sorter_failure({"id": "x"}) is None


def test_select_failures_orders_worst_first():
    ranked = [
        {"trace": _sorter_trace("ok", True, True),
         "flags": {"doc_type_failed": False, "subtype_failed": False}},
        {"trace": _sorter_trace("both", False, False),
         "flags": {"doc_type_failed": True, "subtype_failed": True}},
        {"trace": _sorter_trace("sub", True, False),
         "flags": {"doc_type_failed": False, "subtype_failed": True}},
        {"trace": _sorter_trace("unk", True, True), "flags": None},
    ]
    failed = select_failures(ranked, None)
    assert [r["trace"]["id"] for r in failed] == ["both", "sub"]
    bounded = select_failures(ranked, 1)
    assert [r["trace"]["id"] for r in bounded] == ["both"]


def test_build_subtype_enqueues_failures_only(fake_client, capsys):
    stub = fake_client
    stub.traces = [
        _sorter_trace("s1", doc_type_ok=True, subtype_ok=True),
        _sorter_trace("s2", doc_type_ok=True, subtype_ok=False),
        _sorter_trace("s3", doc_type_ok=False, subtype_ok=False),
    ]
    rc = tool.main_with_args(["build", "--task", "subtype", "--since-days", "60"])
    assert rc == 0
    assert [q["name"] for q in stub.queues] == ["entity-extraction-low-performers"]
    assert {i["objectId"] for i in stub.items} == {"s2", "s3"}
    out = capsys.readouterr().out
    assert "failed: 2" in out
    assert "class-failed: 1" in out
    assert "subtype-failed: 2" in out
    assert "entity-extraction-low-performers" in out


def test_build_subtype_dry_run_writes_nothing(fake_client, capsys):
    stub = fake_client
    stub.traces = [_sorter_trace("s2", doc_type_ok=True, subtype_ok=False)]
    rc = tool.main_with_args(["build", "--task", "subtype", "--dry-run",
                              "--since-days", "60"])
    assert rc == 0
    assert not stub.queues and not stub.items
    out = capsys.readouterr().out
    assert "would enqueue" in out and "subtype FAIL" in out


def test_build_subtype_idempotent(fake_client, capsys):
    stub = fake_client
    stub.traces = [_sorter_trace("s2", doc_type_ok=True, subtype_ok=False),
                   _sorter_trace("s3", doc_type_ok=False, subtype_ok=False)]
    tool.main_with_args(["build", "--task", "subtype", "--since-days", "60"])
    assert len(stub.items) == 2
    rc = tool.main_with_args(["build", "--task", "subtype", "--since-days", "60"])
    assert rc == 0
    assert len(stub.items) == 2
    assert "already present: 2" in capsys.readouterr().out


def test_status_subtype_shows_flags_and_scores(fake_client, capsys):
    stub = fake_client
    stub.traces = [
        _sorter_trace("s2", doc_type_ok=True, subtype_ok=False),
        _sorter_trace("s3", doc_type_ok=False, subtype_ok=False),
    ]
    tool.main_with_args(["build", "--task", "subtype", "--since-days", "60"])
    rc = tool.main_with_args(["status", "--task", "subtype"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "entity-extraction-low-performers" in out
    assert "subtype FAIL" in out
    assert "exact_match" in out or "subtype_acc" in out
    assert "pj-dojo" in out


def test_status_since_days_bounds_scan(fake_client, capsys):
    """status --since-days bounds the trace-meta scan (no all-history pagination)."""
    stub = fake_client
    stub.traces = [
        _sorter_trace("s_old", doc_type_ok=True, subtype_ok=False,
                      timestamp="2026-01-01T00:00:00.000Z"),
    ]
    tool.main_with_args(["build", "--task", "subtype", "--since-days", "365"])
    assert len(stub.items) == 1
    capsys.readouterr()

    rc = tool.main_with_args(["status", "--task", "subtype"])
    assert rc == 0
    assert "sort_s_old.txt" not in capsys.readouterr().out

    rc = tool.main_with_args(["status", "--task", "subtype", "--since-days", "365"])
    assert rc == 0
    assert "sort_s_old.txt" in capsys.readouterr().out


def test_shared_queue_status_filters_items_by_task(fake_client, capsys):
    """The shared queue mixes tasks; status shows only the requested task's items."""
    stub = fake_client
    stub.traces = [
        _trace("e1", 0.71),
        _sorter_trace("s2", doc_type_ok=True, subtype_ok=False),
    ]
    tool.main_with_args(["build", "--threshold", "0.85", "--since-days", "60"])
    tool.main_with_args(["build", "--task", "subtype", "--since-days", "60"])
    assert {i["objectId"] for i in stub.items} == {"e1", "s2"}
    assert len(stub.queues) == 1
    capsys.readouterr()  # drain the builds' output

    rc = tool.main_with_args(["status", "--task", "subtype"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "subtype FAIL" in out and "sort_s2.txt" in out
    assert "doc_e1.txt" not in out

    rc = tool.main_with_args(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc_e1.txt" in out and "sort_s2.txt" not in out
