#!/usr/bin/env python3
"""Contracts-specialist EXTRACTION evaluation against CUAD ground truth.

Runs the contracts specialist on real CUAD contracts (from Braintrust) and
scores its entity extraction against the CUAD clause-QA labels — the labeled
extracted information from the Atticus dataset — using the deterministic
field-type-aware content scorer (src/field_scoring.py).

Scorer economy: the task computes EVERY score locally (deterministic
field-type-aware content scoring incl. semantic embedding rescue) and returns
a composite output; registered Braintrust scorers are trivial lookups on that
composite — nothing is recomputed on the Braintrust side. By default
``--bt-scores overall`` registers the cross-experiment tracker set: the
complex content accuracy (``overall_extraction_score``) plus the binary
conformance guard (``field_presence``), so every experiment is comparable in
the Braintrust UI. ``--bt-scores none`` registers nothing (pure local scoring
+ post-hoc manifest report via scripts/reporting/score_extraction_manifest.py);
``--bt-scores full`` adds schema_valid and every per-field score/F1.

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
    parser.add_argument("--max-tokens", type=int, default=16384, help="Max output tokens")
    parser.add_argument("--reasoning-effort", default="none",
                        help="Reasoning effort for the extraction call ('none' default: the "
                             "specialist emits JSON directly — thinking models otherwise burn "
                             "the whole token budget on reasoning and hit length limits on "
                             "long extractions; 'low'/'medium'/'high' re-enable thinking)")
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
    parser.add_argument("--bt-scores", choices=("none", "overall", "full"), default="overall",
                        help="Braintrust scorer registration (registered scorers are trivial "
                             "lookups on the locally-computed composite, so they cost almost "
                             "nothing): overall = the cross-experiment tracker set — complex "
                             "content accuracy (overall_extraction_score) + binary conformance "
                             "(field_presence) (default); none = zero scorers, pure local + "
                             "post-hoc manifest scoring; full = adds schema_valid + every "
                             "per-field score/F1 (most UI detail)")
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
        """Extract entities from one contract; returns a COMPOSITE output.

        The composite carries the predicted extraction PLUS the locally
        computed scores (overall content score, per-field scores, binary
        presence/schema validity). Registered Braintrust scorers are trivial
        lookups on this dict — nothing is recomputed or re-scored on the
        Braintrust side, and the numbers always match the manifest.
        """
        filename = input_data["filename"]
        expected_fields = input_data["expected_fields"]

        specialist = ContractsSpecialist(model=args.model, api_key=openrouter_key,
                                         prompt_version=args.prompt_version)
        specialist._max_input_chars = args.max_input_chars
        specialist._max_tokens = args.max_tokens
        specialist._reasoning_effort = args.reasoning_effort

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                braintrust.current_span().log(
                    metadata={"cached": True, "filename": filename,
                              "prompt_version": args.prompt_version}
                )
                return cached.get("scores", {}).get("composite") or {
                    "predicted": cached.get("predicted") or {}, "overall_score": 0.0,
                    "field_presence": 0.0, "schema_valid": 0.0,
                    "field_scores": {}, "ambiguous_fields": [], "error": "cached incomplete",
                }

        doc_text = input_data["doc_text"]
        try:
            predicted = specialist.extract(doc_text)
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
            composite = {"predicted": {}, "error": str(exc), "schema_valid": 0.0,
                         "overall_score": 0.0, "field_presence": 0.0,
                         "field_scores": {}, "ambiguous_fields": []}
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": str(exc),
                                 "expected_fields": expected_fields, "scores": {"composite": composite}})
            return composite

        if predicted.get("_parse_error"):
            composite = {"predicted": {}, "error": "parse error", "schema_valid": 0.0,
                         "overall_score": 0.0, "field_presence": 0.0,
                         "field_scores": {}, "ambiguous_fields": []}
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": "parse error",
                                 "expected_fields": expected_fields, "scores": {"composite": composite}})
            return composite

        # Deterministic content scoring against CUAD ground truth (LOCAL —
        # with semantic embedding rescue; never executed on the Braintrust side).
        result = score_extraction("contract", field_types, predicted, expected_fields)
        populated = sum(
            1 for key, value in expected_fields.items()
            if predicted.get(key) not in (None, "", [])
        )
        field_presence = populated / len(expected_fields) if expected_fields else 0.0

        composite = {
            "predicted": predicted,
            "overall_score": result.overall_score or 0.0,
            "field_presence": field_presence,
            "schema_valid": 1.0,
            "field_scores": result.field_scores,
            "entity_list_f1": {k: v.f1 for k, v in result.entity_list_scores.items()},
            "ambiguous_fields": result.ambiguous_fields,
        }

        span_meta = {
            "filename": filename,
            "prompt_version": args.prompt_version,
            "overall_score": result.overall_score,
            "field_scores": result.field_scores,
            "ambiguous_fields": result.ambiguous_fields,
            "expected_fields": expected_fields,
            "extracted_fields": {k: v for k, v in predicted.items() if v not in (None, "", [])},
            "entity_list_f1": composite["entity_list_f1"],
            "composite": composite,
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
        return composite

    # ------------------------------------------------------------------
    # Braintrust scorers — trivial lookups on the locally-computed composite
    # (nothing recomputed server-side; numbers always match the manifest)
    # ------------------------------------------------------------------

    def overall_extraction_score(output: dict, expected) -> float:
        """CONTENT accuracy: mean deterministic content score over non-null
        CUAD ground-truth fields (computed locally, incl. embedding rescue)."""
        return float((output or {}).get("overall_score") or 0.0)

    def field_presence(output: dict, expected) -> float:
        """BINARY conformance: share of expected fields populated (non-null,
        non-empty) in the model output."""
        return float((output or {}).get("field_presence") or 0.0)

    def schema_valid(output: dict, expected) -> float:
        """BINARY: did the model return parseable, schema-conformant JSON?"""
        return float((output or {}).get("schema_valid") or 0.0)

    def make_field_scorer(field_name: str):
        def scorer(output: dict, expected) -> float:
            return float(((output or {}).get("field_scores") or {}).get(field_name) or 0.0)
        scorer.__name__ = f"{field_name}_score"
        return scorer

    def make_list_f1_scorer(field_name: str):
        def scorer(output: dict, expected) -> float:
            return float(((output or {}).get("entity_list_f1") or {}).get(field_name) or 0.0)
        scorer.__name__ = f"{field_name}_f1"
        return scorer

    if args.bt_scores == "none":
        bt_scorers = []
    elif args.bt_scores == "overall":
        # ONE cross-experiment tracker set: complex content accuracy + the
        # binary presence guard — cheap lookups, comparable across runs.
        bt_scorers = [overall_extraction_score, field_presence]
    else:
        bt_scorers = [overall_extraction_score, field_presence, schema_valid]
        for field_name in scored_fields:
            bt_scorers.append(make_field_scorer(field_name))
            field_type = field_types.get(field_name) or "name"
            if is_entity_list(field_type):
                bt_scorers.append(make_list_f1_scorer(field_name))

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
    """Print per-field mean content scores, overall, and presence.

    Reads the locally computed scores carried in the composite task output —
    identical to what the manifest and the Braintrust lookups report.
    """
    rows = [r for r in result.results if r.error is None and isinstance(r.output, dict)]
    if not rows:
        print("\nNo scored rows.")
        return

    totals: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        output = r.output
        if output.get("error"):
            continue
        totals["overall"].append(float(output.get("overall_score") or 0.0))
        for key in scored_fields:
            if key in (output.get("field_scores") or {}):
                totals[key].append(float(output["field_scores"][key]))

    print("\n== Extraction eval (content scores vs CUAD ground truth) ==")
    for key in ["overall"] + scored_fields:
        values = totals.get(key)
        if not values:
            continue
        mean = sum(values) / len(values)
        print(f"{key:<28} n={len(values):<4} mean={mean:.4f}")

    presence = [r for r in rows if not r.output.get("error")]
    if presence:
        values = [float(r.output.get("field_presence") or 0.0) for r in presence]
        print(f"\nfield_presence (binary conformance): {sum(values) / len(values):.4f}")


if __name__ == "__main__":
    raise SystemExit(main())
