"""Run-level diagnostic metrics for the entity-extraction task.

The per-row composite (``score_extraction`` + the eval runners) already
produces per-field content scores, entity-list precision/recall/F1, and the
factuality audit. This module AGGREGATES those numbers — plus two new
regression-style measurements (date MAE and duration MAE) — into the
run-level diagnostics that the experiment log displays for researchers:

List quality (over ``entity_list_scores``, raw not GT-coverage):
  - ``list_{precision,recall,f1}``      macro mean over ``key_obligations``
  - ``list_micro_{precision,recall,f1}`` span-summed (pooled) over
    ``key_obligations`` — the same numbers with each contract weighted by
    its number of spans instead of equally
  - ``entity_list_{precision,recall}``  per-field macro means for EVERY
    list field
  - ``entity_list_raw_f1``              per-field macro mean of raw F1 (the
    ``entity_list_f1`` tracker reports GT-coverage for partial-GT fields;
    raw F1 is the complementary over/under-extraction diagnostic)

Regression error (new — parsed against the ground truth):
  - ``date_mae_days`` / ``date_median_ae_days`` — mean/median ABSOLUTE
    error in calendar days between the predicted and expected dates of
    date-typed fields (``effective_date``), computed only over rows where
    BOTH sides parse. A 0 value means the model's dates were exactly the
    annotator's dates; MAE weights small-but-systematic offsets (a
    day-shifted date is a near-miss, not a binary wrong answer).
  - ``duration_mae_days`` / ``duration_median_ae_days`` — same, over
    duration-typed fields (``term_length``, ``renewal_terms``) when the
    expected text parses as a duration ("2 years", "thirty (30) days") and
    the prediction does too.
  - ``money_mae_usd`` / ``money_median_ae_usd`` — same, over money-typed
    fields (``contract_value``, ``demand_amount``) with both sides parsed
    to a USD float; ``$250,001`` vs ``$250,000`` is a $1 error, not a
    binary miss.
  - ``date_r2`` / ``duration_r2`` — coefficient of determination over the
    SAME parseable (predicted, expected) pairs:
    ``1 - SS_res/SS_tot`` with ``SS_res = sum((pred - exp)^2)`` and
    ``SS_tot = sum((exp - mean(exp))^2)`` — the share of ground-truth
    variance the predictions explain. 1.0 = perfect, 0.0 = as good as
    predicting the mean, NEGATIVE = worse than the mean (kept, not
    clamped). Undefined (None) with fewer than 2 pairs or zero expected
    variance (all expected values identical). R² is translation-invariant,
    so dates are encoded as ordinal days.
  - per-field buckets ``date_mae_per_field`` / ``duration_mae_per_field``
    / ``money_mae_per_field`` and ``date_r2_per_field`` /
    ``duration_r2_per_field``.
  - support sizes ``date_n_pairs`` / ``duration_n_pairs`` /
    ``money_n_pairs`` — the number of (predicted, expected) pairs behind
    each MAE/R² row, so researchers can see how much evidence a number
    rests on.

Extraction-volume error (span-count, over list fields):
  - ``span_count_mae`` / ``span_count_mae_per_field`` — mean over documents
    of ``|n_predicted - n_expected|`` per list field: how far the model's
    item counts drift from the annotator's, in items. MAE is symmetric
    (over- and under-extraction both hurt); the signed companion shows the
    DIRECTION of the drift.
  - ``span_count_signed_mean`` / ``span_count_signed_mean_per_field`` —
    mean of ``(n_predicted - n_expected)``; POSITIVE = systematic
    over-extraction (the model invents or splits spans), NEGATIVE =
    systematic under-extraction (it merges or omits spans). Zero means the
    counts cancel even when individual docs drift.
  - ``span_count_n_docs`` — documents contributing to the span-count rows.

Field-level error decomposition (over ``field_scores``):
  - ``field_exact_rate`` — share of scored (doc, field) pairs scoring 1.0
  - ``field_partial_rate`` — share scoring 0 < s < 1 (fuzzy match, partial
    credit, contained match)
  - ``field_miss_rate`` — share scoring 0.0 (missing or wrong)
  - ``error_decomposition`` — the same three rates per field
  - ``field_presence_per_field`` — share of docs where the model populated
    each field (the per-field analogue of the run ``field_presence``)

Expected values for the MAE parsers prefer the master labels CSV
(``src/master_labels.py`` — the curated normalized answers like "5/8/14",
"2 years") and fall back to the raw CUAD clause-label text.
"""

from __future__ import annotations

import re
from collections import defaultdict

from src.cuad_ground_truth import CUAD_CATEGORIES
from src.field_scoring import is_entity_list, parse_date, parse_money
from src.master_labels import resolve_expected_value

# Schema fields whose expected text is a DURATION ("2 years", "30 days").
DURATION_FIELDS = {"term_length", "renewal_terms"}
# Fields whose expected text is (or contains) a date.
DATE_FIELDS = {"effective_date"}

# Schema field -> the CUAD categories that label it (for master-CSV joins).
_FIELD_CATEGORIES: dict[str, list[str]] = defaultdict(list)
for _category, _spec in CUAD_CATEGORIES.items():
    if _spec.get("field"):
        _FIELD_CATEGORIES[_spec["field"]].append(_category)

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "twentyfour": 24, "twenty-four": 24, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "onehundred": 100, "hundred": 100,
}
_DAYS_PER = {"year": 365, "month": 30, "week": 7, "day": 1}
_DURATION_RE = re.compile(
    r"(\d+|[a-z][a-z-]*)\s*(?:\(\s*(\d+)\s*\))?\s*"
    r"(years?|months?|weeks?|days?)",
    flags=re.IGNORECASE,
)


def parse_duration_days(text) -> int | None:
    """Parse a duration phrase ("two (2) years", "thirty (30) days", "24
    months", "annual") into its length in days, or None when no duration is
    present. Uses the LAST (number, unit) pair in the text (the operative
    term; leading qualifiers like "up to another" are ignored), and prefers
    a parenthesized digit over the spelled number ("two (2) years" -> 365).
    """
    if not isinstance(text, str):
        return None
    s = re.sub(r"[,.]", " ", text).lower()
    if re.search(r"\ban[n]?ual", s):
        return 365
    matches = _DURATION_RE.findall(s)
    if not matches:
        return None
    number_tok, paren_digit, unit = matches[-1]
    if paren_digit:
        number = int(paren_digit)
    elif number_tok.isdigit():
        number = int(number_tok)
    else:
        number = _NUM_WORDS.get(number_tok)
        if number is None:
            return None
    return number * _DAYS_PER[unit.rstrip("s")]


def _date_pair_days(predicted: str, expected: str) -> tuple[float, float] | None:
    """(predicted, expected) as ordinal-day floats — the regression pair for
    the date R² — or None when either side is unparseable. Ordinal days are
    translation-invariant, which R² is, so the encoding offset is irrelevant.
    """
    pred_date = parse_date(predicted)
    exp_date = parse_date(expected)
    if pred_date is None or exp_date is None:
        return None
    return float(pred_date.toordinal()), float(exp_date.toordinal())


def _r2(pairs: list[tuple[float, float]]) -> float | None:
    """Coefficient of determination ``1 - SS_res/SS_tot`` over (predicted,
    expected) pairs.

    Undefined (None) with fewer than 2 pairs or zero expected variance
    (``SS_tot == 0`` — every expected value identical). Negative values are
    kept: they mean the predictions explain LESS variance than predicting
    the mean, which is a real diagnostic signal.
    """
    if len(pairs) < 2:
        return None
    expected = [e for _, e in pairs]
    mean_expected = sum(expected) / len(expected)
    ss_res = sum((pred - exp) ** 2 for pred, exp in pairs)
    ss_tot = sum((exp - mean_expected) ** 2 for exp in expected)
    if ss_tot == 0:
        return None
    return round(1.0 - ss_res / ss_tot, 4)


def _expected_for_field(master, filename: str, field: str, fallback: str) -> str:
    """Master-CSV normalized answer for the field (any labeling category),
    else the raw clause-label text."""
    for category in _FIELD_CATEGORIES.get(field, []):
        value = resolve_expected_value(master, filename, category, "")
        if value:
            return value
    return str(fallback or "")


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    med = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return round(float(med), 4)


def extraction_diagnostics(rows: list[dict], field_types: dict[str, str],
                           master: dict[str, dict[str, str]] | None = None) -> dict:
    """Aggregate the per-row composite into run-level diagnostic metrics.

    Args:
        rows: one dict per scored document with
            ``filename``, ``predicted``, ``expected_fields``, ``field_scores``,
            ``entity_list_scores`` and ``entity_list_audit``.
        field_types: the doc class' field->scoring-type mapping
            (``get_field_types("contract")``).
        master: master-labels map (``master_labels.load_master_labels``).

    Returns a flat dict of run-level metrics (all means are macro over
    documents unless named ``micro`` or ``per_field``).
    """
    list_fields = [f for f, ft in (field_types or {}).items() if is_entity_list(ft)]
    date_fields = [f for f, ft in (field_types or {}).items() if ft == "date"] or list(DATE_FIELDS)
    duration_fields = [f for f in field_types if f in DURATION_FIELDS]
    money_fields = [f for f, ft in (field_types or {}).items() if ft == "money"]

    precision: dict[str, list[float]] = defaultdict(list)
    recall: dict[str, list[float]] = defaultdict(list)
    raw_f1: dict[str, list[float]] = defaultdict(list)
    micro = {"n_pred": 0, "n_exp": 0, "matched": 0}
    flags: dict[str, list[str]] = defaultdict(list)
    presence: dict[str, list[float]] = defaultdict(list)
    date_err: dict[str, list[float]] = defaultdict(list)
    duration_err: dict[str, list[float]] = defaultdict(list)
    date_pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    duration_pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    money_err: dict[str, list[float]] = defaultdict(list)
    span_drift: dict[str, list[float]] = defaultdict(list)
    all_flags: list[str] = []
    n_fields_scored = 0

    for row in rows:
        filename = str(row.get("filename") or "")
        predicted = row.get("predicted") or {}
        expected = row.get("expected_fields") or {}
        field_scores = row.get("field_scores") or {}
        list_scores = row.get("entity_list_scores") or {}

        # ---- list quality --------------------------------------------------
        for field in list_fields:
            score = list_scores.get(field)
            if not isinstance(score, dict):
                continue
            precision[field].append(float(score.get("precision") or 0.0))
            recall[field].append(float(score.get("recall") or 0.0))
            f1 = score.get("f1")
            raw_f1[field].append(float(f1 or 0.0))
            micro["n_pred"] += int(score.get("n_predicted") or 0)
            micro["n_exp"] += int(score.get("n_expected") or 0)
            micro["matched"] += int(score.get("matched") or 0)
            # span-count drift: how many items the model added/removed vs the
            # annotator's list, per document.
            if score.get("n_expected") is not None:
                span_drift[field].append(
                    float(int(score.get("n_predicted") or 0) - int(score["n_expected"])))

        # ---- field-level error decomposition --------------------------------
        for field, score in field_scores.items():
            if not isinstance(score, (int, float)):
                continue
            n_fields_scored += 1
            flag = "exact" if score >= 1.0 else ("miss" if score <= 0.0 else "partial")
            flags[field].append(flag)
            all_flags.append(flag)

        # ---- per-field presence ---------------------------------------------
        for field in field_types:
            value = predicted.get(field)
            presence[field].append(1.0 if value not in (None, "", []) else 0.0)

        # ---- MAE + R² (dates and durations) ---------------------------------
        for field in date_fields:
            pred_value = predicted.get(field)
            exp_value = _expected_for_field(master, filename, field,
                                            expected.get(field) or "")
            if pred_value not in (None, ""):
                pair = _date_pair_days(str(pred_value), exp_value)
                if pair is not None:
                    date_err[field].append(abs(pair[0] - pair[1]))
                    date_pairs[field].append(pair)
        for field in duration_fields:
            pred_value = predicted.get(field)
            exp_value = _expected_for_field(master, filename, field,
                                            expected.get(field) or "")
            if not pred_value:
                continue
            exp_dur = parse_duration_days(exp_value)
            pred_dur = parse_duration_days(str(pred_value))
            if exp_dur is not None and pred_dur is not None:
                duration_err[field].append(float(abs(exp_dur - pred_dur)))
                duration_pairs[field].append((float(pred_dur), float(exp_dur)))
            else:
                # term_length expected text is sometimes an expiration DATE
                # ("...shall terminate on June 30, 2010"): score as date MAE.
                pair = _date_pair_days(str(pred_value), exp_value)
                if pair is not None:
                    date_err[field].append(abs(pair[0] - pair[1]))
                    date_pairs[field].append(pair)
        for field in money_fields:
            pred_value = predicted.get(field)
            exp_value = _expected_for_field(master, filename, field,
                                            expected.get(field) or "")
            if pred_value in (None, ""):
                continue
            pred_usd = parse_money(str(pred_value))
            exp_usd = parse_money(exp_value)
            if pred_usd is not None and exp_usd is not None:
                money_err[field].append(abs(pred_usd - exp_usd))

    def _rate(flags_: list[str], flag: str) -> float | None:
        return round(sum(1 for f in flags_ if f == flag) / len(flags_), 4) \
            if flags_ else None

    def _field_bucket(bucket: dict[str, list[float]]) -> dict[str, float]:
        return {f: _mean(v) for f, v in bucket.items() if v}

    metrics: dict = {
        "n_fields_scored": n_fields_scored,
        "field_exact_rate": _rate(all_flags, "exact") or 0.0,
        "field_partial_rate": _rate(all_flags, "partial") or 0.0,
        "field_miss_rate": _rate(all_flags, "miss") or 0.0,
        "error_decomposition": {
            f: {"exact_rate": _rate(flags[f], "exact"),
                "partial_rate": _rate(flags[f], "partial"),
                "miss_rate": _rate(flags[f], "miss")}
            for f in flags
        },
        "field_presence_per_field": _field_bucket(presence),
    }

    # entity-list diagnostics (raw P/R/F1, not GT-coverage)
    metrics["entity_list_precision"] = _field_bucket(precision)
    metrics["entity_list_recall"] = _field_bucket(recall)
    metrics["entity_list_raw_f1"] = _field_bucket(raw_f1)
    ko = "key_obligations"
    if precision.get(ko):
        metrics["list_precision"] = _mean(precision[ko])
        metrics["list_recall"] = _mean(recall[ko])
        metrics["list_f1"] = _mean(raw_f1[ko])
    if micro["n_pred"] or micro["n_exp"]:
        micro_p = micro["matched"] / micro["n_pred"] if micro["n_pred"] else 0.0
        micro_r = micro["matched"] / micro["n_exp"] if micro["n_exp"] else 0.0
        metrics["list_micro_precision"] = round(micro_p, 4)
        metrics["list_micro_recall"] = round(micro_r, 4)
        metrics["list_micro_f1"] = round(
            2 * micro_p * micro_r / (micro_p + micro_r), 4) if micro_p + micro_r else 0.0
        metrics["list_micro_n_predicted"] = micro["n_pred"]
        metrics["list_micro_n_expected"] = micro["n_exp"]
        metrics["list_micro_matched"] = micro["matched"]

    # MAE + R² aggregation (both over the same parseable pairs)
    all_date_err = [e for errors in date_err.values() for e in errors]
    if all_date_err:
        metrics["date_mae_days"] = _mean(all_date_err)
        metrics["date_median_ae_days"] = _median(all_date_err)
        metrics["date_mae_per_field"] = _field_bucket(date_err)
    if date_pairs:
        metrics["date_r2"] = _r2([p for pairs in date_pairs.values() for p in pairs])
        metrics["date_r2_per_field"] = {f: _r2(p) for f, p in date_pairs.items()}
    metrics["date_n_pairs"] = len(all_date_err)
    all_duration_err = [e for errors in duration_err.values() for e in errors]
    if all_duration_err:
        metrics["duration_mae_days"] = _mean(all_duration_err)
        metrics["duration_median_ae_days"] = _median(all_duration_err)
        metrics["duration_mae_per_field"] = _field_bucket(duration_err)
    if duration_pairs:
        metrics["duration_r2"] = _r2(
            [p for pairs in duration_pairs.values() for p in pairs])
        metrics["duration_r2_per_field"] = {
            f: _r2(p) for f, p in duration_pairs.items()}
    metrics["duration_n_pairs"] = len(all_duration_err)

    # Money MAE (USD float pairs)
    all_money_err = [e for errors in money_err.values() for e in errors]
    if all_money_err:
        metrics["money_mae_usd"] = _mean(all_money_err)
        metrics["money_median_ae_usd"] = _median(all_money_err)
        metrics["money_mae_per_field"] = _field_bucket(money_err)
    metrics["money_n_pairs"] = len(all_money_err)

    # Span-count drift: symmetric MAE + signed mean (direction of drift)
    if span_drift:
        all_drift = [d for drifts in span_drift.values() for d in drifts]
        metrics["span_count_n_docs"] = len(all_drift)
        metrics["span_count_mae"] = _mean([abs(d) for d in all_drift])
        metrics["span_count_signed_mean"] = _mean(all_drift)
        metrics["span_count_mae_per_field"] = {
            f: _mean([abs(d) for d in drifts]) for f, drifts in span_drift.items()}
        metrics["span_count_signed_mean_per_field"] = {
            f: _mean(drifts) for f, drifts in span_drift.items()}

    return metrics
