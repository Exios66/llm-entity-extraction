#!/usr/bin/env python3
"""Build and plot a confusion matrix from a Braintrust experiment.

Fetches the scored task rows of an experiment (by name), computes the
expected-vs-predicted confusion matrix over the taxonomy classes, and writes:

- ``reports/confusion_matrix_<experiment>.png`` — matplotlib heatmap
- ``reports/confusion_matrix_<experiment>.csv`` — machine-readable matrix

Usage:
    python scripts/reporting/confusion_matrix.py --experiment qwen3.7-flash_sorter_v0
    python scripts/reporting/confusion_matrix.py --experiment qwen3.7-flash_sorter_v0 \
        --output-dir reports --no-plot
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import fetch_experiment_rows, find_experiment_by_name
from src.env_utils import require_env
from src.scorers import ERROR_PREFIX, normalize_label
from src.taxonomy import doc_class_keys

_CONFIG = load_braintrust_config()


def build_matrix(task_rows: list[dict], classes: list[str]) -> tuple[dict, int]:
    """Compute the confusion matrix {expected: {predicted: count}}.

    Rows whose output is the ERROR sentinel are counted as ``failed`` (a
    pseudo-prediction so failed rows never silently vanish).
    """
    matrix: dict[str, dict[str, int]] = {cls: {cls2: 0 for cls2 in classes} for cls in classes}
    matrix["__failed__"] = {"__failed__": 0}
    failed = 0
    for row in task_rows:
        expected = normalize_label(row["expected"])
        output = str(row["output"])
        if output.startswith(ERROR_PREFIX):
            matrix["__failed__"]["__failed__"] += 1
            failed += 1
            continue
        predicted = normalize_label(output)
        if expected not in matrix:
            matrix.setdefault(expected, {cls2: 0 for cls2 in classes})
        if predicted not in matrix[expected]:
            matrix[expected][predicted] = 0
        matrix[expected][predicted] += 1
    return matrix, failed


def write_csv(matrix: dict, path: Path) -> None:
    classes = [c for c in matrix if c != "__failed__"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["expected\\predicted"] + classes + ["failed"])
        for expected in classes + ["__failed__"]:
            row = matrix.get(expected, {})
            writer.writerow([expected] + [row.get(p, 0) for p in classes] +
                            [row.get("__failed__", 0)])
    print(f"CSV written to {path}")


def plot_matrix(matrix: dict, classes: list[str], experiment: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    n = len(classes)
    data = np.zeros((n, n), dtype=int)
    for i, expected in enumerate(classes):
        row = matrix.get(expected, {})
        for j, predicted in enumerate(classes):
            data[i, j] = row.get(predicted, 0)

    fig, ax = plt.subplots(figsize=(max(8, n * 1.3), max(7, n * 1.3)))
    im = ax.imshow(data, cmap="Blues")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(classes, rotation=45, ha="right")
    ax.set_yticklabels(classes)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Expected")
    ax.set_title(f"Confusion matrix — {experiment}")
    for i in range(n):
        for j in range(n):
            ax.text(j, i, str(data[i, j]) if data[i, j] else "",
                    ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Plot written to {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Braintrust experiment name")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"), help="Output directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip the PNG heatmap")
    args = parser.parse_args()

    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")
    exp = find_experiment_by_name(braintrust_key, _CONFIG.project_id, args.experiment, _CONFIG.api_base)
    if not exp:
        parser.error(f"Experiment not found: {args.experiment!r} (list experiments via --list).")
    rows = fetch_experiment_rows(braintrust_key, exp["id"], _CONFIG.api_base)

    task_rows = [
        {"expected": r.get("expected"), "output": r.get("output"), "input": r.get("input"),
         "metadata": r.get("metadata") or {}, "metrics": r.get("metrics") or {}}
        for r in rows
        if r.get("expected") is not None and r.get("output") is not None
    ]
    if not task_rows:
        parser.error(f"No scored task rows in experiment {args.experiment!r}.")

    classes = doc_class_keys()
    matrix, failed = build_matrix(task_rows, classes)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    slug = args.experiment.replace("/", "_")
    csv_path = args.output_dir / f"confusion_matrix_{slug}.csv"
    write_csv(matrix, csv_path)
    if not args.no_plot:
        png_path = args.output_dir / f"confusion_matrix_{slug}.png"
        try:
            plot_matrix(matrix, classes, args.experiment, png_path)
        except ImportError:
            print("matplotlib not installed — skipping PNG (pip install matplotlib)", file=sys.stderr)

    total = sum(sum(row.values()) for row in matrix.values())
    diag = sum(matrix[c][c] for c in classes if c in matrix)
    print(f"\n{matrix['__failed__'].get('__failed__', 0)} failed rows "
          f"({matrix['__failed__']['__failed__'] / max(1, total):.1%})")
    print(f"exact_match (incl. failed as misses): {diag}/{total} ({diag / max(1, total):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
