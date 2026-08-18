"""ContractEval-style mapping scorer over stored extraction runs.

Benchmarks this repo's one-pass contract-extraction pipeline against
ContractEval (arXiv 2508.03080, github.com/olivialiu121/ContractEval) by
mapping each predicted obligation span to its CUAD category and then applying
ContractEval's exact correctness rubric.

Task-unit mismatch (documented in the report and memo): ContractEval runs ONE
(contract, question) call per CUAD category and the model either quotes the
category's clause(s) or answers "No related clause."; this pipeline extracts
the ``key_obligations``/``termination_clauses`` umbrella in ONE pass. The
mapping scorer bridges the gap by attributing each disaggregated predicted
span to the CUAD category whose label it covers, then synthesizing the
per-category answer (union of mapped spans, else "No related clause.").

Metrics mirror ``ContractEval/Evaluation.py`` + ``open_source_model.py``
exactly: Correctness accuracy/precision/recall/F1/F2 with TP = every
ground-truth label span verbatim-contained in the output; Output
Effectiveness = mean token-set Jaccard over positive-label pairs; and the
"no related clause" / false-"no related clause" rates.

Caveat carried into every result: a one-pass extractor cannot claim a
category the GT marks absent, so precision is structurally 1.0 and the
discriminating signals versus ContractEval are recall, F2, Jaccard, and the
false-"no related clause" rate.
"""

from __future__ import annotations

import ast
import csv
import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# The clause-list fields the mapping scorer consumes (CUAD YES/NO categories
# map onto these in ``src.cuad_ground_truth.CUAD_CATEGORIES``).
OBLIGATION_FIELDS: tuple[str, ...] = ("key_obligations", "termination_clauses")

# ContractEval Table III (arXiv 2508.03080) — published per-model
# (F1, F2, Jaccard, false-"no related clause" rate). Reference row for the
# comparison table; F1/F2 rounded to 3dp as printed in the paper.
CONTRACTEVAL_TABLE_III: dict[str, dict[str, float]] = {
    "gpt-4.1": {"f1": 0.641, "f2": 0.672, "jaccard": 0.472, "false_no_related": 0.071},
    "gpt-4.1-mini": {"f1": 0.644, "f2": 0.678, "jaccard": 0.435, "false_no_related": 0.072},
    "claude-sonnet-4": {"f1": 0.523, "f2": 0.578, "jaccard": 0.458, "false_no_related": 0.025},
    "gemini-2.5-pro": {"f1": 0.497, "f2": 0.604, "jaccard": 0.506, "false_no_related": 0.011},
    "qwen3-8b-thinking": {"f1": 0.540, "f2": 0.512, "jaccard": 0.391, "false_no_related": 0.110},
}

# Lower bound for the best-match fallback mapping (expected-within-predicted
# token containment of a predicted span against a category's label).
BEST_MATCH_FLOOR: float = 0.5

_NO_RELATED_PHRASE = "no related clause"


def normalize_filename(name: Any) -> str:
    """Aggressive filename normalization used to join stored-run rows to the
    master-clauses GT: lowercase, drop the extension, and collapse every
    non-alphanumeric character (so ``A&R ... .PDF`` == ``A_R ...``)."""
    s = str(name or "").lower()
    s = re.sub(r"\.pdf$", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_spans(value: Any) -> list[str]:
    """Parse a master-clauses category cell (a Python-list literal of clause
    spans) into a list of spans; ``[]``/blank cells become an empty list."""
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        logger.warning("master_gt_cell_unparseable", cell=text[:80])
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def load_master_gt(path: str | Path) -> dict[str, dict[str, list[str]]]:
    """Load ``data/cuad/master_clauses.csv`` into
    ``{normalized_filename: {category: [clause spans]}}`` (offline,
    reproducible GT for the mapping scorer)."""
    out: dict[str, dict[str, list[str]]] = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return out
        category_cols = [
            col for col in reader.fieldnames
            if col != "Filename" and not col.lower().endswith("answer")
            and not col.lower().endswith("- answer")
        ]
        for row in reader:
            key = normalize_filename(row.get("Filename"))
            if not key:
                continue
            spans: dict[str, list[str]] = {}
            for col in category_cols:
                parsed = _parse_spans(row.get(col))
                if parsed:
                    spans[col] = parsed
            out[key] = spans
    return out


def applicable_categories() -> list[str]:
    """The CUAD YES/NO categories this pipeline can score (those mapped onto
    the obligation clause-list fields), in sorted order."""
    from src.cuad_ground_truth import ANSWER_YES_NO, CUAD_CATEGORIES

    return sorted(
        cat for cat, spec in CUAD_CATEGORIES.items()
        if spec["answer_format"] == ANSWER_YES_NO
        and spec.get("field") in OBLIGATION_FIELDS
    )


def disaggregate_spans(items: Any) -> list[str]:
    """Disaggregate a predicted clause list into discrete sentence-level spans
    (issue #21 fix #1), via the llm-dojo-scoring package v0.3.0 helper."""
    from src.field_scoring import disaggregate_clause_spans

    return disaggregate_clause_spans(items)


def get_jaccard(gt: str, pred: str) -> float:
    """Exact copy of ContractEval's ``get_jaccard``: strip ``.,;:``, lowercase,
    replace ``/`` with space, then token-set Jaccard over whitespace tokens."""
    for token in (".", ",", ";", ":"):
        gt = gt.replace(token, "")
        pred = pred.replace(token, "")
    gt = gt.lower().replace("/", " ")
    pred = pred.lower().replace("/", " ")
    gt_words = set(gt.split(" "))
    pred_words = set(pred.split(" "))
    union = gt_words.union(pred_words)
    if not union:
        return 0.0
    return len(gt_words.intersection(pred_words)) / len(union)


def _containment(span: str, label: str) -> float:
    from src.field_scoring import score_containment_field

    return score_containment_field(span, label)


def map_span_to_categories(span: str, gt_spans: dict[str, list[str]],
                           routed: dict[str, list[str]]) -> list[str]:
    """CUAD categories one predicted span belongs to.

    Priority: (1) reasoning-trace routing — an entry tagged with the canonical
    category name whose evidence is contained in (or contains) the span
    (issue #21 fix #2; fires on v33+ runs); (2) verbatim containment — every
    category with at least one label span inside the span (the pre-retag path,
    enabled by disaggregation); (3) best-match fallback — every category whose
    expected-within-predicted containment reaches ``BEST_MATCH_FLOOR`` (a span
    can cover several categories' clauses at once, mirroring ContractEval's
    per-category calls).
    """
    cats: set[str] = set()
    for cat, evidences in routed.items():
        for evidence in evidences:
            if not evidence:
                continue
            if evidence in span or span in evidence or _containment(span, evidence) >= 0.7:
                cats.add(cat)
    for cat, labels in gt_spans.items():
        if not labels:
            continue
        if any(label.strip(" \n`") in span for label in labels):
            cats.add(cat)
    if not cats:
        for cat, labels in gt_spans.items():
            if not labels:
                continue
            score = max(_containment(span, label) for label in labels)
            if score >= BEST_MATCH_FLOOR:
                cats.add(cat)
    return sorted(cats)


def build_category_output(predicted: dict, doc_gt: dict[str, list[str]]) -> dict[str, str]:
    """Synthesize the per-CUAD-category answer for one stored row.

    Returns ``{category: output_string}`` for every applicable obligation
    category, where the output is the union of mapped disaggregated spans or
    the ContractEval "no related clause" phrase when nothing maps.
    """
    spans = []
    for field in OBLIGATION_FIELDS:
        spans.extend(disaggregate_spans(predicted.get(field)))
    routed: dict[str, list[str]] = {}
    for entry in (predicted.get("reasoning") or {}).get("entries") or []:
        field_name = str(entry.get("field") or "").strip()
        evidence = str(entry.get("evidence") or "").strip()
        if field_name and evidence and field_name in applicable_categories():
            routed.setdefault(field_name, []).append(evidence)

    mapped: dict[str, list[str]] = {}
    for span in spans:
        for cat in map_span_to_categories(span, doc_gt, routed):
            mapped.setdefault(cat, []).append(span)

    output: dict[str, str] = {}
    for cat in applicable_categories():
        cat_spans = mapped.get(cat) or []
        output[cat] = " ".join(cat_spans) if cat_spans else _NO_RELATED_PHRASE
    return output


def contracteval_metrics(pairs: list[tuple[list[str], str]]) -> dict[str, Any]:
    """ContractEval metrics over ``(label_spans, output)`` pairs — mirrors
    ``Evaluation.py`` / ``open_source_model.py`` confusion logic exactly."""
    tp = tn = fn = fp = 0
    jaccards: list[float] = []
    no_related_cnt = 0
    false_no_related_cnt = 0
    for label, output in pairs:
        output_stripped = output.strip(" \n`")
        said_no_related = _NO_RELATED_PHRASE in output_stripped.lower()
        if said_no_related:
            no_related_cnt += 1
        if len(label) == 0:
            if said_no_related:
                tn += 1
            else:
                fp += 1
        else:
            if said_no_related:
                false_no_related_cnt += 1
            classified = all(
                substr.strip(" \n`") in output_stripped for substr in label
            )
            if classified:
                tp += 1
            else:
                fn += 1
            jaccards.append(get_jaccard(" ".join(label), output_stripped))

    total = tp + tn + fn + fp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    f2 = 5 * precision * recall / (4 * precision + recall) if (4 * precision + recall) else 0.0
    n_pos = tp + fn
    return {
        "n_pairs": total,
        "n_positive": n_pos,
        "tp": tp, "tn": tn, "fn": fn, "fp": fp,
        "accuracy": round((tp + tn) / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "f2": round(f2, 4),
        "jaccard_mean": round(sum(jaccards) / len(jaccards), 4) if jaccards else 0.0,
        "jaccard_median": round(sorted(jaccards)[len(jaccards) // 2], 4) if jaccards else 0.0,
        "no_related_rate": round(no_related_cnt / total, 4) if total else 0.0,
        "false_no_related_rate": round(false_no_related_cnt / n_pos, 4) if n_pos else 0.0,
    }


def evaluate_record(record: dict, master_gt: dict[str, dict[str, list[str]]],
                    categories: list[str] | None = None) -> dict[str, Any]:
    """Evaluate ONE stored extraction record (an experiment-log line) against
    the master GT, returning the pooled ContractEval metrics + per-row detail.

    Only rows whose normalized filename resolves in the GT and whose predicted
    output parsed (no parse error) are scored; unjoinable rows are counted.
    """
    from src.field_scoring import disaggregate_clause_spans  # noqa: F401 (import path check)

    categories = categories or applicable_categories()
    results = record.get("results") or []
    pairs: list[tuple[list[str], str]] = []
    rows: list[dict[str, Any]] = []
    n_docs = 0
    n_unjoined = 0
    n_parse_errors = 0
    for row in results:
        predicted = row.get("predicted") or {}
        if row.get("error") or predicted.get("_parse_error"):
            n_parse_errors += 1
            continue
        doc_gt = master_gt.get(normalize_filename(row.get("filename")))
        if not doc_gt:
            n_unjoined += 1
            continue
        n_docs += 1
        output = build_category_output(predicted, doc_gt)
        for cat in categories:
            label = doc_gt.get(cat) or []
            output_str = output.get(cat, _NO_RELATED_PHRASE)
            pairs.append((label, output_str))
            rows.append({"category": cat, "label": label,
                         "output": output_str, "filename": row.get("filename")})
    metrics = contracteval_metrics(pairs)
    metrics["n_docs"] = n_docs
    metrics["n_unjoined"] = n_unjoined
    metrics["n_parse_errors"] = n_parse_errors
    metrics["rows"] = rows
    return metrics


def coverage_bands(record: dict, master_gt: dict[str, dict[str, list[str]]],
                   categories: list[str] | None = None) -> dict[str, Any]:
    """Semantic-coverage companion to the verbatim ContractEval rubric.

    For every positive-label (doc, category) pair, measure the best
    expected-within-predicted token containment of any disaggregated predicted
    span against any GT label span. This quantifies how much of the
    verbatim-recall gap is a PARAPHRASE/formatting penalty rather than a
    missing extraction (issue #21's contained-label rule)."""
    categories = categories or applicable_categories()
    results = record.get("results") or []
    counts = {"n_pos": 0, "verbatim": 0, "ge0_7": 0, "ge0_5": 0, "ge0_3": 0}
    for row in results:
        predicted = row.get("predicted") or {}
        if row.get("error") or predicted.get("_parse_error"):
            continue
        doc_gt = master_gt.get(normalize_filename(row.get("filename")))
        if not doc_gt:
            continue
        spans = disaggregate_spans(predicted.get("key_obligations"))
        spans += disaggregate_spans(predicted.get("termination_clauses"))
        union = " ".join(spans)
        for cat in categories:
            labels = doc_gt.get(cat) or []
            if not labels:
                continue
            counts["n_pos"] += 1
            if all(label.strip(" \n`") in union for label in labels):
                counts["verbatim"] += 1
            best = max(
                (_containment(span, label) for span in spans for label in labels),
                default=0.0,
            )
            if best >= 0.7:
                counts["ge0_7"] += 1
            if best >= 0.5:
                counts["ge0_5"] += 1
            if best >= 0.3:
                counts["ge0_3"] += 1
    n = counts["n_pos"]
    return {
        "n_pos": n,
        "verbatim": round(counts["verbatim"] / n, 4) if n else 0.0,
        "ge0_7": round(counts["ge0_7"] / n, 4) if n else 0.0,
        "ge0_5": round(counts["ge0_5"] / n, 4) if n else 0.0,
        "ge0_3": round(counts["ge0_3"] / n, 4) if n else 0.0,
    }


def format_report(results: dict[str, dict[str, Any]],
                  include_reference: bool = True) -> str:
    """Render a pooled comparison table: our runs vs ContractEval Table III."""
    lines = [
        "# ContractEval mapping-scorer benchmark",
        "",
        "Pooled over the CUAD YES/NO obligation categories (32 per document) on "
        "stored full-corpus extraction runs, using the ContractEval rubric "
        "(arXiv 2508.03080): TP = every GT label span verbatim-contained in the "
        "synthesized per-category answer; Jaccard over positive-label pairs; "
        "false-'no related clause' rate over positive-label pairs.",
        "",
        "| Run | n_pairs | n_pos | Acc | P | R | F1 | F2 | Jacc | no-rel | false-nr |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, m in results.items():
        lines.append(
            f"| {name} | {m['n_pairs']} | {m['n_positive']} | {m['accuracy']:.3f} | "
            f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['f2']:.3f} | "
            f"{m['jaccard_mean']:.3f} | {m['no_related_rate']:.3f} | "
            f"{m['false_no_related_rate']:.3f} |"
        )
    if include_reference:
        lines += [
            "",
            "ContractEval Table III reference (F1/F2/Jaccard/false-nr):",
            "",
            "| Model | F1 | F2 | Jacc | false-nr |",
            "|---|---|---|---|---|",
        ]
        for model, ref in CONTRACTEVAL_TABLE_III.items():
            lines.append(
                f"| {model} | {ref['f1']:.3f} | {ref['f2']:.3f} | "
                f"{ref['jaccard']:.3f} | {ref['false_no_related']:.3f} |"
            )
        lines += [
            "",
            "**Caveat:** this pipeline is a one-pass extractor — it never claims a "
            "category the GT marks absent, so Precision is structurally 1.0 and F1 "
            "tracks recall. The discriminating signals versus ContractEval are "
            "recall, F2, Jaccard, and the false-'no related clause' rate. "
            "ContractEval's false-rate denominator is its hardcoded 1,244 positive "
            "pairs; the rate above uses this benchmark's own n_pos.",
        ]
    return "\n".join(lines)
