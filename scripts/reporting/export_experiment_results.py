#!/usr/bin/env python3
"""Regenerate the per-task experiment performance workbooks + codebooks.

The workbook builders live in the **llm-dojo-scoring** package
(``llm_dojo_scoring.export`` — column specs byte-identical to the reference
formats, verified against llm-dojo-scoring v0.1.0); this script is a thin
re-export shim that keeps the local CLI contract so the sweep exporter
(``export_sweep_results.py``), the slides deck (``export_slides_deck.py``),
and the tests keep working unchanged.

Formats (unchanged):

- ``Sorter_Experiment_Results.xlsx``  — one row per sorter subtype run
  (``task == "subtype_classification"``), 114 columns: headline accuracies,
  CIs, failure-mode counts, per-subtype accuracy (strict + equiv) and cell
  sizes, tokens/cost, run parameters.  Two sheets: ``Eval Results`` and a
  compact ``Codebook``.
- ``Entity_Extraction_Results.xlsx`` — one row per extraction run
  (``task == "contract_entity_extraction"``), 141 columns: overall + per-field
  scores, CI, hallucination / verified-precision rates, entity-list F1,
  diagnostics (error decomposition, MAE/R2, span-count drift), parameters.
- ``<Task>_Experiment_Codebook.csv`` — the FULL variable dictionary for the
  workbook (every column, one row per variable) in Google-Sheets-compatible
  form (plain 5-column table: Variable, Description, Type, Source, Example).

Usage::

    python scripts/reporting/export_experiment_results.py            # both tasks
    python scripts/reporting/export_experiment_results.py --task sorter
    python scripts/reporting/export_experiment_results.py --task extraction
    python scripts/reporting/export_experiment_results.py --outdir ~/Downloads
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm_dojo_scoring.config import PER_SUBTYPE  # noqa: E402  (re-export shim)
from llm_dojo_scoring.export import (  # noqa: E402  (re-export shim)
    build_sweep_workbook,
    champion_prompt_version,
    display_model,
    display_prompt_version,
    dotted_get,
    extraction_columns,
    extraction_records,
    load_records,
    sorter_columns,
    sorter_records,
    sweep_records,
    write_codebook,
    write_compact_codebook_sheet,
    write_workbook,
)

# Constant used by the sweep exporter's Notes column (kept for import compat).
_STR = "string"


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate per-task experiment performance workbooks + codebooks "
                    "(Google-Sheets-friendly, matching the reference formats).")
    parser.add_argument("--task", choices=["sorter", "extraction", "all"], default="all",
                        help="Which task workbook(s) to regenerate (default: all)")
    parser.add_argument("--outdir", default=".",
                        help="Output directory for the workbooks + codebooks (default: current dir)")
    parser.add_argument("--log", default="reports/experiment_log.jsonl",
                        help="Path to the experiment log (default: reports/experiment_log.jsonl)")
    args = parser.parse_args(argv)

    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)
    records = load_records(args.log)

    tasks = ["sorter", "extraction"] if args.task == "all" else [args.task]
    for task in tasks:
        if task == "sorter":
            cols = sorter_columns()
            recs = sorter_records(records)
            wb_path = os.path.join(outdir, "Sorter_Experiment_Results.xlsx")
            cb_path = os.path.join(outdir, "Sorter_Experiment_Codebook.csv")
            title = "Eval Results"
            with_codebook = True
        else:
            cols = extraction_columns()
            recs = extraction_records(records)
            wb_path = os.path.join(outdir, "Entity_Extraction_Results.xlsx")
            cb_path = os.path.join(outdir, "Entity_Extraction_Codebook.csv")
            title = "Eval Results"
            with_codebook = False

        write_workbook(wb_path, title, cols, recs, codebook_sheet=with_codebook)
        write_codebook(cb_path, cols)
        print(f"[{task}] {len(recs)} runs -> {wb_path} ({len(cols)} cols) + {cb_path}")

    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
