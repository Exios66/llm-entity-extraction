#!/usr/bin/env python3
"""Build the joint Monte Carlo corpus from the experiment log + manifests.

Aggregates every scored row from ``reports/experiment_log.jsonl`` (per-row
``results`` for the sorter/subtype/docclass/chained tasks) and enriches it with
the richer per-row records from ``data/manifests/*.jsonl`` (which carry the
full reasoning + predicted dicts for runs whose log rows are score-only). The
output is one flat JSONL per (run, document):

``{task, experiment_name, model, prompt_version, dataset, temperature,
reasoning_effort, tracing_backend, filename, predicted, expected, correct,
confidence, reasoning, failure_mode, status, error, tokens, cost_usd}``

The corpus is the single input to the ``monte_carlo_*`` scripts; it embeds
reasoning traces, so it is gitignored (``reports/monte_carlo/``) and rebuilt
idempotently with ``--rebuild``. A ``corpus-summary.md`` (tracked) records the
surface composition for the site/reports.

Usage:
    python scripts/reporting/monte_carlo_corpus.py
    python scripts/reporting/monte_carlo_corpus.py --rebuild
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monte_carlo import task_label_vocabulary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_LOG = ROOT / "reports" / "experiment_log.jsonl"
MANIFESTS_DIR = ROOT / "data" / "manifests"
OUT_DIR = ROOT / "reports" / "monte_carlo"
CORPUS_PATH = OUT_DIR / "corpus.jsonl"
SUMMARY_PATH = OUT_DIR / "corpus-summary.md"

# Tasks whose per-row records carry a single predicted label + reasoning (the
# classification surfaces the Monte Carlo scenarios reason about).
_LABEL_TASKS = {"subtype_classification", "docclass_classification",
                "sorter_classification", "chained_sorter_extractor"}


def _log_rows(record: dict) -> list[dict]:
    """Per-row results of an experiment-log record (normalized)."""
    return record.get("results") or []


def _extract_sorter_dict(row: dict) -> dict | None:
    """The sorter prediction dict (subtype/docclass/chained rows)."""
    sorter = row.get("sorter") or {}
    if not isinstance(sorter, dict):
        return None
    return sorter


def normalize_log_row(record: dict, row: dict, manifest_override: dict | None = None,
                         prompt_version: str = "") -> dict | None:
    """Normalize one experiment-log row into a flat corpus record.

    ``manifest_override`` (when given) is the richer manifest row for the same
    (experiment, filename) — its reasoning/confidence win over the log's.
    """
    task = record.get("task") or ""
    filename = row.get("filename") or ""
    if not filename:
        return None
    status = row.get("status") or "completed"
    error = row.get("error")
    params = record.get("parameters") or {}
    prompt_version = (prompt_version
                      or record.get("prompt_version")
                      or params.get("sorter_prompt_version")
                      or params.get("extractor_prompt_version") or "")
    dataset = params.get("dataset") or (record.get("data_source") or {}).get("project") or ""

    sorter = _extract_sorter_dict(row)
    manifest_sorter = None
    if manifest_override and isinstance(manifest_override.get("scores"), dict):
        manifest_sorter = (manifest_override.get("scores") or {}).get("composite", {}).get("sorter")
    if manifest_sorter is None and manifest_override:
        manifest_sorter = manifest_override.get("sorter")

    if task in _LABEL_TASKS and sorter is not None:
        if task == "docclass_classification":
            predicted = sorter.get("doc_type") or ""
            expected = sorter.get("expected_doc_type") or ""
        elif task == "sorter_classification":
            predicted = sorter.get("doc_type") or ""
            expected = sorter.get("expected_doc_type") or ""
        else:
            predicted = sorter.get("contract_subtype") or sorter.get("doc_type") or ""
            expected = sorter.get("expected_subtype") or sorter.get("expected_doc_type") or ""
        confidence = sorter.get("confidence")
        reasoning = sorter.get("reasoning")
        failure_mode = sorter.get("failure_mode")
        if manifest_sorter:
            confidence = manifest_sorter.get("confidence", confidence)
            reasoning = manifest_sorter.get("reasoning", reasoning)
            failure_mode = manifest_sorter.get("failure_mode", failure_mode)
            if task == "docclass_classification":
                predicted = manifest_sorter.get("doc_type") or predicted
                expected = manifest_sorter.get("expected_doc_type") or expected
            else:
                predicted = (manifest_sorter.get("contract_subtype")
                             or manifest_sorter.get("doc_type") or predicted)
                expected = (manifest_sorter.get("expected_subtype")
                            or manifest_sorter.get("expected_doc_type") or expected)
        correct = (predicted or "") == (expected or "")
        record_out = {
            "task": task, "experiment_name": record.get("experiment_name") or "",
            "model": record.get("model") or "", "prompt_version": prompt_version,
            "dataset": dataset,
            "temperature": params.get("temperature"),
            "reasoning_effort": params.get("reasoning_effort"),
            "tracing_backend": params.get("tracing_backend"),
            "filename": filename, "predicted": predicted or "", "expected": expected or "",
            "correct": bool(correct), "confidence": confidence,
            "reasoning": reasoning or "", "failure_mode": failure_mode,
            "status": status, "error": error if error else "",
            "tokens": row.get("sorter_tokens") or row.get("tokens") or {},
            "cost_usd": None,
        }
        return record_out

    if task == "sorter_classification" and row.get("predicted"):
        # Flat rows (predicted/correct at row level) — e.g. non-langfuse runs.
        predicted = row.get("predicted") or ""
        expected = row.get("expected") or ""
        return {
            "task": task, "experiment_name": record.get("experiment_name") or "",
            "model": record.get("model") or "", "prompt_version": prompt_version,
            "dataset": dataset,
            "temperature": params.get("temperature"),
            "reasoning_effort": params.get("reasoning_effort"),
            "tracing_backend": params.get("tracing_backend"),
            "filename": filename, "predicted": predicted or "", "expected": expected or "",
            "correct": bool(row.get("correct", predicted == expected)),
            "confidence": None, "reasoning": "", "failure_mode": None,
            "status": status, "error": error if error else "",
            "tokens": row.get("tokens") or {}, "cost_usd": row.get("cost_usd"),
        }

    return None  # non-label tasks are skipped by the classification scenarios


def _manifest_rows_by_experiment() -> tuple[dict[str, dict[str, dict]], dict[str, dict]]:
    """(rows_by_experiment, headers_by_experiment) from every manifest checkpoint.

    ``rows_by_experiment[exp] = {filename: last row}`` (append-only checkpoints:
    last state per filename is authoritative); ``headers_by_experiment[exp]`` is
    the run header metadata (the authoritative prompt-version / dataset source
    when the experiment-log record omits them).
    """
    if not MANIFESTS_DIR.exists():
        return {}, {}
    rows_out: dict[str, dict[str, dict]] = {}
    headers_out: dict[str, dict] = {}
    for path in sorted(MANIFESTS_DIR.glob("*.jsonl")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue
        try:
            header = json.loads(lines[0])
        except json.JSONDecodeError:
            continue
        meta = header.get("metadata") or {}
        experiment = (meta.get("experiment_name")
                      or header.get("experiment_name") or path.stem)
        headers_out.setdefault(experiment, {}).update(meta)
        final: dict[str, dict] = {}
        for line in lines[1:]:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("type") == "header":
                continue
            final[row.get("filename") or ""] = row
        if experiment and final:
            rows_out.setdefault(experiment, {}).update(final)
    return rows_out, headers_out


def _prompt_version_from_name(experiment_name: str) -> str:
    """Best-effort prompt version from the run name (``{model}_{prompt}_task``)."""
    import re

    patterns = [
        r"(sorter_docclass_v\d+)", r"(sorter_v\d+)", r"(contracts_specialist_v\d+)",
        r"(legalbench_task_v\d+(?:_[a-z0-9]+)*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, experiment_name or "")
        if match:
            return match.group(1)
    return ""


def build_corpus() -> list[dict]:
    if not EXPERIMENT_LOG.exists():
        raise FileNotFoundError(f"experiment log not found: {EXPERIMENT_LOG}")
    manifest_by_exp, headers_by_exp = _manifest_rows_by_experiment()
    records = [json.loads(line) for line in EXPERIMENT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    out: list[dict] = []
    n_manifest_enriched = 0
    for record in records:
        task = record.get("task") or ""
        exp = record.get("experiment_name") or ""
        manifest_rows = manifest_by_exp.get(exp, {})
        header_meta = headers_by_exp.get(exp, {})
        prompt_version = (record.get("prompt_version")
                          or header_meta.get("sorter_prompt_version")
                          or header_meta.get("extractor_prompt_version")
                          or header_meta.get("prompt_version")
                          or _prompt_version_from_name(exp))
        for row in _log_rows(record):
            override = manifest_rows.get(row.get("filename") or "")
            normalized = normalize_log_row(record, row, override, prompt_version)
            if normalized is None:
                continue
            if override:
                n_manifest_enriched += 1
            out.append(normalized)
    return out


def render_summary(corpus: list[dict]) -> str:
    rows = [r for r in corpus if r["status"] == "completed"]
    L = ["# Monte Carlo corpus summary", ""]
    L.append(f"_Derived by `scripts/reporting/monte_carlo_corpus.py` from "
             f"`reports/experiment_log.jsonl` + `data/manifests/*.jsonl`_")
    L.append("")
    L.append(f"**{len(corpus)} scored rows** ({(len(corpus) - len(rows))} non-completed) "
             f"across **{len({r['experiment_name'] for r in corpus})} runs**.")
    L.append("")
    by_task = Counter(r["task"] for r in rows)
    L.append("## Rows by task")
    L.append("")
    L.append("| task | rows |")
    L.append("|---|---|")
    for task, n in by_task.most_common():
        L.append(f"| {task} | {n:,} |")
    L.append("")
    by_model = Counter(r["model"] for r in rows)
    L.append("## Rows by model")
    L.append("")
    L.append("| model | rows |")
    L.append("|---|---|")
    for model, n in by_model.most_common():
        L.append(f"| {model} | {n:,} |")
    L.append("")
    # Shared-document surfaces (docs observed by >= 2 runs)
    per_doc: dict[str, set] = {}
    for r in rows:
        per_doc.setdefault((r["task"], r["filename"]), set()).add(r["experiment_name"])
    multi = {k: v for k, v in per_doc.items() if len(v) >= 2}
    L.append(f"## Shared-document surfaces (docs with >= 2 runs)")
    L.append("")
    L.append(f"**{len(multi)} documents** observed by multiple runs — the paired "
             "comparison surface for prompt ablation / ensemble voting.")
    L.append("")
    by_task_multi = Counter(k[0] for k in multi)
    for task, n in by_task_multi.most_common():
        L.append(f"- {task}: {n} shared docs")
    L.append("")
    reasoning = sum(1 for r in rows if (r.get("reasoning") or "").strip())
    L.append(f"## Reasoning coverage")
    L.append("")
    L.append(f"**{reasoning:,} / {len(rows):,}** completed rows carry a reasoning "
             f"trace ({reasoning / max(1, len(rows)):.1%}) — the near-miss/exemplar "
             "material for the exemplar miner.")
    L.append("")
    return "\n".join(L)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    parser.add_argument("--no-summary", action="store_true", help="Skip the summary md")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = build_corpus()
    corpus_path = out_dir / "corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as fh:
        for record in corpus:
            fh.write(json.dumps(record) + "\n")
    print(f"corpus: {len(corpus)} rows -> {corpus_path}")
    if not args.no_summary:
        summary_path = out_dir / "corpus-summary.md"
        summary_path.write_text(render_summary(corpus), encoding="utf-8")
        print(f"summary: {summary_path}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()