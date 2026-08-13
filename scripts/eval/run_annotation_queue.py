#!/usr/bin/env python3
"""Human-in-the-loop annotation queue for low-performing extraction traces.

Builds a Langfuse **annotation queue** from the entity-extraction pipeline
(``contract_entity_extraction`` traces in the llm-dojo environment) that
filters IN the low performers: traces whose attached deterministic task
score (``overall_extraction_score`` by default) falls below a threshold are
enqueued as ``PENDING`` items for a human reviewer.

The queue is the HITL loop around the experiment cycle:

1. ``build``  — pull extraction traces, rank by score, enqueue the worst.
2. humans    — review in the Langfuse UI (the queue URL is printed; each
               item opens its trace: predicted output vs GT, per-field
               scores, the specialist span, per-chunk generations).
3. annotate  — reviewers score traces (via the queue's score configs, or
               any score name) directly in the UI; those annotations are
               the labeled misses for the next prompt iteration.
4. ``status`` — list the queue with per-item scores + trace URLs so the
               backlog is auditable.

Uses the Langfuse public API directly (annotation-queues endpoints) with
the same credentials as the mirror tracers (``langfuse.env``,
:func:`src.langfuse_config.load_langfuse_config`). Idempotent: a queue is
created once by name; traces already in the queue are never re-enqueued.

Network note: every subcommand talks to Langfuse (this script is the
mirror-side companion of ``run_langfuse_*_eval.py``); ``--dry-run``
performs the full scan + ranking but performs no writes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import structlog  # noqa: E402

from src.langfuse_config import load_langfuse_config  # noqa: E402

logger = structlog.get_logger(__name__)

TRACE_NAME = "contract_entity_extraction"
DEFAULT_QUEUE_NAME = "entity-extraction-low-performers"
DEFAULT_ANNOTATION_CONFIG = "annotation-verdict"
DEFAULT_ANNOTATION_CATEGORIES = [
    {"label": "correct", "value": 1},
    {"label": "partial", "value": 0.5},
    {"label": "incorrect", "value": 0},
]
DEFAULT_QUEUE_DESCRIPTION = (
    "Extraction traces (contract_entity_extraction) below the quality bar — "
    "enqueued automatically from the llm-dojo mirror; review the specialist "
    "span + per-chunk generations against the CUAD ground truth and score "
    "the trace in the UI."
)
DEFAULT_THRESHOLD = 0.85
DEFAULT_SCORE_NAME = "overall_extraction_score"
DEFAULT_SESSION_CONTAINS = "extraction_langfuse"
PAGE_SIZE = 100


class LangfuseApiError(RuntimeError):
    """Raised when the Langfuse public API returns an error status."""


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class AnnotationQueueClient:
    """Minimal Langfuse public-API client for traces + annotation queues.

    All methods are thin wrappers over the Langfuse REST API (Basic auth
    with the project public/secret keys); pagination is handled for the
    list endpoints.
    """

    def __init__(self, base_url: str, public_key: str, secret_key: str,
                 timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth = (public_key, secret_key)
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, params: dict | None = None,
                 json_body: dict | None = None, _retries: int = 5) -> dict:
        url = f"{self.base_url}/api/public/{path.lstrip('/')}"
        for attempt in range(_retries + 1):
            resp = requests.request(
                method, url, params=params, json=json_body, auth=self._auth,
                timeout=self._timeout)
            if resp.status_code == 429 and attempt < _retries:
                retry_after = 1.0
                try:
                    details = resp.json().get("details") or {}
                    retry_after = float(details.get("retryAfterSeconds", 1.0))
                except ValueError:
                    pass
                # honor the server's reset window, with a small safety margin
                time.sleep(min(retry_after + 1.0, 60.0))
                logger.warning("rate_limited_retrying", path=path,
                               attempt=attempt + 1, wait_s=retry_after)
                continue
            if resp.status_code >= 400:
                raise LangfuseApiError(
                    f"{method} {path} -> {resp.status_code}: {resp.text[:300]}")
            if not resp.content:
                return {}
            return resp.json()
        raise LangfuseApiError(f"{method} {path} -> rate limited after retries")

    def _get_all(self, path: str, params: dict | None = None) -> list[dict]:
        """Page through a cursor/pagination list endpoint."""
        out: list[dict] = []
        page, seen = 1, 0
        while True:
            body = self._request("GET", path, params={**(params or {}), "page": page, "limit": PAGE_SIZE})
            rows = body.get("data", [])
            out.extend(rows)
            seen += len(rows)
            meta = body.get("meta", {}) or {}
            total = meta.get("totalItems", 0)
            if not rows or (total and seen >= total) or (len(rows) < PAGE_SIZE and seen == len(out)):
                break
            page += 1
            if page > 200:  # safety valve
                break
        return out

    # ------------------------------------------------------------------
    # Traces
    # ------------------------------------------------------------------

    def list_extraction_traces(self, name: str, since: datetime | None,
                               session_contains: str | None) -> list[dict]:
        """Fetch trace summaries (with scores + input) matching the task.

        Filtering is done server-side on the trace ``name``; the
        ``session_contains`` / prompt-version scoping happens in
        :meth:`keep_for_pipeline` on the caller side because session ids
        are not filter columns.

        Note: the list endpoint returns score *ids* (strings), so
        :meth:`trace_with_scores` must be called per trace before ranking.
        """
        filters: list[dict] = [{
            "type": "string", "column": "name", "operator": "=", "value": name,
        }]
        if since is not None:
            filters.append({
                "type": "datetime", "column": "timestamp", "operator": ">=",
                "value": _iso(since),
            })
        return self._get_all(
            "traces",
            params={"filter": json.dumps(filters), "fields": "core,io,scores"})

    def trace_with_scores(self, trace: dict) -> dict:
        """Expand score ids into score objects via the single-trace endpoint.

        Intended for small volumes only (e.g. the ``status`` subcommand);
        the Langfuse public API rate-limits per-trace reads.
        """
        scores = trace.get("scores") or []
        if scores and isinstance(scores[0], dict):
            return trace
        full = self._request(
            "GET", f"traces/{trace['id']}", params={"fields": "core,io,scores"})
        if full:
            return full
        return trace

    @staticmethod
    def composite_score(trace: dict, score_name: str) -> float | None:
        """Rank score from the trace ``output`` composite (no extra reads).

        The mirror tracer writes the composite to the trace output via
        ``trace_handle.set_output`` — the same value the task score was
        derived from, so the ranking needs zero additional API calls.
        """
        output = trace.get("output") or {}
        if not isinstance(output, dict):
            return None
        key = {"overall_extraction_score": "overall_score"}.get(score_name, score_name)
        value = output.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def keep_for_pipeline(trace: dict, session_contains: str,
                          prompt_version_prefix: str) -> bool:
        """Keep traces belonging to the entity-extraction pipeline.

        A trace belongs to the pipeline when its session id marks an
        extraction run and its input identifies a contracts specialist
        prompt version (chained runs and other tasks are excluded).
        """
        session = trace.get("sessionId") or ""
        if session_contains and session_contains not in session:
            return False
        inp = trace.get("input") or {}
        prompt_version = (inp.get("prompt_version") or "")
        if prompt_version_prefix and not prompt_version.startswith(prompt_version_prefix):
            return False
        return True

    @staticmethod
    def score_value(trace: dict, score_name: str) -> float | None:
        """The last attached value for ``score_name`` on the trace."""
        value: float | None = None
        for score in trace.get("scores") or []:
            if score.get("name") == score_name:
                value = score.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def trace_input_field(trace: dict, field: str) -> str:
        inp = trace.get("input") or {}
        return str(inp.get(field) or "")

    # ------------------------------------------------------------------
    # Annotation queues
    # ------------------------------------------------------------------

    def list_queues(self) -> list[dict]:
        return self._get_all("annotation-queues")

    def create_queue(self, name: str, description: str,
                     score_config_ids: list[str] | None = None) -> dict:
        body: dict[str, Any] = {
            "name": name, "description": description,
            "scoreConfigIds": score_config_ids or [],
        }
        return self._request("POST", "annotation-queues", json_body=body)

    def get_or_create_queue(self, name: str, description: str,
                            score_config_ids: list[str] | None = None) -> dict:
        for queue in self.list_queues():
            if queue.get("name") == name:
                return queue
        return self.create_queue(name, description, score_config_ids)

    def list_queue_items(self, queue_id: str,
                         status: str | None = None) -> list[dict]:
        params = {"status": status} if status else None
        return self._get_all(f"annotation-queues/{queue_id}/items", params=params)

    def enqueue_item(self, queue_id: str, trace_id: str,
                     status: str = "PENDING") -> dict:
        return self._request(
            "POST", f"annotation-queues/{queue_id}/items",
            json_body={"objectId": trace_id, "objectType": "TRACE",
                       "status": status})

    # ------------------------------------------------------------------
    # Project context (for review URLs)
    # ------------------------------------------------------------------

    def project_id(self, project_name: str) -> str | None:
        for project in self._get_all("projects"):
            if project.get("name") == project_name:
                return project.get("id")
        return None


def trace_review_url(base_url: str, project_id: str, trace_id: str) -> str:
    return f"{base_url.rstrip('/')}/project/{project_id}/traces/{trace_id}"


def select_low_performers(ranked: list[dict], score_name: str, threshold: float,
                          limit: int | None, include_unscored: bool = False) -> list[dict]:
    """Traces whose ``score_name`` < threshold, worst first.

    ``ranked`` items are ``{"trace": ..., "score": float|None, ...}``;
    unscored traces are excluded unless ``include_unscored`` (they land
    last, still within ``limit``).
    """
    bad = [r for r in ranked if r["score"] is not None and r["score"] < threshold]
    unscored = [r for r in ranked if r["score"] is None]
    bad.sort(key=lambda r: r["score"])
    if include_unscored:
        bad.extend(unscored)
    if limit is not None:
        bad = bad[:limit]
    return bad


def print_summary(queue: dict, items: list[dict], base_url: str,
                  project_id: str | None, dry_run: bool) -> None:
    action = "would enqueue" if dry_run else "enqueued"
    print(f"queue          : {queue.get('name')} ({queue.get('id')})")
    print(f"project        : {project_id or '?'}")
    if project_id:
        print(f"review at      : {base_url.rstrip('/')}/project/{project_id}/annotation-queues/{queue.get('id')}")
    print(f"{action}        : {len(items)} trace(s)")
    for item in items:
        trace = item["trace"]
        url = (trace_review_url(base_url, project_id, trace["id"])
               if project_id else trace["id"])
        score = item["score"]
        score_text = "n/a" if score is None else f"{score:.4f}"
        print(f"  score={score_text}  {trace_input_name(trace)}")
        print(f"    {url}")


def trace_input_name(trace: dict) -> str:
    return AnnotationQueueClient.trace_input_field(trace, "filename")


def build_queue(args: argparse.Namespace) -> int:
    config = load_langfuse_config(args.env_file)
    client = AnnotationQueueClient(
        config.base_url, config.public_key, config.secret_key)

    since = (datetime.now(timezone.utc) - timedelta(days=args.since_days)
             if args.since_days else None)
    logger.info("scanning_traces", name=TRACE_NAME, since_days=args.since_days)
    traces = client.list_extraction_traces(TRACE_NAME, since, args.session_contains)
    kept = [t for t in traces
            if client.keep_for_pipeline(t, args.session_contains, "contracts_specialist")]
    ranked = [{"trace": t,
               "score": client.composite_score(t, args.score_name),
               "filename": trace_input_name(t)} for t in kept]
    low = select_low_performers(ranked, args.score_name, args.threshold,
                                args.limit, args.include_unscored)
    print(f"traces scanned : {len(traces)}  (pipeline: {len(kept)}, "
          f"below {args.threshold}: {len([r for r in ranked if r['score'] is not None and r['score'] < args.threshold])}, "
          f"unscored: {len([r for r in ranked if r['score'] is None])})")

    if args.dry_run or not low:
        print_summary({"name": args.queue_name, "id": "(dry-run)"},
                      low, config.base_url, None, True)
        print("(dry-run — nothing written)" if args.dry_run else
              "(nothing to enqueue)")
        return 0

    queue = client.get_or_create_queue(args.queue_name,
                                       args.queue_description,
                                       args.score_config_ids)
    existing = {item.get("objectId")
                for item in client.list_queue_items(queue["id"])}
    fresh = [r for r in low if r["trace"]["id"] not in existing]
    for r in low:
        if r["trace"]["id"] in existing:
            logger.info("already_in_queue", trace_id=r["trace"]["id"])
    for r in fresh:
        client.enqueue_item(queue["id"], r["trace"]["id"])
        logger.info("enqueued", trace_id=r["trace"]["id"],
                    score=r["score"])
    project_id = client.project_id(config.project)
    print_summary(queue, low, config.base_url, project_id, dry_run=False)
    print(f"newly enqueued : {len(fresh)}  (already present: {len(low) - len(fresh)})")
    return 0


def queue_status(args: argparse.Namespace) -> int:
    config = load_langfuse_config(args.env_file)
    client = AnnotationQueueClient(
        config.base_url, config.public_key, config.secret_key)
    queue = None
    for candidate in client.list_queues():
        if candidate.get("name") == args.queue_name:
            queue = candidate
            break
    if queue is None:
        print(f"queue not found: {args.queue_name}")
        return 1
    items = client.list_queue_items(queue["id"])
    scores = {}
    for item in items:
        tid = item.get("objectId")
        if tid not in scores:
            trace = client._request("GET", f"traces/{tid}", params={"fields": "core,io,scores"})
            scores[tid] = (client.score_value(trace, args.score_name),
                           trace_input_name(trace),
                           (trace.get("input") or {}).get("prompt_version") or "")
    pending = [i for i in items if i.get("status") == "PENDING"]
    processed = [i for i in items if i.get("status") == "PROCESSED"]
    project_id = client.project_id(config.project)
    print(f"queue          : {queue['name']} ({queue['id']})")
    print(f"items          : {len(items)}  (pending: {len(pending)}, processed: {len(processed)})")
    if project_id:
        print(f"review at      : {config.base_url}/project/{project_id}/annotation-queues/{queue['id']}")
    for item in sorted(items, key=lambda i: (i.get("status") != "PENDING",
                                             scores.get(i.get("objectId"), (None, "", ""))[0] or 0)):
        score, filename, version = scores.get(item.get("objectId"), (None, "", ""))
        score_text = "n/a" if score is None else f"{score:.4f}"
        print(f"  [{item.get('status'):<9}] {score_text:>7}  "
              f"{(version or '')[:28]:<28} {filename[:60]}")
        if project_id:
            print(f"      {trace_review_url(config.base_url, project_id, item['objectId'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HITL annotation queue for low-performing extraction traces (llm-dojo).")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--queue-name", default=DEFAULT_QUEUE_NAME)
    common.add_argument("--env-file", default="langfuse.env",
                        help="dotenv file with LANGFUSE_* keys (default: langfuse.env)")
    common.add_argument("--score-name", default=DEFAULT_SCORE_NAME,
                        help=f"trace score to rank on (default: {DEFAULT_SCORE_NAME})")

    p_build = sub.add_parser("build", parents=[common],
                             help="scan extraction traces and enqueue low performers")
    p_build.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                         help=f"enqueue traces with score < threshold (default: {DEFAULT_THRESHOLD})")
    p_build.add_argument("--limit", type=int, default=None,
                         help="max traces to enqueue (worst first)")
    p_build.add_argument("--since-days", type=int, default=30,
                         help="only traces newer than N days (default: 30)")
    p_build.add_argument("--session-contains", default=DEFAULT_SESSION_CONTAINS,
                         help="session-id substring that marks extraction runs")
    p_build.add_argument("--include-unscored", action="store_true",
                         help="also enqueue traces missing the score (old runs)")
    p_build.add_argument("--score-config-ids", default=None,
                         help="comma-separated score config ids attached to the queue "
                              "for UI annotations")
    p_build.add_argument("--queue-description", default=DEFAULT_QUEUE_DESCRIPTION)
    p_build.add_argument("--dry-run", action="store_true",
                         help="scan + rank only; make no writes")

    p_status = sub.add_parser("status", parents=[common],
                              help="list queue items with scores + trace URLs")
    return parser


def main_with_args(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    score_config_ids = getattr(args, "score_config_ids", None)
    if score_config_ids:
        args.score_config_ids = [s.strip() for s in score_config_ids.split(",") if s.strip()]
    else:
        args.score_config_ids = None
    if args.command == "build":
        return build_queue(args)
    return queue_status(args)


def main() -> None:
    sys.exit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
