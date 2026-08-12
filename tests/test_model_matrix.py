"""Cross-model matrix runner tests (GitHub issue #1)."""

from __future__ import annotations

import pytest


def test_matrix_dry_run_plans_grid():
    from scripts.eval import run_model_matrix

    rc = run_model_matrix.main_with_args([
        "--task", "subtype",
        "--models", "qwen/qwen3.7-flash,deepseek/deepseek-v4-flash",
        "--prompts", "sorter_v5,sorter_v6",
        "--sample", "10", "--seed", "42",
        "--dry-run",
    ])
    assert rc == 0


def test_matrix_requires_models_and_prompts():
    from scripts.eval import run_model_matrix

    with pytest.raises(SystemExit):
        run_model_matrix.main_with_args(["--task", "subtype", "--models", "a,b"])


def _synthetic_record(task, model, prompt, value, cost, seed=42, n=10, fp="fp1"):
    return {
        "type": "experiment",
        "task": task,
        "experiment_name": f"matrix_{task}_{model.split('/')[-1]}_{prompt}",
        "model": model,
        "prompt_version": prompt,
        "data_source": {"dataset_fingerprint": fp, "seed": seed, "n_samples": n},
        "tokens": {"total_tokens": 1000, "cost_usd": cost / n, "cost_total_usd": cost},
        "scores": ({"sorter": {"subtype_accuracy": value, "subtype_accuracy_ci": {"lo": value - 0.1, "hi": value + 0.1}}}
                   if task == "subtype_classification"
                   else {"exact_match": value, "exact_match_ci": {"lo": value - 0.1, "hi": value + 0.1}}),
    }


def test_print_matrix_layout(capsys):
    from scripts.eval import run_model_matrix

    records = [
        _synthetic_record("subtype_classification", "qwen/qwen3.7-flash", "sorter_v5", 0.8, 0.5),
        _synthetic_record("subtype_classification", "qwen/qwen3.7-flash", "sorter_v6", 0.9, 0.6),
        _synthetic_record("subtype_classification", "deepseek/deepseek-v4-flash", "sorter_v5", 0.75, 0.4),
        _synthetic_record("subtype_classification", "deepseek/deepseek-v4-flash", "sorter_v6", 0.82, 0.45),
    ]
    run_model_matrix.print_matrix(records, task="subtype",
                                  models=["qwen/qwen3.7-flash", "deepseek/deepseek-v4-flash"],
                                  prompts=["sorter_v5", "sorter_v6"])
    out = capsys.readouterr().out
    assert "MODEL MATRIX RESULTS" in out
    assert "0.900" in out  # best cell rendered
    assert "0.800" in out
    assert "Compare cells ONLY within this matrix" in out
