#!/usr/bin/env python3
"""LANGFUSE MIRROR of the CHAINED two-agent evaluation (sorter -> specialist).

Runs the EXACT SAME experiment as ``run_chained_eval.py`` — same Braintrust
dataset, same sorter -> contracts-specialist pipeline, same deterministic
logic scorers, same manifest resume, same append-only repo experiment log —
but traces into a SEPARATE Langfuse environment (own project keys in
``langfuse.env``; every trace tagged with ``LANGFUSE_ENVIRONMENT``).

Per-agent designated tasks: every trace carries ONE observation PER AGENT —
``sorter`` (scores: exact_match, subtype_accuracy, subtype_accuracy_equiv,
confidence) and ``contracts_specialist`` (scores: overall_extraction_score,
field_presence, overall_verified_precision, category_presence, schema_valid)
— with the scores attached to the AGENT's own observation, so per-agent
performance metrics are derivable over time in Langfuse. The sorter's
class + subclass pass to the specialist via ``handoff_context``; with the
default ``--handoff-scope subtype`` the specialist is additionally cued with
the predicted subtype's CUAD field-group scope (expected schema fields +
applicable/never-applicable clause categories).

Usage:
    python scripts/eval/run_langfuse_chained_eval.py --dry-run
    python scripts/eval/run_langfuse_chained_eval.py --sample 5 --seed 42 \
        --manifest data/manifests/chained_langfuse.jsonl
    python scripts/eval/run_langfuse_chained_eval.py \
        --sorter-prompt-version sorter_v6 \
        --extractor-prompt-version contracts_specialist_v11
    python scripts/eval/run_langfuse_chained_eval.py --handoff-scope none
"""

from __future__ import annotations

import argparse
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sorter_agent import SUBTYPE_UNKNOWN, SorterAgent, normalize_subtype  # noqa: E402
from agents.specialist_agents import ContractsSpecialist  # noqa: E402
from scripts.eval.run_chained_eval import log_experiment_to_repo  # noqa: E402
from scripts.eval.run_extraction_eval import load_expected_fields  # noqa: E402
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.cuad_ground_truth import build_subtype_handoff  # noqa: E402
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
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--sorter-prompt-version", default="sorter_v1",
                        help="Sorter prompt version (classifies doc_type + contract_subtype)")
    parser.add_argument("--extractor-prompt-version", default="contracts_specialist_v4",
                        help="Contracts specialist prompt version (extraction)")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=32768,
                        help="Max output tokens (extraction of 50+ verbatim clauses on long "
                             "agreements exceeds 16k — 16,384 truncates the JSON)")
    parser.add_argument("--reasoning-effort", default="none",
                        help="Reasoning effort for the extraction call")
    parser.add_argument("--sorter-reasoning-effort", default="medium",
                        help="Reasoning effort for the SORTER's classification call")
    parser.add_argument("--max-input-chars", type=int, default=150_000,
                        help="Hard safety cap on document text fed to the agents "
                             "(150k default: the full corpus's largest contracts run "
                             "106-122k chars; head+tail window when exceeded)")
    parser.add_argument("--max-concurrency", type=int, default=None,
                        help="Concurrent API calls (default: AUTO — scales with the "
                             "sample size, 8..32 workers, until diminishing returns / "
                             "rate limits; pass N to pin)")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{sorter}+{extractor}_chained_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/chained_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--handoff-scope", choices=("subtype", "none", "ground_truth"), default="subtype",
                        help="Specialist handoff scope: 'subtype' (default) appends the "
                             "PREDICTED subtype's CUAD field-group cue to the extractor "
                             "context; 'none' reproduces the legacy handoff line only")
    parser.add_argument("--lf-project", default=None, help="Override the Langfuse project name")
    parser.add_argument("--lf-environment", default=None, help="Override the trace environment tag")
    parser.add_argument("--lf-trace-name", default="chained_sorter_extractor",
                        help="Langfuse trace name for each document")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    add_research_funding_flag(parser)
    args = parser.parse_args(argv)

    openrouter_key = resolve_openrouter_key(args.research_funding_key)
    require_env("BRAINTRUST_API_KEY")  # still needed to load the Braintrust dataset

    available = list_prompts()
    for version in (args.sorter_prompt_version, args.extractor_prompt_version):
        if version not in available:
            parser.error(f"Unknown prompt version {version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.sorter_prompt_version}"
        f"+{args.extractor_prompt_version}_chained_langfuse"
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

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        print(f"Dry run: {len(with_truth)} contracts -> experiment '{experiment_name}'")
        print(f"  sorter={args.sorter_prompt_version} extractor={args.extractor_prompt_version} "
              f"model={args.model} handoff_scope={args.handoff_scope}")
        print(f"  tracing=langfuse session={experiment_name} trace_name={args.lf_trace_name}")
        return 0

    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "dataset": args.dataset,
            "dataset_size": len(with_truth),
            "dataset_fingerprint": dataset_fingerprint(with_truth),
            "model": args.model,
            "sorter_prompt_version": args.sorter_prompt_version,
            "extractor_prompt_version": args.extractor_prompt_version,
            "handoff_scope": args.handoff_scope,
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
        tags=[f"prompt:{args.sorter_prompt_version}", f"extractor:{args.extractor_prompt_version}",
              args.model.split("/")[-1]],
        trace_name=args.lf_trace_name,
    )
    if tracer.disabled:
        print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys in "
              "langfuse.env) — the run proceeds untraced; results still land in "
              "the repo experiment log.", file=sys.stderr)
    else:
        print(f"Tracing to Langfuse project '{lf_config.project}' "
              f"(environment '{lf_config.environment}') at {lf_config.base_url}")

    sorter_usage_by_index: dict[int, dict] = {}
    extractor_usage_by_index: dict[int, dict] = {}

    def chain_one(input_data: dict) -> EvalResultShim:
        """Sorter classifies, then hands the document off to the extractor."""
        filename = input_data["filename"]
        expected_fields = input_data["expected_fields"]
        expected_subtype = normalize_subtype(input_data.get("expected_subtype"))

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                return EvalResultShim(
                    input_data,
                    cached.get("scores", {}).get("composite") or {
                        "sorter": {}, "extractor": {}, "error": "cached incomplete"},
                )

        doc_text = input_data["doc_text"]

        with tracer.trace_document(
            filename, expected_subtype,
            {"dataset": args.dataset, "prompt_version": args.sorter_prompt_version,
             "extractor_prompt": args.extractor_prompt_version,
             "model": args.model, "handoff_scope": args.handoff_scope},
        ) as trace_handle:
            # ---- Agent 1: SORTER (doc_type + contract_subtype) ----
            with tracer.agent_observation(
                "sorter",
                {"prompt_version": args.sorter_prompt_version, "model": args.model,
                 "reasoning_effort": args.sorter_reasoning_effort,
                 "max_concurrency": args.max_concurrency},
            ) as sorter_handle:
                sorter = SorterAgent(model=args.model, api_key=openrouter_key,
                                     prompt_version=args.sorter_prompt_version,
                                     callbacks=[sorter_handle.handler] if sorter_handle.handler else None)
                sorter._max_input_chars = args.max_input_chars
                sorter._max_tokens = min(args.max_tokens, 4096)
                sorter._reasoning_effort = args.sorter_reasoning_effort
                try:
                    sorter_result = sorter.classify_json(doc_text, subtype_focus=True)
                except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                    sorter_result = {"doc_type": "correspondence", "contract_subtype": SUBTYPE_UNKNOWN,
                                     "confidence": 0.0, "reasoning": f"error: {exc}"}
                sorter_usage_by_index[input_data["index"]] = sorter._last_usage or {}
                sorter_doc_type = str(sorter_result.get("doc_type", "correspondence")).strip().lower()
                sorter_subtype = normalize_subtype(sorter_result.get("contract_subtype"))
                try:
                    sorter_confidence = float(sorter_result.get("confidence", 0.0))
                except (TypeError, ValueError):
                    sorter_confidence = 0.0
                doc_type_ok = sorter_doc_type == "contract"
                subtype_ok = doc_type_ok and sorter_subtype == expected_subtype

                sorter_handle.set_output({
                    "doc_type": sorter_doc_type, "contract_subtype": sorter_subtype,
                    "expected_subtype": expected_subtype, "confidence": sorter_confidence,
                })
                sorter_handle.score("exact_match", 1.0 if doc_type_ok else 0.0,
                                    comment="doc_type == contract")
                sorter_handle.score("subtype_accuracy", 1.0 if subtype_ok else 0.0,
                                    comment="subtype == CUAD folder")
                sorter_handle.score("confidence", sorter_confidence,
                                    comment="model-reported confidence")

            # ---- Agent 2: EXTRACTOR (receives the sorter's handoff) ----
            with tracer.agent_observation(
                "contracts_specialist",
                {"prompt_version": args.extractor_prompt_version, "model": args.model,
                 "reasoning_effort": args.reasoning_effort},
            ) as specialist_handle:
                specialist = ContractsSpecialist(
                    model=args.model, api_key=openrouter_key,
                    prompt_version=args.extractor_prompt_version,
                    callbacks=[specialist_handle.handler] if specialist_handle.handler else None)
                specialist._max_input_chars = args.max_input_chars
                specialist._max_tokens = args.max_tokens
                specialist._reasoning_effort = args.reasoning_effort
                specialist.handoff_context = (
                    f"Sorter classification: doc_type={sorter_doc_type} "
                    f"contract_subtype={sorter_subtype}. Extract this contract's fields "
                    f"accordingly, ensuring every clause of this agreement family is captured."
                )
                if args.handoff_scope in ("subtype", "ground_truth"):
                    cue = build_subtype_handoff(sorter_subtype)
                    if cue:
                        specialist.handoff_context += f"\n\n{cue}"
                try:
                    predicted = specialist.extract(doc_text)

                except Exception as exc:  # noqa: BLE001
                    print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
                    composite = {
                        "sorter": {"doc_type": sorter_doc_type, "contract_subtype": sorter_subtype,
                                   "expected_subtype": expected_subtype, "confidence": sorter_confidence,
                                   "doc_type_ok": doc_type_ok, "subtype_ok": subtype_ok},
                        "extractor": {"overall_score": 0.0, "field_presence": 0.0,
                                      "category_presence": 0.0, "overall_verified_precision": 0.0,
                                      "error": str(exc)},
                        "error": str(exc),
                    }
                    if manifest:
                        manifest.append({"filename": filename, "status": "error", "tag": "ERROR!",
                                         "predicted": {}, "error": str(exc),
                                         "expected_fields": expected_fields,
                                         "scores": {"composite": composite}})
                    return EvalResultShim(input_data, composite)

                extractor_usage_by_index[input_data["index"]] = specialist._last_usage or {}

                if predicted.get("_parse_error"):
                    composite = {
                        "sorter": {"doc_type": sorter_doc_type, "contract_subtype": sorter_subtype,
                                   "expected_subtype": expected_subtype, "confidence": sorter_confidence,
                                   "doc_type_ok": doc_type_ok, "subtype_ok": subtype_ok},
                        "extractor": {"overall_score": 0.0, "field_presence": 0.0,
                                      "category_presence": 0.0, "overall_verified_precision": 0.0,
                                      "error": "parse error"},
                        "error": "parse error",
                    }
                    if manifest:
                        manifest.append({"filename": filename, "status": "error", "tag": "ERROR!",
                                         "predicted": {}, "error": "parse error",
                                         "expected_fields": expected_fields,
                                         "scores": {"composite": composite}})
                    return EvalResultShim(input_data, composite)

                result = score_extraction("contract", field_types, predicted, expected_fields,
                                          doc_text=doc_text)
                populated = sum(1 for k, v in expected_fields.items()
                                if predicted.get(k) not in (None, "", []))
                field_presence = populated / len(expected_fields) if expected_fields else 0.0
                category_presence, presence_detail = score_category_presence(
                    predicted, input_data.get("expected_presence") or {}, field_types)

                composite = {
                    "sorter": {"doc_type": sorter_doc_type, "contract_subtype": sorter_subtype,
                               "expected_subtype": expected_subtype, "confidence": sorter_confidence,
                               "reasoning": str(sorter_result.get("reasoning", ""))[:500],
                               "doc_type_ok": doc_type_ok, "subtype_ok": subtype_ok},
                    "extractor": {
                        "predicted": predicted,
                        "overall_score": result.overall_score or 0.0,
                        "field_presence": field_presence,
                        "schema_valid": 1.0,
                        "category_presence": category_presence,
                        "category_presence_detail": presence_detail,
                        "overall_verified_precision": result.overall_verified_precision or 0.0,
                        "field_scores": result.field_scores,
                        "entity_list_f1": {k: v.score for k, v in result.entity_list_scores.items()},
                        "entity_list_audit": result.entity_list_audit,
                        "ambiguous_fields": result.ambiguous_fields,
                        "truncated": bool(specialist._last_truncated),
                    },
                }

                # ---- Issue #1: error-propagation ablation -------------------
                # ground_truth scope: same doc, same model, but the specialist is
                # cued with the GROUND-TRUTH subtype — the score gap vs the
                # predicted-handoff pass isolates sorter routing error from
                # specialist error.
                if args.handoff_scope == "ground_truth":
                    gt_specialist = ContractsSpecialist(
                        model=args.model, api_key=openrouter_key,
                        prompt_version=args.extractor_prompt_version,
                        callbacks=[specialist_handle.handler] if specialist_handle.handler else None)
                    gt_specialist._max_input_chars = args.max_input_chars
                    gt_specialist._max_tokens = args.max_tokens
                    gt_specialist._reasoning_effort = args.reasoning_effort
                    gt_specialist.handoff_context = (
                        f"Sorter classification: doc_type={sorter_doc_type} "
                        f"contract_subtype={expected_subtype}. Extract this contract's fields "
                        f"accordingly, ensuring every clause of this agreement family is captured."
                    )
                    gt_cue = build_subtype_handoff(expected_subtype)
                    if gt_cue:
                        gt_specialist.handoff_context += f"\n\n{gt_cue}"
                    try:
                        gt_predicted = gt_specialist.extract(doc_text)
                        gt_result = score_extraction("contract", field_types, gt_predicted,
                                                     expected_fields, doc_text=doc_text)
                        gt_populated = sum(
                            1 for k, v in expected_fields.items()
                            if gt_predicted.get(k) not in (None, "", []))
                        gt_presence, _ = score_category_presence(
                            gt_predicted, input_data.get("expected_presence") or {}, field_types)
                        composite["extractor_gt"] = {
                            "handoff_subtype": expected_subtype,
                            "overall_score": gt_result.overall_score or 0.0,
                            "field_presence": (gt_populated / len(expected_fields)
                                               if expected_fields else 0.0),
                            "category_presence": gt_presence,
                            "overall_verified_precision": gt_result.overall_verified_precision or 0.0,
                            "ambiguous_fields": gt_result.ambiguous_fields,
                        }
                    except Exception as exc:  # noqa: BLE001
                        composite["extractor_gt"] = {
                            "handoff_subtype": expected_subtype,
                            "overall_score": 0.0, "category_presence": 0.0,
                            "error": str(exc)}

                specialist_handle.set_output({
                    "overall_score": composite["extractor"]["overall_score"],
                    "field_presence": field_presence,
                    "category_presence": category_presence,
                    "overall_verified_precision": composite["extractor"]["overall_verified_precision"],
                    "schema_valid": 1.0,
                    "truncated": composite["extractor"]["truncated"],
                })
                specialist_handle.score("overall_extraction_score", composite["extractor"]["overall_score"],
                                        comment="mean deterministic content score vs CUAD GT")
                specialist_handle.score("field_presence", field_presence,
                                        comment="share of expected fields populated")
                specialist_handle.score("overall_verified_precision",
                                        composite["extractor"]["overall_verified_precision"],
                                        comment="factuality guard (grounded share)")
                specialist_handle.score("category_presence", category_presence,
                                        comment="CUAD YES/NO category conformance")

            trace_handle.set_output(composite)

            if manifest:
                manifest.append({"filename": filename, "status": "completed", "tag": "OK",
                                 "predicted": predicted, "error": "",
                                 "expected_fields": expected_fields,
                                 "scores": {"composite": composite}})

        return EvalResultShim(input_data, composite)

    rows = [
        {"index": i, "filename": d["filename"], "expected": d["expected"],
         "doc_text": d["doc_text"], "expected_fields": d["expected_fields"],
         "expected_presence": d.get("expected_presence") or {},
         "expected_subtype": (d.get("metadata") or {}).get("category"),
         "doc_category": d.get("doc_category")}
        for i, d in enumerate(with_truth)
    ]
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    # Adaptive concurrency: scale the worker pool with the sample size until
    # diminishing returns / rate limits (explicit --max-concurrency N wins).
    args.max_concurrency = resolve_concurrency(len(rows), args.max_concurrency)
    retry_stats: dict = {"rate_limit_retries": 0}
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {pool.submit(call_with_rate_limit_retry, chain_one, row, stats=retry_stats): i for i, row in enumerate(rows)}
        for future, i in futures.items():
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], None, str(exc))
    for failure in [r for r in results if r.error]:
        print(f"ERROR {failure.input['filename']}: {failure.error}", file=sys.stderr)

    tracer.flush()
    tracer.shutdown()

    log_experiment_to_repo(
        EvalRunShim(results), scored_fields, with_truth, args, experiment_name,
        sorter_usage_by_index, extractor_usage_by_index, log_path, md_log_path,
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


if __name__ == "__main__":
    raise SystemExit(main())
