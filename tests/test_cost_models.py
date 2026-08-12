"""Token x price cost estimation tests (GitHub issue #1 cost scoring)."""

from __future__ import annotations

import pytest

from src.cost_models import estimate_cost, estimate_for_record, price_for


class TestEstimateCost:
    def test_qwen_pricing(self):
        # 1M prompt + 1M completion at qwen rates = $0.03 + $0.13
        assert estimate_cost(1_000_000, 1_000_000, "qwen/qwen3.7-flash") == pytest.approx(0.16)

    def test_known_run_magnitude(self):
        # 155,373 prompt + 42,724 completion tokens on qwen
        cost = estimate_cost(155_373, 42_724, "qwen/qwen3.7-flash")
        assert cost == pytest.approx(0.03 * 155_373 / 1e6 + 0.13 * 42_724 / 1e6, abs=1e-6)
        assert 0.004 < cost < 0.012  # a realistic chained 10-doc run

    def test_prefix_match_for_dated_model(self):
        # A dated OpenRouter model id rolls to the base price.
        cost = estimate_cost(1_000_000, 1_000_000, "qwen/qwen3.7-flash-20260727")
        assert cost == pytest.approx(0.16)

    def test_unknown_model_returns_none(self):
        assert estimate_cost(100, 100, "openai/gpt-9-nonexistent") is None
        assert price_for(None) is None
        assert price_for("") is None

    def test_no_tokens_returns_none(self):
        assert estimate_cost(0, 0, "qwen/qwen3.7-flash") is None
        assert estimate_cost(None, None, "qwen/qwen3.7-flash") is None

    def test_zero_cost_model(self):
        assert estimate_cost(10, 10, "deepseek/deepseek-v4-pro") is not None


class TestEstimateForRecord:
    def _record(self, tokens, model="qwen/qwen3.7-flash", n_rows=10):
        return {"model": model, "n_rows": n_rows, "tokens": tokens}

    def test_flat_tokens(self):
        out = estimate_for_record(self._record({"prompt_tokens": 1000, "completion_tokens": 500}))
        assert out["cost_estimated_usd"] == pytest.approx(0.03 * 1000 / 1e6 + 0.13 * 500 / 1e6)
        assert out["per_doc_usd"] == pytest.approx(round(out["cost_estimated_usd"] / 10, 6))

    def test_stage_buckets_use_total(self):
        out = estimate_for_record(self._record({
            "sorter": {"prompt_tokens": 100, "completion_tokens": 100},
            "total": {"prompt_tokens": 200, "completion_tokens": 200},
        }))
        assert out["prompt_tokens"] == 200

    def test_unknown_model_honest_none(self):
        out = estimate_for_record(self._record({"prompt_tokens": 10, "completion_tokens": 10},
                                               model="unknown/model"))
        assert out["cost_estimated_usd"] is None
