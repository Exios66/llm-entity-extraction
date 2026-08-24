#!/usr/bin/env python3
"""Build the full LegalBench pack for HF publishing (KANBAN-071).

Fetches EVERY task directory from HazyResearch/legalbench (CC BY 4.0) and
stages, under ``data/hf_export/legalbench_full/``::

    tasks/<task>/train.tsv            # verbatim upstream bytes
    tasks/<task>/train.enriched.jsonl # row-level records + CUAD enrichment
    tasks/<task>/test.tsv             # verbatim (when present)
    tasks/<task>/test.enriched.jsonl  # (when present)
    tasks/<task>/base_prompt.txt      # verbatim (when present)
    tasks/<task>/README.md            # verbatim
    index.jsonl                       # one record per task (types, counts)
    ENRICHMENT_REPORT.json            # cuad_* join statistics (honest gaps)

CUAD enrichment (human directive 2026-08-22: raise LegalBench contract-row
labels to CUAD-dataset quality): for every ``cuad_*`` row we locate the
excerpt inside the source contract (CUAD_v1.json ``context``) with a
whitespace-flexible regex, then attach every expert QA annotation whose
highlighted answer span overlaps that region — giving each row its clause
category (CUAD question), expert answer span, char offsets, and contract
identity. Original TSVs stay byte-verbatim; enrichment lives beside them.

Usage:
    .venv/bin/python scripts/datasets/build_legalbench_full_pack.py
    .venv/bin/python scripts/datasets/build_legalbench_full_pack.py --tasks cuad_expiration_date,hearsay
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import io
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

# KANBAN-088: shared JSONL line-boundary safety (Hub worker splits rows on
# U+2028/U+2029/NEL; see scripts/datasets/_jsonl_safety.py).
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from scripts.datasets._jsonl_safety import safe_jsonl_line

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.datasets.stream_legalbench_tasks_to_bt import (  # noqa: E402
    fetch_task_file,
    list_task_dirs,
    task_type_from_readme,
    valid_classes_for,
)

OUT_DIR = REPO_ROOT / "data" / "hf_export" / "legalbench_full"
CUAD_JSON = REPO_ROOT / "data" / "cuad_pdfs" / "CUAD_v1.json"
REQUEST_SLEEP = 0.15


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def contract_key(s: str) -> str:
    """Normalize a CUAD contract title / LB document_name to a join key.

    LB carries a trailing ``.PDF``; CUAD_v1.json titles don't. Casefold
    FIRST, then strip the extension (a case-sensitive pre-strip misses it).
    """
    return re.sub(r"\.pdf$", "", norm(s))


def task_category(task: str) -> str:
    """``cuad_expiration_date`` -> ``expiration date`` (category key).

    Underscores become spaces (they separate words in task names); hyphens
    stay, because they occur *inside* category names ("Affiliate
    License-Licensee") exactly as the CUAD questions quote them.
    """
    return norm(task[len("cuad_"):].replace("_", " ")) if task.startswith("cuad_") else ""


QUOTED_CATEGORY = re.compile(r'"([^"]+)"')


def question_category(question: str) -> str:
    """Extract the quoted category from a CUAD question, normalized."""
    m = QUOTED_CATEGORY.search(question)
    return norm(m.group(1)) if m else ""


def load_cuad_contracts() -> dict[str, dict]:
    """Map normalized contract title -> context + QA annotations."""
    raw = json.loads(CUAD_JSON.read_text(encoding="utf-8"))
    contracts: dict[str, dict] = {}
    for block in raw.get("data", []):
        title = contract_key(block.get("title", ""))
        paras = block.get("paragraphs") or []
        context = "\n\n".join(p.get("context", "") for p in paras)
        qas = []
        for p in paras:
            for qa in p.get("qas") or []:
                answers = [
                    {"text": a.get("text", ""), "answer_start": a.get("answer_start", -1)}
                    for a in qa.get("answers") or []
                ]
                qas.append({"question": qa.get("question", ""), "answers": answers})
        contracts[title] = {"context": context, "qas": qas}
    return contracts


def flex_pattern(excerpt: str) -> re.Pattern:
    """Whitespace-flexible literal pattern for locating an excerpt."""
    parts = [re.escape(tok) for tok in excerpt.split()]
    return re.compile(r"\s+".join(parts) if parts else r".^", re.IGNORECASE | re.DOTALL)


def enrich_row(row: dict, contract: dict | None, task: str = "") -> dict:
    """Attach CUAD expert annotations to one LB cuad_* row.

    When the row's task maps to a CUAD category (``cuad_<category>``), the
    row's Yes/No answer is cross-audited against CUAD's own annotations for
    that category: LB ``Yes`` should coincide with an expert-highlighted
    span, ``No`` with its absence. Mismatches are flagged, never rewritten —
    the original answer stays untouched and both records ship.
    """
    out = dict(row)
    enr: dict = {"source": "CUAD_v1.json", "match_status": "no_contract"}
    out["enrichment"] = enr
    category = task_category(task)
    if not contract:
        enr["match_status"] = "unknown_contract"
        return out
    ctx = contract["context"]
    pat = flex_pattern(row.get("text", ""))
    m = pat.search(ctx)
    if not m:
        # fuzzy fallback: best-matching window of similar length
        target = norm(row.get("text", ""))[:120]
        window = max(len(row.get("text", "")), 64)
        best, best_score = None, 0.0
        step = max(window // 2, 32)
        for start in range(0, max(len(ctx) - window, 1), step):
            score = difflib.SequenceMatcher(
                None, target, norm(ctx[start:start + window])[:len(target)] or " "
            ).ratio()
            if score > best_score:
                best, best_score = start, score
        if best is None or best_score < 0.75:
            enr["match_status"] = "span_unmatched"
            return out
        enr.update(match_status="fuzzy", char_start=best, char_end=best + window,
                   fuzzy_score=round(best_score, 4))
        lo, hi = best, best + window
    else:
        enr.update(match_status="exact", char_start=m.start(), char_end=m.end())
        lo, hi = m.start(), m.end()

    hits = []
    for qa in contract["qas"]:
        overlapping = []
        max_overlap = 0
        for ans in qa["answers"]:
            a_lo = ans["answer_start"]
            a_hi = a_lo + len(ans["text"])
            o = max(0, min(hi, a_hi) - max(lo, a_lo))
            if o > 0:
                overlapping.append({"text": ans["text"], "answer_start": a_lo})
                max_overlap = max(max_overlap, o)
        if overlapping:
            hits.append((max_overlap, qa["question"], overlapping))
    hits.sort(key=lambda h: -h[0])
    enr["num_clause_annotations"] = len(hits)
    if hits:
        enr["primary_clause_question"] = hits[0][1]
        enr["clause_questions"] = [{"question": q,
                                    "expert_answer_spans": spans}
                                   for _, q, spans in hits]
        enr.setdefault("match_status", "exact")
    else:
        # negative rows legitimately lack a highlighted span; contract still known
        enr.setdefault("match_status", "exact_no_overlapping_annotation")

    # --- cross-audit: LB's Yes/No vs CUAD's expert highlights ON THE EXCERPT.
    # These tasks classify excerpts ("is THIS clause about <category>?"), so
    # agreement is judged by whether an expert-highlighted span for the task's
    # category overlaps THIS excerpt — contract-level span counts elsewhere are
    # context only (a No row from a contract that has the category in a
    # different clause is a normal negative example). Flagged, never rewritten.
    if category:
        cat_qas = [qa for qa in contract["qas"]
                   if question_category(qa["question"]) == category]
        cat_spans = [{"question": qa["question"],
                      "spans": [{"text": a["text"], "answer_start": a["answer_start"]}
                                for a in qa["answers"]]}
                     for qa in cat_qas]
        cat_spans = [c for c in cat_spans if c["spans"]]
        has_span_contract = bool(cat_spans)
        lo, hi = enr.get("char_start"), enr.get("char_end")
        if has_span_contract and lo is not None and hi is not None:
            overlaps = any(
                max(0, min(hi, s["answer_start"] + len(s["text"])) - max(lo, s["answer_start"])) > 0
                for c in cat_spans for s in c["spans"])
        else:
            overlaps = False
        answer = str(row.get("answer") or "").strip().casefold()
        audit = {
            "category": category,
            "lb_answer": answer,
            "span_overlaps_excerpt": bool(overlaps),
            "num_category_spans_in_contract": sum(len(c["spans"]) for c in cat_spans),
        }
        if answer not in ("yes", "no"):
            audit.update(status="skipped_non_binary")
        elif answer == "yes" and overlaps:
            audit.update(status="agree",
                         note="LB Yes confirmed: expert-highlighted span overlaps this excerpt")
        elif answer == "yes":
            audit.update(status="SUSPECT",
                         note=("LB says Yes but the expert spans for this category sit "
                               "elsewhere in the contract, not on this excerpt"))
        elif overlaps:
            audit.update(status="MISMATCH",
                         note=("CUAD experts highlighted a span for this category inside "
                               "this excerpt but LB labels it No"))
        else:
            audit.update(status="agree",
                         note="LB No consistent: no expert span for this category on this excerpt")
        enr["category_audit"] = audit
    return out


def parse_tsv(raw: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw), delimiter="\t")
    return [dict(r) for r in reader]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="",
                        help="comma-separated subset (default: every task dir)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("loading CUAD_v1.json for enrichment ...", flush=True)
    contracts = load_cuad_contracts() if CUAD_JSON.exists() else {}
    print(f"  {len(contracts)} contracts indexed")

    wanted = {t.strip() for t in args.tasks.split(",")} if args.tasks else None
    all_dirs = list_task_dirs()
    tasks = [t for t in all_dirs if wanted is None or t in wanted]
    print(f"{len(tasks)} tasks to fetch (of {len(all_dirs)} dirs)")

    index_rows, report = [], {"tasks": {}, "totals": Counter()}
    for i, task in enumerate(tasks, 1):
        tdir = OUT_DIR / "tasks" / task
        tdir.mkdir(parents=True, exist_ok=True)
        rec: dict = {"task": task}

        train_raw = fetch_task_file(task, "train.tsv")
        if not train_raw.strip():
            (tdir / "EMPTY").touch()
            rec.update(rows_train=0, note="no train.tsv upstream")
            index_rows.append(rec)
            continue
        (tdir / "train.tsv").write_bytes(train_raw.encode("utf-8"))

        readme = fetch_task_file(task, "README.md")
        (tdir / "README.md").write_bytes(readme.encode("utf-8"))
        prompt = fetch_task_file(task, "base_prompt.txt")
        if prompt:
            (tdir / "base_prompt.txt").write_bytes(prompt.encode("utf-8"))
        test_raw = fetch_task_file(task, "test.tsv")

        rows = parse_tsv(train_raw)
        ttype = task_type_from_readme(readme)
        rec.update(task_type=ttype,
                   valid_classes=valid_classes_for(rows, ttype),
                   rows_train=len(rows),
                   train_sha256=sha256_bytes(train_raw.encode("utf-8")))

        if test_raw.strip():
            (tdir / "test.tsv").write_bytes(test_raw.encode("utf-8"))
            rec["rows_test"] = len(parse_tsv(test_raw))
            rec["test_sha256"] = sha256_bytes(test_raw.encode("utf-8"))

        stats = Counter()
        if task.startswith("cuad_"):
            for split, split_rows, out_name in (
                ("train", rows, "train"),
                ("test", parse_tsv(test_raw) if test_raw.strip() else [], "test"),
            ):
                if not split_rows:
                    continue
                enriched = []
                for r in split_rows:
                    key = contract_key(r.get("document_name", ""))
                    res = enrich_row(r, contracts.get(key), task=task)
                    if key not in contracts:
                        stats[f"{split}_unknown_contract"] += 1
                    else:
                        stats[f"{split}_{res['enrichment']['match_status']}"] += 1
                        audit = res["enrichment"].get("category_audit") or {}
                        if audit.get("status") in ("agree", "MISMATCH", "SUSPECT"):
                            stats[f"{split}_audit_{audit['status'].lower()}"] += 1
                    enriched.append(res)
                (tdir / f"{out_name}.enriched.jsonl").write_text(
                    "".join(safe_jsonl_line(e) + "\n" for e in enriched),
                    encoding="utf-8")
            rec["enrichment_stats"] = dict(stats)
            report["tasks"][task] = dict(stats)
            report["totals"].update(stats)

        index_rows.append(rec)
        print(f"[{i}/{len(tasks)}] {task}: train={rec['rows_train']}"
              f"{' test=' + str(rec['rows_test']) if 'rows_test' in rec else ''}"
              f"{' ' + json.dumps(rec['enrichment_stats']) if 'enrichment_stats' in rec else ''}",
              flush=True)
        time.sleep(REQUEST_SLEEP)

    (OUT_DIR / "index.jsonl").write_text(
        "".join(safe_jsonl_line(r) + "\n" for r in index_rows),
        encoding="utf-8")
    report["totals"] = dict(report["totals"])
    report["cuad_json_source"] = str(CUAD_JSON)
    report["contracts_indexed"] = len(contracts)
    (OUT_DIR / "ENRICHMENT_REPORT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print("\nDONE:", OUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
