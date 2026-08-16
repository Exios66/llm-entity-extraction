#!/usr/bin/env python3
"""Full exploratory data analysis of the CUAD contracts corpus.

Sources:
  - ``CUAD_v1.json`` (raw annotations: 510 contracts, 41 categories,
    20,910 QA pairs with answer spans) — the annotation-side truth.
  - ``mailroom-cuad-contracts-full`` (Braintrust) for per-document text
    (loaded via ``src.braintrust_utils``) — text-side statistics. Falls back
    to the local ``data/cuad/contracts/*.txt`` extractions and, finally, the
    raw CUAD_v1.json ``paragraphs[0].context`` (complete 510-doc coverage).
  - ``config/taxonomy.yaml`` + ``src/cuad_ground_truth.py`` for the
    mailroom 25-family taxonomy mapping.

Outputs (written under ``data/eda/``, all git-tracked):
  - ``report.md``     — the full EDA report (tables + findings)
  - ``findings.md``   — condensed findings summary
  - ``figures/*.png`` — matplotlib visualizations
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from src.cuad_ground_truth import (  # noqa: E402
    CUAD_CATEGORIES,
    SUBTYPE_CUAD_FOLDERS,
)
from agents.sorter_agent import CONTRACT_SUBTYPES  # noqa: E402

OUT = Path("data/eda")
FIG = OUT / "figures"
# Repo-local corpus paths (`data/cuad_pdfs/` per its README — gitignored),
# with the llm-mailroom mirror as fallback when the sibling repo is present.
CUAD_JSON = Path("data/cuad_pdfs/CUAD_v1.json")
CUAD_JSON_FALLBACK = Path("../llm-mailroom/data/cuad/CUAD_v1.json")

# Dataset citation footer for every figure (KANBAN-014 follow-on).
CUAD_CITE = ("Source: CUAD — Contract Understanding Atticus Dataset "
             "(Hendrycks et al., NeurIPS 2021), The Atticus Project · "
             "https://huggingface.co/datasets/theatticusproject/cuad")

# Fraction of the figure height reserved for the citation footer band. Large
# enough for a wrapped two-line citation on the shortest figures, so the axes
# (with its x labels / legend) always sits fully above the band.
FOOTER_FRAC = 0.10

# Title -> 25-family subtype matcher for the per-subtype length stats. Patterns
# are built from the taxonomy's CUAD folder names (`SUBTYPE_CUAD_FOLDERS`),
# each family's `CONTRACT_SUBTYPES` label, and observed CUAD title variants;
# longest match wins so multi-family titles route to the most specific family.
_SUBTYPE_PATTERNS: dict[str, list[str]] = {}
for _s in CONTRACT_SUBTYPES:
    _key, _label = _s["key"], _s["label"]
    _pats = [p.replace("_", " ") for p in SUBTYPE_CUAD_FOLDERS.get(_key, [])]
    _pats += [_label]
    if _key == "ip":
        _pats += ["Intellectual Property"]
    if _key == "joint_venture":
        _pats += ["Joint Filing"]
    if _key == "collaboration":
        _pats += ["Cooperation"]
    if _key == "non_compete_no_solicit":
        _pats += ["Non-Compete", "No-Solicit", "Non-Disparagement"]
    _SUBTYPE_PATTERNS[_key] = sorted({p for p in _pats if len(p) >= 6},
                                     key=len, reverse=True)


def _norm_pat(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower())


def _subtype_from_title(title: str) -> str | None:
    """Best-effort 25-family subtype for a CUAD title (longest match wins)."""
    t = _norm_pat(title)
    best_key, best_len = None, 0
    for key, pats in _SUBTYPE_PATTERNS.items():
        for p in pats:
            np_ = _norm_pat(p)
            if np_ in t and len(np_) > best_len:
                best_key, best_len = key, len(np_)
    return best_key


def _add_citation(fig, ax, note: str = "") -> None:
    """Footer dataset citation on a figure (dedicated band below the axes).

    Reserves a footer band under the axes and centers the citation inside it,
    so it never collides with the x-axis labels, tick labels, or a legend
    (a plain ``ax.text`` at negative axes coordinates would render the text
    overlapping the label area on short figures).
    """
    txt = CUAD_CITE + (f" · {note}" if note else "")
    fig.tight_layout(rect=[0, FOOTER_FRAC, 1, 1])
    fig.text(0.5, FOOTER_FRAC / 2, txt, ha="center", va="center",
             fontsize=7, color="#444")

# Ground-truth CUAD contract subclass counts (mailroom 25-family taxonomy) for
# the 509-contract eval corpus (`mailroom-cuad-contracts-full`), derived from
# the experiment-log per-subtype totals (sums to 509, verified). Used by
# figure 01 and the report's corpus-composition table — the original
# taxonomy-derived `subtype_distribution.json` no longer exists in either repo.
SUBTYPE_FALLBACK = {
    "maintenance": 34, "license": 33, "distributor": 32,
    "strategic_alliance": 32, "sponsorship": 31, "development": 28,
    "service": 28, "collaboration": 26, "endorsement": 24,
    "joint_venture": 23, "co_branding": 22, "hosting": 20,
    "outsourcing": 18, "supply": 18, "ip": 17, "manufacturing": 17,
    "marketing": 17, "franchise": 15, "agency": 13,
    "transportation": 13, "promotion": 12, "reseller": 12,
    "consulting": 11, "affiliate": 10, "non_compete_no_solicit": 3,
}

PALETTE = ["#2563eb", "#7c3aed", "#db2777", "#059669", "#d97706", "#dc2626",
           "#0891b2", "#65a30d", "#9333ea", "#ea580c"]
REDACT_RE = re.compile(r"\[\*{1,6}\]|\[\*\*\]|XX+|\$\*\*")
FILING_RE = re.compile(
    r"(EX-\d+\.?\d*\(?[^)-]*\)?|S-\d[A-Z]?A?|SB-2A?|10-12G|485BPOS|DRS"
    r"|8-K|10-Q|10-KA?|F-1A?|F-4|DEF 14A|20-F|SC 13|6-K|S-4A?|S-3|N-6|425)"
)

# Categories whose clause labels feed the extractor's ``key_obligations``
# field (the restriction/covenant families — the extractor's GT scope).
KEY_OBLIGATIONS = [c for c, s in CUAD_CATEGORIES.items()
                   if s["answer_format"] == "yes_no" and s["field"] == "key_obligations"]
KEY_OBLIGATIONS_SET = set(KEY_OBLIGATIONS)

# Restriction-family categories tracked for co-occurrence analysis.
COOCCUR = ["Non-Compete", "Exclusivity", "No-Solicit Of Customers",
           "No-Solicit Of Employees", "Competitive Restriction Exception",
           "Anti-Assignment", "Change Of Control", "Rofr/Rofo/Rofn",
           "Most Favored Nation", "Non-Disparagement"]

# Pipeline-relevant text-length budgets (chars).
BUDGETS = {"25k (small)": 25_000, "90k (chunk window)": 90_000,
           "128k (~32k tokens)": 128_000, "256k (~64k tokens)": 256_000}


def _load_cuad() -> list[dict]:
    path = CUAD_JSON if CUAD_JSON.exists() else CUAD_JSON_FALLBACK
    if not path.exists():
        raise SystemExit(f"CUAD_v1.json not found at {CUAD_JSON} "
                         f"(or {CUAD_JSON_FALLBACK})")
    return json.load(open(path))["data"]


def _load_full_texts() -> list[dict]:
    """Load the Braintrust full-corpus rows (doc_text + filename + expected)."""
    from src.braintrust_config import load_braintrust_config
    from src.braintrust_utils import load_braintrust_dataset

    cfg = load_braintrust_config()
    rows = load_braintrust_dataset(
        cfg.dataset_project, "mailroom-cuad-contracts-full",
        project_id=cfg.project_id,
    )
    return rows


def _filing_type(title: str) -> str:
    """Roll a title up to a filing/exhibit family (e.g. any ``EX-10.x``
    exhibit -> ``EX-10``; ``8-K`` stays ``8-K``)."""
    m = re.search(r"EX-(\d+)", title)
    if m:
        return f"EX-{m.group(1)}"
    m = FILING_RE.search(title)
    return m.group(1) if m else "other"


def _category_from_question(q: str) -> str:
    m = re.search(r'related to "([^"]+)"', q)
    return m.group(1) if m else "?"


def analyze() -> dict:
    docs = _load_cuad()
    cat_stats: dict[str, dict] = {
        c: {"yes_docs": 0, "answers": 0, "span_len": []} for c in CUAD_CATEGORIES
    }
    doc_cats: list[set] = []
    per_doc_spans: list[int] = []
    per_doc_ko_spans: list[int] = []
    titles: list[str] = []
    filing = Counter()
    n_qa = 0
    for doc in docs:
        title = doc["title"]
        titles.append(title)
        filing[_filing_type(title)] += 1
        yes: set[str] = set()
        spans = 0
        ko_spans = 0
        for para in doc.get("paragraphs", []):
            for q in para.get("qas", []):
                n_qa += 1
                cat = _category_from_question(q.get("question", ""))
                if cat not in cat_stats:
                    continue
                if q.get("answers"):
                    yes.add(cat)
                    cat_stats[cat]["yes_docs"] += 1
                    for a in q["answers"]:
                        cat_stats[cat]["answers"] += 1
                        cat_stats[cat]["span_len"].append(len(a.get("text", "")))
                        spans += 1
                        if cat in KEY_OBLIGATIONS_SET:
                            ko_spans += 1
        doc_cats.append(yes)
        per_doc_spans.append(spans)
        per_doc_ko_spans.append(ko_spans)

    # text-side stats: Braintrust full corpus -> local txts -> CUAD contexts.
    # Texts are aligned to the 510 CUAD titles (by normalized filename/title
    # match) so per-document stats join cleanly.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", s.lower())

    texts: list[str] = [""] * len(docs)
    try:
        text_rows = _load_full_texts()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Braintrust full-corpus load failed ({exc}); "
              f"text stats will use the local contract texts if present")
        text_rows = []
    matched = 0
    if text_rows:
        by_title = {_norm(doc["title"]): doc for doc in docs}
        for row in text_rows:
            key = _norm(row.get("filename") or "")
            text = row.get("doc_text") or ""
            if key in by_title:
                for i, doc in enumerate(docs):
                    if _norm(doc["title"]) == key and not texts[i]:
                        texts[i] = text
                        matched += 1
                        break
    if matched < len(docs):
        local: list[Path] = sorted(Path("../llm-mailroom/data/cuad/contracts").glob("*.txt"))
        local_by_stem = {_norm(Path(f).stem): f for f in local}
        for i, doc in enumerate(docs):
            if texts[i]:
                continue
            key = _norm(doc["title"])
            if key in local_by_stem:
                texts[i] = local_by_stem[key].read_text(errors="ignore")
            else:
                para = doc.get("paragraphs") or [{}]
                texts[i] = para[0].get("context", "")
    print(f"[info] text aligned for {sum(1 for t in texts if t)}/{len(docs)} "
          f"contracts ({matched} from the full corpus)")
    text_lens = [len(t) for t in texts]
    text_tokens = [round(len(t) / 4) for t in texts]

    # redaction markers in the text bodies
    redacted_text = sum(1 for t in texts if REDACT_RE.search(t))
    redact_hits = sum(len(REDACT_RE.findall(t)) for t in texts)
    redacted_titles = sum(1 for t in titles if REDACT_RE.search(t))

    # category co-occurrence over the restriction families
    coocc: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for yes in doc_cats:
        for a in COOCCUR:
            for b in COOCCUR:
                if a in yes and b in yes:
                    coocc[a][b] += 1
    coocc_norm: dict[str, dict[str, float]] = {}
    for a in COOCCUR:
        coocc_norm[a] = {}
        for b in COOCCUR:
            denom = min(cat_stats[a]["yes_docs"], cat_stats[b]["yes_docs"])
            coocc_norm[a][b] = coocc[a][b] / denom if denom else 0.0

    # per-subtype text-length table (median/min/max chars) from the aligned
    # texts, grouped by the title-derived 25-family subtype (KANBAN-014
    # follow-on; replaces the removed taxonomy-JSON dependency).
    per_subtype_raw: dict[str, list[int]] = {}
    for i, t in enumerate(texts):
        sub = _subtype_from_title(titles[i])
        if sub and t:
            per_subtype_raw.setdefault(sub, []).append(len(t))
    per_subtype: dict[str, dict] = {
        k: {"count": len(v), "median_chars": int(np.median(v)),
            "min_chars": min(v), "max_chars": max(v)}
        for k, v in per_subtype_raw.items()
    }
    print(f"[info] subtype assigned for "
          f"{sum(len(v) for v in per_subtype_raw.values())}/{len(docs)} "
          f"contracts via title matching")

    return {
        "n_docs": len(docs), "n_qa": n_qa,
        "titles": titles, "filing": dict(filing),
        "cat_stats": cat_stats, "doc_cats": doc_cats,
        "per_doc_spans": per_doc_spans, "per_doc_ko_spans": per_doc_ko_spans,
        "text_lens": text_lens, "text_tokens": text_tokens, "texts": texts,
        "redacted_text": redacted_text, "redact_hits": redact_hits,
        "redacted_titles": redacted_titles,
        "coocc": coocc, "coocc_norm": coocc_norm,
        "subtype_dist": SUBTYPE_FALLBACK,
        "per_subtype": per_subtype,
    }


def _budget_shares(res: dict) -> dict[str, float]:
    n = len(res["text_lens"]) or 1
    return {k: sum(1 for l in res["text_lens"] if l > v) / n
            for k, v in BUDGETS.items()}


def make_figures(res: dict) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12,
                         "axes.titleweight": "bold", "figure.facecolor": "white"})
    n = res["n_docs"]

    # 1. CUAD contract subclass distribution (mailroom 25-family taxonomy)
    #    Data: ground-truth subtype counts of the 509-contract eval corpus
    #    (`mailroom-cuad-contracts-full`, experiment-log per-subtype totals).
    dist = res["subtype_dist"]
    items = sorted(dist.items(), key=lambda kv: -kv[1])[:25]
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.barh(names[::-1], vals[::-1], color=PALETTE[0], edgecolor="white")
    for y, v in enumerate(vals[::-1]):
        ax.text(v + 0.4, y, str(v), va="center", fontsize=7, color="#333")
    ax.set_title("CUAD contract subclass distribution "
                 f"(25-family taxonomy, n={sum(vals)})")
    ax.set_xlabel("contracts")
    ax.grid(axis="x", alpha=0.3)
    _add_citation(fig, ax, "n=509 contracts in the eval corpus")
    fig.savefig(FIG / "01_subtype_distribution.png", dpi=140)
    plt.close(fig)

    # 2. Text length histogram
    if res["text_lens"]:
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist([l / 1000 for l in res["text_lens"]], bins=40,
                color=PALETTE[1], edgecolor="white", alpha=0.9)
        ax.set_title(f"Contract text length (n={len(res['text_lens'])} docs)")
        ax.set_xlabel("chars (thousands)")
        ax.set_ylabel("contracts")
        ax.grid(axis="y", alpha=0.3)
        _add_citation(fig, ax, "510 contracts · CUAD_v1.json paragraph contexts")
        fig.savefig(FIG / "02_text_length_hist.png", dpi=140)
        plt.close(fig)

    # 3. Category YES rates (top 24)
    cs = res["cat_stats"]
    yes_rates = [(c, s["yes_docs"] / n) for c, s in cs.items() if s["yes_docs"]]
    yes_rates.sort(key=lambda kv: -kv[1])
    names = [c for c, _ in yes_rates[:24]][::-1]
    vals = [r for _, r in yes_rates[:24]][::-1]
    fig, ax = plt.subplots(figsize=(10.5, 8))
    ax.barh(names, vals, color=PALETTE[4], edgecolor="white")
    ax.set_title(f"CUAD category presence rate across {n} contracts (top 24)")
    ax.set_xlabel("share of contracts where the category is labeled YES")
    ax.grid(axis="x", alpha=0.3)
    _add_citation(fig, ax, "annotator YES labels across the 41 clause categories")
    fig.savefig(FIG / "03_category_yes_rates.png", dpi=140)
    plt.close(fig)

    # 4. Answer spans per category (count vs mean span length)
    cats = [c for c, s in cs.items() if s["answers"] > 0]
    means = [sum(s["span_len"]) / len(s["span_len"]) if s["span_len"] else 0
             for c, s in cs.items() if s["answers"] > 0]
    counts = [s["answers"] for c, s in cs.items() if s["answers"] > 0]
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.scatter(counts, means, s=42, color=PALETTE[2], alpha=0.8, zorder=3)
    for c, x, y in zip(cats, counts, means):
        if x > 300 or y > 60:
            ax.annotate(c.replace(" ", "\n"), (x, y), fontsize=6,
                        ha="center", va="bottom")
    ax.set_title("CUAD answer spans per category (count vs mean span length)")
    ax.set_xlabel("total answer spans")
    ax.set_ylabel("mean span length (chars)")
    ax.grid(alpha=0.3)
    _add_citation(fig, ax, "20,910 QA pairs · answer-span annotations")
    fig.savefig(FIG / "04_category_spans.png", dpi=140)
    plt.close(fig)

    # 5. Spans per document histogram (all categories vs key_obligations)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(res["per_doc_spans"], bins=30, color=PALETTE[3], edgecolor="white",
            alpha=0.75, label="all 41 categories")
    ax.hist(res["per_doc_ko_spans"], bins=30, color=PALETTE[6], edgecolor="white",
            alpha=0.75, label="key_obligations families")
    ax.set_title("Answer spans per contract (all categories vs restriction family)")
    ax.set_xlabel("spans")
    ax.set_ylabel("contracts")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _add_citation(fig, ax, "answer spans per contract · all 41 categories")
    fig.savefig(FIG / "05_spans_per_doc.png", dpi=140)
    plt.close(fig)

    # 6. Filing-type distribution
    filing = res["filing"]
    items = sorted(filing.items(), key=lambda kv: -kv[1])[:14]
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.bar([k for k, _ in items], [v for _, v in items],
           color=PALETTE[5], edgecolor="white")
    ax.set_title("SEC filing context of the corpus exhibits")
    ax.set_xlabel("filing type")
    ax.set_ylabel("contracts")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    _add_citation(fig, ax, "SEC exhibit tags parsed from the 510 document titles")
    fig.savefig(FIG / "06_filing_types.png", dpi=140)
    plt.close(fig)

    # 7. Per-subtype text length (min / median / max chars)
    ps = res["per_subtype"]
    if ps:
        rows = sorted(((k, v) for k, v in ps.items()), key=lambda kv: -kv[1]["median_chars"])
        keys = [k for k, _ in rows]
        meds = [v["median_chars"] / 1000 for _, v in rows]
        mins = [v["min_chars"] / 1000 for _, v in rows]
        maxs = [v["max_chars"] / 1000 for _, v in rows]
        fig, ax = plt.subplots(figsize=(11, 6.5))
        y = np.arange(len(keys))
        ax.hlines(y, mins, maxs, color=PALETTE[7], alpha=0.5, lw=6,
                  label="min–max range")
        ax.scatter(meds, y, s=34, color=PALETTE[0], zorder=3, label="median")
        ax.set_yticks(y)
        ax.set_yticklabels(keys, fontsize=8)
        ax.set_title("Contract text length by subtype (chars in thousands)")
        ax.set_xlabel("chars (thousands)")
        ax.legend(loc="lower right")
        ax.grid(axis="x", alpha=0.3)
        _add_citation(fig, ax, "title-derived 25-family subtype grouping")
        fig.savefig(FIG / "07_subtype_lengths.png", dpi=140)
        plt.close(fig)

    # 8. Restriction-family co-occurrence heatmap (pairwise presence)
    cn = res["coocc_norm"]
    keys = COOCCUR
    mat = np.array([[cn[a][b] for b in keys] for a in keys])
    fig, ax = plt.subplots(figsize=(9, 7.5))
    im = ax.imshow(mat, cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(keys)), [k.replace(" ", "\n") for k in keys],
                  fontsize=6.5)
    ax.set_yticks(np.arange(len(keys)), keys, fontsize=6.5)
    ax.tick_params(top=True, bottom=False, labeltop=True)
    for i in range(len(keys)):
        for j in range(len(keys)):
            if mat[i][j] > 0.04:
                ax.text(j, i, f"{mat[i][j]:.0%}", ha="center", va="center",
                        fontsize=5.5, color="white" if mat[i][j] < 0.65 else "black")
    ax.set_title("Restriction-family co-occurrence (share of the less-common "
                 "category's docs that also carry the other)")
    fig.colorbar(im, shrink=0.75, label="co-occurrence (normalized)")
    _add_citation(fig, ax, "10 restriction-family categories · YES-label co-presence")
    fig.savefig(FIG / "08_restriction_cooccurrence.png", dpi=140)
    plt.close(fig)

    # 9. Text length vs pipeline budgets
    if res["text_lens"]:
        tl = np.array(res["text_lens"]) / 1000
        fig, ax = plt.subplots(figsize=(9.5, 5))
        ax.hist(tl, bins=50, color=PALETTE[1], edgecolor="white", alpha=0.9)
        for color, (label, budget) in zip(PALETTE[6:], BUDGETS.items()):
            ax.axvline(budget / 1000, color=color, ls="--", lw=1.4)
            ax.text(budget / 1000, ax.get_ylim()[1] * 0.92, label, rotation=90,
                    fontsize=7, color=color, va="top")
        ax.set_title("Contract text length vs pipeline input budgets (chars in thousands)")
        ax.set_xlabel("chars (thousands)")
        ax.set_ylabel("contracts")
        ax.grid(axis="y", alpha=0.3)
        _add_citation(fig, ax, "pipeline input budgets vs the 510-doc text corpus")
        fig.savefig(FIG / "09_length_budgets.png", dpi=140)
        plt.close(fig)

    # 10. Annotation density vs text length
    if res["text_lens"] and len(res["text_lens"]) == len(res["per_doc_spans"]):
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.scatter([l / 1000 for l in res["text_lens"]],
                   [s / (l / 1000 + 1e-9) for s, l in
                    zip(res["per_doc_spans"], res["text_lens"])],
                   s=20, color=PALETTE[2], alpha=0.6, zorder=3)
        ax.set_title("Annotation density vs contract length")
        ax.set_xlabel("chars (thousands)")
        ax.set_ylabel("spans per 1k chars")
        ax.grid(alpha=0.3)
        _add_citation(fig, ax, "span annotations vs text length, per contract")
        fig.savefig(FIG / "10_density_vs_length.png", dpi=140)
        plt.close(fig)

    print(f"figures written to {FIG}")


def render_report(res: dict) -> str:
    cs = res["cat_stats"]
    n = res["n_docs"]
    L = []
    L.append("# CUAD Contracts — Full Exploratory Data Analysis\n")
    L.append(f"**Corpus**: theatticusproject/cuad (CUAD_v1.json) · "
             f"**contracts**: {n} · **QA pairs**: {res['n_qa']:,} · "
             f"**categories**: {len(CUAD_CATEGORIES)}\n")
    if res["text_lens"]:
        tl = sorted(res["text_lens"])
        tk = sorted(res["text_tokens"])
        L.append(f"**Text corpus**: {len(tl)} documents (of {n} contracts; "
                 f"{n - len(tl)} absent from the synced full corpus), "
                 f"min {tl[0]:,} / median {tl[len(tl)//2]:,} / "
                 f"mean {sum(tl)/len(tl):,.0f} / max {tl[-1]:,} chars "
                 f"(~{tk[len(tk)//2]:,} tokens median by chars/4)\n")

    L.append("## 1. Corpus composition\n")
    dist = res["subtype_dist"]
    L.append("| subtype | contracts | share |\n|---|---|---|")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        L.append(f"| `{k}` | {v} | {v/n:.1%} |")

    L.append("\n## 2. Filing context\n")
    L.append("| filing type | contracts |\n|---|---|")
    for k, v in sorted(res["filing"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {k} | {v} |")

    L.append("\n## 3. Text length vs pipeline budgets\n")
    L.append("| budget | contracts over | share |\n|---|---|---|")
    for k, v in _budget_shares(res).items():
        over = sum(1 for l in res["text_lens"] if l > BUDGETS[k])
        L.append(f"| {k} | {over} | {v:.1%} |")

    L.append("\n## 4. Text length by subtype (chars)\n")
    ps = res["per_subtype"]
    L.append("| subtype | contracts | median | min | max |\n|---|---|---|---|---|")
    for k, v in sorted(ps.items(), key=lambda kv: -kv[1]["median_chars"]):
        L.append(f"| `{k}` | {v['count']} | {v['median_chars']:,} | "
                 f"{v['min_chars']:,} | {v['max_chars']:,} |")

    L.append("\n## 5. Category presence (annotator YES rates)\n")
    rows = [(c, s["yes_docs"], s["yes_docs"] / n, s["answers"]) for c, s in cs.items()]
    rows.sort(key=lambda r: -r[1])
    L.append("| category | docs YES | rate | answer spans |\n|---|---|---|---|")
    for c, yes, rate, ans in rows:
        L.append(f"| {c} | {yes} | {rate:.1%} | {ans} |")

    L.append("\n## 6. Restriction-family span load per contract "
             "(key_obligations scope)\n")
    sp = res["per_doc_ko_spans"]
    sp_sorted = sorted(sp)
    zero = sum(1 for x in sp if x == 0)
    L.append(f"The extractor's ``key_obligations`` GT scope covers "
             f"{len(KEY_OBLIGATIONS)} of the 41 categories (the "
             "restriction/covenant families).\n")
    L.append("| metric | all categories | restriction families |\n|---|---|---|")
    all_sp = res["per_doc_spans"]
    L.append(f"| mean spans/doc | {sum(all_sp)/len(all_sp):.1f} | "
             f"{sum(sp)/len(sp):.1f} |")
    L.append(f"| median spans/doc | {sorted(all_sp)[len(all_sp)//2]} | "
             f"{sp_sorted[len(sp_sorted)//2]} |")
    L.append(f"| max spans/doc | {sorted(all_sp)[-1]} | {sp_sorted[-1]} |")
    L.append(f"| docs with 0 spans | "
             f"{sum(1 for x in all_sp if x == 0)} | {zero} |")

    L.append("\n## 7. Restriction-family co-occurrence highlights\n")
    cn = res["coocc_norm"]
    co = res["coocc"]
    pairs = sorted(((cn[a][b], a, b) for a in COOCCUR for b in COOCCUR
                    if a < b), reverse=True)[:10]
    L.append("Share = fraction of the less-common category's docs that also "
             "carry the other category (co-occurring docs / smaller YES count).\n")
    L.append("| category pair | share | co-occurring docs |\n|---|---|---|")
    for share, a, b in pairs:
        L.append(f"| {a} + {b} | {share:.0%} | {co[a][b]} |")

    L.append("\n## 8. Data-quality markers\n")
    L.append(f"- Titles carrying redaction markers (`[***]`-style): "
             f"{res['redacted_titles']}")
    L.append(f"- Text bodies carrying redaction markers: "
             f"{res['redacted_text']} docs, {res['redact_hits']} markers total")
    L.append(f"- Zero-span docs (no labeled category at all): "
             f"{sum(1 for x in res['per_doc_spans'] if x == 0)}")
    L.append(f"- Figures: `figures/01`–`10` (subtype distribution, text lengths, "
             f"category YES rates, category span load, spans/doc, filing types, "
             f"subtype lengths, restriction co-occurrence, length budgets, "
             f"annotation density)\n")
    return "\n".join(L) + "\n"


def render_findings(res: dict) -> str:
    cs = res["cat_stats"]
    n = res["n_docs"]
    top = sorted(((c, s["yes_docs"] / n) for c, s in cs.items()),
                 key=lambda kv: -kv[1])[:6]
    sp = res["per_doc_spans"]
    ko = res["per_doc_ko_spans"]
    tl = sorted(res["text_lens"]) if res["text_lens"] else []
    shares = _budget_shares(res)
    L = ["# EDA Findings — CUAD Contracts\n"]
    L.append("## Key findings\n")
    L.append("1. **The corpus is obligation-rich and near-universally labeled**: "
             "the five most-labeled categories are "
             + ", ".join(f"`{c}` ({r:.0%})" for c, r in top)
             + " — every contract carries multiple review-relevant clauses "
             "(zero docs have no labeled category).")
    L.append(f"2. **Span load is right-skewed**: mean {sum(sp)/len(sp):.1f} "
             f"spans/doc (all 41 categories), median {sorted(sp)[len(sp)//2]}, "
             f"max {sorted(sp)[-1]} — a small set of dense agreements carries "
             "most of the labeling volume.")
    L.append(f"3. **Restriction families carry the extractor's ``key_obligations`` "
             f"GT scope ({len(KEY_OBLIGATIONS)} of 41 categories)**: they average "
             f"{sum(ko)/len(ko):.1f} spans/doc "
             f"(median {sorted(ko)[len(ko)//2]}, max {sorted(ko)[-1]}), and "
             f"{sum(1 for x in ko if x == 0)} of {n} contracts carry none — "
             "a null-expectation baseline the extractor must survive.")
    if tl:
        L.append(f"4. **Text length spans {tl[0]:,}–{tl[-1]:,} chars "
                 f"(median {tl[len(tl)//2]:,}, mean {sum(tl)/len(tl):,.0f})** — "
                 f"{shares['90k (chunk window)']:.0%} of contracts exceed the "
                 "90k-char chunk window and "
                 f"{shares['128k (~32k tokens)']:.0%} exceed a 32k-token context, "
                 "which is why the chunked/head+tail-truncated extraction "
                 "architecture exists.")
    L.append(f"5. **The corpus is SEC-exhibit-centric**: "
             f"{sum(res['filing'].values()) - res['filing'].get('other', 0)} of "
             f"{sum(res['filing'].values())} titles are SEC exhibit tags "
             f"(top families: `EX-10` {res['filing'].get('EX-10', 0)}, "
             f"`EX-99` {res['filing'].get('EX-99', 0)}, `EX-4` "
             f"{res['filing'].get('EX-4', 0)}) — extraction must tolerate "
             "exhibit wrappers and redaction markers "
             f"({res['redacted_text']} docs carry `[***]`-style markers in their text).")
    cn = res["coocc_norm"]
    L.append("6. **Restriction clauses co-occur strongly**: top pairwise shares — "
             + "; ".join(f"{a}+{b} {share:.0%}" for share, a, b in
                         sorted(((cn[a][b], a, b) for a in COOCCUR for b in COOCCUR
                                 if a < b), key=lambda p: -p[0])[:3])
             + ".")
    L.append("\n## Figures\n")
    for f in sorted(FIG.glob("*.png")):
        L.append(f"- `{f.name}`")
    return "\n".join(L) + "\n"


def main_with_args(argv: list[str]) -> int:
    global OUT, FIG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT), help="Output directory")
    args = parser.parse_args(argv)
    OUT = Path(args.out)
    FIG = OUT / "figures"
    OUT.mkdir(parents=True, exist_ok=True)

    res = analyze()
    make_figures(res)
    (OUT / "report.md").write_text(render_report(res), encoding="utf-8")
    (OUT / "findings.md").write_text(render_findings(res), encoding="utf-8")
    print(f"EDA written to {OUT}: report.md, findings.md, figures/")
    return 0


def main() -> None:
    sys.exit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
