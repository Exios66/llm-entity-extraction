#!/usr/bin/env python3
"""LANGFUSE MIRROR of the specialist-only extraction evaluation.

Runs the EXACT SAME experiment as ``run_extraction_eval.py`` — same Braintrust
dataset, same ContractsSpecialist task, same deterministic field-type-aware
content scorers, same manifest resume, same append-only repo experiment log —
but traces into a SEPARATE Langfuse environment (own project keys in
``langfuse.env``; every trace tagged with ``LANGFUSE_ENVIRONMENT``).

Per-agent designated task: every trace carries ONE observation per document
named ``contracts_specialist`` with the specialist's task scores
(overall_extraction_score, field_presence, overall_verified_precision,
category_presence, schema_valid) attached to the agent's own observation —
the metrics surface per agent in Langfuse over time.

Usage:
    python scripts/eval/run_langfuse_extraction_eval.py --dry-run
    python scripts/eval/run_langfuse_extraction_eval.py --sample 5 --seed 42 \
        --manifest data/manifests/extraction_langfuse.jsonl
    python scripts/eval/run_langfuse_extraction_eval.py \
        --prompt-version contracts_specialist_v11
"""

from __future__ import annotations

import argparse
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.specialist_agents import ContractsSpecialist  # noqa: E402
from scripts.eval.run_extraction_eval import (  # noqa: E402
    load_expected_fields,
    log_experiment_to_repo,
    print_extraction_summary,
)
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.env_utils import (  # noqa: E402
    add_research_funding_flag,
    assert_production_run,
    require_env,
    resolve_openrouter_key,
)
from src.evaluation import (  # noqa: E402
    ManifestStore,
    call_with_rate_limit_retry,
    dataset_fingerprint,
    resolve_concurrency,
    validate_dataset,
)
from src.experiment_log import default_jsonl_path, default_md_path  # noqa: E402
from src.field_scoring import get_field_types, score_category_presence, score_extraction  # noqa: E402
from src.tracing import resolve_tracer  # noqa: E402
from src.prompts import list_prompts  # noqa: E402

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


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


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name, help="Braintrust project name (dataset source)")
    parser.add_argument("--project-id", default=_CONFIG.project_id, help="Braintrust project id (dataset source)")
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project, help="Project holding the dataset")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N contracts")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N contracts")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--prompt-version", default="contracts_specialist_v2",
                        help="Specialist prompt version to test (one per experiment)")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=16384, help="Max output tokens")
    parser.add_argument("--reasoning-effort", default="none",
                        help="Reasoning effort for the extraction call")
    parser.add_argument("--max-input-chars", type=int, default=150_000,
                        help="Hard safety cap on document text fed to the model "
                             "(150k default: the full corpus's largest contracts run "
                             "106-122k chars; head+tail window when exceeded)")
    parser.add_argument("--chunked", action="store_true",
                        help="Chunked extraction pass (v15 architecture): split the "
                             "document into overlapping windows, extract each in its "
                             "own call, merge (list fields union with dedupe, scalars "
                             "first-non-null, confidence max) — nothing is truncated")
    parser.add_argument("--chunk-chars", type=int, default=90_000,
                        help="Chunk window size for --chunked (default: 90000 chars)")
    parser.add_argument("--chunk-overlap", type=int, default=8_000,
                        help="Overlap carried between chunks for --chunked "
                             "(default: 8000 chars — re-quotes boundary clauses)")
    parser.add_argument("--audit", action="store_true",
                        help="Runner-level audit pass (KANBAN-060): after the "
                             "extraction, a SECOND structured call per window "
                             "feeds the already-quoted clauses back and returns "
                             "missed obligation sentences (verbatim, ADDING-only) "
                             "for the absent-family recall mass; merged as a "
                             "union with normalized dedupe")
    parser.add_argument("--max-concurrency", type=int, default=None,
                        help="Concurrent API calls (default: AUTO — scales with the "
                             "sample size, 8..32 workers, until diminishing returns / "
                             "rate limits; pass N to pin)")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_extraction_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/extraction_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--lf-project", default=None, help="Override the Langfuse project name")
    parser.add_argument("--lf-environment", default=None, help="Override the trace environment tag")
    parser.add_argument("--lf-trace-name", default="contract_entity_extraction",
                        help="Langfuse trace name for each document")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--master-labels", type=Path, default=None,
                        help="Master ground-truth labels CSV (default: MASTER_LABELS_CSV env "
                             "or data/cuad/master_clauses.csv, the repo-local curated table). "
                             "The curated normalized per-category answers feed the MAE/R² "
                             "diagnostics (dates, durations) in the experiment log.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    add_research_funding_flag(parser)
    args = parser.parse_args(argv)

    openrouter_key = resolve_openrouter_key(args.research_funding_key)
    require_env("BRAINTRUST_API_KEY")  # still needed to load the Braintrust dataset

    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.prompt_version}_extraction_langfuse"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset,
                                      project_id=_CONFIG.project_id)
    dataset = load_expected_fields(dataset)
    total_rows = len(dataset)
    if args.sample:
        dataset = random.Random(args.seed).sample(dataset, min(args.sample, len(dataset)))
    if args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No contracts found in the dataset.")
    with_truth = [d for d in dataset if d.get("expected_fields")]
    if not with_truth:
        parser.error(f"Dataset {args.dataset!r} has no CUAD clause-label ground truth.")
    print(f"{len(with_truth)}/{len(dataset)} rows carry CUAD ground truth")
    assert_production_run(args.research_funding_key, dry_run=args.dry_run,
                          selected_rows=len(with_truth), total_rows=total_rows)

    field_types = get_field_types("contract")
    scored_fields = sorted({f for d in with_truth for f in d["expected_fields"]})
    validate_dataset(with_truth)

    from src.master_labels import DEFAULT_MASTER_LABELS, load_master_labels
    master_labels_path = args.master_labels or DEFAULT_MASTER_LABELS
    master_labels = load_master_labels(master_labels_path)
    master_labels_used = bool(master_labels)

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        print(f"Dry run: {len(with_truth)} contracts -> experiment '{experiment_name}'")
        print(f"  prompt_version={args.prompt_version} model={args.model}")
        if args.chunked:
            print(f"  mode=chunked windows={args.chunk_chars} overlap={args.chunk_overlap}")
        if args.audit:
            print("  audit=ON (runner-level missed-category audit pass, second call per window)")
        print(f"  fields scored: {scored_fields}")
        print(f"  tracing=langfuse session={experiment_name} trace_name={args.lf_trace_name}")
        return 0

    # ------------------------------------------------------------------
    # Tracer — Langfuse PRIMARY, local Arize Phoenix server as fallback
    # (human directive 2026-08-16; resolver in src/tracing.py).
    # ------------------------------------------------------------------
    tracer, tracing_backend, tracing_meta = resolve_tracer(
        session_id=experiment_name,
        trace_name=args.lf_trace_name,
        tags=[f"extractor:{args.prompt_version}", args.model.split("/")[-1]],
        lf_project=args.lf_project,
        lf_environment=args.lf_environment,
    )
    if tracing_backend == "langfuse":
        if tracer.disabled:
            print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys in "
                  "langfuse.env) — the run proceeds untraced; results still land in "
                  "the repo experiment log.", file=sys.stderr)
        else:
            print(f"Tracing to Langfuse project '{tracing_meta['project']}' "
                  f"(environment '{tracing_meta['environment']}') at {tracing_meta['base_url']}")
    else:
        if tracer.disabled:
            print("WARNING: Phoenix tracing is DISABLED — the run proceeds "
                  "untraced; results still land in the repo experiment log.",
                  file=sys.stderr)
        else:
            print(f"Tracing to Arize Phoenix (local OpenTelemetry, "
                  f"endpoint={tracing_meta['endpoint']}) "
                  f"— Langfuse fallback (keys unavailable)")


    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "dataset": args.dataset,
            "dataset_size": len(with_truth),
            "dataset_fingerprint": dataset_fingerprint(with_truth),
            "model": args.model,
            "prompt_version": args.prompt_version,
            "tracing_backend": tracing_backend,
        })
        manifest.initialize()

    # ------------------------------------------------------------------
    # Tracer — Langfuse PRIMARY, local Arize Phoenix server as fallback
    # (human directive 2026-08-16; resolver in src/tracing.py).
    # ------------------------------------------------------------------
    tracer, tracing_backend, tracing_meta = resolve_tracer(
        session_id=experiment_name,
        trace_name=args.lf_trace_name,
        tags=[f"extractor:{args.prompt_version}", args.model.split("/")[-1]],
        lf_project=args.lf_project,
        lf_environment=args.lf_environment,
    )
    if tracing_backend == "langfuse":
        if tracer.disabled:
            print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys in "
                  "langfuse.env) — the run proceeds untraced; results still land in "
                  "the repo experiment log.", file=sys.stderr)
        else:
            print(f"Tracing to Langfuse project '{tracing_meta['project']}' "
                  f"(environment '{tracing_meta['environment']}') at {tracing_meta['base_url']}")
    else:
        if tracer.disabled:
            print("WARNING: Phoenix tracing is DISABLED — the run proceeds "
                  "untraced; results still land in the repo experiment log.",
                  file=sys.stderr)
        else:
            print(f"Tracing to Arize Phoenix (local OpenTelemetry, "
                  f"endpoint={tracing_meta['endpoint']}) "
                  f"— Langfuse fallback (keys unavailable)")

    usage_by_index: dict[int, dict] = {}

    def extract_one(input_data: dict) -> EvalResultShim:
        """Extract entities from one contract; returns the COMPOSITE output."""
        filename = input_data["filename"]
        expected_fields = input_data["expected_fields"]

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                return EvalResultShim(
                    input_data,
                    cached.get("scores", {}).get("composite") or {
                        "predicted": cached.get("predicted") or {}, "overall_score": 0.0,
                        "field_presence": 0.0, "schema_valid": 0.0,
                        "field_scores": {}, "ambiguous_fields": [], "error": "cached incomplete",
                    },
                )

        doc_text = input_data["doc_text"]
        with tracer.trace_document(
            filename, input_data["expected"],
            {"dataset": args.dataset, "prompt_version": args.prompt_version,
             "model": args.model, "doc_category": input_data.get("doc_category")},
        ) as trace_handle:
            with tracer.agent_observation(
                "contracts_specialist",
                {"prompt_version": args.prompt_version, "model": args.model,
                 "reasoning_effort": args.reasoning_effort,
                 "max_concurrency": args.max_concurrency},
            ) as specialist_handle:
                specialist = ContractsSpecialist(
                    model=args.model, api_key=openrouter_key,
                    prompt_version=args.prompt_version,
                    callbacks=[specialist_handle.handler] if specialist_handle.handler else None)
                specialist._max_input_chars = args.max_input_chars
                specialist._max_tokens = args.max_tokens
                specialist._reasoning_effort = args.reasoning_effort
                try:
                    if args.chunked:
                        predicted = specialist.extract_chunked(
                            doc_text, args.chunk_chars, args.chunk_overlap)
                    else:
                        predicted = specialist.extract(doc_text)
                    if args.audit and not predicted.get("_parse_error"):
                        predicted = specialist.audit_extraction(
                            doc_text, predicted, args.chunk_chars, args.chunk_overlap)
                except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                    print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
                    composite = {"predicted": {}, "error": str(exc), "schema_valid": 0.0,
                                 "overall_score": 0.0, "field_presence": 0.0,
                                 "category_presence": 0.0,
                                 "field_scores": {}, "ambiguous_fields": []}
                    if manifest:
                        manifest.append({"filename": filename, "status": "error",
                                         "tag": "ERROR!", "predicted": {}, "error": str(exc),
                                         "expected_fields": expected_fields,
                                         "scores": {"composite": composite}})
                    return EvalResultShim(input_data, composite)

                usage_by_index[input_data["index"]] = specialist._last_usage or {}

                if predicted.get("_parse_error"):
                    composite = {"predicted": {}, "error": "parse error", "schema_valid": 0.0,
                                 "overall_score": 0.0, "field_presence": 0.0,
                                 "category_presence": 0.0,
                                 "field_scores": {}, "ambiguous_fields": []}
                    if manifest:
                        manifest.append({"filename": filename, "status": "error",
                                         "tag": "ERROR!", "predicted": {}, "error": "parse error",
                                         "expected_fields": expected_fields,
                                         "scores": {"composite": composite}})
                    return EvalResultShim(input_data, composite)

                result = score_extraction("contract", field_types, predicted, expected_fields,
                                          doc_text=doc_text)
                populated = sum(1 for key, value in expected_fields.items()
                                if predicted.get(key) not in (None, "", []))
                field_presence = populated / len(expected_fields) if expected_fields else 0.0
                category_presence, presence_detail = score_category_presence(
                    predicted, input_data.get("expected_presence") or {}, field_types)

                composite = {
                    "predicted": predicted,
                    "overall_score": result.overall_score or 0.0,
                    "field_presence": field_presence,
                    "schema_valid": 1.0,
                    "field_scores": result.field_scores,
                    "category_presence": category_presence,
                    "category_presence_detail": presence_detail,
                    "entity_list_f1": {k: v.score for k, v in result.entity_list_scores.items()},
                    "entity_list_scores": {
                        k: {"precision": v.precision, "recall": v.recall, "f1": v.f1,
                            "matched": v.matched, "n_predicted": v.matched + v.unmatched_predicted,
                            "n_expected": v.matched + v.unmatched_expected}
                        for k, v in result.entity_list_scores.items()
                    },
                    "entity_list_audit": result.entity_list_audit,
                    "overall_verified_precision": result.overall_verified_precision or 0.0,
                    "ambiguous_fields": result.ambiguous_fields,
                    "truncated": bool(specialist._last_truncated),
                    "chunked": bool(args.chunked),
                    "audit": bool(args.audit),
                    "n_chunks": int(getattr(specialist, "_last_n_chunks", 0) or 0),
                }

                specialist_handle.set_output({
                    "overall_score": composite["overall_score"],
                    "field_presence": field_presence,
                    "category_presence": category_presence,
                    "overall_verified_precision": composite["overall_verified_precision"],
                    "schema_valid": 1.0,
                    "truncated": composite["truncated"],
                })
                specialist_handle.score("overall_extraction_score", composite["overall_score"],
                                        comment="mean deterministic content score vs CUAD GT")
                specialist_handle.score("field_presence", field_presence,
                                        comment="share of expected fields populated")
                specialist_handle.score("overall_verified_precision",
                                        composite["overall_verified_precision"],
                                        comment="factuality guard (grounded share)")
                specialist_handle.score("category_presence", category_presence,
                                        comment="CUAD YES/NO category conformance")
                specialist_handle.score("schema_valid", 1.0,
                                        comment="parseable schema-conformant JSON")

            trace_handle.set_output(composite)

            if manifest:
                manifest.append({"filename": filename, "status": "completed",
                                 "tag": "OK", "predicted": predicted, "error": "",
                                 "expected_fields": expected_fields,
                                 "scores": {"composite": composite}})

        return EvalResultShim(input_data, composite)

    rows = [
        {"index": i, "filename": d["filename"], "expected": d["expected"],
         "doc_text": d["doc_text"], "expected_fields": d["expected_fields"],
         "expected_presence": d.get("expected_presence") or {},
         "doc_category": d.get("doc_category")}
        for i, d in enumerate(with_truth)
    ]
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    # Adaptive concurrency: scale the worker pool with the sample size until
    # diminishing returns / rate limits (explicit --max-concurrency N wins).
    args.max_concurrency = resolve_concurrency(len(rows), args.max_concurrency)
    retry_stats: dict = {"rate_limit_retries": 0}
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {pool.submit(call_with_rate_limit_retry, extract_one, row, stats=retry_stats): i for i, row in enumerate(rows)}
        for future, i in futures.items():
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], None, str(exc))
    for failure in [r for r in results if r.error]:
        print(f"ERROR {failure.input['filename']}: {failure.error}", file=sys.stderr)

    tracer.flush()
    tracer.shutdown()

    run = EvalRunShim(results)
    print_extraction_summary(run, scored_fields)
    log_experiment_to_repo(
        run, scored_fields, with_truth, args, experiment_name,
        usage_by_index, log_path, md_log_path,
        tracing_backend=tracing_backend,
        tracing_meta=tracing_meta,
        field_types=field_types,
        master_labels=master_labels if master_labels_used else None,
        master_labels_path=str(master_labels_path) if master_labels_used else None,
    )
    print(f"\nExperiment logged to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
