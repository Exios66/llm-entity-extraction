"""Repository-local experiment log.

Every eval run appends ONE JSON record (plus a human-readable markdown
section) to ``reports/experiment_log.jsonl`` / ``reports/experiment_log.md``,
so the repo carries a complete, append-only history of every experiment:
model, prompt version, data source, all run parameters, token usage, every
score, and every per-row result.

Paths are overridable via the ``EXPERIMENT_LOG_PATH`` /
``EXPERIMENT_LOG_MD_PATH`` env vars (or the ``--experiment-log`` CLI flag in
the eval runners); tests redirect them to a tmp dir. The log is deliberately
append-only — one line per experiment — and never overwritten.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JSONL_ENV = "EXPERIMENT_LOG_PATH"
MD_ENV = "EXPERIMENT_LOG_MD_PATH"
DEFAULT_JSONL = "reports/experiment_log.jsonl"
DEFAULT_MD = "reports/experiment_log.md"


def default_jsonl_path() -> Path:
    """Resolve the JSONL log path from env (or the repo default)."""
    return Path(os.environ.get(JSONL_ENV, DEFAULT_JSONL))


def default_md_path() -> Path:
    """Resolve the markdown log path from env (or the repo default)."""
    return Path(os.environ.get(MD_ENV, DEFAULT_MD))


def git_snapshot() -> dict:
    """Best-effort repo state at run time (commit hash + dirty flag)."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        )
        return {"commit": commit or None, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return {"commit": None, "dirty": None}


def mean(values: list[float]) -> float:
    """Arithmetic mean over a list of numbers (0.0 for an empty list)."""
    return sum(values) / len(values) if values else 0.0


def tokens_summary(usage_records: list[dict]) -> dict:
    """Aggregate per-row usage dicts into one tokens/cost summary.

    Each usage record comes from the agent's ``_last_usage``:
    ``{prompt_tokens, completion_tokens, total_tokens, cost}``. Rows replayed
    from a manifest carry no usage (they were paid for in the original run).
    """
    prompt = completion = total = 0
    cost_values: list[float] = []
    rows = 0
    for usage in usage_records or []:
        if not isinstance(usage, dict) or not usage:
            continue
        prompt += int(usage.get("prompt_tokens") or 0)
        completion += int(usage.get("completion_tokens") or 0)
        total += int(usage.get("total_tokens") or 0)
        cost = usage.get("cost")
        if isinstance(cost, (int, float)):
            cost_values.append(float(cost))
        rows += 1
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "cost_usd": round(mean(cost_values), 6),
        "cost_total_usd": round(sum(cost_values), 6),
        "rows_with_usage": rows,
    }


def append_experiment(record: dict, path: Path | None = None) -> Path:
    """Append one JSON record to the experiment log (one line per run).

    The record is stamped with an ISO timestamp if absent. Returns the path
    actually written.
    """
    path = Path(path or default_jsonl_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(record)
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    return path


def experiment_markdown(record: dict) -> str:
    """Render a human-readable section for one experiment record."""
    lines: list[str] = []
    name = record.get("experiment_name") or record.get("name") or "experiment"
    task = record.get("task", "")
    lines.append(f"## {name}" + (f"  ({task})" if task else ""))
    lines.append("")

    summary = record.get("summary") or {}
    for key, label in (
        ("timestamp", "Timestamp"),
        ("model", "Model"),
        ("prompt_version", "Prompt"),
        ("git", "Git"),
        ("data_source", "Data source"),
        ("n_samples", "Samples"),
        ("parameters", "Parameters"),
        ("tokens", "Tokens"),
        ("scores", "Scores"),
    ):
        value = record.get(key) if key != "summary" else None
        if value is None:
            continue
        if isinstance(value, dict):
            lines.append(f"- **{label}**: `{json.dumps(value, default=str)}`")
        else:
            lines.append(f"- **{label}**: {value}")
    lines.append("")

    results = record.get("results") or []
    if results:
        present = {key for row in results for key in row}
        columns = [
            col for col in ("filename", "status", "expected", "predicted",
                            "correct", "overall_score", "field_presence", "error")
            if col in present
        ]
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("|" + "|".join("---" for _ in columns) + "|")
        for row in results:
            cells = []
            for col in columns:
                value = row.get(col)
                if isinstance(value, bool):
                    value = "✓" if value else "✗"
                elif isinstance(value, float):
                    value = f"{value:.4f}"
                cells.append(str(value if value not in (None, "") else "—"))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines)


def append_markdown(record: dict, path: Path | None = None) -> Path:
    """Append a human-readable section to the markdown experiment log."""
    path = Path(path or default_md_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(experiment_markdown(record))
        if not str(record.get("experiment_name", "")).endswith("\n"):
            fh.write("\n")
    return path
