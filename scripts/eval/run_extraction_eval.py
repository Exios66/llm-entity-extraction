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
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from braintrust.integrations.langchain import setup_langchain

import braintrust

from agents.specialist_agents import ContractsSpecialist
from src.braintrust_config import load_braintrust_config
from src.braintrust_logging import braintrust_logging_enabled, langsmith_enabled
from src.braintrust_utils import load_braintrust_dataset
from src.cuad_ground_truth import build_expected_fields, build_presence_expectations
from src.env_utils import require_env
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset
from src.eval_shims import run_local_eval
from src.experiment_log import (
    append_experiment,
    append_markdown,
    default_jsonl_path,
    default_md_path,
    git_snapshot,
    mean,
    tokens_summary,
)
from src.field_scoring import (
    get_field_types,
    is_entity_list,
    score_category_presence,
    score_extraction,
    score_field,
)
from src.prompts import list_prompts
from src.scorers import ERROR_PREFIX

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


def load_expected_fields(rows: list[dict]) -> list[dict]:
    """Derive per-row expected_fields from the dataset's CUAD ground truth.

    Per the CUAD dataset card, NOT all expected fields map to each document:
    the contract TYPE the document belongs to decides what fields to expect,
    so the row's metadata ``category`` (CUAD folder) drives the derivation.
    Also builds the YES/NO category presence expectations. Prefers
    ``expected_fields`` surfaced by the loader (stored in the row's expected
    dict); falls back to deriving from the raw clause labels.
    """
    for row in rows:
        clause_labels = row.get("clause_labels") or (row.get("expected_output") or {}).get("clause_labels") or []
        doc_category = (row.get("metadata") or {}).get("category") or None
        row["doc_category"] = doc_category
        if not row.get("expected_fields"):
            row["expected_fields"] = build_expected_fields(clause_labels, doc_category=doc_category)
        row["expected_presence"] = build_presence_expectations(clause_labels, doc_category=doc_category)
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
    parser.add_argument("--max-input-chars", type=int, default=150_000,
                        help="Hard safety cap on document text fed to the model "
                             "(150k default: the full corpus's largest contracts run "
                             "106-122k chars; head+tail window when exceeded)")
    parser.add_argument("--max-concurrency", type=int, default=4, help="Concurrent API calls")
    parser.add_argument("--chunked", action="store_true",
                        help="Split long documents into overlapping windows, one extraction "
                             "call per window, and merge (list fields union with dedupe, "
                             "scalars keep the first non-null value, confidence takes the "
                             "max). REQUIRED for meaningful key_obligations/term_length "
                             "measurements: unchunked extraction head+tail-truncates long "
                             "docs, which drops the mid-document restriction/covenant "
                             "families and collapses term_length (the Phasebio confound, "
                             "memos/contracts_specialist_v28.md).")
    parser.add_argument("--chunk-chars", type=int, default=90_000,
                        help="Chunk window size for --chunked (default: 90000 chars)")
    parser.add_argument("--chunk-overlap", type=int, default=8_000,
                        help="Overlap carried between chunks for --chunked "
                             "(default: 8000 chars)")
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
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH or "
                             "reports/experiment_log.jsonl); a markdown section is appended "
                             "to $EXPERIMENT_LOG_MD_PATH or reports/experiment_log.md")
    parser.add_argument("--master-labels", type=Path, default=None,
                        help="Master ground-truth labels CSV (default: MASTER_LABELS_CSV env "
                             "or data/cuad/master_clauses.csv, the repo-local curated table). "
                             "The curated normalized per-category answers feed the MAE "
                             "diagnostics (dates, durations) in the experiment log.")
    args = parser.parse_args(argv)

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")
    bt_enabled = braintrust_logging_enabled()

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

    # Master labels CSV: curated normalized ground-truth answers (dates like
    # "5/8/14", durations like "2 years") used by the MAE diagnostics. Best
    # effort — diagnostics degrade to raw clause-text parsing when absent.
    from src.master_labels import DEFAULT_MASTER_LABELS, load_master_labels
    master_labels_path = args.master_labels or DEFAULT_MASTER_LABELS
    master_labels = load_master_labels(master_labels_path)
    master_labels_used = bool(master_labels)

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
        if args.chunked:
            print(f"  mode=chunked windows={args.chunk_chars} overlap={args.chunk_overlap}")
        else:
            print("  WARNING: --chunked off — key_obligations/term_length measurements are "
                  "truncation-confounded on long documents (the Phasebio confound: 0.125 "
                  "unchunked vs 0.94 chunked; see memos/contracts_specialist_v28.md). Use "
                  "--chunked for production-representative extraction A/Bs.")
        return 0

    if bt_enabled:
        setup_langchain(api_key=braintrust_key, project_id=args.project_id, project_name=args.project)
    else:
        print("Braintrust experiment logging DISABLED (BRAINTRUST_LOGGING=disabled) — "
              "results sink to the repo experiment log"
              + (" and LangSmith (LANGSMITH_TRACING=true)" if langsmith_enabled() else "")
              + "; use the run_langfuse_*_eval.py runner for Langfuse traces.")

    from src.prompts import get_prompt

    prompt_text = get_prompt(args.prompt_version)

    def _persist_calibration_judgment(experiment_name: str, entry: dict) -> None:
        """Append one judge-vs-deterministic row to data/judgments/<exp>.jsonl
        (Issue #1 judge-calibration tracker: lets us measure whether the LLM
        judge systematically leans lenient/strict against the deterministic
        scorer before trusting it more broadly)."""
        from src.experiment_log import JUDGMENTS_DIR

        path = JUDGMENTS_DIR / f"{experiment_name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")

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

    # Per-row actual token usage/cost, captured from the specialist's last
    # LLM call (the manifest + experiment log aggregate these per run).
    usage_by_index: dict[int, dict] = {}

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
            if args.chunked:
                predicted = specialist.extract_chunked(
                    doc_text, args.chunk_chars, args.chunk_overlap)
            else:
                predicted = specialist.extract(doc_text)
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            print(f"ERROR {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
            composite = {"predicted": {}, "error": str(exc), "schema_valid": 0.0,
                         "overall_score": 0.0, "field_presence": 0.0,
                         "category_presence": 0.0,
                         "field_scores": {}, "ambiguous_fields": []}
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": str(exc),
                                 "expected_fields": expected_fields, "scores": {"composite": composite}})
            return composite

        usage = specialist._last_usage or {}
        usage_by_index[input_data["index"]] = usage

        if predicted.get("_parse_error"):
            composite = {"predicted": {}, "error": "parse error", "schema_valid": 0.0,
                         "overall_score": 0.0, "field_presence": 0.0,
                         "category_presence": 0.0,
                         "field_scores": {}, "ambiguous_fields": []}
            if manifest:
                manifest.append({"filename": filename, "status": "error",
                                 "tag": "ERROR!", "predicted": {}, "error": "parse error",
                                 "expected_fields": expected_fields, "scores": {"composite": composite}})
            return composite

        # Deterministic content scoring against CUAD ground truth (LOCAL —
        # with semantic embedding rescue; never executed on the Braintrust side).
        # doc_text is passed in for the FACTUALITY guard: every predicted list
        # item must match a label or be grounded in the source document.
        result = score_extraction("contract", field_types, predicted, expected_fields,
                                  doc_text=doc_text)
        populated = sum(
            1 for key, value in expected_fields.items()
            if predicted.get(key) not in (None, "", [])
        )
        field_presence = populated / len(expected_fields) if expected_fields else 0.0

        # CUAD YES/NO category presence: the 32 presence-type categories each
        # expect a binary answer — labeled clause present (the extraction must
        # cover it) or absent (satisfied unless fabricated).
        category_presence, presence_detail = score_category_presence(
            predicted, input_data.get("expected_presence") or {}, field_types
        )

        composite = {
            "predicted": predicted,
            "overall_score": result.overall_score or 0.0,
            "field_presence": field_presence,
            "schema_valid": 1.0,
            "field_scores": result.field_scores,
            "category_presence": category_presence,
            "category_presence_detail": presence_detail,
            # The list score that feeds the per-field score and the overall
            # tracker: ground-truth COVERAGE (recall) for partial-GT fields,
            # F1 otherwise. Raw precision/recall/f1 are kept in
            # ``entity_list_scores`` for audit, so every Braintrust tracker
            # is mutually consistent.
            "entity_list_f1": {k: v.score for k, v in result.entity_list_scores.items()},
            "entity_list_scores": {
                k: {"precision": v.precision, "recall": v.recall, "f1": v.f1,
                    "matched": v.matched, "n_predicted": v.matched + v.unmatched_predicted,
                    "n_expected": v.matched + v.unmatched_expected}
                for k, v in result.entity_list_scores.items()
            },
            # Factuality guard: verified_precision (share of predicted items
            # that match a label OR are grounded in the source document) and
            # hallucination_rate (share that are neither).
            "entity_list_audit": result.entity_list_audit,
            "overall_verified_precision": result.overall_verified_precision or 0.0,
            "ambiguous_fields": result.ambiguous_fields,
            # Truncation auditability: True when the document exceeded the input
            # cap and the specialist saw only head+tail.
            "truncated": bool(specialist._last_truncated),
            # Chunk auditability: windowed mode + how many windows this doc
            # needed (1 = single pass).
            "chunked": bool(getattr(specialist, "_last_chunked", False)),
            "n_chunks": int(getattr(specialist, "_last_n_chunks", 0) or 0),
        }

        span_meta = {
            "filename": filename,
            "prompt_version": args.prompt_version,
            "doc_category": input_data.get("doc_category"),
            "overall_score": result.overall_score,
            "field_scores": result.field_scores,
            "ambiguous_fields": result.ambiguous_fields,
            "expected_fields": expected_fields,
            "expected_presence": input_data.get("expected_presence") or {},
            "extracted_fields": {k: v for k, v in predicted.items() if v not in (None, "", [])},
            "entity_list_f1": composite["entity_list_f1"],
            "entity_list_scores": composite["entity_list_scores"],
            "entity_list_audit": composite["entity_list_audit"],
            "category_presence": category_presence,
            "category_presence_detail": presence_detail,
            "composite": composite,
            "usage": usage,
        }

        if args.judge and result.needs_judge_review:
            verdict = _run_judge(filename, doc_text, predicted,
                                 expected_fields, result.ambiguous_fields)
            span_meta["judge"] = verdict
            _persist_calibration_judgment(experiment_name, {
                "kind": "calibration",
                "filename": filename,
                "deterministic_overall_score": round(result.overall_score or 0.0, 4),
                "ambiguous_fields": result.ambiguous_fields,
                "correctness_label": (verdict.get("correctness") or {}).get("extraction_correctness_label"),
                "correctness_error": verdict.get("correctness_error"),
                "completeness_label": (verdict.get("completeness") or {}).get("completeness_label"),
            })

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

    def overall_verified_precision(output: dict, expected) -> float:
        """FACTUALITY guard: mean over the row's list fields of the share of
        predicted items that match a ground-truth label OR are grounded in
        the source document. Items that are neither are hallucinations —
        a row reporting fabricated content scores 0 on this tracker even
        when its coverage score is perfect."""
        audits = ((output or {}).get("entity_list_audit") or {})
        values = [float(a.get("verified_precision") or 0.0) for a in audits.values()
                  if a.get("n_predicted")]
        return round(sum(values) / len(values), 4) if values else 0.0

    def category_presence(output: dict, expected) -> float:
        """CUAD YES/NO category conformance: share of the document's
        applicable presence-type categories (labeled clauses that must be
        covered) whose clause is present in the extraction. Per the CUAD
        dataset card, these categories expect a Yes/No answer; absent
        categories are satisfied unless the model fabricates them."""
        return float((output or {}).get("category_presence") or 0.0)

    def make_field_scorer(field_name: str):
        def scorer(output: dict, expected) -> float:
            return float(((output or {}).get("field_scores") or {}).get(field_name) or 0.0)
        scorer.__name__ = f"{field_name}_score"
        return scorer

    def make_list_f1_scorer(field_name: str):
        """List trackers report the SAME list score that feeds the per-field
        score (GT coverage for partial-GT fields, F1 otherwise) — so the
        per-field score, the *_f1 tracker, and the overall tracker never
        disagree in the Braintrust UI. Raw precision/recall/f1 remain
        available in the row's ``entity_list_scores`` metadata for audit."""
        def scorer(output: dict, expected) -> float:
            return float(((output or {}).get("entity_list_f1") or {}).get(field_name) or 0.0)
        scorer.__name__ = f"{field_name}_f1"
        return scorer

    def make_list_precision_scorer(field_name: str):
        """OVER-EXTRACTION guard: share of predicted items that match a
        ground-truth label (raw precision). Extra-but-true items lower this
        tracker; the verified_precision tracker shows how many of the extras
        are at least grounded in the source document."""
        def scorer(output: dict, expected) -> float:
            audit = ((output or {}).get("entity_list_audit") or {}).get(field_name) or {}
            n_pred = audit.get("n_predicted") or 0
            if not n_pred:
                return 0.0
            return round(audit.get("matched_gt", 0) / n_pred, 4)
        scorer.__name__ = f"{field_name}_precision"
        return scorer

    def make_list_verified_precision_scorer(field_name: str):
        """TRUTH guard: share of predicted items that match a label OR are
        grounded in the source document text."""
        def scorer(output: dict, expected) -> float:
            audit = ((output or {}).get("entity_list_audit") or {}).get(field_name) or {}
            return float(audit.get("verified_precision") or 0.0)
        scorer.__name__ = f"{field_name}_verified_precision"
        return scorer

    if args.bt_scores == "none":
        bt_scorers = []
    elif args.bt_scores == "overall":
        # ONE cross-experiment tracker set: complex content accuracy + the
        # binary presence guard + the factuality guard + CUAD YES/NO
        # category conformance — cheap lookups, comparable across runs.
        bt_scorers = [overall_extraction_score, field_presence,
                      overall_verified_precision, category_presence]
    else:
        bt_scorers = [overall_extraction_score, field_presence, schema_valid,
                      overall_verified_precision, category_presence]
        for field_name in scored_fields:
            bt_scorers.append(make_field_scorer(field_name))
            field_type = field_types.get(field_name) or "name"
            if is_entity_list(field_type):
                bt_scorers.append(make_list_f1_scorer(field_name))
                bt_scorers.append(make_list_precision_scorer(field_name))
                bt_scorers.append(make_list_verified_precision_scorer(field_name))

    def _report_eval(evaluator, result, verbose, jsonl):
        failures = [r for r in result.results if r.error]
        for failure_ in failures:
            print(f"ERROR {failure_.input['filename']}: {failure_.error}", file=sys.stderr)
        return not failures

    def _report_run(results, verbose, jsonl):
        return all(results)

    if bt_enabled:
        result = braintrust.Eval(
            args.project,
            data=lambda: [
                {"input": {"index": i, "filename": d["filename"], "expected": d["expected"],
                           "doc_text": d["doc_text"], "expected_fields": d["expected_fields"],
                           "expected_presence": d.get("expected_presence") or {},
                           "doc_category": d.get("doc_category")},
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
    else:
        rows = [
            {"input": {"index": i, "filename": d["filename"], "expected": d["expected"],
                       "doc_text": d["doc_text"], "expected_fields": d["expected_fields"],
                       "expected_presence": d.get("expected_presence") or {},
                       "doc_category": d.get("doc_category")},
             "expected": {
                 "doc_type": d["expected"],
                 "expected_fields": d["expected_fields"],
             },
             "filename": d["filename"]}
            for i, d in enumerate(with_truth)
        ]
        result = run_local_eval(extract_contract, rows, args.max_concurrency)

    print_extraction_summary(result, scored_fields)
    log_experiment_to_repo(result, scored_fields, with_truth, args, experiment_name,
                           usage_by_index, log_path, md_log_path, field_types=field_types,
                           master_labels=master_labels if master_labels_used else None,
                           master_labels_path=str(master_labels_path) if master_labels_used else None,
                           tracing_backend="braintrust" if bt_enabled else "none",
                           tracing_meta=None if bt_enabled else {
                               "braintrust_logging": False,
                               "langsmith": langsmith_enabled(),
                               "hint": "run_langfuse_*_eval.py for Langfuse traces",
                           })
    if bt_enabled:
        braintrust.flush()
    return 0


def log_experiment_to_repo(result, scored_fields: list[str], dataset: list[dict],
                           args, experiment_name: str, usage_by_index: dict[int, dict],
                           log_path: Path, md_log_path: Path,
                           tracing_backend: str = "braintrust",
                           tracing_meta: dict | None = None,
                           field_types: dict[str, str] | None = None,
                           master_labels: dict | None = None,
                           master_labels_path: str | None = None) -> None:
    """Append ONE record of this experiment to the repo experiment log.

    The record carries every score (overall, presence, schema validity,
    per-field content scores and entity-list F1), all run parameters, token
    usage/cost totals, the data source, and every per-row result — read from
    the locally computed composite, so it always matches the manifest and the
    Braintrust lookups.

    ``tracing_backend`` names where the run was traced (``braintrust``
    default, ``langfuse`` for the mirror runner); ``tracing_meta`` carries
    backend specifics (project/environment) into the record's parameters.
    """
    def _mean_over(outputs: list[dict], key: str) -> float | None:
        values = [float(o.get(key) or 0.0) for o in outputs if o.get(key) is not None]
        return round(mean(values), 4) if values else None

    def _judge_calibration(experiment_name: str) -> dict:
        """Judge-vs-deterministic-scorer agreement over the rows the judge
        actually reviewed (ambiguous band). Bands mirror the scoring guide:
        strong >= 0.85, weak <= 0.5. Lean signals:
        judge_strict = deterministic strong but judge says inaccurate,
        judge_lenient = deterministic weak but judge says accurate."""
        import json as _json
        from src.experiment_log import JUDGMENTS_DIR

        path = JUDGMENTS_DIR / f"{experiment_name}.jsonl"
        if not path.exists():
            return {}
        rows = [_json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        rows = [r for r in rows if r.get("kind") == "calibration"]
        if not rows:
            return {}
        agree = judge_strict = judge_lenient = n_scored = 0
        for r in rows:
            label = r.get("correctness_label")
            score = r.get("deterministic_overall_score")
            if label is None or not isinstance(score, (int, float)):
                continue
            n_scored += 1
            if score >= 0.85 and label == "accurate":
                agree += 1
            elif score <= 0.5 and label == "inaccurate":
                agree += 1
            elif score >= 0.85 and label == "inaccurate":
                judge_strict += 1
            elif score <= 0.5 and label == "accurate":
                judge_lenient += 1
        return {
            "n_judged": len(rows),
            "n_scored": n_scored,
            "agree_rate": round(agree / n_scored, 4) if n_scored else None,
            "judge_strict": judge_strict,
            "judge_lenient": judge_lenient,
            "bands": {"strong_ge": 0.85, "weak_le": 0.5},
            "judgments_file": str(path),
        }

    def _bootstrap_ci(values):
        from src.bootstrap import bootstrap_ci as _bci
        return _bci(values)

    def _mean_field(outputs: list[dict], bucket: str, field: str) -> float | None:
        values = [
            float((o.get(bucket) or {}).get(field) or 0.0)
            for o in outputs if (o.get(bucket) or {}).get(field) is not None
        ]
        return round(mean(values), 4) if values else None

    def _mean_audit(outputs: list[dict], field: str, subkey: str) -> float | None:
        values = [
            float(((o.get("entity_list_audit") or {}).get(field) or {}).get(subkey) or 0.0)
            for o in outputs
            if ((o.get("entity_list_audit") or {}).get(field) or {}).get(subkey) is not None
        ]
        return round(mean(values), 4) if values else None

    rows = [r for r in result.results if r.error is None and isinstance(r.output, dict)]
    ok_outputs = [r.output for r in rows if not r.output.get("error")]
    per_field = {f: _mean_field(ok_outputs, "field_scores", f) for f in scored_fields}
    per_field = {f: v for f, v in per_field.items() if v is not None}
    entity_f1 = {f: _mean_field(ok_outputs, "entity_list_f1", f) for f in scored_fields}
    entity_f1 = {f: v for f, v in entity_f1.items() if v is not None}
    verified = {f: _mean_audit(ok_outputs, f, "verified_precision") for f in scored_fields}
    verified = {f: v for f, v in verified.items() if v is not None}
    hallucinations = {f: _mean_audit(ok_outputs, f, "hallucination_rate") for f in scored_fields}
    hallucinations = {f: v for f, v in hallucinations.items() if v is not None}

    per_row = []
    for r in result.results:
        output = r.output if isinstance(r.output, dict) else {}
        index = r.input.get("index", -1) if isinstance(r.input, dict) else -1
        per_row.append({
            "filename": r.input.get("filename") if isinstance(r.input, dict) else "",
            "status": "error" if r.error is not None or output.get("error") else "completed",
            "error": r.error or output.get("error"),
            "overall_score": output.get("overall_score"),
            "field_presence": output.get("field_presence"),
            "schema_valid": output.get("schema_valid"),
            # The specialist's raw predicted extraction — logged so the
            # experiment log carries the model OUTPUT, not just its scores.
            "predicted": output.get("predicted"),
            "field_scores": output.get("field_scores"),
            "entity_list_f1": output.get("entity_list_f1"),
            "entity_list_scores": output.get("entity_list_scores"),
            "entity_list_audit": output.get("entity_list_audit"),
            "overall_verified_precision": output.get("overall_verified_precision"),
            "category_presence": output.get("category_presence"),
            "ambiguous_fields": output.get("ambiguous_fields"),
            "truncated": output.get("truncated"),
            "chunked": output.get("chunked"),
            "n_chunks": output.get("n_chunks"),
            "tokens": usage_by_index.get(index) or {},
        })

    # ---- run-level diagnostic metrics --------------------------------------
    # Precision/recall/F1 (raw list matching, macro + micro), date/duration
    # MAE vs the master-labels normalized answers, and the field-level error
    # decomposition (exact / partial / miss rates). See src/metrics.py.
    from src.metrics import extraction_diagnostics

    expected_by_index = {i: d.get("expected_fields") or {}
                         for i, d in enumerate(dataset)}
    diag_rows = []
    for r in result.results:
        if r.error is not None:
            continue
        output = r.output if isinstance(r.output, dict) else {}
        if output.get("error"):
            continue
        index = r.input.get("index", -1) if isinstance(r.input, dict) else -1
        diag_rows.append({
            "filename": r.input.get("filename") if isinstance(r.input, dict) else "",
            "predicted": output.get("predicted") or {},
            "expected_fields": expected_by_index.get(index) or {},
            "field_scores": output.get("field_scores") or {},
            "entity_list_scores": output.get("entity_list_scores") or {},
        })
    diagnostics = extraction_diagnostics(
        diag_rows, field_types or {}, master=master_labels) if diag_rows else {}

    record = {
        "type": "experiment",
        "task": "contract_entity_extraction",
        "experiment_name": experiment_name,
        "git": git_snapshot(),
        "model": args.model,
        "prompt_version": args.prompt_version,
        "data_source": {
            "project": f"{args.dataset_project}/{args.dataset}",
            "ground_truth": "cuad_v1_clause_labels",
            "ground_truth_mode": "cuad_type_aware",
            "master_labels": master_labels_path,
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "n_samples": len(dataset),
            "sample_requested": args.sample,
            "limit": args.limit,
            "seed": args.seed,
        },
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "max_input_chars": args.max_input_chars,
            "reasoning_effort": args.reasoning_effort,
            "max_concurrency": args.max_concurrency,
            "bt_scores": getattr(args, "bt_scores", "none"),
            "judge": getattr(args, "judge", False),
            "chunked": bool(getattr(args, "chunked", False)),
            "chunk_chars": getattr(args, "chunk_chars", None),
            "chunk_overlap": getattr(args, "chunk_overlap", None),
            "manifest": str(args.manifest) if args.manifest else None,
            "tracing_backend": tracing_backend,
            **({"tracing": tracing_meta} if tracing_meta else {}),
        },
        "tokens": tokens_summary(list(usage_by_index.values()), model=args.model),
        "scores": {
            **({"judge_calibration": _judge_calibration(experiment_name)}
               if getattr(args, "judge", False) else {}),
            "overall_extraction_score": _mean_over(ok_outputs, "overall_score"),
            "overall_extraction_score_ci": _bootstrap_ci(
                [o.get("overall_score") for o in ok_outputs]),
            "field_presence": _mean_over(ok_outputs, "field_presence"),
            "schema_valid": _mean_over(ok_outputs, "schema_valid"),
            "overall_verified_precision": _mean_over(ok_outputs, "overall_verified_precision"),
            "category_presence": _mean_over(ok_outputs, "category_presence"),
            "per_field": per_field,
            "entity_list_f1": entity_f1,
            "verified_precision": verified,
            "hallucination_rate": hallucinations,
            **({"diagnostics": diagnostics} if diagnostics else {}),
        },
        "n_rows": len(result.results),
        "n_ok": len(ok_outputs),
        "n_error": len(result.results) - len(ok_outputs),
        "results": per_row,
    }
    jsonl_path = append_experiment(record, log_path)
    append_markdown(record, md_log_path)
    print(f"\nExperiment logged to {jsonl_path}")


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
