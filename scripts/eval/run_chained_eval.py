#!/usr/bin/env python3
"""CHAINED two-agent evaluation: SorterAgent -> ContractsSpecialist.

Each row is ONE contract (same PDF text for both agents). The sorter
classifies it FIRST — doc_type (6 classes) AND contract_subtype (the 25
CUAD contract families, per the dataset card: the group a document belongs
to decides what fields to expect) — and hands the document off to the
contracts specialist, which extracts with the sorter's classification as
context. Both agents run for every row; both are scored:

  Sorter      sorter_exact_match (doc_type == contract), sorter_subtype_accuracy
              (contract_subtype == the row's CUAD folder), sorter_confidence
  Extractor   overall_extraction_score, field_presence,
              overall_verified_precision, category_presence (the same
              cross-experiment trackers as run_extraction_eval.py)

The composite output carries both agents' results; every Braintrust scorer
is a trivial local lookup. A JSONL manifest checkpoints completed rows and
the repo experiment log is updated automatically.

Usage:
    python scripts/eval/run_chained_eval.py --sample 5 --seed 42 \
        --manifest data/manifests/chained_5.jsonl
    python scripts/eval/run_chained_eval.py \
        --sorter-prompt-version sorter_v0 --extractor-prompt-version contracts_specialist_v3
    python scripts/eval/run_chained_eval.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from braintrust.integrations.langchain import setup_langchain

import braintrust

from agents.sorter_agent import SUBTYPE_UNKNOWN, SorterAgent, normalize_subtype
from agents.specialist_agents import ContractsSpecialist
from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import load_braintrust_dataset
from src.env_utils import require_env
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset
from src.experiment_log import (
    append_experiment,
    append_markdown,
    default_jsonl_path,
    default_md_path,
    git_snapshot,
    mean,
    tokens_summary,
)
from src.cuad_ground_truth import build_subtype_handoff
from src.field_scoring import (
    get_field_types,
    score_category_presence,
    score_extraction,
)
from src.prompts import list_prompts

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"

# Reuse the CUAD type-aware expected-fields derivation from the extraction
# runner (identical semantics; both pipelines must score the same GT).
from scripts.eval.run_extraction_eval import load_expected_fields  # noqa: E402


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name, help="Braintrust project name")
    parser.add_argument("--project-id", default=_CONFIG.project_id, help="Braintrust project id")
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
                        help="Reasoning effort for the SORTER's classification call "
                             "(default: medium — the sorter must weigh operative "
                             "clauses across 25 near-synonymous families)")
    parser.add_argument("--max-input-chars", type=int, default=150_000,
                        help="Hard safety cap on document text fed to the agents "
                             "(150k default: the full corpus's largest contracts run "
                             "106-122k chars; head+tail window when exceeded)")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_sorter-v{extractor}_chained)")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--bt-scores", choices=("none", "overall", "full"), default="overall",
                        help="Braintrust scorer registration (default: the cross-experiment "
                             "tracker set for BOTH agents)")
    parser.add_argument("--handoff-scope", choices=("subtype", "none"), default="subtype",
                        help="Specialist handoff scope: 'subtype' (default) appends the "
                             "PREDICTED subtype's CUAD field-group cue (expected schema "
                             "fields + applicable/never-applicable clause categories) to the "
                             "extractor context; 'none' reproduces the legacy "
                             "doc_type+contract_subtype line only")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")

    available = list_prompts()
    for version in (args.sorter_prompt_version, args.extractor_prompt_version):
        if version not in available:
            parser.error(f"Unknown prompt version {version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.sorter_prompt_version}"
        f"+{args.extractor_prompt_version}_chained"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset,
                                      project_id=_CONFIG.project_id)
    dataset = load_expected_fields(dataset)
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

    field_types = get_field_types("contract")
    scored_fields = sorted({f for d in with_truth for f in d["expected_fields"]})
    validate_dataset(with_truth)

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

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
        })
        manifest.initialize()

    if args.dry_run:
        print(f"Dry run: {len(with_truth)} contracts -> experiment '{experiment_name}'")
        print(f"  sorter={args.sorter_prompt_version} extractor={args.extractor_prompt_version} "
              f"model={args.model}")
        return 0

    setup_langchain(api_key=braintrust_key, project_id=args.project_id, project_name=args.project)

    sorter_usage_by_index: dict[int, dict] = {}
    extractor_usage_by_index: dict[int, dict] = {}

    @braintrust.traced
    def chain(input_data: dict) -> dict:
        """Sorter classifies, then hands the document off to the extractor."""
        filename = input_data["filename"]
        expected_fields = input_data["expected_fields"]
        expected_subtype = normalize_subtype(input_data.get("expected_subtype"))

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                braintrust.current_span().log(
                    metadata={"cached": True, "filename": filename}
                )
                return cached.get("scores", {}).get("composite") or {
                    "sorter": {}, "extractor": {}, "error": "cached incomplete"}

        doc_text = input_data["doc_text"]

        # ---- Agent 1: SORTER (doc_type + contract_subtype) ----
        sorter = SorterAgent(model=args.model, api_key=openrouter_key,
                             prompt_version=args.sorter_prompt_version)
        sorter._max_input_chars = args.max_input_chars
        sorter._max_tokens = min(args.max_tokens, 4096)
        sorter._reasoning_effort = args.sorter_reasoning_effort
        try:
            # subtype_focus=True: every chained row IS a contract, so the
            # sorter is explicitly tasked with sorting the document into its
            # contract subtype — its scores then measure the subtype task,
            # not a general doc-type gate.
            sorter_result = sorter.classify_json(doc_text, subtype_focus=True)
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            sorter_result = {"doc_type": "correspondence", "contract_subtype": SUBTYPE_UNKNOWN,
                             "confidence": 0.0, "reasoning": f"error: {exc}"}
        sorter_usage_by_index[input_data["index"]] = sorter._last_usage or {}
        sorter_doc_type = str(sorter_result.get("doc_type", "correspondence")).strip().lower()
        sorter_subtype = normalize_subtype(sorter_result.get("contract_subtype"))
        sorter_confidence = sorter_result.get("confidence", 0.0)
        try:
            sorter_confidence = float(sorter_confidence)
        except (TypeError, ValueError):
            sorter_confidence = 0.0
        doc_type_ok = sorter_doc_type == "contract"
        subtype_ok = doc_type_ok and sorter_subtype == expected_subtype

        # ---- Agent 2: EXTRACTOR (receives the sorter's handoff context) ----
        specialist = ContractsSpecialist(model=args.model, api_key=openrouter_key,
                                         prompt_version=args.extractor_prompt_version)
        specialist._max_input_chars = args.max_input_chars
        specialist._max_tokens = args.max_tokens
        specialist._reasoning_effort = args.reasoning_effort
        specialist.handoff_context = (
            f"Sorter classification: doc_type={sorter_doc_type} "
            f"contract_subtype={sorter_subtype}. Extract this contract's fields "
            f"accordingly, ensuring every clause of this agreement family is captured."
        )
        if args.handoff_scope == "subtype":
            # Cue the specialist with the field scope of the PREDICTED subtype —
            # the narrowed set of expected schema fields and applicable/never-
            # applicable CUAD clause categories for that family (a pure function
            # of the subtype; no ground-truth answers are passed).
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
            return composite

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
            return composite

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
                # Truncation auditability: True when the document exceeded the
                # input cap and the specialist saw only head+tail (labeled
                # clauses in the omitted middle are unrecoverable).
                "truncated": bool(specialist._last_truncated),
            },
        }

        span_meta = {
            "filename": filename,
            "sorter": composite["sorter"],
            "extractor_scores": composite["extractor"],
            "expected_fields": expected_fields,
            "composite": composite,
            "sorter_usage": sorter._last_usage or {},
            "extractor_usage": specialist._last_usage or {},
        }
        if manifest:
            manifest.append({"filename": filename, "status": "completed", "tag": "OK",
                             "predicted": predicted, "error": "",
                             "expected_fields": expected_fields,
                             "scores": span_meta})

        braintrust.current_span().log(metadata=span_meta)
        return composite

    # ------------------------------------------------------------------
    # Braintrust scorers — trivial lookups on the composite
    # ------------------------------------------------------------------

    def sorter_exact_match(output: dict, expected) -> float:
        """SORTER: did the sorter classify the document as contract?"""
        return 1.0 if ((output or {}).get("sorter") or {}).get("doc_type_ok") else 0.0

    def sorter_subtype_accuracy(output: dict, expected) -> float:
        """SORTER: did the contract_subtype match the document's CUAD type?"""
        return 1.0 if ((output or {}).get("sorter") or {}).get("subtype_ok") else 0.0

    def sorter_confidence(output: dict, expected) -> float:
        """SORTER: the model's classification confidence."""
        return float(((output or {}).get("sorter") or {}).get("confidence") or 0.0)

    def extractor_overall(output: dict, expected) -> float:
        """EXTRACTOR: complex content accuracy vs CUAD ground truth."""
        return float(((output or {}).get("extractor") or {}).get("overall_score") or 0.0)

    def extractor_field_presence(output: dict, expected) -> float:
        """EXTRACTOR: binary conformance (share of expected fields populated)."""
        return float(((output or {}).get("extractor") or {}).get("field_presence") or 0.0)

    def extractor_verified_precision(output: dict, expected) -> float:
        """EXTRACTOR: factuality guard (share of reported content grounded)."""
        return float(((output or {}).get("extractor") or {}).get("overall_verified_precision") or 0.0)

    def extractor_category_presence(output: dict, expected) -> float:
        """EXTRACTOR: CUAD YES/NO category conformance."""
        return float(((output or {}).get("extractor") or {}).get("category_presence") or 0.0)

    def extractor_schema_valid(output: dict, expected) -> float:
        return float(((output or {}).get("extractor") or {}).get("schema_valid") or 0.0)

    if args.bt_scores == "none":
        bt_scorers = []
    elif args.bt_scores == "overall":
        bt_scorers = [sorter_exact_match, sorter_subtype_accuracy, sorter_confidence,
                      extractor_overall, extractor_field_presence,
                      extractor_verified_precision, extractor_category_presence]
    else:
        bt_scorers = [sorter_exact_match, sorter_subtype_accuracy, sorter_confidence,
                      extractor_overall, extractor_field_presence,
                      extractor_verified_precision, extractor_category_presence,
                      extractor_schema_valid]

    def _report_eval(evaluator, result, verbose, jsonl):
        failures = [r for r in result.results if r.error]
        for failure_ in failures:
            print(f"ERROR {failure_.input['filename']}: {failure_.error}", file=sys.stderr)
        return not failures

    def _report_run(results, verbose, jsonl):
        return all(results)

    result = braintrust.Eval(
        args.project,
        data=lambda: [
            {"input": {"index": i, "filename": d["filename"], "expected": d["expected"],
                       "doc_text": d["doc_text"], "expected_fields": d["expected_fields"],
                       "expected_presence": d.get("expected_presence") or {},
                       "expected_subtype": (d.get("metadata") or {}).get("category"),
                       "doc_category": d.get("doc_category")},
             "expected": {"doc_type": d["expected"], "expected_fields": d["expected_fields"]},
             "filename": d["filename"]}
            for i, d in enumerate(with_truth)
        ],
        task=chain,
        scores=bt_scorers,
        max_concurrency=args.max_concurrency,
        reporter=braintrust.Reporter("chained-sorter-extractor",
                                     report_eval=_report_eval, report_run=_report_run),
        project_id=args.project_id,
        experiment_name=experiment_name,
        metadata={
            "sorter_prompt": args.sorter_prompt_version,
            "extractor_prompt": args.extractor_prompt_version,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "sorter_reasoning_effort": args.sorter_reasoning_effort,
            "handoff_scope": args.handoff_scope,
            "task": "chained_sorter_extractor",
            "ground_truth": "cuad_v1_clause_labels",
            "ground_truth_mode": "cuad_type_aware",
            "dataset": f"{args.dataset_project}/{args.dataset}",
            "dataset_size": len(with_truth),
            "dataset_fingerprint": dataset_fingerprint(with_truth),
            "bt_scores": args.bt_scores,
        },
        description=(f"{args.model} | sorter {args.sorter_prompt_version} -> "
                     f"extractor {args.extractor_prompt_version} | chained"),
    )

    log_experiment_to_repo(result, scored_fields, with_truth, args, experiment_name,
                           sorter_usage_by_index, extractor_usage_by_index,
                           log_path, md_log_path)
    braintrust.flush()
    return 0


def log_experiment_to_repo(result, scored_fields, dataset, args, experiment_name,
                           sorter_usage, extractor_usage, log_path, md_log_path,
                           tracing_backend: str = "braintrust",
                           tracing_meta: dict | None = None) -> None:
    """Append ONE experiment-log record for the chained run.

    ``tracing_backend`` names where the run was traced (``braintrust`` default,
    ``langfuse`` for the mirror runner); ``tracing_meta`` carries backend
    specifics (project/environment) into the record's parameters.
    """
    rows = [r for r in result.results if r.error is None and isinstance(r.output, dict)]
    ok = [r.output for r in rows if isinstance(r.output, dict)]

    def _mean(key: str, bucket: str) -> float | None:
        values = []
        for o in ok:
            value = (o.get(bucket) or {}).get(key)
            if value is not None:
                values.append(float(value))
        return round(mean(values), 4) if values else None

    sorter_stats = {
        "exact_match": _mean("doc_type_ok", "sorter"),
        "subtype_accuracy": _mean("subtype_ok", "sorter"),
        "confidence": _mean("confidence", "sorter"),
    }
    extractor_stats = {
        "overall_extraction_score": _mean("overall_score", "extractor"),
        "field_presence": _mean("field_presence", "extractor"),
        "overall_verified_precision": _mean("overall_verified_precision", "extractor"),
        "category_presence": _mean("category_presence", "extractor"),
    }

    per_row = []
    for r in result.results:
        output = r.output if isinstance(r.output, dict) else {}
        index = r.input.get("index", -1) if isinstance(r.input, dict) else -1
        per_row.append({
            "filename": r.input.get("filename") if isinstance(r.input, dict) else "",
            "status": "error" if r.error is not None else "completed",
            "error": r.error,
            "sorter": (output.get("sorter") or {}),
            "extractor_scores": (output.get("extractor") or {}),
            "sorter_tokens": sorter_usage.get(index) or {},
            "extractor_tokens": extractor_usage.get(index) or {},
        })

    record = {
        "type": "experiment",
        "task": "chained_sorter_extractor",
        "experiment_name": experiment_name,
        "git": git_snapshot(),
        "model": args.model,
        "prompt_versions": {
            "sorter": args.sorter_prompt_version,
            "extractor": args.extractor_prompt_version,
        },
        "data_source": {
            "project": f"{args.dataset_project}/{args.dataset}",
            "ground_truth": "cuad_v1_clause_labels",
            "ground_truth_mode": "cuad_type_aware",
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "n_samples": len(dataset),
            "sample_requested": args.sample,
            "limit": args.limit,
            "seed": args.seed,
        },
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "reasoning_effort": args.reasoning_effort,
            "sorter_reasoning_effort": args.sorter_reasoning_effort,
            "max_input_chars": args.max_input_chars,
            "max_concurrency": args.max_concurrency,
            "bt_scores": getattr(args, "bt_scores", "none"),
            "handoff_scope": getattr(args, "handoff_scope", "none"),
            "manifest": str(args.manifest) if args.manifest else None,
            "tracing_backend": tracing_backend,
            **({"tracing": tracing_meta} if tracing_meta else {}),
        },
        "tokens": {
            "sorter": tokens_summary(list(sorter_usage.values())),
            "extractor": tokens_summary(list(extractor_usage.values())),
            "total": tokens_summary(
                list(sorter_usage.values()) + list(extractor_usage.values())
            ),
        },
        "scores": {"sorter": sorter_stats, "extractor": extractor_stats},
        "n_rows": len(result.results),
        "n_ok": len(ok),
        "results": per_row,
    }
    jsonl_path = append_experiment(record, log_path)
    append_markdown(record, md_log_path)
    print(f"\nExperiment logged to {jsonl_path}")


if __name__ == "__main__":
    raise SystemExit(main())
