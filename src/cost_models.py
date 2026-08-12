"""Per-model token pricing + cost estimation (GitHub issue #1, cost scoring).

OpenRouter usage payloads carry no cost field, so every run in the
experiment log recorded ``cost_total_usd = 0.0`` despite real token usage.
This module scores cost deterministically from the recorded prompt/
completion token counts x verified per-model prices — every run with token
data gets a proper ``cost_estimated_usd``.

Prices are the OpenRouter list prices verified against the live models API
and mirrored in llm-mailroom's ``config/taxonomy.yaml`` ``cost_models:``
(synced to the Langfuse model registry by ``sync_models.py``):

    qwen/qwen3.7-flash          $0.03 / $0.13 per 1M  (in / out)
    deepseek/deepseek-v4-flash  $0.05 / $0.25 per 1M
    deepseek/deepseek-v4-pro    $0.435 / $0.87 per 1M

Unknown models resolve by prefix (e.g. a dated ``qwen/qwen3.7-flash-20260727``
rolls to the base price) and otherwise report ``None`` — an honest "unknown
price", never a fabricated number.
"""

from __future__ import annotations

from typing import Any, Optional

# model -> (price_per_million_in, price_per_million_out)
PRICES: dict[str, tuple[float, float]] = {
    "qwen/qwen3.7-flash": (0.03, 0.13),
    "deepseek/deepseek-v4-flash": (0.05, 0.25),
    "deepseek/deepseek-v4-pro": (0.435, 0.87),
}


def price_for(model: Optional[str]) -> Optional[tuple[float, float]]:
    """Resolve a model string to its per-1M-token prices (prefix-matched)."""
    if not model:
        return None
    model = model.strip()
    if model in PRICES:
        return PRICES[model]
    for known, prices in PRICES.items():
        if model.startswith(known):
            return prices
    return None


def estimate_cost(
    prompt_tokens: Optional[Any],
    completion_tokens: Optional[Any],
    model: Optional[str],
) -> Optional[float]:
    """USD cost for one run's token counts, or None when the model's price
    is unknown or no tokens were recorded."""
    prices = price_for(model)
    if prices is None:
        return None
    try:
        prompt = int(prompt_tokens or 0)
        completion = int(completion_tokens or 0)
    except (TypeError, ValueError):
        return None
    if prompt + completion <= 0:
        return None
    per_million_in, per_million_out = prices
    return round(prompt * per_million_in / 1_000_000
                 + completion * per_million_out / 1_000_000, 6)


def estimate_for_record(record: dict) -> dict[str, Any]:
    """Cost estimate for an experiment-log record (stage-aware).

    Returns ``{"cost_estimated_usd", "prompt_tokens", "completion_tokens",
    "model", "price_source", "per_doc_usd"}`` — ``cost_estimated_usd`` is
    None when the model's price is unknown or the record has no tokens.
    """
    tokens = record.get("tokens") or {}
    if "total" in tokens:
        bucket = tokens["total"] or {}
    else:
        bucket = tokens
    prompt = bucket.get("prompt_tokens")
    completion = bucket.get("completion_tokens")
    model = record.get("model")
    cost = estimate_cost(prompt, completion, model)
    per_doc = None
    if cost is not None:
        n_rows = record.get("n_rows") or 0
        per_doc = round(cost / n_rows, 6) if n_rows else None
    return {
        "cost_estimated_usd": cost,
        "per_doc_usd": per_doc,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "model": model,
        "price_source": price_for(model),
    }
