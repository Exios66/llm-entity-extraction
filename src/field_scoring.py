"""Deterministic, field-type-aware extraction scoring — re-export shim.

The scoring definitions now live in the **llm-dojo-scoring** package
(``llm_dojo_scoring.field_scoring``), the single source shared with
llm-mailroom; the local module keeps its public API as a thin re-export so
every import site (eval runners, reporting scripts, tests, and llm-mailroom's
``pip install -e .`` imports) keeps working unchanged. The scoring algorithm
itself is byte-identical (verified against llm-dojo-scoring v0.1.0).

Two local adaptations sit on top of the package API:

- ``get_field_types(doc_class)`` keeps its one-argument form and resolves the
  taxonomy from ``config/taxonomy.yaml`` — the package version requires the
  taxonomy dict to be passed explicitly and silently returns ``{}`` when it
  is not.
- The package ``Settings`` are wired from the same taxonomy file at import
  time (``src/dojo_config.py::apply_taxonomy_settings``), so thresholds,
  ``embedding_enabled``, partial-GT/containment field lists, and the cost
  table behave exactly as before.
"""

from __future__ import annotations

from typing import Any

from llm_dojo_scoring.field_scoring import *  # noqa: F401,F403  (re-export shim)
from llm_dojo_scoring.field_scoring import (  # noqa: F401  (re-export shim)
    EntityListScore,
    ExtractionScoreResult,
    get_ambiguous_band,
    get_bipartite_match_threshold,
    get_containment_fields,
    get_partial_gt_fields,
    score_category_presence,
    score_entity_list,
    score_extraction,
    score_field,
    verify_list_items,
)

from src.dojo_config import apply_taxonomy_settings
from src.taxonomy import load_taxonomy

apply_taxonomy_settings()


def get_field_types(doc_class: str, taxonomy: dict | None = None) -> dict[str, Any]:
    """Field→scoring-type mapping for a doc class from the repo taxonomy.

    Resolves ``config/taxonomy.yaml`` when no taxonomy dict is passed (the
    package's two-argument form requires it explicitly and returns ``{}``
    without it — that silent-empty trap is why the local one-argument form
    stays).
    """
    from llm_dojo_scoring.field_scoring import get_field_types as _package_get_field_types

    return _package_get_field_types(
        doc_class, taxonomy if taxonomy is not None else load_taxonomy())
