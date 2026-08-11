#!/usr/bin/env python3
"""LANGFUSE MIRROR of the sorter-only subtype evaluation.

Runs the EXACT SAME experiment as ``run_subtype_eval.py`` — same Braintrust
dataset (``mailroom-cuad-contracts-full``), same one-sorter-call-per-PDF task,
same deterministic logic scorers (exact_match, subtype_accuracy,
subtype_accuracy_equiv, confidence), same manifest resume, same append-only
repo experiment log — but traces every classification into a SEPARATE
Langfuse environment instead of a Braintrust experiment.

Separation model: the tracer uses its OWN project keys from ``langfuse.env``
(never the primary llm-mailroom project's), every trace carries
``environment=<LANGFUSE_ENVIRONMENT>``, and ``session_id`` groups all traces
of one experiment. Langfuse runs never consume Braintrust scored-run quotas —
the scorers are computed locally and logged per trace as NUMERIC scores.

Usage:
    python scripts/eval/run_langfuse_subtype_eval.py --dry-run
    python scripts/eval/run_langfuse_subtype_eval.py \
        --dataset mailroom-cuad-contracts-full --sorter-prompt-version sorter_v5
    python scripts/eval/run_langfuse_subtype_eval.py --stratified 200 --seed 42
    python scripts/eval/run_langfuse_subtype_eval.py \
        --manifest data/manifests/subtype_langfuse.jsonl   # resumable
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sorter_agent import (  # noqa: E402
    SUBTYPE_UNKNOWN,
    SorterAgent,
    equivalent_subtypes,
    normalize_subtype,
)
from scripts.eval.run_subtype_eval import (  # noqa: E402
    _reasoning_span,
    classify_failure,
    log_experiment_to_repo,
    stratified_sample,
)
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset  # noqa: E402
from src.experiment_log import default_jsonl_path, default_md_path  # noqa: E402
from src.langfuse_config import load_langfuse_config  # noqa: E402
from src.langfuse_tracing import LangfuseTracer  # noqa: E402
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
    parser.add_argument("--stratified", type=int, default=0,
                        help="STRATIFIED sample of N contracts: evenly distributed across every "
                             "expected subtype (identical semantics to run_subtype_eval.py)")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample/--stratified")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--sorter-prompt-version", default="sorter_v3",
                        help="Sorter prompt version (classifies doc_type + contract_subtype)")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max output tokens for the sorter's classification call")
    parser.add_argument("--reasoning-effort", default="medium",
                        help="Reasoning effort for the classification call (default: medium)")
    parser.add_argument("--max-input-chars", type=int, default=100_000,
                        help="Hard safety cap on document text fed to the sorter "
                             "(head+tail window when exceeded)")
    parser.add_argument("--max-concurrency", type=int, default=8, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_subtype_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/subtype_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--lf-project", default=None,
                        help="Override the Langfuse project name (default: langfuse.env)")
    parser.add_argument("--lf-environment", default=None,
                        help="Override the trace environment tag (default: langfuse.env)")
    parser.add_argument("--lf-trace-name", default="subtype_classification",
                        help="Langfuse trace name for each document")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    require_env("BRAINTRUST_API_KEY")  # still needed to load the Braintrust dataset

    available = list_prompts()
    if args.sorter_prompt_version not in available:
        parser.error(f"Unknown prompt version {args.sorter_prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.sorter_prompt_version}_subtype_langfuse"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset,
                                      project_id=_CONFIG.project_id)
    for d in dataset:
        d["expected_subtype"] = normalize_subtype((d.get("metadata") or {}).get("category"))
    if args.stratified:
        dataset = stratified_sample(dataset, args.stratified, args.seed)
        print(f"Stratified {len(dataset)} contracts evenly across subtypes "
              f"(requested {args.stratified}, seed {args.seed})")
    elif args.sample:
        dataset = random_sample(dataset, args.sample, args.seed)
    elif args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No contracts found in the dataset.")

    for d in dataset:
        d["expected_subtype"] = normalize_subtype((d.get("metadata") or {}).get("category"))
    unknown = [d for d in dataset if d["expected_subtype"] == SUBTYPE_UNKNOWN]
    if unknown:
        print(f"WARNING: {len(unknown)} rows have unnormalized CUAD folders:", file=sys.stderr)
        for d in unknown[:5]:
            print(f"  {(d.get('metadata') or {}).get('category')!r}", file=sys.stderr)
    validate_dataset(dataset)

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        how = (f"stratified {args.stratified} (even across subtypes, seed {args.seed})"
               if args.stratified else
               f"sample {args.sample} (seed {args.seed})" if args.sample else
               f"limit {args.limit}" if args.limit else "all")
        print(f"Dry run: {len(dataset)} contracts ({how}) -> experiment '{experiment_name}'")
        print(f"  sorter={args.sorter_prompt_version} model={args.model}")
        print(f"  tracing=langfuse session={experiment_name} trace_name={args.lf_trace_name}")
        return 0

    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "dataset": args.dataset,
            "dataset_size": len(dataset),
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "model": args.model,
            "sorter_prompt_version": args.sorter_prompt_version,
            "tracing_backend": "langfuse",
        })
        manifest.initialize()

    # ------------------------------------------------------------------
    # Langfuse tracer — separate environment from the primary project
    # ------------------------------------------------------------------
    lf_config = load_langfuse_config()
    if args.lf_project:
        lf_config = replace(lf_config, project=args.lf_project)
    if args.lf_environment:
        lf_config = replace(lf_config, environment=args.lf_environment)
    tracer = LangfuseTracer(
        config=lf_config,
        session_id=experiment_name,
        tags=[f"prompt:{args.sorter_prompt_version}", args.model.split("/")[-1]],
        trace_name=args.lf_trace_name,
    )
    if tracer.disabled:
        print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys in "
              "langfuse.env) — the run proceeds untraced; results still land in "
              "the repo experiment log.", file=sys.stderr)
    else:
        print(f"Tracing to Langfuse project '{lf_config.project}' "
              f"(environment '{lf_config.environment}') at {lf_config.base_url}")

    usage_by_index: dict[int, dict] = {}

    def classify_one(input_data: dict) -> EvalResultShim:
        """Classify ONE PDF's contract subtype (exactly one sorter call)."""
        index = input_data["index"]
        filename = input_data["filename"]
        expected_subtype = input_data["expected_subtype"]

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                return EvalResultShim(
                    input_data,
                    cached.get("scores", {}).get("composite") or {"sorter": {}, "error": "cached incomplete"},
                )

        trace_meta = {
            "dataset": args.dataset,
            "prompt_version": args.sorter_prompt_version,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
        }
        with tracer.trace_document(filename, expected_subtype, trace_meta) as handle:
            sorter = SorterAgent(model=args.model, api_key=openrouter_key,
                                 prompt_version=args.sorter_prompt_version,
                                 callbacks=[handle.handler] if handle.handler else None)
            sorter._max_input_chars = args.max_input_chars
            sorter._max_tokens = args.max_tokens
            sorter._reasoning_effort = args.reasoning_effort
            try:
                result = sorter.classify_json(input_data["doc_text"])
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                result = {"doc_type": "correspondence", "contract_subtype": SUBTYPE_UNKNOWN,
                          "confidence": 0.0, "reasoning": f"error: {exc}"}
            usage_by_index[index] = sorter._last_usage or {}

            doc_type = str(result.get("doc_type", "correspondence")).strip().lower()
            subtype = normalize_subtype(result.get("contract_subtype"))
            try:
                confidence = float(result.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            doc_type_ok = doc_type == "contract"
            subtype_ok = doc_type_ok and subtype == expected_subtype
            subtype_ok_equiv = doc_type_ok and equivalent_subtypes(subtype, expected_subtype)

            composite = {
                "sorter": {
                    "doc_type": doc_type,
                    "contract_subtype": subtype,
                    "expected_subtype": expected_subtype,
                    "confidence": confidence,
                    "reasoning": _reasoning_span(result, failed=not subtype_ok),
                    "doc_type_ok": doc_type_ok,
                    "subtype_ok": subtype_ok,
                    "subtype_ok_equiv": subtype_ok_equiv,
                    "failure_mode": classify_failure({
                        "doc_type_ok": doc_type_ok,
                        "contract_subtype": subtype,
                        "subtype_ok_equiv": subtype_ok_equiv,
                    }) if not subtype_ok else None,
                    "truncated": sorter._last_truncated,
                },
            }

            # Same deterministic logic scorers as the Braintrust runner,
            # logged per trace as NUMERIC Langfuse scores (no LLM scorers).
            handle.set_output(composite)
            handle.score("exact_match", 1.0 if doc_type_ok else 0.0,
                         comment="doc_type == contract")
            handle.score("subtype_accuracy", 1.0 if subtype_ok else 0.0,
                         comment="normalized subtype == CUAD folder")
            handle.score("subtype_accuracy_equiv", 1.0 if subtype_ok_equiv else 0.0,
                         comment="exact OR defensible equivalent family")
            handle.score("confidence", confidence, comment="model-reported confidence")

            if manifest:
                manifest.append({"filename": filename, "status": "completed", "tag": "OK",
                                 "predicted": {"doc_type": doc_type,
                                               "contract_subtype": subtype},
                                 "error": "",
                                 "expected_subtype": expected_subtype,
                                 "scores": {"composite": composite}})

        return EvalResultShim(input_data, composite)

    rows = [
        {"index": i, "filename": d["filename"], "expected": d["expected"],
         "doc_text": d["doc_text"], "expected_subtype": d["expected_subtype"]}
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

    log_experiment_to_repo(
        EvalRunShim(results), dataset, args, experiment_name,
        usage_by_index, log_path, md_log_path,
        tracing_backend="langfuse",
        tracing_meta={
            "project": lf_config.project,
            "environment": lf_config.environment,
            "base_url": lf_config.base_url,
            "session_id": experiment_name,
            "trace_name": args.lf_trace_name,
            "disabled": tracer.disabled,
        },
    )
    print(f"\nExperiment logged to {log_path}")
    return 0


def random_sample(dataset: list[dict], n: int, seed: int) -> list[dict]:
    """Seeded random sample (mirrors run_subtype_eval.py semantics)."""
    import random

    return random.Random(seed).sample(dataset, min(n, len(dataset)))


if __name__ == "__main__":
    raise SystemExit(main())
