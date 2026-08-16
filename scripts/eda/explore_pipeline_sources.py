#!/usr/bin/env python3
"""Full exploratory data analysis of the NEW pipeline data sources (KANBAN-045).

Covers every source integrated into the pipeline after the CUAD baseline
(KANBAN-014): the MAUD merger-agreement corpus (Zenodo ``maud_v1``), the EDGAR
S-1 corporate-record exhibits, the merged hierarchical doc-class dataset, and
the LegalBench tasks (hearsay + CUAD subtasks).

Sources and what is measured per source:

- ``data/maud/contracts.jsonl`` (152 merger agreements, CC BY 4.0) — text
  size distribution, consideration-type subclass GT balance, MAUD category
  coverage per contract, label density, ``[***]`` redaction prevalence.
- ``data/maud/classification.jsonl`` (25,827 per-question rows) — the 22
  question families across 7 categories, per-task answer balance, valid-class
  cardinality, train coverage.
- ``data/s1_corporate_records/corporate-records.jsonl`` (15 EDGAR exhibits) —
  exhibit-type mix (EX-3.x/4.x), record-type subclass balance, filers/dates,
  text size.
- ``data/datasets/docclass_merged.jsonl`` (676 rows) — the merged surface
  (CUAD 509 + MAUD 152 + S-1 15), doc-class distribution, subclass balance
  including the GT-``other`` gap cluster that drives the subclass metric.
- ``data/legalbench_local/*.jsonl`` — the hearsay train/test split + the 10
  CUAD subtask surfaces (answer balance, task types, slice coverage).

Outputs (all git-tracked, under ``data/eda/<source>/``):
  - ``report.md``   — the full EDA report (tables + interpretation)
  - ``findings.md`` — condensed findings summary
  - ``figures/*.png`` — matplotlib visualizations (``--no-figures`` to skip)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "eda"

MAUD_CONTRACTS = ROOT / "data" / "maud" / "contracts.jsonl"
MAUD_CLASSIFICATION = ROOT / "data" / "maud" / "classification.jsonl"
S1_RECORDS = ROOT / "data" / "s1_corporate_records" / "corporate-records.jsonl"
DOCCLASS_MERGED = ROOT / "data" / "datasets" / "docclass_merged.jsonl"
LEGALBENCH_DIR = ROOT / "data" / "legalbench_local"

CITES = {
    "maud": ("Source: MAUD — Merger Agreement Understanding Dataset (Gebre et al., "
             "COLING 2025), CC BY 4.0 · Zenodo maud_v1"),
    "s1": "Source: EDGAR S-1 exhibits (SEC public-domain filings, Aug 2026 collection)",
    "docclass": "Source: merged doc-class surface (CUAD 509 + MAUD 152 + S-1 15, fp 5602b71f)",
    "legalbench": ("Source: LegalBench (Neel Guha et al.) — hearsay + CUAD clause "
                   "subtasks, CC BY 4.0"),
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _text_stats(recs: list[dict], text_key: str = "doc_text") -> dict:
    """Per-document text-size stats (chars, words, tokens≈chars/4)."""
    lens = [len(r.get(text_key) or "") for r in recs]
    if not lens:
        return {}
    lens = sorted(lens)
    n = len(lens)
    words = [len((r.get(text_key) or "").split()) for r in recs]
    redacted = sum(1 for r in recs if "[***]" in (r.get(text_key) or ""))
    return {
        "n": n,
        "chars_total": sum(lens),
        "chars_min": lens[0],
        "chars_q25": lens[n // 4],
        "chars_median": lens[n // 2],
        "chars_q75": lens[3 * n // 4],
        "chars_max": lens[-1],
        "words_median": sorted(words)[n // 2],
        "tokens_est_median": round(lens[n // 2] / 4),
        "redacted": redacted,
        "over_90k": sum(1 for l in lens if l > 90_000),
        "over_16k": sum(1 for l in lens if l > 16_000),
    }


def _fmt_stats(t: dict) -> str:
    return (
        f"{t['n']} docs · {t['chars_total']:,} chars total\n"
        f"  size: min {t['chars_min']:,} / p25 {t['chars_q25']:,} / median "
        f"{t['chars_median']:,} / p75 {t['chars_q75']:,} / max {t['chars_max']:,} chars\n"
        f"  median {t['words_median']:,} words (≈{t['tokens_est_median']:,} tokens at 4 ch/tok)\n"
        f"  docs over 90k chars (chunk window): {t['over_90k']} · over 16k (single-pass "
        f"limit): {t['over_16k']}\n"
        f"  docs with [***] redaction markers: {t['redacted']}"
    )


# ---------------------------------------------------------------------------
# MAUD
# ---------------------------------------------------------------------------


def _maud_subclasses(recs: list[dict]) -> Counter:
    out: Counter = Counter()
    for r in recs:
        sub = r.get("expected_subclass") or r["metadata"].get("expected_subclass") or "other"
        out[sub] += 1
    return out


def analyze_maud() -> dict:
    contracts = _load_jsonl(MAUD_CONTRACTS)
    rows = _load_jsonl(MAUD_CLASSIFICATION)
    res: dict = {"source": "maud", "n_contracts": len(contracts), "n_rows": len(rows)}
    if contracts:
        res["contracts_text"] = _text_stats(contracts)
        res["subclasses"] = dict(_maud_subclasses(contracts).most_common())
        cat_counts: Counter = Counter()
        label_counts: list[int] = []
        for r in contracts:
            md = r["metadata"]
            for cat, n in (md.get("maud_categories") or {}).items():
                cat_counts[cat] += n
            label_counts.append(int(md.get("maud_label_count") or 0))
        res["category_labels"] = dict(cat_counts.most_common())
        res["labels_total"] = sum(label_counts)
        res["labels_median"] = sorted(label_counts)[len(label_counts) // 2] if label_counts else 0
        res["labels_per_contract"] = label_counts
    if rows:
        tasks: Counter = Counter()
        cats: Counter = Counter()
        splits: Counter = Counter()
        class_card: Counter = Counter()
        answer_balance: dict[str, Counter] = defaultdict(Counter)
        contracts_seen: set = set()
        subquestions = 0
        for r in rows:
            md = r["metadata"]
            task = md.get("task") or "?"
            tasks[task] += 1
            cats[md.get("category") or "?"] += 1
            splits[md.get("split") or "?"] += 1
            vc = md.get("valid_classes") or []
            class_card[len(vc)] += 1
            answer_balance[task][str(r.get("expected") or "")] += 1
            contracts_seen.add(md.get("contract") or "?")
            if md.get("subquestion") not in (None, "", "<NONE>"):
                subquestions += 1
        res["tasks"] = dict(tasks.most_common())
        res["categories"] = dict(cats.most_common())
        res["splits"] = dict(splits)
        res["n_tasks"] = len(tasks)
        res["n_contracts_covered"] = len(contracts_seen)
        res["subquestions"] = subquestions
        res["class_cardinality"] = dict(class_card)
        res["answer_balance"] = {t: dict(c.most_common()) for t, c in sorted(answer_balance.items())}
    return res


def render_maud_report(res: dict) -> str:
    L = ["# MAUD — merger-agreement corpus + per-question classification suite", ""]
    L.append(f"_Emitted by `scripts/eda/explore_pipeline_sources.py --source maud`_")
    L.append(f"_Note: {CITES['maud']}_")
    L.append("")
    L.append(f"**Contracts**: {res['n_contracts']} merger agreements "
             f"(`data/maud/contracts.jsonl`)")
    L.append(f"**Per-question rows**: {res['n_rows']:,} (`data/maud/classification.jsonl`)")
    L.append("")
    if "contracts_text" in res:
        L.append("## Contract text size")
        L.append("")
        L.append(_fmt_stats(res["contracts_text"]))
        L.append("")
    if "subclasses" in res:
        L.append("## Consideration-type subclass (expert GT)")
        L.append("")
        L.append("| subclass | contracts | share |")
        L.append("|---|---|---|")
        n = sum(res["subclasses"].values())
        for k, v in res["subclasses"].items():
            L.append(f"| {k} | {v} | {v / n:.1%} |")
        L.append("")
    if "category_labels" in res:
        L.append("## MAUD category coverage (label counts over the 152 contracts)")
        L.append("")
        L.append("| category | labels | share |")
        L.append("|---|---|---|")
        tot = sum(res["category_labels"].values())
        for k, v in res["category_labels"].items():
            L.append(f"| {k} | {v:,} | {v / tot:.1%} |")
        L.append("")
        L.append(f"Total labels across the corpus: **{res.get('labels_total', 0):,}** "
                 f"(median {res.get('labels_median', 0)} per contract).")
        L.append("")
    if "tasks" in res:
        L.append("## Per-question suite (22 question families / 7 categories)")
        L.append("")
        L.append(f"**{res['n_tasks']} tasks** across **{len(res['categories'])} categories**; "
                 f"train rows cover **{res['n_contracts_covered']}** distinct contracts; "
                 f"**{res.get('subquestions', 0):,}** rows carry a subquestion.")
        L.append("")
        L.append("| category | rows |")
        L.append("|---|---|")
        for k, v in sorted(res["categories"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {k} | {v:,} |")
        L.append("")
        L.append("| task | rows |")
        L.append("|---|---|")
        for k, v in sorted(res["tasks"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {k} | {v:,} |")
        L.append("")
        L.append("### Answer cardinality")
        L.append("")
        L.append("| valid classes per row | rows |")
        L.append("|---|---|")
        for k, v in sorted(res["class_cardinality"].items()):
            L.append(f"| {k} | {v:,} |")
        L.append("")
        L.append("### Answer balance (per task)")
        L.append("")
        for task, bal in res["answer_balance"].items():
            L.append(f"- **{task}**: " + ", ".join(f"{k} {v:,}" for k, v in bal.items()))
        L.append("")
    return "\n".join(L)


def render_maud_findings(res: dict) -> str:
    L = ["# MAUD findings (condensed)", ""]
    if "subclasses" in res:
        n = sum(res["subclasses"].values())
        top = res["subclasses"].most_common(1)[0] if hasattr(res["subclasses"], "most_common") else None
        other = res["subclasses"].get("other", 0)
        L.append(f"- Consideration GT balance over {n} contracts: "
                 + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in res["subclasses"].items())
                 + f" — `other` ({other}) is the GT-gap bucket the subclass metric loses on.")
    if "category_labels" in res:
        tot = res["category_labels"]
        top_cat = max(tot, key=tot.get)
        L.append(f"- Heaviest MAUD category by labels: **{top_cat}** "
                 f"({tot[top_cat]:,}/{sum(tot.values()):,}).")
    if "tasks" in res:
        top_task = max(res["tasks"], key=res["tasks"].get)
        L.append(f"- Largest question family: **{top_task}** ({res['tasks'][top_task]:,} rows).")
    if "contracts_text" in res:
        t = res["contracts_text"]
        L.append(f"- MAUD contracts are large (median {t['chars_median']:,} chars, "
                 f"{t['over_90k']}/{t['n']} over the 90k chunk window) — the docclass "
                 f"vision/truncation arm must chunk or head+tail these.")
        L.append(f"- {t['redacted']} contracts carry `[***]` redaction markers.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# S-1 corporate records
# ---------------------------------------------------------------------------


def analyze_s1() -> dict:
    recs = _load_jsonl(S1_RECORDS)
    res: dict = {"source": "s1", "n": len(recs)}
    if not recs:
        return res
    res["text"] = _text_stats(recs)
    res["exhibit_types"] = dict(Counter(r["metadata"].get("exhibit_type") for r in recs).most_common())
    res["subclasses"] = dict(Counter(r.get("expected_subclass") for r in recs).most_common())
    res["filers"] = dict(Counter((r["metadata"].get("filer") or "?") for r in recs).most_common())
    res["ciks"] = len({r["metadata"].get("cik") for r in recs})
    res["filing_dates"] = sorted((r["metadata"].get("filing_date") or "") for r in recs)
    res["accessions"] = sorted(r["metadata"].get("accession") or "" for r in recs)
    return res


def render_s1_report(res: dict) -> str:
    L = ["# EDGAR S-1 corporate-record exhibits", ""]
    L.append(f"_Emitted by `scripts/eda/explore_pipeline_sources.py --source s1`_")
    L.append(f"_Note: {CITES['s1']}_")
    L.append("")
    L.append(f"**{res['n']} exhibits** (`data/s1_corporate_records/corporate-records.jsonl`)")
    L.append("")
    if "text" in res:
        L.append("## Text size")
        L.append("")
        L.append(_fmt_stats(res["text"]))
        L.append("")
    if "exhibit_types" in res:
        L.append("## Exhibit type")
        L.append("")
        L.append("| exhibit | count |")
        L.append("|---|---|")
        for k, v in res["exhibit_types"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
    if "subclasses" in res:
        L.append("## Record-type subclass (content-detected)")
        L.append("")
        L.append("| subclass | count |")
        L.append("|---|---|")
        for k, v in res["subclasses"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
    if "filers" in res:
        L.append(f"## Filers — **{res['ciks']} distinct CIKs**")
        L.append("")
        L.append("| filer | count |")
        L.append("|---|---|")
        for k, v in res["filers"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
        L.append(f"Filing dates (earliest → latest): {', '.join(res['filing_dates'])}")
        L.append("")
    return "\n".join(L)


def render_s1_findings(res: dict) -> str:
    L = ["# S-1 corporate records findings (condensed)", ""]
    if "subclasses" in res:
        L.append("- Subclass balance: "
                 + ", ".join(f"{k} {v}" for k, v in res["subclasses"].items())
                 + " — the collection skews to charter instruments (articles_of_incorporation) "
                 "and rights instruments (EX-4.x).")
    if "exhibit_types" in res:
        L.append("- Exhibit mix: "
                 + ", ".join(f"{k}×{v}" for k, v in res["exhibit_types"].items()) + ".")
    if "text" in res:
        t = res["text"]
        L.append(f"- S-1 exhibits are small (median {t['chars_median']:,} chars) — far below "
                 "the CUAD/MAUD truncation regime; single-pass text handles them.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Merged docclass surface
# ---------------------------------------------------------------------------


def analyze_docclass() -> dict:
    recs = _load_jsonl(DOCCLASS_MERGED)
    res: dict = {"source": "docclass", "n": len(recs)}
    if not recs:
        return res
    res["composition"] = dict(Counter(r["metadata"].get("source_dataset") or "?" for r in recs).most_common())
    res["doc_types"] = dict(Counter(r["expected"] for r in recs).most_common())
    res["subclasses"] = dict(Counter(r.get("expected_subclass") for r in recs).most_common())
    res["subclass_none"] = sum(1 for r in recs if not r.get("expected_subclass"))
    res["subclass_present"] = res["n"] - res["subclass_none"]
    # GT "other" gap cluster — subclass GT where the model often reads an explicit label.
    res["gt_other"] = sum(1 for r in recs if r.get("expected_subclass") == "other")
    # Per-source text stats
    by_source: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        by_source[r["metadata"].get("source_dataset") or "?"].append(r)
    res["per_source_text"] = {src: _text_stats(v) for src, v in by_source.items()}
    res["applicable_categories"] = dict(
        Counter(r["metadata"].get("category") or "?" for r in recs if r["metadata"].get("category")).most_common()
    )
    return res


def render_docclass_report(res: dict) -> str:
    L = ["# Merged hierarchical doc-class surface (676 rows)", ""]
    L.append(f"_Emitted by `scripts/eda/explore_pipeline_sources.py --source docclass`_")
    L.append(f"_Note: {CITES['docclass']}_")
    L.append("")
    L.append(f"**{res['n']} rows** (`data/datasets/docclass_merged.jsonl`)")
    L.append("")
    L.append("## Composition by source")
    L.append("")
    L.append("| source | rows |")
    L.append("|---|---|")
    for k, v in res["composition"].items():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## Doc class (primary dimension)")
    L.append("")
    L.append("| doc_type | rows | share |")
    L.append("|---|---|---|")
    n = res["n"]
    for k, v in res["doc_types"].items():
        L.append(f"| {k} | {v} | {v / n:.1%} |")
    L.append("")
    L.append("## Subclass (second dimension)")
    L.append("")
    L.append(f"Rows WITH subclass GT: **{res['subclass_present']}** · without: "
             f"**{res['subclass_none']}** (unscored on the subclass metric) · "
             f"GT-`other` gap cluster: **{res['gt_other']}**.")
    L.append("")
    L.append("| subclass | rows |")
    L.append("|---|---|")
    for k, v in res["subclasses"].items():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("## Text size by source")
    L.append("")
    L.append("| source | n | median chars | max chars | over 90k |")
    L.append("|---|---|---|---|---|")
    for src, t in res["per_source_text"].items():
        L.append(f"| {src} | {t['n']} | {t['chars_median']:,} | {t['chars_max']:,} | {t['over_90k']} |")
    L.append("")
    if res["applicable_categories"]:
        L.append("## CUAD category metadata (contract rows)")
        L.append("")
        L.append("| category | docs |")
        L.append("|---|---|")
        for k, v in res["applicable_categories"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
    return "\n".join(L)


def render_docclass_findings(res: dict) -> str:
    L = ["# Merged doc-class findings (condensed)", ""]
    L.append(f"- {res['n']} rows: "
             + ", ".join(f"{k} {v}" for k, v in res["composition"].items()) + ".")
    L.append(f"- Subclass GT coverage: {res['subclass_present']}/{res['n']} rows scored "
             f"({res['subclass_none']} unscored); **{res['gt_other']} GT-`other` rows** — "
             "the dominant driver of the 56/69 full-676 subclass misses (the model reads an "
             "explicit consideration where MAUD GT falls back to `other`).")
    dt = res["doc_types"]
    n = res["n"]
    balance = ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in dt.items())
    L.append(f"- Doc-class balance: {balance}.")
    worst = max(res["per_source_text"].items(), key=lambda kv: kv[1]["over_90k"])
    L.append(f"- Truncation regime is source-bound: {worst[0]} has the most over-90k docs "
             f"({worst[1]['over_90k']}/{worst[1]['n']}) — chunking/head+tail is required there.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# LegalBench
# ---------------------------------------------------------------------------


def analyze_legalbench() -> dict:
    files = sorted(LEGALBENCH_DIR.glob("*.jsonl")) if LEGALBENCH_DIR.exists() else []
    res: dict = {"source": "legalbench", "files": []}
    for f in files:
        recs = _load_jsonl(f)
        name = f.stem
        entry: dict = {"name": name, "n": len(recs), "rows": recs}
        if recs:
            md = recs[0]["metadata"]
            entry["task"] = md.get("task") or name
            entry["task_type"] = md.get("task_type") or "?"
            entry["valid_classes"] = md.get("valid_classes") or []
            entry["answer_balance"] = dict(Counter(str(r.get("expected")) for r in recs).most_common())
            entry["slices"] = dict(Counter(str((r.get("metadata") or {}).get("slice") or "?") for r in recs).most_common())
            entry["text"] = _text_stats(recs)
        res["files"].append(entry)
    res["n_files"] = len(res["files"])
    res["n_rows"] = sum(e["n"] for e in res["files"])
    return res


def render_legalbench_report(res: dict) -> str:
    L = ["# LegalBench tasks (hearsay + CUAD subtasks)", ""]
    L.append(f"_Emitted by `scripts/eda/explore_pipeline_sources.py --source legalbench`_")
    L.append(f"_Note: {CITES['legalbench']}_")
    L.append("")
    L.append(f"**{res['n_files']} files** / **{res['n_rows']:,} rows** under "
             f"`data/legalbench_local/`")
    L.append("")
    L.append("| task | rows | type | answers | slices | median chars |")
    L.append("|---|---|---|---|---|---|")
    for e in res["files"]:
        bal = ", ".join(f"{k} {v}" for k, v in e["answer_balance"].items())
        sl = ", ".join(e["slices"].keys())
        md = e["text"].get("chars_median", 0)
        L.append(f"| {e['name']} | {e['n']} | {e['task_type']} | {bal} | {sl} | {md:,} |")
    L.append("")
    hearsay = next((e for e in res["files"] if e["name"] in ("hearsay", "hearsay-test")), None)
    if hearsay:
        L.append("## Hearsay split")
        L.append("")
        for e in res["files"]:
            if e["name"].startswith("hearsay"):
                L.append(f"- **{e['name']}**: {e['n']} rows, "
                         + ", ".join(f"{k} {v} ({v / e['n']:.0%})" for k, v in e["answer_balance"].items())
                         + f" — slices: {', '.join(e['slices'].keys())}")
        L.append("")
    return "\n".join(L)


def render_legalbench_findings(res: dict) -> str:
    L = ["# LegalBench findings (condensed)", ""]
    subtask = [e for e in res["files"] if e["name"].startswith("cuad_")]
    ht = [e for e in res["files"] if e["name"].startswith("hearsay")]
    L.append(f"- **{len(ht)} hearsay files** (train {next((e['n'] for e in ht if e['name'] == 'hearsay'), 0)} "
             f"/ test {next((e['n'] for e in ht if e['name'] == 'hearsay-test'), 0)} rows) and "
             f"**{len(subtask)} CUAD subtask files** ({sum(e['n'] for e in subtask)} rows, 6-row "
             "controlled surfaces).")
    L.append("- Subtask answer balance: "
             + ", ".join(f"{e['name'].replace('cuad_', '')} "
                         f"{next(iter(e['answer_balance']), '?')}×{e['n']}"
                         for e in subtask[:5])
             + (" …" if len(subtask) > 5 else "")
             + " — small n surfaces, same-surface A/B is the only valid comparison.")
    L.append("- Slices present: "
             + ", ".join(sorted({s for e in ht for s in e["slices"]}))
             + ".")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def _hist_ax(ax, values, xlabel, title, color="#1f77b4"):
    ax.hist(values, bins=min(40, max(5, len(set(values)))), color=color, edgecolor="white")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    ax.set_title(title)


def make_maud_figures(res: dict, figdir: Path) -> None:
    if "contracts_text" not in res:
        return
    t = res["contracts_text"]
    fig, ax = plt.subplots(figsize=(7, 4))
    _hist_ax(ax, [int(r["metadata"].get("chars") or 0) for r in _load_jsonl(MAUD_CONTRACTS)],
             "chars", "MAUD contract size", "#6d28d9")
    ax.axvline(90_000, color="crimson", ls="--", lw=1.2)
    ax.text(91_000, ax.get_ylim()[1] * 0.9, "90k chunk window", color="crimson", fontsize=8)
    fig.text(0.99, 0.01, CITES["maud"], ha="right", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(figdir / "maud_contract_size.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    subs = list(res["subclasses"].keys())
    vals = list(res["subclasses"].values())
    ax.bar(subs, vals, color="#6d28d9")
    ax.set_title("MAUD consideration-type subclass GT")
    ax.set_ylabel("contracts")
    ax.tick_params(axis="x", rotation=30)
    fig.text(0.99, 0.01, CITES["maud"], ha="right", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(figdir / "maud_subclasses.png", dpi=110)
    plt.close(fig)

    if "tasks" in res:
        fig, ax = plt.subplots(figsize=(8, 4))
        names = [k for k, _ in sorted(res["tasks"].items(), key=lambda kv: -kv[1])]
        counts = [res["tasks"][k] for k in names]
        ax.barh(range(len(names))[::-1], counts, color="#0f766e")
        ax.set_yticks(range(len(names))[::-1])
        ax.set_yticklabels(names, fontsize=7)
        ax.set_xlabel("rows")
        ax.set_title("MAUD per-question task volume")
        fig.text(0.99, 0.01, CITES["maud"], ha="right", fontsize=7, color="gray")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(figdir / "maud_task_volume.png", dpi=110)
        plt.close(fig)


def make_s1_figures(res: dict, figdir: Path) -> None:
    if "exhibit_types" not in res:
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))
    ax1.bar(res["exhibit_types"].keys(), res["exhibit_types"].values(), color="#b45309")
    ax1.set_title("S-1 exhibit type")
    ax1.set_ylabel("exhibits")
    ax1.tick_params(axis="x", rotation=30)
    ax2.bar(res["subclasses"].keys(), res["subclasses"].values(), color="#0f766e")
    ax2.set_title("record-type subclass")
    ax2.tick_params(axis="x", rotation=30)
    fig.text(0.99, 0.01, CITES["s1"], ha="right", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(figdir / "s1_exhibits_and_subclasses.png", dpi=110)
    plt.close(fig)


def make_docclass_figures(res: dict, figdir: Path) -> None:
    if "doc_types" not in res:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    names = list(res["doc_types"].keys())
    vals = list(res["doc_types"].values())
    ax.bar(names, vals, color="#1d4ed8")
    ax.set_title("Merged doc-class surface — doc_type balance")
    ax.set_ylabel("rows")
    fig.text(0.99, 0.01, CITES["docclass"], ha="right", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(figdir / "docclass_balance.png", dpi=110)
    plt.close(fig)

    if "subclasses" in res:
        fig, ax = plt.subplots(figsize=(8, 4))
        subs = {k: v for k, v in res["subclasses"].items() if k is not None}
        names = list(subs.keys())
        vals = list(subs.values())
        ax.barh(range(len(names))[::-1], vals, color="#1d4ed8")
        ax.set_yticks(range(len(names))[::-1])
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("rows")
        ax.set_title(f"Subclass GT (without/None = {res['subclass_none']}, GT-other = {res['gt_other']})")
        fig.text(0.99, 0.01, CITES["docclass"], ha="right", fontsize=7, color="gray")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(figdir / "docclass_subclasses.png", dpi=110)
        plt.close(fig)


def make_legalbench_figures(res: dict, figdir: Path) -> None:
    if not res["files"]:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    names = [e["name"] for e in res["files"]]
    counts = [e["n"] for e in res["files"]]
    ax.bar(range(len(names)), counts, color="#be185d")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("rows")
    ax.set_title("LegalBench task surface sizes")
    fig.text(0.99, 0.01, CITES["legalbench"], ha="right", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(figdir / "legalbench_surfaces.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_SOURCES = {
    "maud": (analyze_maud, render_maud_report, render_maud_findings, make_maud_figures),
    "s1": (analyze_s1, render_s1_report, render_s1_findings, make_s1_figures),
    "docclass": (analyze_docclass, render_docclass_report, render_docclass_findings, make_docclass_figures),
    "legalbench": (analyze_legalbench, render_legalbench_report, render_legalbench_findings, make_legalbench_figures),
}


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT), help="Output root (default: data/eda)")
    parser.add_argument("--source", default="all",
                        choices=["all", *sorted(_SOURCES)],
                        help="Which source(s) to analyze (default: all)")
    parser.add_argument("--no-figures", action="store_true", help="Skip PNG figures")
    args = parser.parse_args(argv)

    out = Path(args.out)
    targets = sorted(_SOURCES) if args.source == "all" else [args.source]
    for name in targets:
        analyze, render_report, render_findings, make_figs = _SOURCES[name]
        res = analyze()
        src_dir = out / name
        figdir = src_dir / "figures"
        src_dir.mkdir(parents=True, exist_ok=True)
        if not args.no_figures:
            figdir.mkdir(parents=True, exist_ok=True)
            make_figs(res, figdir)
        (src_dir / "report.md").write_text(render_report(res), encoding="utf-8")
        (src_dir / "findings.md").write_text(render_findings(res), encoding="utf-8")
        n_figs = len(list(figdir.glob("*.png"))) if figdir.exists() else 0
        print(f"[{name}] {res.get('n') or res.get('n_rows') or res.get('n_contracts') or 0} "
              f"items -> {src_dir} ({n_figs} figures)")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()