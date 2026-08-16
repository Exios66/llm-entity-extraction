"""Per-model token pricing + cost estimation — re-export shim.

The pricing/cost logic lives in the **llm-dojo-scoring** package
(``llm_dojo_scoring.cost``, identical implementations); this module re-exports
it so every local import site keeps working unchanged. Prices resolve through
the package ``Settings`` (wired from ``config/taxonomy.yaml`` by
``src/dojo_config.py``), so the taxonomy's ``cost_models:`` block — written as
``{input_per_million, output_per_million}`` dicts — stays authoritative.

OpenRouter usage payloads carry no cost field, so every run in the experiment
log records ``cost_total_usd = 0.0`` despite real token usage; cost scoring is
deterministic from the recorded token counts x the verified per-model prices
(GitHub issue #1). Unknown models resolve by prefix and otherwise report
``None`` — an honest "unknown price", never a fabricated number.
"""

from __future__ import annotations

from llm_dojo_scoring.cost import (  # noqa: F401  (re-export shim)
    estimate_cost,
    estimate_for_record,
    price_for,
    tokens_summary,
)
