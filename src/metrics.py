"""Run-level diagnostic metrics for the entity-extraction task.

The aggregation logic lives in the **llm-dojo-scoring** package
(``llm_dojo_scoring.diagnostics`` — identical algorithm); this module is a
thin re-export shim that keeps the repo's local contract:

- ``extraction_diagnostics(rows, field_types, master=...)`` keeps the
  ``master=`` keyword — the package takes an ``expected_resolver(master,
  filename, field, fallback)`` callable instead and dropped the master-label
  preference. The local resolver (``_expected_for_field`` + the
  ``_FIELD_CATEGORIES`` CUAD field→category map, which the package removed)
  is recreated here, so MAE/R² parsing prefers the curated master-labels
  normalized answers and falls back to raw clause text exactly as before.

What the aggregations mean (unchanged):

List quality (over ``entity_list_scores``, raw not GT-coverage):
  - ``list_{precision,recall,f1}``      macro mean over ``key_obligations``
  - ``list_micro_{precision,recall,f1}`` span-summed (pooled) over
    ``key_obligations`` — the same numbers with each contract weighted by
    its number of spans instead of equally
  - ``entity_list_{precision,recall}``  per-field macro means for EVERY
    list field
  - ``entity_list_raw_f1``              per-field macro mean of raw F1

Regression error (parsed against the ground truth):
  - ``date_mae_days`` / ``date_median_ae_days`` / ``date_r2`` (+ per-field)
    over parseable (predicted, expected) date pairs (``effective_date``).
  - ``duration_mae_days`` / ``duration_median_ae_days`` / ``duration_r2``
    (+ per-field) over duration pairs (``term_length``, ``renewal_terms``);
    term_length expected text that parses as an expiration DATE is scored as
    date MAE instead.
  - ``money_mae_usd`` / ``money_median_ae_usd`` (+ per-field) over money
    pairs (``contract_value``, ``demand_amount``).
  - support sizes ``date_n_pairs`` / ``duration_n_pairs`` /
    ``money_n_pairs``.

Extraction-volume error (span-count, over list fields):
  - ``span_count_mae`` / ``span_count_mae_per_field`` — symmetric drift
  - ``span_count_signed_mean`` / ``span_count_signed_mean_per_field`` —
    direction of drift (positive = over-extraction)
  - ``span_count_n_docs``

Field-level error decomposition (over ``field_scores``):
  - ``field_exact_rate`` / ``field_partial_rate`` / ``field_miss_rate``
  - ``error_decomposition`` — the same three rates per field
  - ``field_presence_per_field`` — share of docs where each field is
    populated
"""

from __future__ import annotations

from collections import defaultdict

from llm_dojo_scoring.diagnostics import (  # noqa: F401  (re-export shim)
    DATE_FIELDS,
    DURATION_FIELDS,
    _r2,
    extraction_diagnostics as _package_extraction_diagnostics,
    parse_duration_days,
)

from src.cuad_ground_truth import CUAD_CATEGORIES
from src.field_scoring import is_entity_list, parse_date, parse_money  # noqa: F401  (re-export shim)
from src.master_labels import resolve_expected_value

# Schema field -> the CUAD categories that label it (for master-CSV joins).
# The package's diagnostics dropped this mapping; it is recreated here so the
# ``master=`` resolver reproduces the repo's master-label preference.
_FIELD_CATEGORIES: dict[str, list[str]] = defaultdict(list)
for _category, _spec in CUAD_CATEGORIES.items():
    if _spec.get("field"):
        _FIELD_CATEGORIES[_spec["field"]].append(_category)


def _expected_for_field(master, filename: str, field: str, fallback: str) -> str:
    """Master-CSV normalized answer for the field (any labeling category),
    else the raw clause-label text."""
    for category in _FIELD_CATEGORIES.get(field, []):
        value = resolve_expected_value(master, filename, category, "")
        if value:
            return value
    return str(fallback or "")


def extraction_diagnostics(rows: list[dict], field_types: dict[str, str],
                           master: dict[str, dict[str, str]] | None = None) -> dict:
    """Aggregate the per-row composite into run-level diagnostic metrics.

    Args:
        rows: one dict per scored document with ``filename``, ``predicted``,
            ``expected_fields``, ``field_scores``, ``entity_list_scores`` and
            ``entity_list_audit``.
        field_types: the doc class' field->scoring-type mapping
            (``get_field_types("contract")``).
        master: master-labels map (``master_labels.load_master_labels``).

    Returns a flat dict of run-level metrics (all means are macro over
    documents unless named ``micro`` or ``per_field``).
    """
    # Bind ``master`` into the resolver — the package calls the resolver as
    # ``resolver(master, filename, field, fallback)`` with its own master
    # slot, so without the closure the master-label preference is lost and
    # the raw clause-text fallback wins.
    resolver = lambda _master, filename, field, fallback: _expected_for_field(  # noqa: E731
        master, filename, field, fallback)
    return _package_extraction_diagnostics(
        rows, field_types, expected_resolver=resolver)
