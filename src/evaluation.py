"""Evaluation validation, accounting, and resumable-run helpers.

Ported from the RVL-CDIP classifier repo's ``src/evaluation.py``: fail-fast
dataset validation, dataset fingerprints, and the thread-safe JSONL manifest
that lets an interrupted Braintrust evaluation resume exactly where it left
off (the manifest header must match the rerun's metadata exactly).
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.taxonomy import doc_class_keys

DOCUMENT_CLASSES = doc_class_keys()


def validate_dataset(dataset: list[dict], valid: set[str] | None = None) -> None:
    """Fail before an evaluation if its input cannot produce a valid score.

    Args:
        dataset: List of rows with ``filename`` and ``expected`` keys.
        valid: Allowed expected values (defaults to the taxonomy doc classes).
    """
    if not dataset:
        raise ValueError("evaluation dataset is empty")

    valid = valid or set(DOCUMENT_CLASSES)
    seen: set[str] = set()
    for index, row in enumerate(dataset):
        filename = str(row.get("filename") or "")
        expected = row.get("expected")
        if not filename:
            raise ValueError(f"dataset row {index} has no filename")
        if filename in seen:
            raise ValueError(f"dataset contains duplicate filename: {filename}")
        seen.add(filename)
        if expected not in valid:
            raise ValueError(f"dataset row {filename} has invalid expected class: {expected!r}")


def dataset_fingerprint(dataset: list[dict]) -> str:
    """Return a stable identity for labels and filenames in an evaluation."""
    payload = "\n".join(
        f"{row['filename']}\0{row['expected']}" for row in dataset
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Eval-runner concurrency: sample-size-aware worker scaling + rate-limit retry
# ---------------------------------------------------------------------------
# The langfuse eval runners submit one row per worker. Wall time scales with
# the number of workers until the provider/tenant rate limit dominates
# (measured ~230ms burst 429s on qwen via Alibaba at sustained concurrency,
# KANBAN-024; OpenRouter failover absorbs most), so the adaptive default
# raises workers with the sample size and stops at a diminishing-returns
# ceiling. An explicit ``--max-concurrency N`` always wins; the retry helper
# makes even the ceiling safe by backing off on transient 429s.
#
# Single source of truth for ``CONCURRENCY_MIN`` / ``CONCURRENCY_MAX`` so the
# runners do not drift.

CONCURRENCY_MIN = 8  # floor: tiny samples still need enough workers to pipeline
CONCURRENCY_MAX = 32  # ceiling: beyond ~32 concurrent OpenRouter calls the
# tenant rate limit dominates and wall time stops shrinking
CONCURRENCY_ROWS_PER_WORKER = 25  # slope: +1 worker per ~25 rows


def resolve_concurrency(
    n_rows: int,
    requested: int | None = None,
    *,
    floor: int = CONCURRENCY_MIN,
    ceiling: int = CONCURRENCY_MAX,
    rows_per_worker: int = CONCURRENCY_ROWS_PER_WORKER,
) -> int:
    """Resolve an eval runner's worker count; auto scales with the sample.

    An explicit ``requested`` value (``--max-concurrency N``) wins, else the
    pool scales with the sample size until diminishing returns:

        workers = min(ceiling, max(1, min(floor + ceil(n_rows / step), n_rows)))

    — 5 rows -> 5 workers, 30 -> 10, 200 -> 25 capped at 32, 676 -> 32. The
    ceiling embodies the diminishing-returns point (provider rate limits);
    never more workers than rows.
    """
    if requested:
        return max(1, int(requested))
    if n_rows <= 0:
        return max(1, floor)
    scaled = floor + max(1, -(-n_rows // rows_per_worker))  # ceil division
    return min(ceiling, max(1, min(scaled, n_rows)))


def call_with_rate_limit_retry(
    fn,
    *args,
    retries: int = 4,
    base_delay: float = 2.0,
    factor: float = 2.0,
    max_delay: float = 30.0,
    jitter: float = 0.25,
    stats: dict | None = None,
    **kwargs,
):
    """Call ``fn(*args, **kwargs)`` retrying transient rate-limit errors.

    A rate limit is detected when the exception chain (message or type) says
    "rate limit" or "429" — the classic OpenAI-compatible provider burst
    shape (qwen via Alibaba 429s, KANBAN-024). Retries use exponential
    backoff with jitter; other exceptions propagate unchanged. When ``stats``
    is a dict, it receives ``rate_limit_retries``.
    """
    import random as _random
    import time as _time

    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - must inspect the chain
            chain = str(exc)
            if "rate limit" not in chain.lower() and "429" not in str(type(exc).__name__) \
                    and "429" not in chain:
                raise
            if attempt >= retries:
                raise
            attempt += 1
            if stats is not None:
                stats["rate_limit_retries"] = stats.get("rate_limit_retries", 0) + 1
            sleep = min(max_delay, base_delay * factor ** (attempt - 1))
            sleep *= 1 + _random.uniform(-jitter, jitter)
            _time.sleep(max(0.0, sleep))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManifestStore:
    """Thread-safe JSONL manifest used to resume interrupted evaluations.

    The first line is a run header. Subsequent lines are append-only row states;
    the last state for a filename is authoritative. A manifest is reusable only
    when its run metadata matches the current evaluation exactly.
    """

    def __init__(self, path: str | Path, metadata: dict[str, Any]):
        self.path = Path(path)
        self.metadata = metadata
        self._lock = threading.Lock()
        self.records: dict[str, dict[str, Any]] = {}
        self.reused = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if not lines:
                return
            header = json.loads(lines[0])
            if header.get("type") != "header" or header.get("metadata") != self.metadata:
                raise ValueError("manifest metadata does not match this evaluation")
            for line in lines[1:]:
                record = json.loads(line)
                if record.get("filename"):
                    self.records[record["filename"]] = record
            self.reused = True
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"cannot reuse manifest {self.path}: {exc}") from exc

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > 0:
            return
        self.path.write_text(
            json.dumps({"type": "header", "metadata": self.metadata}, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def get_completed(self, filename: str) -> dict[str, Any] | None:
        record = self.records.get(filename)
        if record and record.get("status") == "completed":
            return record
        return None

    def append(self, record: dict[str, Any]) -> None:
        record = {**record, "updated_at": utc_now()}
        line = json.dumps(record, sort_keys=True) + "\n"
        with self._lock:
            self.initialize()
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line)
                stream.flush()
            self.records[str(record["filename"])] = record
