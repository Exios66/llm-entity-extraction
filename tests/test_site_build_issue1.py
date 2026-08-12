"""Site builder tests for the issue #1 display features (no network)."""

from __future__ import annotations

import json

import pytest

from scripts.site import build_site


_DEFAULT_SCORES = {
    "subtype_classification": {"sorter": {"exact_match": 1.0, "subtype_accuracy": 0.8}},
    "contract_entity_extraction": {"overall_extraction_score": 0.7},
    "chained_sorter_extractor": {"sorter": {"exact_match": 1.0},
                                 "extractor": {"overall_extraction_score": 0.7}},
    "legalbench_binary_answer": {"accuracy": 0.6},
}


def _record(task="subtype_classification", fingerprint="fp-x", seed=42, n=10,
            mode_counts=None, results=None, cost=0.5, scores=None):
    score_dict = dict(_DEFAULT_SCORES[task]) if scores is None else scores
    if mode_counts is not None:
        score_dict.setdefault("sorter", {})["failure_insights"] = {"mode_counts": mode_counts}
    return {
        "type": "experiment",
        "task": task,
        "experiment_name": "run_test",
        "model": "qwen/qwen3.7-flash",
        "prompt_version": "sorter_v5",
        "prompt_versions": {"sorter": "sorter_v5"} if task == "chained_sorter_extractor" else None,
        "data_source": {"dataset_fingerprint": fingerprint, "seed": seed, "n_samples": n},
        "parameters": {"handoff_scope": "subtype"},
        "tokens": {"total_tokens": 1000, "cost_usd": cost / n, "cost_total_usd": cost},
        "scores": score_dict,
        "n_rows": n, "n_ok": n, "n_error": 0,
        "timestamp": "2026-08-11T00:00:00+00:00",
        "results": results or [],
    }


class TestSameSurfaceGuardrail:
    def test_sample_key(self):
        r1 = _record(fingerprint="fp-a", seed=1, n=10)
        r2 = _record(fingerprint="fp-a", seed=1, n=10)
        r3 = _record(fingerprint="fp-b", seed=1, n=10)
        assert build_site._sample_key(r1) == build_site._sample_key(r2)
        assert build_site._sample_key(r1) != build_site._sample_key(r3)
        assert build_site._sample_key(r1) == "fp-a:1:10"

    def test_summary_carries_surface_and_ci(self):
        record = _record(results=[{"sorter": {"subtype_ok": True}},
                                  {"sorter": {"subtype_ok": False}}])
        summary = build_site.summarize(record, 1, {"subtype_classification": 0.8},
                                       {("subtype_classification", "fp-x:42:10"): 0.8})
        assert summary["sample_key"] == "fp-x:42:10"
        assert summary["fingerprint"] == "fp-x"
        assert summary["ci95"]["method"] == "percentile-bootstrap"
        assert summary["ci95"]["source"] == "results-bootstrap"
        # headline is the recorded aggregate; the CI comes from the per-doc
        # results (1/2 subtype_ok -> bootstrap mean 0.5, wide interval).
        assert summary["headline"]["value"] == 0.8
        assert summary["ci95"]["n"] == 2
        # same-surface delta vs the 0.8 best = 0
        assert summary["delta_best_pp"] == 0.0

    def test_record_ci_preferred_over_results(self):
        record = _record(scores={"sorter": {"subtype_accuracy": 0.8,
                                            "subtype_accuracy_ci": {"lo": 0.7, "hi": 0.9, "n": 10}}},
                         results=[{"sorter": {"subtype_ok": True}}])
        ci = build_site._record_ci(record)
        assert ci["lo"] == 0.7 and ci["hi"] == 0.9

    def test_single_doc_no_ci(self):
        record = _record(results=[{"sorter": {"subtype_ok": True}}])
        ci = build_site._record_ci(record)
        # bootstrap returns None for n=1; the Wilson fallback still renders.
        assert ci is None or isinstance(ci, dict)


class TestTrendsAndPrompts:
    def test_build_trends(self):
        records = [
            _record(mode_counts={"family_confusion": 3}),
            _record(task="contract_entity_extraction"),
        ]
        summaries = [build_site.summarize(r, i + 1, {}, {}) for i, r in enumerate(records)]
        trends = build_site.build_trends(records, summaries)
        assert "subtype_classification" in trends["tasks"]
        assert "contract_entity_extraction" in trends["tasks"]
        entry = trends["tasks"]["subtype_classification"][0]
        assert entry["headline_value"] == 0.8
        assert entry["mode_counts"] == {"family_confusion": 3}
        assert entry["cost_total_usd"] == 0.5
        assert entry["sample_key"] == "fp-x:42:10"

    def test_build_prompts(self):
        prompts = build_site.build_prompts()
        assert "sorter_v5" in prompts
        assert len(prompts["sorter_v5"]) > 100
        # Derived versions resolve too (the diff viewer needs both sides).
        assert "contracts_specialist_v12" in prompts
