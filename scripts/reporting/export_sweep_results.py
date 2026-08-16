#!/usr/bin/env python3
"""Export the sorter MODEL SWEEP workbook — every model evaluated on the
champion sorter prompt.

Builds ``Sorter_Model_Sweep_Results.xlsx`` in the same Google-Sheets-friendly
format as the reference ``Sorter_Experiment_Results.xlsx`` (114-column
``Eval Results`` sheet + 5-column ``Codebook`` sheet, one row per run):
rows are filtered to ``subtype_classification`` runs of the champion prompt
(``sorter_v13`` by default) — i.e. the full-509 qwen3.7-flash champion
rerun, gpt-5-nano (KANBAN-035), deepseek-v4-flash (KANBAN-036), the
gpt-4.1-nano / deepseek smoke runs, and the DEGRADED first v13 run (kept so
the sweep is a faithful log slice). A trailing ``Notes`` column flags each
row (champion / degraded / smoke / benchmark).

Column spec, styling and the compact codebook are reused verbatim from
``export_experiment_results.py`` so the sweep workbook round-trips into
Google Sheets exactly like the reference.

Usage::

    python scripts/reporting/export_sweep_results.py
    python scripts/reporting/export_sweep_results.py --prompt sorter_v13
    python scripts/reporting/export_sweep_results.py --outdir reports/sheets
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_experiment_results import (  # noqa: E402
    _STR,
    load_records,
    sorter_columns,
    write_workbook,
)

DEFAULT_LOG = "reports/experiment_log.jsonl"
DEFAULT_OUTDIR = "reports/sheets"
DEFAULT_PROMPT = "sorter_v13"
DEFAULT_OUTFILE = "Sorter_Model_Sweep_Results.xlsx"

# Per-run flags for the Notes column — keyed by experiment name; every
# unlisted row gets a generic note. Kept explicit so a log change never
# silently re-labels a run.
_NOTE_BY_RUN = {
    "qwen3.7-flash_sorter_v13_subtype_langfuse@2026-08-16T03:39:32": (
        "DEGRADED first v13 run — 93 transient connection-error defaults "
        "(KANBAN-031); superseded by the clean champion rerun below"),
    "qwen3.7-flash_sorter_v13_subtype_langfuse@2026-08-16T03:56:38": (
        "CHAMPION baseline — clean full-509 rerun of sorter_v13 "
        "(maintenance title-wins arm, KANBAN-031); every other model in "
        "this sweep is compared against it"),
    "gpt-5-nano_sorter_v13_subtype_langfuse@2026-08-16T05:19:37": (
        "Full-509 benchmark (KANBAN-035) — cost-floor frontier arm "
        "($0.05/M prompt + $0.40/M completion); −4.5pp vs champion"),
    "deepseek-v4-flash_sorter_v13_smoke1@2026-08-16T05:26:50": (
        "1-doc smoke run on the default key before the funded full launch"),
    "gpt-4.1-nano_sorter_v13_smoke1@2026-08-16T05:27:13": (
        "1-doc smoke run on the default key before the funded full launch "
        "— full-509 run pending (KANBAN-036)"),
    "deepseek-v4-flash_sorter_v13_subtype_langfuse@2026-08-16T05:44:26": (
        "Full-509 benchmark (KANBAN-036) — cheapest deepseek v4 flash arm "
        "($0.0629/M prompt + $0.1257/M completion)"),
}


def sweep_records(records: list[dict], prompt: str) -> list[dict]:
    """Subtype-classification runs of the given sorter prompt, chronological."""
    out = []
    for r in records:
        if r.get("task") != "subtype_classification":
            continue
        pv = (r.get("prompt_versions") or {}).get("sorter")
        if pv == prompt:
            out.append(r)
    out.sort(key=lambda r: r.get("timestamp", ""))
    return out


def run_note(r: dict) -> str:
    """The Notes-column value for a run (explicit map, generic fallback)."""
    key = f"{r.get('experiment_name')}@{r.get('timestamp', '')[:19]}"
    if key in _NOTE_BY_RUN:
        return _NOTE_BY_RUN[key]
    n = r.get("n_rows")
    if n == 1:
        return "1-doc smoke run (pre-launch gate on the default key)"
    if (r.get("n_ok") or 0) < (r.get("n_rows") or 0):
        return f"DEGRADED — only {r.get('n_ok')}/{r.get('n_rows')} rows completed (transient errors)"
    return "Full-corpus run on the champion prompt"


def build_sweep_workbook(log_path: str, prompt: str, out_path: str) -> int:
    """Write the sweep workbook; returns the number of rows included."""
    records = sweep_records(load_records(log_path), prompt)
    if not records:
        raise SystemExit(f"No {prompt} subtype_classification runs in {log_path}")
    columns = sorter_columns()
    columns.append({
        "header": "Notes",
        "get": run_note,
        "fmt": _STR,
        "desc": "Run-scope flag: champion baseline / degraded / smoke / benchmark context",
        "type": "String",
        "src": "derived (experiment-name + timestamp map)",
        "example": "CHAMPION baseline — clean full-509 rerun of sorter_v13",
    })
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    write_workbook(out_path, "Eval Results", columns, records, codebook_sheet=True)
    return len(records)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=DEFAULT_LOG, help="experiment log JSONL path")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT,
                        help="champion sorter prompt version to sweep (default: sorter_v13)")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR, help="output directory")
    parser.add_argument("--outfile", default=DEFAULT_OUTFILE, help="output workbook filename")
    args = parser.parse_args(argv)
    out = os.path.join(args.outdir, args.outfile)
    n = build_sweep_workbook(args.log, args.prompt, out)
    print(f"Wrote {out} — {n} run(s) of {args.prompt} (sweep rows + Codebook sheet)")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
