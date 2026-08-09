#!/usr/bin/env python3
"""Contracts-specialist EXTRACTION evaluation against CUAD ground truth.

Runs the contracts specialist on real CUAD contracts (from Braintrust) and
scores its entity extraction against the CUAD clause-QA labels — the labeled
extracted information from the Atticus dataset — using the deterministic
field-type-aware content scorer (src/field_scoring.py).

Scorer economy: by default ZERO Braintrust scorers are registered
(``--bt-scores none``) — every field is scored LOCALLY during the run (pure
deterministic math, no Braintrust work) and written to the JSONL manifest
(``--manifest``) together with the predicted and expected fields. The
post-hoc report (scripts/reporting/score_extraction_manifest.py) recomputes
and summarizes everything from the manifest without burning any Braintrust
scorer quota. ``--bt-scores overall`` registers exactly one score for UI
visibility; ``--bt-scores full`` registers the whole per-field set (opt-in —
it burns a scorer per field per row).

``--judge`` adds the grounded LLM-as-judge pass (correctness/completeness
against the source text) for rows whose content scores land in the ambiguous
band, the llm-mailroom escalation pattern.

Per-row span metadata records extracted-vs-expected values, per-field scores,
and ambiguous fields so every decision is auditable in Braintrust.

Usage:
    python scripts/eval/run_extraction_eval.py --dataset mailroom-cuad-contracts \\
        --manifest data/manifests/extract_v2.jsonl
    python scripts/eval/run_extraction_eval.py --prompt-version contracts_specialist
    python scripts/eval/run_extraction_eval.py --bt-scores overall --limit 3
    python scripts/eval/run_extraction_eval.py --judge --limit 3
    python scripts/eval/run_extraction_eval.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from braintrust.integrations.langchain import setup_langchain

import braintrust

from agents.specialist_agents import ContractsSpecialist
from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import load_braintrust_dataset
from src.cuad_ground_truth import build_expected_fields
from src.env_utils import require_env
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset
from src.field_scoring import (
    get_field_types,
    is_entity_list,
    score_extraction,
    score_field,
)
from src.prompts import list_prompts
from src.scorers import ERROR_PREFIX

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


def load_expected_fields(rows: list[dict]) -> list[dict]:
    """Derive per-row expected_fields from the dataset's CUAD ground truth.

    Prefers ``expected_fields`` surfaced by the loader (stored in the row's
    expected dict); falls back to deriving from the raw clause labels.
    """
    for row in rows:
        if row.get("expected_fields"):
            continue
        clause_labels = row.get("clause_labels") or (row.get("expected_output") or {}).get("clause_labels") or []
        row["expected_fields"] = build_expected_fields(clause_labels)
    return rows


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
    parser.add_argument("--prompt-version", default="contracts_specialist_v2",
                        help="Specialist prompt version to test (one per experiment)")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=8192, help="Max output tokens")
    parser.add_argument("--max-input-chars", type=int, default=100_000,
                        help="Hard safety cap on document text fed to the model")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_extraction)")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--judge", action="store_true",
                        help="Run the grounded LLM-as-judge pass (correctness/completeness) for "
                             "rows whose content scores land in the ambiguous band")
    parser.add_argument("--bt-scores", choices=("none", "overall", "full"), default="none",
                        help="Braintrust scorer registration (each registered scorer costs "
                             "Braintrust-side scoring work per row): none = zero scorers, all "
                             "scoring is local and scored post-hoc from the manifest (default); "
                             "overall = exactly ONE overall score for UI visibility; "
                             "full = the whole per-field scorer set (burns scorer quota)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")

    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.prompt_version}_extraction"
    )

    dataset = load_braintrust_dataset(args.dataset_project, args.dataset, project_id=_CONFIG.project_id)
    dataset = load_expected_fields(dataset)
    if args.sample:
        dataset = random.Random(args.seed).sample(dataset, min(args.sample, len(dataset)))
    if args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No contracts with clause labels found in the dataset.")
    # Only rows with CUAD ground truth participate in the extraction eval.
    with_truth = [d for d in dataset if d.get("expected_fields")]
    if not with_truth:
        parser.error(f"Dataset {args.dataset!r} has no CUAD clause-label ground truth "
                     "(re-sync with stream_cuad_to_bt.py).")
    print(f"{len(with_truth)}/{len(dataset)} rows carry CUAD ground truth")

    field_types = get_field_types("contract")
    # The union of expected fields across the sample determines which
    # per-field scorers get registered.
    scored_fields = sorted({f for d in with_truth for f in d["expected_fields"]})

    validate_dataset(with_truth)

    manifest = None
    manifest_meta = {
        "experiment_name": experiment_name,
        "dataset": args.dataset,
        "dataset_size": len(with_truth),
        "dataset_fingerprint": dataset_fingerprint(with_truth),
        "model": args.model,
        "prompt_version": args.prompt_version,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "judge": args.judge,
    }
    if args.manifest:
        manifest = ManifestStore(args.manifest, manifest_meta)
        manifest.initialize()

    if args.dry_run:
        print(f"Dry run: {len(with_truth)} contracts -> experiment '{experiment_name}'")
        print(f"  prompt_version={args.prompt_version} model={args.model}")
        print(f"  fields scored: {scored_fields}")
        return 0

    setup_langchain(api_key=braintrust_key, project_id=args.project_id, project_name=args.project)

    from src.prompts import get_prompt

    prompt_text = get_prompt(args.prompt_version)

    def _run_judge(filename, doc_text, predicted, expected_fields, ambiguous) -> dict:
        from agents.judge_agent import JudgeAgent

        judge = JudgeAgent(api_key=openrouter_key)
        verdict = {}
        try:
            verdict["correctness"] = judge.judge_extraction_correctness(
                "contract", predicted, doc_text
            )
        except Exception as exc:  # noqa: BLE001
            verdict["correctness_error"] = str(exc)
        try:
            verdict["completeness"] = judge.judge_completeness(
                "contract", predicted, doc_text
            )
        except Exception as exc:  # noqa: BLE001
            verdict["completeness_error"] = str(exc)
        verdict["ambiguous_fields"] = ambiguous
        print(f"JUDGE {filename}: correctness={verdict.get('correctness', {}).get('extraction_correctness_label', '?')} "
              f"completeness={verdict.get('completeness', {}).get('completeness_label', '?')}")
        return verdict

    @braintrust.traced
    def extract_contract(input_data: dict) -> dict:
        """Extract entities from one contract; returns the predicted dict."""
        filename = input_data["filename"]
        expected_fields = input_data["expected_fields"]

        specialist = ContractsSpecialist(model=args.model, api_key=openrouter_key)
        specialist._max_input_chars = args.max_input_chars
        specialist._max_tokens = args.max_tokens

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                braintrust.current_span().log(
                    metadata={"cached": True, "filename": filename,
                              "prompt_version": args.prompt_version}
                )
                return cached.get("predicted") or {"_parse_error": True}

        doc_text = input_data["doc_text"]
        try:
            predicted = specialist.extract(doc_text)
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": str(exc)})
            return {"_parse_error": True, "error": str(exc)}

        if predicted.get("_parse_error"):
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": "parse error"})
            return predicted

        # Deterministic content scoring against CUAD ground truth.
        result = score_extraction("contract", field_types, predicted, expected_fields)
        span_meta = {
            "filename": filename,
            "prompt_version": args.prompt_version,
            "overall_score": result.overall_score,
            "field_scores": result.field_scores,
            "ambiguous_fields": result.ambiguous_fields,
            "expected_fields": expected_fields,
            "extracted_fields": {k: v for k, v in predicted.items() if v not in (None, "", [])},
            "entity_list_f1": {k: v.f1 for k, v in result.entity_list_scores.items()},
        }

        if args.judge and result.needs_judge_review:
            span_meta["judge"] = _run_judge(filename, doc_text, predicted,
                                            expected_fields, result.ambiguous_fields)

        if manifest:
            manifest.append({"filename": filename, "status": "completed",
                             "tag": "OK", "predicted": predicted, "error": "",
                             "expected_fields": expected_fields,
                             "scores": span_meta})

        braintrust.current_span().log(metadata=span_meta)
        return predicted

    # ------------------------------------------------------------------
    # Braintrust scorers (ALL scoring is local; registration is opt-in)
    # ------------------------------------------------------------------

    def schema_valid(output: dict, expected) -> float:
        """BINARY: did the model return parseable, schema-conformant JSON?"""
        return 0.0 if not isinstance(output, dict) or output.get("_parse_error") else 1.0

    def field_presence(output: dict, expected) -> float:
        """BINARY conformance: share of expected fields populated (non-null,
        non-empty) in the model output — the right expected number of fields."""
        expected_fields = expected.get("expected_fields") or {}
        if not expected_fields:
            return 0.0
        populated = sum(
            1 for key, value in expected_fields.items()
            if output.get(key) not in (None, "", [])
        )
        return populated / len(expected_fields)

    def overall_extraction_score(output: dict, expected) -> float:
        """CONTENT score: mean of the per-field deterministic scores over
        non-null CUAD ground-truth fields."""
        expected_fields = expected.get("expected_fields") or {}
        result = score_extraction("contract", field_types, output, expected_fields)
        return result.overall_score or 0.0

    def make_field_scorer(field_name: str, field_type: str):
        def scorer(output: dict, expected) -> float:
            expected_fields = expected.get("expected_fields") or {}
            if field_name not in expected_fields:
                return 0.0
            if is_entity_list(field_type):
                result = score_field(field_type, output.get(field_name),
                                     expected_fields[field_name])
                return getattr(result, "f1", 0.0)
            return score_field(field_type, output.get(field_name),
                               expected_fields[field_name])
        scorer.__name__ = f"{field_name}_score"
        return scorer

    def make_list_f1_scorer(field_name: str, field_type: str):
        def scorer(output: dict, expected) -> float:
            expected_fields = expected.get("expected_fields") or {}
            if field_name not in expected_fields:
                return 0.0
            result = score_field(field_type, output.get(field_name),
                                 expected_fields[field_name])
            return getattr(result, "f1", 0.0)
        scorer.__name__ = f"{field_name}_f1"
        return scorer

    if args.bt_scores == "none":
        bt_scorers = []
    elif args.bt_scores == "overall":
        bt_scorers = [overall_extraction_score]
    else:
        bt_scorers = [schema_valid, field_presence, overall_extraction_score]
        for field_name in scored_fields:
            field_type = field_types.get(field_name) or "name"
            bt_scorers.append(make_field_scorer(field_name, field_type))
            if is_entity_list(field_type):
                bt_scorers.append(make_list_f1_scorer(field_name, field_type))

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
                       "doc_text": d["doc_text"], "expected_fields": d["expected_fields"]},
             "expected": {
                 "doc_type": d["expected"],
                 "expected_fields": d["expected_fields"],
             },
             "filename": d["filename"]}
            for i, d in enumerate(with_truth)
        ],
        task=extract_contract,
        scores=bt_scorers,
        max_concurrency=args.max_concurrency,
        reporter=braintrust.Reporter("extraction-only",
                                     report_eval=_report_eval, report_run=_report_run),
        project_id=args.project_id,
        experiment_name=experiment_name,
        metadata={
            "prompt": prompt_text,
            "prompt_version": args.prompt_version,
            "model": args.model,
            "task": "contract_entity_extraction",
            "ground_truth": "cuad_v1_clause_labels",
            "scoring": "field_type_aware_content_scoring",
            "bt_scores": args.bt_scores,
            "judge": args.judge,
            "fields": scored_fields,
            "dataset": f"{args.dataset_project}/{args.dataset}",
            "dataset_size": len(with_truth),
            "dataset_fingerprint": dataset_fingerprint(with_truth),
            "manifest": str(args.manifest) if args.manifest else None,
        },
        description=f"{args.model} | {args.prompt_version} | CUAD extraction eval | fields={len(scored_fields)} | bt_scores={args.bt_scores}",
    )

    print_extraction_summary(result, scored_fields)
    braintrust.flush()
    return 0


def print_extraction_summary(result, scored_fields: list[str]) -> None:
    """Print per-field mean content scores, overall, and presence."""
    rows = [r for r in result.results if r.error is None and
            isinstance(r.output, dict) and not r.output.get("_parse_error")]
    if not rows:
        print("\nNo scored rows.")
        return

    totals: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        expected_fields = (r.expected or {}).get("expected_fields") or {}
        from src.field_scoring import score_extraction, get_field_types

        res = score_extraction("contract", get_field_types("contract"), r.output, expected_fields)
        totals["overall"].append(res.overall_score or 0.0)
        for key in scored_fields:
            if key in res.field_scores:
                totals[key].append(res.field_scores[key])

    print("\n== Extraction eval (content scores vs CUAD ground truth) ==")
    for key in ["overall"] + scored_fields:
        values = totals.get(key)
        if not values:
            continue
        mean = sum(values) / len(values)
        print(f"{key:<28} n={len(values):<4} mean={mean:.4f}")

    presence = [
        r for r in result.results
        if r.error is None and isinstance(r.output, dict) and not r.output.get("_parse_error")
    ]
    if presence:
        from src.field_scoring import score_extraction

        populated_share = []
        for r in presence:
            expected_fields = (r.expected or {}).get("expected_fields") or {}
            if not expected_fields:
                continue
            populated = sum(1 for k, v in expected_fields.items()
                            if r.output.get(k) not in (None, "", []))
            populated_share.append(populated / len(expected_fields))
        if populated_share:
            print(f"\nfield_presence (binary conformance): {sum(populated_share) / len(populated_share):.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
