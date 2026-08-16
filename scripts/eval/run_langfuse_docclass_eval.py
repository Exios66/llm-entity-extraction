#!/usr/bin/env python3
"""LANGFUSE/PHOENIX doc-class evaluation — the hierarchical sorter task.

Runs the sorter over the EXTENDED primary classification (KANBAN-033): the
shared 6 doc classes PLUS ``merger_agreement`` (MAUD corpus), scoring BOTH
the primary ``doc_type`` and the second-level ``doc_subclass`` dimension
(consideration type for merger agreements — MAUD expert GT; record type for
corporate records — content-detected from the document). The tertiary level
is absent by design (human directive: only where the data necessitates it).

Datasets (each row carries ``expected`` doc_type + ``metadata.expected_subclass``):
- ``mailroom-maud-contracts``        — 152 MAUD merger agreements
- ``mailroom-cuad-contracts-full``   — the 510 CUAD contracts (subclass = CUAD subtype)
- ``mailroom-s1-corporate-records``  — EDGAR S-1 corporate-record exhibits

Local JSONL dumps (the reliable path while Braintrust row uploads are
org-capped) are loaded with ``--local-dumps`` — the flat shape the streamers'
``--local-dump`` writes (``{filename, doc_text, expected, expected_subclass,
metadata}``). The two loaders produce identical row shapes, so the eval loop
is byte-for-byte the same either way.

One sorter call per document; deterministic logic scorers
(doc_type_accuracy, subclass_accuracy, exact_match, confidence); manifest
resume; append-only repo experiment log; Arize Phoenix tracing by default
(Langfuse fallback).

Usage:
    python scripts/eval/run_langfuse_docclass_eval.py --dry-run
    python scripts/eval/run_langfuse_docclass_eval.py \\
        --datasets mailroom-maud-contracts,mailroom-cuad-contracts-full \\
        --stratified 120 --seed 42
    python scripts/eval/run_langfuse_docclass_eval.py \\
        --local-dumps data/maud/contracts.jsonl,data/s1_corporate_records/corporate-records.jsonl
    python scripts/eval/run_langfuse_docclass_eval.py --sample 5 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sorter_agent import (  # noqa: E402
    DOC_SUBCLASS_UNKNOWN,
    DOCCLASS_CLASS_KEYS,
    DOCCLASS_CLASSES,
    DOCCLASS_SCHEMA,
    SorterAgent,
    normalize_doc_subclass,
    normalize_subtype,
)
from scripts.eval.run_subtype_eval import _reasoning_span  # noqa: E402
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset  # noqa: E402
from src.experiment_log import default_jsonl_path, default_md_path  # noqa: E402
from src.langfuse_config import load_langfuse_config  # noqa: E402
from src.langfuse_tracing import LangfuseTracer  # noqa: E402
from src.phoenix_tracing import PhoenixTracer, phoenix_enabled  # noqa: E402
from src.prompts import list_prompts  # noqa: E402

_CONFIG = load_braintrust_config()
DEFAULT_DATASETS = "mailroom-maud-contracts,mailroom-cuad-contracts-full,mailroom-s1-corporate-records"
DEFAULT_PROMPT = "sorter_docclass_v0"


class EvalResultShim:
    """Minimal braintrust.EvalResult-compatible row for the shared logger."""

    def __init__(self, input, output, error=None):
        self.input = input
        self.output = output
        self.error = error


class EvalRunShim:
    """Minimal braintrust.Eval-result-compatible container."""

    def __init__(self, results: list):
        self.results = results


def load_docclass_dataset(dataset_names: list[str], project: str, project_id: str,
                          local_dumps: list[Path] | None = None) -> list[dict]:
    """Load rows from Braintrust datasets and/or local JSONL dumps.

    Every returned row carries ``{doc_text, filename, expected, metadata,
    expected_subclass}`` where ``expected`` is the doc_type key and
    ``expected_subclass`` the second-level key (None when the class has no
    subclass dimension — e.g. correspondence).
    """
    rows: list[dict] = []
    valid = set(DOCCLASS_CLASS_KEYS)
    for name in dataset_names:
        dataset = load_braintrust_dataset(project, name, valid=valid, project_id=project_id)
        for d in dataset:
            d["expected_subclass"] = (d.get("metadata") or {}).get("expected_subclass")
            d["source_dataset"] = name
        rows.extend(dataset)
        print(f"  {name}: {len(dataset)} rows")
    for path in (local_dumps or []):
        if not path.exists():
            print(f"WARNING: local dump not found: {path}", file=sys.stderr)
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                expected = str(row.get("expected") or "").strip()
                if expected not in valid:
                    continue
                doc_text = str(row.get("doc_text") or "")
                if not doc_text.strip():
                    continue
                metadata = dict(row.get("metadata") or {})
                rows.append({
                    "doc_text": doc_text,
                    "prompt": str(row.get("prompt") or ""),
                    "filename": str(row.get("filename") or f"row_{len(rows) + 1}"),
                    "expected": expected,
                    "metadata": metadata,
                    "expected_subclass": row.get("expected_subclass") or metadata.get("expected_subclass"),
                    "source_dataset": str(path),
                })
        print(f"  {path}: local dump loaded")
    return rows


def stratified_sample(dataset: list[dict], n: int, seed: int) -> list[dict]:
    """Evenly distribute the sample across expected doc_type classes."""
    import random

    rng = random.Random(seed)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for d in dataset:
        by_class[d["expected"]].append(d)
    per_class = max(1, n // max(1, len(by_class)))
    picked: list[dict] = []
    for cls in sorted(by_class):
        picked.extend(rng.sample(by_class[cls], min(per_class, len(by_class[cls]))))
    if len(picked) < n:
        rest = [d for d in dataset if d not in picked]
        picked.extend(rng.sample(rest, min(n - len(picked), len(rest))))
    return picked[:n]


def random_sample(dataset: list[dict], n: int, seed: int) -> list[dict]:
    """Seeded random sample (mirrors run_subtype_eval.py semantics)."""
    import random

    return random.Random(seed).sample(dataset, min(n, len(dataset)))


def classify_failure(doc_type_ok: bool, subclass_ok: bool,
                     predicted_subclass: str | None) -> str | None:
    """Failure mode for the docclass task (None when the row is correct)."""
    if doc_type_ok and subclass_ok:
        return None
    if not doc_type_ok:
        return "doc_type_miss"
    return "subclass_miss"


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name, help="Braintrust project name (dataset source)")
    parser.add_argument("--project-id", default=_CONFIG.project_id, help="Braintrust project id (dataset source)")
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project, help="Project holding the datasets")
    parser.add_argument("--datasets", default=DEFAULT_DATASETS,
                        help="Comma-separated Braintrust datasets to evaluate")
    parser.add_argument("--local-dumps", default=None,
                        help="Comma-separated local JSONL dumps (replaces Braintrust loading)")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N rows")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N rows")
    parser.add_argument("--stratified", type=int, default=0,
                        help="STRATIFIED sample of N rows: evenly distributed across doc_type classes")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample/--stratified")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT,
                        help=f"Sorter prompt version (default: {DEFAULT_PROMPT})")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max output tokens for the sorter's classification call")
    parser.add_argument("--reasoning-effort", default="medium",
                        help="Reasoning effort for the classification call (default: medium)")
    parser.add_argument("--max-input-chars", type=int, default=100_000,
                        help="Hard safety cap on document text fed to the sorter")
    parser.add_argument("--max-concurrency", type=int, default=8, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_docclass_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/docclass_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--lf-project", default=None, help="Override the Langfuse project name")
    parser.add_argument("--lf-environment", default=None, help="Override the trace environment tag")
    parser.add_argument("--lf-trace-name", default="docclass_classification",
                        help="Langfuse trace name for each document")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    require_env("BRAINTRUST_API_KEY")  # still needed to load Braintrust datasets

    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.prompt_version}_docclass_langfuse"
    )

    dataset_names = [n.strip() for n in args.datasets.split(",") if n.strip()]
    local_dumps = None
    if args.local_dumps:
        local_dumps = [Path(p.strip()) for p in args.local_dumps.split(",") if p.strip()]
        dataset_names = []

    print(f"Loading datasets: {dataset_names or local_dumps}")
    dataset = load_docclass_dataset(dataset_names, args.dataset_project or args.project,
                                    project_id=_CONFIG.project_id, local_dumps=local_dumps)
    if args.stratified:
        dataset = stratified_sample(dataset, args.stratified, args.seed)
        print(f"Stratified {len(dataset)} rows evenly across doc_type "
              f"(requested {args.stratified}, seed {args.seed})")
    elif args.sample:
        dataset = random_sample(dataset, args.sample, args.seed)
    elif args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No rows found in the datasets.")

    class_counts = Counter(d["expected"] for d in dataset)
    subclass_counts = Counter(d["expected_subclass"] for d in dataset if d.get("expected_subclass"))
    print(f"doc_type distribution: {dict(class_counts)}")
    if subclass_counts:
        print(f"subclass GT distribution (where present): {dict(subclass_counts)}")
    validate_dataset(dataset)

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        how = (f"stratified {args.stratified} (even across doc_type, seed {args.seed})"
               if args.stratified else
               f"sample {args.sample} (seed {args.seed})" if args.sample else
               f"limit {args.limit}" if args.limit else "all")
        print(f"Dry run: {len(dataset)} rows ({how}) -> experiment '{experiment_name}'")
        print(f"  sorter={args.prompt_version} model={args.model} "
              f"classes={DOCCLASS_CLASS_KEYS}")
        print(f"  tracing={'phoenix' if phoenix_enabled() else 'langfuse'} "
              f"session={experiment_name} trace_name={args.lf_trace_name}")
        return 0

    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "datasets": args.datasets,
            "dataset_size": len(dataset),
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "model": args.model,
            "prompt_version": args.prompt_version,
            "tracing_backend": "phoenix" if phoenix_enabled() else "langfuse",
        })
        manifest.initialize()

    # ------------------------------------------------------------------
    # Tracer — Arize Phoenix (default, local OpenTelemetry) with Langfuse
    # fallback (mirrors run_langfuse_subtype_eval.py).
    # ------------------------------------------------------------------
    if phoenix_enabled():
        tracer = PhoenixTracer(
            session_id=experiment_name,
            tags=[f"prompt:{args.prompt_version}", args.model.split("/")[-1]],
            trace_name=args.lf_trace_name,
        )
        if tracer.disabled:
            print("WARNING: Phoenix tracing is DISABLED — the run proceeds "
                  "untraced; results still land in the repo experiment log.",
                  file=sys.stderr)
        else:
            print(f"Tracing to Arize Phoenix (local OpenTelemetry, "
                  f"endpoint={__import__('os').environ.get('PHOENIX_ENDPOINT', 'http://localhost:6006/v1/traces')})")
    else:
        lf_config = load_langfuse_config()
        if args.lf_project:
            lf_config = replace(lf_config, project=args.lf_project)
        if args.lf_environment:
            lf_config = replace(lf_config, environment=args.lf_environment)
        tracer = LangfuseTracer(
            config=lf_config,
            session_id=experiment_name,
            tags=[f"prompt:{args.prompt_version}", args.model.split("/")[-1]],
            trace_name=args.lf_trace_name,
        )
        if tracer.disabled:
            print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys "
                  "in langfuse.env) — the run proceeds untraced; results still "
                  "land in the repo experiment log.", file=sys.stderr)
        else:
            print(f"Tracing to Langfuse project '{lf_config.project}' "
                  f"(environment '{lf_config.environment}') at {lf_config.base_url}")

    usage_by_index: dict[int, dict] = {}

    def classify_one(input_data: dict) -> EvalResultShim:
        """Classify ONE document (exactly one sorter call, extended schema)."""
        index = input_data["index"]
        filename = input_data["filename"]
        expected_doc_type = input_data["expected"]
        expected_subclass = input_data.get("expected_subclass") or None

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                return EvalResultShim(
                    input_data,
                    cached.get("scores", {}).get("composite") or {"sorter": {}, "error": "cached incomplete"},
                )

        trace_meta = {
            "datasets": args.datasets,
            "prompt_version": args.prompt_version,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
        }
        with tracer.trace_document(filename, expected_doc_type, trace_meta) as handle:
            sorter = SorterAgent(model=args.model, api_key=openrouter_key,
                                 prompt_version=args.prompt_version,
                                 doc_classes=DOCCLASS_CLASSES, schema=DOCCLASS_SCHEMA,
                                 callbacks=[handle.handler] if handle.handler else None)
            sorter._max_input_chars = args.max_input_chars
            sorter._max_tokens = args.max_tokens
            sorter._reasoning_effort = args.reasoning_effort
            try:
                result = sorter.classify_json(input_data["doc_text"])
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                result = {"doc_type": "correspondence", "contract_subtype": None,
                          "doc_subclass": None, "confidence": 0.0,
                          "reasoning": f"error: {exc}"}
            usage_by_index[index] = sorter._last_usage or {}

            doc_type = str(result.get("doc_type", "correspondence")).strip().lower()
            doc_type_ok = doc_type == expected_doc_type
            predicted_subclass = normalize_doc_subclass(
                result.get("doc_subclass") if doc_type in ("merger_agreement", "corporate_record") else None,
                doc_type,
            ) if expected_subclass else None
            subclass_ok = bool(expected_subclass) and predicted_subclass == expected_subclass
            exact = doc_type_ok and (subclass_ok if expected_subclass else True)
            try:
                confidence = float(result.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0

            composite = {
                "sorter": {
                    "doc_type": doc_type,
                    "contract_subtype": normalize_subtype(
                        result.get("contract_subtype") if doc_type == "contract" else None),
                    "doc_subclass": predicted_subclass,
                    "expected_doc_type": expected_doc_type,
                    "expected_subclass": expected_subclass,
                    "confidence": confidence,
                    "reasoning": _reasoning_span(result, failed=not exact),
                    "doc_type_ok": doc_type_ok,
                    "subclass_ok": subclass_ok,
                    "exact_match": exact,
                    "failure_mode": classify_failure(doc_type_ok, subclass_ok, predicted_subclass),
                    "truncated": sorter._last_truncated,
                },
            }

            handle.set_output(composite)
            handle.score("doc_type_accuracy", 1.0 if doc_type_ok else 0.0,
                         comment="predicted doc_type == expected")
            handle.score("subclass_accuracy", 1.0 if subclass_ok else 0.0,
                         comment="predicted doc_subclass == GT (where present)")
            handle.score("exact_match", 1.0 if exact else 0.0,
                         comment="doc_type AND subclass exact")
            handle.score("confidence", confidence, comment="model-reported confidence")

            if manifest:
                manifest.append({"filename": filename, "status": "completed", "tag": "OK",
                                 "predicted": {"doc_type": doc_type,
                                               "doc_subclass": predicted_subclass},
                                 "error": "",
                                 "expected_doc_type": expected_doc_type,
                                 "expected_subclass": expected_subclass,
                                 "scores": {"composite": composite}})

        return EvalResultShim(input_data, composite)

    rows = [
        {"index": i, "filename": d["filename"], "expected": d["expected"],
         "doc_text": d["doc_text"], "expected_subclass": d.get("expected_subclass")}
        for i, d in enumerate(dataset)
    ]
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {pool.submit(classify_one, row): i for i, row in enumerate(rows)}
        for future, i in futures.items():
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], None, str(exc))
    failures = [r for r in results if r.error]
    for failure in failures:
        print(f"ERROR {failure.input['filename']}: {failure.error}", file=sys.stderr)

    tracer.flush()
    tracer.shutdown()

    if phoenix_enabled():
        tracing_backend = "phoenix"
        tracing_meta = {
            "endpoint": __import__("os").environ.get(
                "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
            "service_name": __import__("os").environ.get(
                "PHOENIX_SERVICE_NAME", "llm-entity-extraction"),
            "session_id": experiment_name,
            "trace_name": args.lf_trace_name,
            "disabled": tracer.disabled,
        }
    else:
        tracing_backend = "langfuse"
        tracing_meta = {
            "project": lf_config.project,
            "environment": lf_config.environment,
            "base_url": lf_config.base_url,
            "session_id": experiment_name,
            "trace_name": args.lf_trace_name,
            "disabled": tracer.disabled,
        }

    log_experiment_to_repo(
        EvalRunShim(results), dataset, args, experiment_name,
        usage_by_index, log_path, md_log_path,
        tracing_backend=tracing_backend,
        tracing_meta=tracing_meta,
    )
    print(f"\nExperiment logged to {log_path}")
    return 0


def log_experiment_to_repo(result, dataset, args, experiment_name,
                           usage, log_path, md_log_path,
                           tracing_backend: str = "langfuse",
                           tracing_meta: dict | None = None) -> None:
    """Append ONE experiment-log record for the docclass run."""
    from statistics import mean

    from src.experiment_log import append_experiment, append_markdown, git_snapshot

    rows = [r for r in result.results if r.error is None and isinstance(r.output, dict)]
    ok = [r.output for r in rows if isinstance(r.output, dict)]

    def _mean(key: str) -> float | None:
        values = [float((o.get("sorter") or {}).get(key))
                  for o in ok if (o.get("sorter") or {}).get(key) is not None]
        return round(mean(values), 4) if values else None

    doc_type_acc = _mean("doc_type_ok")
    subclass_acc = _mean("subclass_ok")
    exact_match = _mean("exact_match")
    confidence = _mean("confidence")

    # Per-class accuracy (doc_type level) + subclass confusion.
    per_class: dict[str, dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    subclass_confusion: dict[str, Counter] = defaultdict(Counter)
    failure_insights = []
    mode_counts: Counter = Counter()
    per_row = []
    for r in result.results:
        output = r.output if isinstance(r.output, dict) else {}
        sorter = output.get("sorter") or {}
        index = r.input.get("index", -1) if isinstance(r.input, dict) else -1
        filename = r.input.get("filename") if isinstance(r.input, dict) else ""
        expected_doc_type = r.input.get("expected") if isinstance(r.input, dict) else "?"
        expected_subclass = r.input.get("expected_subclass") if isinstance(r.input, dict) else None
        per_row.append({
            "filename": filename,
            "status": "error" if r.error is not None else "completed",
            "error": r.error,
            "sorter": sorter,
            "sorter_tokens": usage.get(index) or {},
        })
        if r.error is None:
            per_class[expected_doc_type]["total"] += 1
            if sorter.get("doc_type_ok"):
                per_class[expected_doc_type]["correct"] += 1
            if expected_subclass:
                predicted = sorter.get("doc_subclass") or DOC_SUBCLASS_UNKNOWN
                subclass_confusion[expected_subclass][predicted] += 1
            if not sorter.get("exact_match"):
                mode = sorter.get("failure_mode") or "unknown"
                mode_counts[mode] += 1
                failure_insights.append({
                    "filename": filename,
                    "expected": {"doc_type": expected_doc_type,
                                 "doc_subclass": expected_subclass},
                    "predicted": {"doc_type": sorter.get("doc_type"),
                                  "doc_subclass": sorter.get("doc_subclass")},
                    "failure_mode": mode,
                    "reasoning": sorter.get("reasoning"),
                })

    scores = {
        "doc_type_accuracy": doc_type_acc,
        "subclass_accuracy": subclass_acc,
        "exact_match": exact_match,
        "confidence": confidence,
        "n_rows": len(rows),
        "n_errors": len(result.results) - len(rows),
        "per_class_accuracy": {k: round(v["correct"] / v["total"], 4) if v["total"] else None
                               for k, v in sorted(per_class.items())},
        "subclass_confusion": {k: dict(v) for k, v in sorted(subclass_confusion.items())},
        "sorter": {
            "failure_insights": {
                "mode_counts": dict(mode_counts),
                "n_failed": len(failure_insights),
                "failures": failure_insights[:200],
            },
        },
    }

    record = {
        "experiment_name": experiment_name,
        "task": "docclass_classification",
        "model": args.model,
        "prompt_version": args.prompt_version,
        "data_source": args.datasets,
        "data_fingerprint": dataset_fingerprint(dataset),
        "parameters": {
            "datasets": args.datasets,
            "sample": args.sample,
            "stratified": args.stratified,
            "seed": args.seed,
            "max_input_chars": args.max_input_chars,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
            "temperature": args.temperature,
            "tracing_backend": tracing_backend,
            "tracing_meta": tracing_meta or {},
        },
        "scores": scores,
        "per_row": per_row,
        "tokens": {"total": sum(int((u or {}).get("total_tokens", 0)) for u in usage.values())},
        "git_snapshot": git_snapshot(),
    }
    jsonl_path = append_experiment(record, log_path)
    append_markdown(record, md_log_path)
    print(f"\nExperiment logged to {jsonl_path}")


if __name__ == "__main__":
    raise SystemExit(main())
