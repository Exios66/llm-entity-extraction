#!/usr/bin/env python3
"""Render the agent message board (``MESSAGE_BOARD.md``) as a styled Quarto doc.

``MESSAGE_BOARD.md`` is the source of truth for the cross-agent Kanban canvas;
this script parses its Key Kanban table (open cards) + Archive table and emits
``MESSAGE_BOARD.qmd`` — a color-coded, HTML-renderable Quarto document for
aesthetic local viewing (``quarto render MESSAGE_BOARD.qmd`` /
``quarto preview MESSAGE_BOARD.qmd``).

The ``.qmd`` is a DERIVED artifact (like the experiment-log markdown): regenerate
it whenever the board changes. Never hand-edit it — edit ``MESSAGE_BOARD.md``
and re-run this script.

Usage:
    python scripts/reporting/render_message_board_qmd.py
    python scripts/reporting/render_message_board_qmd.py --out MESSAGE_BOARD.qmd
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOARD_MD = REPO_ROOT / "MESSAGE_BOARD.md"
OUT_QMD = REPO_ROOT / "MESSAGE_BOARD.qmd"

# Status pill + card border accent colors (kept in sync with the discussion log).
STATUS_LABEL = {
    "backlog": "backlog",
    "in_progress": "in progress",
    "blocked": "blocked",
    "in_review": "in review",
    "done": "done",
}


def _strip_code(s: str) -> str:
    """`` `` `in_progress` `` `` -> ``in_progress``."""
    s = s.strip()
    if s.startswith("`") and s.endswith("`") and len(s) > 1:
        return s[1:-1]
    return s


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _parse_table(lines: list[str], n_cols: int) -> list[list[str]]:
    """Extract rows (list of cell lists) from a markdown table block."""
    rows: list[list[str]] = []
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = _cells(ln)
        # skip the header + separator rows (first cell is 'Card' or all dashes)
        if cells and cells[0] in ("Card",) or (cells and all(set(c) <= {"-", ":"} for c in cells)):
            continue
        if len(cells) >= n_cols:
            rows.append(cells[:n_cols])
    return rows


def _open_cards(lines: list[str]) -> list[list[str]]:
    """The 7-col Key Kanban table (open cards)."""
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("## Key Kanban table"):
            start = i
            break
    if start is None:
        return []
    end = start
    for j in range(start, len(lines)):
        if lines[j].startswith("## Discussion board") or lines[j].startswith("**Sweep rule"):
            end = j
            break
    else:
        end = len(lines)
    return _parse_table(lines[start:end], 7)


def _archive_cards(lines: list[str]) -> list[list[str]]:
    """The 4-col Archive table."""
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("Archive (completed work"):
            start = i
            break
    if start is None:
        return []
    end = start
    for j in range(start, len(lines)):
        if lines[j].startswith("When moving a card here"):
            end = j
            break
    else:
        end = len(lines)
    return _parse_table(lines[start:end], 4)


def _card_block(card_id: str, issue: str, status: str, summary: str,
                owner: str, target: str, evidence: str) -> str:
    status = _strip_code(status)
    label = STATUS_LABEL.get(status, status)
    head_bits = [f"<span class=\"card-id\">{card_id}</span>",
                 f"<span class=\"pill pill-{status}\">{label}</span>"]
    if owner:
        head_bits.append(f"<span class=\"meta\">owner: {owner}</span>")
    if target:
        head_bits.append(f"<span class=\"meta\">target: {target}</span>")
    if issue and issue != "— (board-only)":
        head_bits.append(f"<span class=\"meta\">issue: {issue}</span>")

    foot = ""
    if evidence:
        foot = f"\n\n<p class=\"card-foot\"><strong>Evidence:</strong> {evidence}</p>"

    body = summary if summary else ""
    return (f"::: {{.card .card-{status}}}\n"
            f"<div class=\"card-head\">{' · '.join(head_bits)}</div>\n\n"
            f"{body}\n"
            f"{foot}\n"
            f":::")


def build_qmd() -> str:
    lines = BOARD_MD.read_text(encoding="utf-8").splitlines()
    open_rows = _open_cards(lines)
    archive_rows = _archive_cards(lines)

    lanes: dict[str, list[list[str]]] = {"in_progress": [], "in_review": [],
                                         "blocked": [], "backlog": [], "done": []}
    for row in open_rows:
        status = _strip_code(row[2])
        if status not in lanes:
            lanes[status] = []
        lanes[status].append(row)

    parts: list[str] = []
    parts.append("""---
title: "Agent Message Board"
subtitle: "Kanban canvas — llm-entity-extraction (rendered from MESSAGE_BOARD.md)"
date: "2026-08-16"
format:
  html:
    toc: true
    toc-title: "Board"
    embed-resources: true
    code-fold: false
  gfm: default
---

> **Derived artifact.** This file is generated from `MESSAGE_BOARD.md` by
> `scripts/reporting/render_message_board_qmd.py`. Edit the `.md` (the source of
> truth), then regenerate. Render locally with `quarto render MESSAGE_BOARD.qmd`
> or `quarto preview MESSAGE_BOARD.qmd`.

<style>
:root {
  --backlog: #6b7280; --in_progress: #2563eb; --blocked: #dc2626;
  --in_review: #d97706; --done: #16a34a;
}
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
.pill {
  display: inline-block; padding: 0.12rem 0.6rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; color: #fff; text-transform: uppercase;
  letter-spacing: 0.03em; vertical-align: middle;
}
.pill-backlog { background: var(--backlog); }
.pill-in_progress { background: var(--in_progress); }
.pill-blocked { background: var(--blocked); }
.pill-in_review { background: var(--in_review); }
.pill-done { background: var(--done); }
.card {
  border: 1px solid #e5e7eb; border-left: 4px solid #d1d5db; border-radius: 8px;
  padding: 0.7rem 1rem; margin: 0.55rem 0; background: #fff;
}
.card-in_progress { border-left-color: var(--in_progress); }
.card-blocked { border-left-color: var(--blocked); }
.card-in_review { border-left-color: var(--in_review); }
.card-done { border-left-color: var(--done); }
.card-backlog { border-left-color: var(--backlog); }
.card-head { font-size: 0.85rem; margin-bottom: 0.4rem; }
.card-id { font-weight: 700; color: #111827; margin-right: 0.35rem; }
.meta { color: #6b7280; font-size: 0.8rem; margin: 0 0.5rem 0 0; }
.card p { margin: 0.25rem 0; }
.card-foot { font-size: 0.8rem; color: #6b7280; margin-top: 0.4rem !important;
             border-top: 1px dashed #e5e7eb; padding-top: 0.4rem; }
.lane h2 { border-bottom: 2px solid #e5e7eb; padding-bottom: 0.25rem; margin-top: 1.4rem; }
.count { color: #9ca3af; font-weight: 500; }
</style>

## Open board
""")

    lane_order = [("in_progress", "In progress"),
                  ("in_review", "In review"),
                  ("blocked", "Blocked"),
                  ("backlog", "Backlog"),
                  ("done", "Done (not yet archived)")]
    total = 0
    for key, heading in lane_order:
        rows = lanes.get(key, [])
        if not rows:
            continue
        total += len(rows)
        parts.append(f"::: {{.lane .lane-{key}}}\n")
        parts.append(f"### {heading} <span class=\"count\">({len(rows)})</span>\n")
        for row in rows:
            card_id, issue, status, summary, owner, target, evidence = (
                row + [""] * 7)[:7]
            parts.append(_card_block(card_id, issue, status, summary, owner,
                                     target, evidence))
        parts.append(":::")
        parts.append("")

    parts.append(f"## Open board summary\n\n{total} open cards.\n")

    if archive_rows:
        parts.append("## Archive (completed work)\n")
        parts.append("""::: {.callout-note}
Finished work is never deleted — it lives here for auditability. Cards are
listed newest-first.
:::
""")
        for row in archive_rows:
            card_id, shipped, commit, result = (row + [""] * 4)[:4]
            label = card_id if card_id else "(archived)"
            parts.append("::: {.card .card-done}\n")
            parts.append(f"<div class=\"card-head\"><span class=\"card-id\">{label}</span>"
                         f"<span class=\"pill pill-done\">shipped</span>"
                         f"<span class=\"meta\">{shipped}</span></div>\n")
            if commit:
                parts.append(f"<p class=\"card-foot\"><strong>Commit / tag:</strong> {commit}</p>\n")
            parts.append(f"\n{result}\n")
            parts.append(":::")
        parts.append("")

    parts.append("---\n\n*Generated from `MESSAGE_BOARD.md` — do not hand-edit this file.*\n")
    return "\n".join(parts)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_QMD,
                        help="Output .qmd path (default: MESSAGE_BOARD.qmd)")
    args = parser.parse_args(argv)

    qmd = build_qmd()
    args.out.write_text(qmd, encoding="utf-8")
    print(f"Wrote {args.out} ({len(qmd)} chars)")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(__import__("sys").argv[1:]))


if __name__ == "__main__":
    main()
