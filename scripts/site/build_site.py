#!/usr/bin/env python3
"""Build the static GitHub Pages site that views the experiment log.

The site lives in ``docs/`` (served by GitHub Pages from the ``main`` branch
via Settings -> Pages -> "Deploy from a branch" -> ``main`` -> ``/docs`` —
no Actions runners involved). ``docs/data/`` is DERIVED, exactly like
``reports/experiment_log.md`` is derived from
``reports/experiment_log.jsonl``: this script regenerates the whole data
tree from the JSONL source of truth, so the site always reflects every
record, in order, with no stale or hand-edited data.

Layout produced:

    docs/data/meta.json          build info + dataset-level facts
    docs/data/index.json         one compact summary per run (index table)
    docs/data/runs/{id}.json     the full record per run (detail pages)

Usage:
    python scripts/site/build_site.py                              # rebuild docs/data
    python scripts/site/build_site.py --jsonl /tmp/log.jsonl \
        --out /tmp/site-data                                      # custom paths
    python scripts/site/build_site.py --check                      # verify data is current
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSONL = REPO_ROOT / "reports" / "experiment_log.jsonl"
DEFAULT_OUT = REPO_ROOT / "docs" / "data"
REPO_URL = "https://github.com/Exios66/llm-entity-extraction"


def _fmt(value: float) -> str:
    """Format a score like the markdown log does (4 decimals)."""
    return f"{value:.4f}"


def load_records(path: Path) -> list[dict]:
    """Read every experiment record from the JSONL log (append-only source)."""
    records = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover
            print(f"Skipping malformed line in {path}: {exc}", file=sys.stderr)
    return records


def headline_score(record: dict) -> dict:
    """Derive the headline score card for a run, mirroring the md index.

    Returns a dict with the score, its human label, and a 0-1 ratio for
    progress-bar rendering; empty dict when the task has no headline metric.
    """
    scores = record.get("scores") or {}
    task = record.get("task")
    if task == "contract_entity_extraction":
        value = scores.get("overall_extraction_score")
        if isinstance(value, (int, float)):
            return {"label": "extraction", "value": value}
    if task == "chained_sorter_extractor":
        sorter = scores.get("sorter") or {}
        extractor = scores.get("extractor") or {}
        extractor_value = extractor.get("overall_extraction_score")
        if isinstance(extractor_value, (int, float)):
            detail = f"extractor {_fmt(extractor_value)}"
            sorter_value = sorter.get("exact_match")
            if isinstance(sorter_value, (int, float)):
                detail += f" · sorter doc_type {_fmt(sorter_value)}"
            return {
                "label": "extractor score",
                "value": extractor_value,
                "detail": detail,
            }
    if task == "subtype_classification":
        sorter = scores.get("sorter") or {}
        doc_type = sorter.get("exact_match")
        strict = sorter.get("subtype_accuracy")
        equiv = sorter.get("subtype_accuracy_equiv")
        if isinstance(strict, (int, float)) and isinstance(doc_type, (int, float)):
            detail = f"doc_type {_fmt(doc_type)} · strict {_fmt(strict)}"
            if isinstance(equiv, (int, float)):
                detail += f" · equiv {_fmt(equiv)}"
            return {
                "label": "subtype strict",
                "value": strict,
                "detail": detail,
            }
    if task == "legalbench_binary_answer":
        value = scores.get("accuracy")
        if isinstance(value, (int, float)):
            detail = (
                f"macro {_fmt(scores.get('macro_category_accuracy') or 0)}"
                f" · yes-F1 {_fmt(scores.get('yes_f1') or 0)}"
                f" · cal {_fmt(scores.get('calibration_error') or 0)}"
            )
            return {"label": "QA accuracy", "value": value, "detail": detail}
    if task == "legalbench_multiclass_classification":
        value = scores.get("accuracy")
        if isinstance(value, (int, float)):
            detail = f"strict {_fmt(value)} · equiv {_fmt(scores.get('accuracy_equiv') or 0)}"
            return {"label": "family accuracy", "value": value, "detail": detail}
    return {}


def breakdown(record: dict) -> dict:
    """Per-task metric breakdown shown in the dashboard (no per-doc data)."""
    task = record.get("task")
    scores = record.get("scores") or {}
    if task == "contract_entity_extraction":
        return {
            "overall_extraction_score": scores.get("overall_extraction_score"),
            "field_presence": scores.get("field_presence"),
            "schema_valid": scores.get("schema_valid"),
            "per_field": scores.get("per_field") or {},
        }
    if task == "chained_sorter_extractor":
        sorter = scores.get("sorter") or {}
        extractor = scores.get("extractor") or {}
        return {
            "sorter": {
                "exact_match": sorter.get("exact_match"),
                "subtype_accuracy": sorter.get("subtype_accuracy"),
                "confidence": sorter.get("confidence"),
            },
            "extractor": {
                "overall_extraction_score": extractor.get("overall_extraction_score"),
                "field_presence": extractor.get("field_presence"),
                "overall_verified_precision": extractor.get("overall_verified_precision"),
                "category_presence": extractor.get("category_presence"),
            },
        }
    if task == "subtype_classification":
        sorter = scores.get("sorter") or {}
        failures = sorter.get("failure_insights") or {}
        return {
            "doc_type_accuracy": sorter.get("exact_match"),
            "subtype_accuracy": sorter.get("subtype_accuracy"),
            "subtype_accuracy_equiv": sorter.get("subtype_accuracy_equiv"),
            "confidence": sorter.get("confidence"),
            "n_failed": failures.get("n_failed"),
            "mode_counts": failures.get("mode_counts") or {},
        }
    if task == "legalbench_binary_answer":
        return {
            "accuracy": scores.get("accuracy"),
            "macro_category_accuracy": scores.get("macro_category_accuracy"),
            "yes_f1": scores.get("yes_f1"),
            "confidence_mean": scores.get("confidence_mean"),
            "calibration_error": scores.get("calibration_error"),
            "n_questions": scores.get("n_questions"),
            "n_yes": scores.get("n_yes"),
            "n_no": scores.get("n_no"),
        }
    if task == "legalbench_multiclass_classification":
        return {
            "accuracy": scores.get("accuracy"),
            "accuracy_equiv": scores.get("accuracy_equiv"),
            "macro_f1": scores.get("macro_f1"),
            "confidence_mean": scores.get("confidence_mean"),
            "calibration_error": scores.get("calibration_error"),
            "n_documents": scores.get("n_documents"),
        }
    return {}


def prompt_string(record: dict) -> str:
    """Human prompt label: record field first, else sorter+extractor pair."""
    prompt = record.get("prompt_version")
    if not prompt and isinstance(record.get("prompt_versions"), dict):
        prompt = " + ".join(str(v) for v in record["prompt_versions"].values())
    return prompt or "—"


def wilson_ci(p: float | None, n: int | None, z: float = 1.96) -> dict | None:
    """Wilson score interval for a proportion (95% by default).

    Sample-size-aware: the interval narrows with n, so a 5-document run gets
    a wide interval while a 509-document run gets a tight one. Used to
    quantify how much a score could vary by chance, and to flag deltas
    between runs of different sizes as not statistically meaningful.
    """
    if p is None or not n:
        return None
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {
        "lo": max(0.0, center - half),
        "hi": min(1.0, center + half),
        "half_pp": half * 100,
    }


def summarize(record: dict, run_id: int, best_by_task: dict[str, float]) -> dict:
    """Compact index-row summary used by the site's index table."""
    tokens = record.get("tokens") or {}
    if "total" in tokens:
        total_tokens = (tokens["total"] or {}).get("total_tokens")
        cost_total = (tokens["total"] or {}).get("cost_total_usd")
    else:
        total_tokens = tokens.get("total_tokens")
        cost_total = tokens.get("cost_total_usd")
    data_source = record.get("data_source") or {}
    headline = headline_score(record)
    task = record.get("task", "")
    delta = None
    best = best_by_task.get(task)
    if headline and best is not None:
        delta = (headline["value"] - best) * 100  # percentage points
    return {
        "id": run_id,
        "experiment_name": record.get("experiment_name", ""),
        "task": task,
        "model": record.get("model", ""),
        "prompts": prompt_string(record),
        "headline": headline,
        "ci95": wilson_ci(headline["value"], record.get("n_rows")) if headline else None,
        "breakdown": breakdown(record),
        "n_rows": record.get("n_rows"),
        "n_ok": record.get("n_ok"),
        "n_error": record.get("n_error") or 0,
        "total_tokens": total_tokens,
        "cost_usd": tokens.get("cost_usd") if tokens else None,
        "cost_total_usd": cost_total,
        "delta_best_pp": delta,
        "timestamp": record.get("timestamp"),
        "git": record.get("git"),
        "data_source_project": data_source.get("project"),
        "data_source_n_samples": data_source.get("n_samples"),
        "seed": data_source.get("seed"),
    }


# ---------------------------------------------------------------------------
# Scoring guide — canonical explanations mirrored from SCORING.md (repo root).
# Rendered verbatim as the reference card on the site index. Keep in sync with
# SCORING.md; the live repo file remains the source of truth.
# ---------------------------------------------------------------------------

BANDS = [
    {"min": 0.85, "label": "Strong", "cls": "good",
     "meaning": "High confidence result; only minor field/family-level misses."},
    {"min": 0.60, "label": "Moderate", "cls": "warn",
     "meaning": "Material misses (this range overlaps the repo's ambiguous band "
                "[0.5, 0.85] that triggers a judge review pass)."},
    {"min": 0.0, "label": "Weak", "cls": "bad",
     "meaning": "Poor result; the model is missing or misclassifying core content."},
]

SCORING_GUIDE = {
    "bands": BANDS,
    "general": (
        "All scores are deterministic and computed locally — no LLM grading. "
        "The markdown log, manifests, and this site all read the same numbers. "
        "Compare runs only on the SAME sample (same dataset, seed, and size): "
        "accuracy deltas across different samples are meaningless."
    ),
    "tasks": {
        "contract_entity_extraction": {
            "headline": {"key": "overall_extraction_score", "label": "Overall extraction"},
            "summary": "How faithfully the contracts-specialist extracted every expected "
                       "field from the contract text, per field's declared type.",
            "formula": ("mean of the per-field content scores over expected fields with a "
                        "non-null ground-truth value"),
            "conveys": ("End-to-end extraction quality: dates/money exact, names fuzzy-"
                        "matched, clauses containment-scored, entity lists bipartite-"
                        "matched against ground truth."),
            "components": [
                {"key": "overall_extraction_score", "label": "Overall extraction",
                 "calculation": "mean of per-field content scores",
                 "meaning": "Composite content accuracy across all expected fields."},
                {"key": "field_presence", "label": "Field presence",
                 "calculation": "share of expected fields the model populated (non-null/non-empty)",
                 "meaning": "Did the model produce a value at all, regardless of correctness?"},
                {"key": "schema_valid", "label": "Schema valid",
                 "calculation": "1.0 iff output is parseable, schema-conformant JSON",
                 "meaning": "Output-contract conformance — 0 means the row was unusable."},
                {"key": "per_field", "label": "Per-field scores",
                 "calculation": ("type-aware: date/money exact; name fuzzy (Jaro-Winkler + "
                                 "token-set); free_text SQuAD token F1; entity_list optimal "
                                 "bipartite matching at 0.6 threshold; containment = "
                                 "expected-token coverage"),
                 "meaning": "Where exactly quality is gained or lost."},
            ],
        },
        "chained_sorter_extractor": {
            "headline": {"key": "extractor.overall_extraction_score",
                         "label": "Extractor score"},
            "summary": "The full sorter → specialist chain: the sorter classifies the "
                       "document, then the specialist extracts with that context.",
            "formula": ("headline = the specialist's overall_extraction_score (same "
                        "composite as the extraction task); the sorter's doc-type match "
                        "is shown alongside"),
            "conveys": "End-to-end pipeline quality — both stages must work.",
            "components": [
                {"key": "sorter.exact_match", "label": "Sorter doc-type match",
                 "calculation": "1.0 iff doc_type == 'contract'",
                 "meaning": "The sorter sent the document down the contract path."},
                {"key": "sorter.subtype_accuracy", "label": "Sorter subtype accuracy",
                 "calculation": "1.0 iff doc_type AND normalized contract subtype match the CUAD folder",
                 "meaning": "Contract-family routing quality."},
                {"key": "extractor.overall_extraction_score", "label": "Extractor overall",
                 "calculation": "mean of per-field content scores (see extraction task)",
                 "meaning": "Field extraction quality given the sorter's context."},
                {"key": "extractor.overall_verified_precision", "label": "Verified precision",
                 "calculation": ("factuality guard: share of predicted items that match a "
                                 "GT label OR are grounded in the document (token coverage "
                                 "≥ 0.7)"),
                 "meaning": "Truthfulness — how much of the output is real, not hallucinated."},
                {"key": "extractor.category_presence", "label": "Category presence",
                 "calculation": "share of the document's applicable CUAD presence-categories covered",
                 "meaning": "Did the extraction cover the labeled clauses that must appear?"},
                {"key": "extractor.field_presence", "label": "Field presence",
                 "calculation": "share of expected fields populated",
                 "meaning": "Completeness of output fields."},
            ],
        },
        "subtype_classification": {
            "headline": {"key": "sorter.subtype_accuracy", "label": "Subtype accuracy (strict)"},
            "summary": "The sorter-only task: one call per document that decides the "
                       "primary class (contract or not) AND the contract-subtype family.",
            "formula": ("headline = strict subtype accuracy: share of rows whose normalized "
                        "predicted subtype exactly equals the CUAD ground-truth folder"),
            "conveys": "Routing quality: strict is the discriminating signal; equiv allows "
                       "defensible family swaps (reseller↔distributor, maintenance↔license, "
                       "development↔license, affiliate↔joint_venture).",
            "components": [
                {"key": "doc_type_accuracy", "label": "Doc-type accuracy (exact_match)",
                 "calculation": "share of rows where doc_type == 'contract'",
                 "meaning": "Primary-class correctness (every CUAD row is a contract)."},
                {"key": "subtype_accuracy", "label": "Subtype strict",
                 "calculation": "share of rows where normalized subtype == CUAD folder exactly",
                 "meaning": "Exact family-level routing."},
                {"key": "subtype_accuracy_equiv", "label": "Subtype equiv",
                 "calculation": "strict OR defensible equivalent family",
                 "meaning": "How often the model routed to a legally-defensible family."},
                {"key": "confidence", "label": "Confidence",
                 "calculation": "mean of the model's reported per-row confidence",
                 "meaning": "Calibration signal — how sure the model claims to be."},
                {"key": "n_failed", "label": "Failed rows",
                 "calculation": "rows with subtype_ok == false, broken down by failure mode",
                 "meaning": ("modes: family_confusion (wrong family), function_over_form "
                             "(doc_type miss), other_fallback (fell to 'other'), "
                             "equivalent_family (recovered by equivalence)")},
            ],
        },
        "legalbench_binary_answer": {
            "headline": {"key": "accuracy", "label": "QA accuracy"},
            "summary": ("LegalBench suite (llm-mailroom/legalbench/) — CUAD contract-QA "
                        "binary-answer task: yes/no questions over contracts with "
                        "evidence spans, scored against the CUAD annotations."),
            "formula": "headline = share of questions answered correctly (predicted yes/no == annotation)",
            "conveys": "Contract-comprehension accuracy on a large, real legal QA corpus.",
            "components": [
                {"key": "accuracy", "label": "Accuracy",
                 "calculation": "share of questions with predicted == expected",
                 "meaning": "Headline comprehension quality."},
                {"key": "macro_category_accuracy", "label": "Macro category accuracy",
                 "calculation": "mean of per-clause-category accuracies (41 categories)",
                 "meaning": "Whether any clause family is disproportionately hard."},
                {"key": "yes_f1", "label": "Yes-class F1",
                 "calculation": "F1 for answering 'yes' (precision/recall over yes predictions vs yes labels)",
                 "meaning": "False-positive tendency on affirmative answers."},
                {"key": "confidence_mean", "label": "Confidence mean",
                 "calculation": "mean of the model's reported per-question confidence",
                 "meaning": "Calibration signal."},
                {"key": "calibration_error", "label": "Calibration error (ECE)",
                 "calculation": "expected calibration error over confidence/outcome pairs",
                 "meaning": "How well confidence matches observed correctness."},
            ],
        },
        "legalbench_multiclass_classification": {
            "headline": {"key": "accuracy", "label": "Family accuracy (strict)"},
            "summary": ("LegalBench suite (llm-mailroom/legalbench/) — CUAD contract-family "
                        "classification: assign one of the 25 contract families (+ other) "
                        "to each contract, scored against the family derived from the "
                        "CUAD folder/title taxonomy."),
            "formula": ("headline = strict family accuracy; equiv additionally accepts "
                        "defensible family swaps (same SUBTYPE_EQUIVALENCES as the sorter)"),
            "conveys": "Multiclass legal-routing accuracy with a defensible-equivalence lens.",
            "components": [
                {"key": "accuracy", "label": "Strict accuracy",
                 "calculation": "share of documents whose family key matches exactly",
                 "meaning": "Exact family-level routing."},
                {"key": "accuracy_equiv", "label": "Equiv accuracy",
                 "calculation": "strict OR defensible equivalent family",
                 "meaning": "Routing to a legally-defensible family."},
                {"key": "macro_f1", "label": "Macro F1",
                 "calculation": "mean one-vs-rest F1 over families with labels present",
                 "meaning": "Class balance-adjusted quality."},
                {"key": "confidence_mean", "label": "Confidence mean",
                 "calculation": "mean of the model's reported per-document confidence",
                 "meaning": "Calibration signal."},
            ],
        },
    },
    "references": {
        "scoring_md": f"{REPO_URL}/blob/main/SCORING.md",
        "agents_md": f"{REPO_URL}/blob/main/AGENTS.md",
    },
}


def build_meta(records: list[dict], jsonl_path: Path, out_dir: Path) -> dict:
    """Dataset-level facts shown in the site header/footer."""
    tasks: dict[str, int] = {}
    models: dict[str, int] = {}
    prompts: dict[str, int] = {}
    n_rows = n_ok = n_error = total_tokens = 0
    for record in records:
        task = record.get("task", "")
        tasks[task] = tasks.get(task, 0) + 1
        model = record.get("model", "")
        models[model] = models.get(model, 0) + 1
        prompt = prompt_string(record)
        prompts[prompt] = prompts.get(prompt, 0) + 1
        n_rows += record.get("n_rows") or 0
        n_ok += record.get("n_ok") or 0
        n_error += record.get("n_error") or 0
        tokens = record.get("tokens") or {}
        if "total" in tokens:
            total_tokens += (tokens["total"] or {}).get("total_tokens") or 0
        else:
            total_tokens += tokens.get("total_tokens") or 0
    best_by_task: dict[str, dict] = {}
    for i, record in enumerate(records, start=1):
        headline = headline_score(record)
        if not headline:
            continue
        task = record.get("task", "")
        current = best_by_task.get(task)
        if current is None or headline["value"] > current["value"]:
            best_by_task[task] = {
                "run_id": i,
                "value": headline["value"],
                "label": headline["label"],
            }

    values_by_task: dict[str, list[tuple[int, float]]] = {}
    for i, record in enumerate(records, start=1):
        headline = headline_score(record)
        if headline:
            values_by_task.setdefault(record.get("task", ""), []).append(
                (i, headline["value"]))
    task_aggregates: dict[str, dict] = {}
    for task, pairs in values_by_task.items():
        values = sorted(v for _, v in pairs)
        n = len(values)
        median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
        best_pair = max(pairs, key=lambda p: p[1])
        worst_pair = min(pairs, key=lambda p: p[1])
        task_aggregates[task] = {
            "runs": n,
            "best": {"run_id": best_pair[0], "value": best_pair[1]},
            "median": median,
            "worst": {"run_id": worst_pair[0], "value": worst_pair[1]},
            "documents": sum(r.get("n_rows") or 0 for r in records if r.get("task") == task),
            "tokens": sum(
                ((r.get("tokens") or {}).get("total") or {}).get("total_tokens")
                if "total" in (r.get("tokens") or {})
                else (r.get("tokens") or {}).get("total_tokens") or 0
                for r in records if r.get("task") == task),
        }

    return {
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": str(jsonl_path.relative_to(REPO_ROOT)),
        "repo_url": REPO_URL,
        "run_count": len(records),
        "tasks": tasks,
        "models": models,
        "prompts": prompts,
        "n_rows": n_rows,
        "n_ok": n_ok,
        "n_error": n_error,
        "total_tokens": total_tokens,
        "best_per_task": best_by_task,
        "task_aggregates": task_aggregates,
        "scoring_guide": SCORING_GUIDE,
    }


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL,
                        help=f"JSONL experiment log (default: {DEFAULT_JSONL})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Site data output dir (default: {DEFAULT_OUT})")
    parser.add_argument("--check", action="store_true",
                        help="Verify docs/data matches the JSONL; exit 1 if stale")
    args = parser.parse_args(argv)

    records = load_records(args.jsonl)
    if not records:
        parser.error(f"No experiment records found in {args.jsonl}.")

    if args.check:
        index_path = args.out / "index.json"
        meta_path = args.out / "meta.json"
        if not index_path.exists() or not meta_path.exists():
            print("Site data is missing; run build_site.py to regenerate.")
            return 1
        current = json.loads(index_path.read_text(encoding="utf-8"))
        if len(current) != len(records):
            print(f"Site data is stale: {len(current)} runs in site, "
                  f"{len(records)} in {args.jsonl}.")
            return 1
        print(f"Site data is current ({len(current)} runs).")
        return 0

    runs_dir = args.out / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    best_values: dict[str, float] = {}
    for i, record in enumerate(records, start=1):
        headline = headline_score(record)
        if headline:
            task = record.get("task", "")
            current = best_values.get(task)
            if current is None or headline["value"] > current:
                best_values[task] = headline["value"]
    summaries = []
    for index, record in enumerate(records, start=1):
        (runs_dir / f"{index:03d}.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")
        summaries.append(summarize(record, index, best_values))
    (args.out / "index.json").write_text(
        json.dumps(summaries, indent=1), encoding="utf-8")
    (args.out / "meta.json").write_text(
        json.dumps(build_meta(records, args.jsonl, args.out), indent=1),
        encoding="utf-8")
    print(f"Site data rebuilt: {len(records)} records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
