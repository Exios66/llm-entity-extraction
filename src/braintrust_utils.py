"""Shared Braintrust HTTP, dataset, and experiment helpers.

Used by the dataset streamers (``scripts/datasets/``), the eval runners
(``scripts/eval/``), and the report generators (``scripts/reporting/``) so the
Braintrust wire protocol (experiment fetch, dataset loading, experiment
listing) lives in one place.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

from src.taxonomy import doc_class_keys

VALID_CLASSES = doc_class_keys()
EXPERIMENT_FETCH_RETRIES = 6
EXPERIMENT_FETCH_LIMIT = 1000  # events per paginated fetch (API supports up to 1000)


# ---------------------------------------------------------------------------
# Experiment + dataset HTTP helpers
# ---------------------------------------------------------------------------


def _v1_api_base(api_base: str) -> str:
    """Ensure an api_base points at the REST endpoints under ``/v1``."""
    api_base = api_base.rstrip("/")
    return f"{api_base}/v1" if not api_base.endswith("/v1") else api_base


def list_experiments(api_key: str, project_id: str, api_base: str = "https://api.braintrust.dev/v1") -> list[dict]:
    """Return metadata for every experiment in a project."""
    resp = requests.get(
        f"{_v1_api_base(api_base)}/experiment",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"project_id": project_id, "limit": 200},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("objects", [])


def list_datasets(api_key: str, project_id: str, api_base: str = "https://api.braintrust.dev/v1") -> list[dict]:
    """Return metadata for every dataset in a project."""
    resp = requests.get(
        f"{_v1_api_base(api_base)}/dataset",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"project_id": project_id, "limit": 200},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("objects", [])


def dataset_exists(api_key: str, project_id: str, name: str, api_base: str = "https://api.braintrust.dev/v1") -> bool:
    """Return True when a dataset with ``name`` exists in the project."""
    return any(d.get("name") == name for d in list_datasets(api_key, project_id, api_base))


def delete_dataset_by_name(
    api_key: str,
    project_id: str,
    name: str,
    api_base: str = "https://api.braintrust.dev/v1",
) -> str | None:
    """Delete a dataset by name if it exists; return its id or None."""
    headers = {"Authorization": f"Bearer {api_key}"}
    for dataset in list_datasets(api_key, project_id, api_base):
        if dataset.get("name") == name:
            dataset_id = dataset["id"]
            resp = requests.delete(f"{_v1_api_base(api_base)}/dataset/{dataset_id}", headers=headers, timeout=60)
            resp.raise_for_status()
            return dataset_id
    return None


def fetch_experiment_rows(
    api_key: str,
    experiment_id: str,
    api_base: str = "https://api.braintrust.dev/v1",
    max_retries: int = EXPERIMENT_FETCH_RETRIES,
    timeout: int = 300,
) -> list[dict]:
    """Fetch every event (span) of an experiment, retrying on rate limits."""
    headers = {"Authorization": f"Bearer {api_key}"}
    rows: list[dict] = []
    cursor = None
    while True:
        body = {"limit": EXPERIMENT_FETCH_LIMIT}
        if cursor:
            body["cursor"] = cursor
        resp = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{_v1_api_base(api_base)}/experiment/{experiment_id}/fetch",
                    headers=headers,
                    json=body,
                    timeout=timeout,
                )
                resp.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if resp is not None and resp.status_code == 429 and attempt < max_retries - 1:
                    wait = min(30, 10 * (2 ** attempt))
                    print(f"  Rate limited, waiting {wait}s (retry {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                elif attempt < max_retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  Retry {attempt + 1}/{max_retries} after {wait}s ({e})")
                    time.sleep(wait)
                else:
                    raise
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)
                    print(f"  Timeout, retry {attempt + 1}/{max_retries} after {wait}s")
                    time.sleep(wait)
                else:
                    raise
        data = resp.json()
        batch = data.get("events", [])
        rows.extend(batch)
        cursor = data.get("cursor")
        if not cursor or not batch:
            break
    return rows


def find_experiment_by_name(api_key: str, project_id: str, name: str, api_base: str = "https://api.braintrust.dev/v1") -> dict | None:
    """Return experiment metadata for the experiment with ``name`` (or None)."""
    for exp in list_experiments(api_key, project_id, api_base):
        if exp.get("name") == name:
            return exp
    return None


def resolve_prompt_version(experiment_meta: dict) -> str:
    """Return the prompt version (e.g. ``sorter_v0``) for an experiment.

    Prefers the experiment's ``metadata.prompt_version``, then parses the
    version out of the experiment name (``qwen3.7-flash_sorter_v0``).
    """
    metadata = experiment_meta.get("metadata") or {}
    version = metadata.get("prompt_version")
    if version:
        return str(version)
    match = re.search(r"_p(v?\d+(?:\.\d+)?|[a-z0-9_]+)$", experiment_meta.get("name") or "")
    return match.group(1) if match else "unknown"


# ---------------------------------------------------------------------------
# Dataset loading (text documents)
# ---------------------------------------------------------------------------


def load_braintrust_dataset(
    project: str,
    dataset_name: str,
    dataset_api_key: str | None = None,
) -> list[dict]:
    """Load a text-document Braintrust dataset into eval records.

    Returns ``[{doc_text, filename, expected}]`` where the expected value is a
    doc class key. Rows without a valid label or document text are skipped.
    """
    import braintrust

    api_key = dataset_api_key or os.environ.get("BRAINTRUST_API_KEY")
    if api_key:
        braintrust.login(api_key=api_key)

    dataset = braintrust.init_dataset(project=project, name=dataset_name)
    records: list[dict] = []
    for i, row in enumerate(dataset):
        expected = row.get("expected")
        if isinstance(expected, dict):
            expected = expected.get("doc_type") or expected.get("expected_doc_class")
        expected = str(expected or "").strip()
        if expected not in VALID_CLASSES:
            continue

        input_data = row.get("input") or {}
        if isinstance(input_data, str):
            doc_text = input_data
        elif isinstance(input_data, dict):
            doc_text = input_data.get("doc_text") or input_data.get("text") or ""
        else:
            doc_text = ""
        doc_text = str(doc_text or "")
        if not doc_text.strip():
            continue

        filename = input_data.get("filename") if isinstance(input_data, dict) else ""
        records.append({
            "doc_text": doc_text,
            "filename": str(filename or f"document_{i + 1}"),
            "expected": expected,
            "metadata": dict(input_data.get("metadata") or {}) if isinstance(input_data, dict) else {},
        })
    return records


def upload_text_dataset(
    records: list[dict],
    project_id: str,
    dataset_name: str,
    api_key: str,
    *,
    description: str = "",
    metadata: dict | None = None,
    experiment_name: str | None = None,
    on_progress=None,
) -> dict:
    """Insert text-document records into a Braintrust dataset.

    Each record: ``{"input": {...}, "expected": ..., "metadata": {...}}``.
    Returns ``{"inserted": n, "failed": m, "failure_details": [...]}`` and
    logs one summary experiment row (``create-<dataset>``) so dataset
    creation is traceable in the project.
    """
    import braintrust

    braintrust.login(api_key=api_key)
    dataset = braintrust.init_dataset(project_id=project_id, name=dataset_name)
    metadata = dict(metadata or {})
    metadata.update({"dataset": dataset_name, "records": len(records)})

    experiment = braintrust.init_experiment(
        project_id=project_id,
        experiment=experiment_name or f"create-{dataset_name}",
        description=description or f"Build text dataset '{dataset_name}'",
        metadata={"task": "dataset_creation", "dataset": dataset_name, **metadata},
    )

    inserted = failed = 0
    failures: list[str] = []
    for i, record in enumerate(records):
        try:
            dataset.insert(
                input=record["input"],
                expected=record["expected"],
                metadata=record.get("metadata", {}),
            )
            inserted += 1
        except Exception as exc:  # noqa: BLE001 - one bad row shouldn't abort
            failed += 1
            failures.append(f"{record.get('input', {}).get('filename', i)}: {exc}")
        if on_progress and (i + 1) % 25 == 0:
            on_progress(i + 1, len(records))

    dataset.flush()
    dataset.close()

    experiment.log(
        input={"dataset": dataset_name, "records": len(records)},
        output={"inserted": inserted, "failed": failed},
        scores={"insertion_rate": inserted / max(1, len(records)),
                "failure_rate": failed / max(1, len(records))},
        metrics={"records": inserted, "failed": failed},
        metadata={"failures": failures[:50]},
    )
    experiment.close()

    return {"inserted": inserted, "failed": failed, "failures": failures}


def load_experiment_task_rows(rows: list[dict]) -> list[dict]:
    """Extract per-task (root span) rows from a raw experiment fetch.

    Each returned dict has ``expected``, ``output``, ``input``, ``filename``,
    ``reasoning``, and ``metrics`` where available. Used by report generation.
    """
    tasks: list[dict] = []
    span_meta: dict[str, dict[str, Any]] = {}

    for row in rows:
        root = row.get("root_span_id") or row.get("span_id") or ""
        metadata = row.get("metadata") or {}
        if isinstance(metadata, dict) and (metadata.get("reasoning") or metadata.get("filename")):
            span_meta.setdefault(root, {}).update(metadata)

    for row in rows:
        output = row.get("output")
        if output is None or row.get("span_attributes") is not None and "task" not in (row.get("span_attributes") or {}):
            continue
        expected = row.get("expected")
        if expected is None:
            continue
        root = row.get("root_span_id") or row.get("span_id") or ""
        meta = dict(row.get("metadata") or {})
        meta.update(span_meta.get(root, {}))
        tasks.append({
            "expected": expected,
            "output": output,
            "input": row.get("input"),
            "filename": str(meta.get("filename") or "") or _filename_from_input(row.get("input")),
            "reasoning": str(meta.get("reasoning") or ""),
            "metrics": dict(row.get("metrics") or {}),
        })
    return tasks


def _filename_from_input(input_data: Any) -> str:
    if isinstance(input_data, dict):
        return str(input_data.get("filename") or "")
    return ""


# ---------------------------------------------------------------------------
# Misclassification analysis (for reports)
# ---------------------------------------------------------------------------


def find_misses(task_rows: list[dict]) -> list[dict]:
    """Return every scored-but-wrong task row.

    Each result dict has ``expected``, ``predicted``, ``filename``,
    ``reasoning``, and ``metrics``. Rows without a valid expected/output are
    skipped.
    """
    misses: list[dict] = []
    for row in task_rows:
        expected = row["expected"]
        output = row["output"]
        if expected not in VALID_CLASSES or not output:
            continue
        predicted = str(output).strip().lower()
        if predicted == expected:
            continue
        misses.append({
            "expected": expected,
            "predicted": predicted,
            "filename": row["filename"],
            "reasoning": row["reasoning"],
            "metrics": row["metrics"],
        })
    return misses
