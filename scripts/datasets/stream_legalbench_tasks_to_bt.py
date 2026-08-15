#!/usr/bin/env python3
"""Sync LegalBench multi-class classification tasks into Braintrust datasets.

LegalBench (HazyResearch/legalbench, CC BY 4.0) is the canonical legal
reasoning benchmark. Its **classification tasks** are exactly the multi-class
set the sorter should be evaluated on beyond the 6 mailroom doc types:

- 34 ``maud_*`` tasks — 4-way (A/B/C/D + Other/None) multiple-choice over
  merger-agreement excerpts
- 60 ``cuad_*`` tasks — Yes/No clause classification over CUAD contracts
- other classification tasks (hearsay, personal_jurisdiction, rule_qa,
  successor_liability, definition_classification, contract_nli_*, ...)

Each task is synced to its own Braintrust dataset ``mailroom-lb-<task>`` with
one row per train example:

    input:  {"doc_text": <excerpt>, "prompt": <base_prompt with {{text}} filled>,
             "question": ..., "filename": ...}
    expected: {"doc_type": <answer>}
    metadata: {task, slice/document_name, valid_classes}

``metadata.valid_classes`` records the task's answer space (derived from the
train answers + the README task type), so eval runners can validate and score
with ``--valid-classes``. A ``--classes-manifest`` JSONL is also written
locally with per-task classes/questions for the eval suite.

Rows carry DETERMINISTIC ids (content-addressed by ``upload_text_dataset``),
so reruns UPSERT in place — never duplicate rows.

Example — the **hearsay** task (Neel Guha, CC BY 4.0): binary Yes/No
classification of whether a piece of evidence qualifies as hearsay under the
Federal Rules of Evidence (out-of-court statement introduced to prove the
truth of the matter asserted). 100 samples total: 5 train rows (one per
slice) + 95 test; the 5 slices are statement made in-court, non-assertive
conduct, standard hearsay, non-verbal hearsay, and not-introduced-to-prove-
truth. ``--tasks hearsay`` syncs the 5-row train set to ``mailroom-lb-hearsay``
with ``valid_classes ["No", "Yes"]``; the base_prompt is a few-shot (4
exemplars) ``Q: ... Is there hearsay?\\nA:`` template.

Data is streamed from GitHub raw (the canonical LegalBench source; the HF
mirror is empty/broken). The TEST splits (absent from GitHub) come from the
task authors' ``nguha/legalbench`` HF dataset. Nothing is committed to the repo.

Usage:
    python scripts/datasets/stream_legalbench_tasks_to_bt.py                 # maud + cuad + curated
    python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks all     # every classification task
    python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks maud_type_of_consideration,hearsay
    python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks hearsay --test   # + mailroom-lb-hearsay-test
    python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks hearsay --test \
        --local-dump data/legalbench_local/                      # write local JSONL instead of Braintrust
    python scripts/datasets/stream_legalbench_tasks_to_bt.py --tasks hearsay --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import upload_text_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402

LB_BASE = "https://raw.githubusercontent.com/HazyResearch/legalbench/main/tasks"
LB_TASKS_API = "https://api.github.com/repos/HazyResearch/legalbench/contents/tasks?per_page=200"
# The canonical LegalBench release by the task authors (GitHub ships only
# train.tsv; the train + test splits live here, e.g. hearsay train 5 / test 94).
HF_DATASET = "nguha/legalbench"
HF_ROWS_API = "https://datasets-server.huggingface.co/rows"
DATASET_PREFIX = "mailroom-lb"

_CUAD = load_braintrust_config()
DEFAULT_PROJECT_ID = _CUAD.project_id

# Classification task families synced by default (maud + cuad + curated others).
CURATED_OTHER_TASKS = [
    "hearsay",
    "personal_jurisdiction",
    "rule_qa",
    "successor_liability",
    "definition_classification",
    "contract_qa",
    "contract_nli_return_of_confidential_information",
    "contract_nli_sharing_with_third-parties",
    "contract_nli_survival_of_obligations",
    "contract_nli_no_licensing",
    "contract_nli_permissible_copy",
    "nys_judicial_ethics",
    "oral_argument_question_purpose",
    "overruling",
    "insurance_policy_interpretation",
    "abercrombie",
    "ucc_v_common_law",
    "corporate_lobbying",
    "unfair_tos",
    "diversity_1",
]

# Task families with non-classification outputs (skipped by --tasks all).
_NON_CLASSIFICATION = {
    "citation_prediction_open", "definition_extraction", "maud_*", "sara_numeric",
}


def list_task_dirs() -> list[str]:
    """Return every task directory name in the LegalBench repo."""
    resp = requests.get(LB_TASKS_API, timeout=120)
    resp.raise_for_status()
    return sorted(t["name"] for t in resp.json() if t.get("type") == "dir")


def fetch_task_file(task: str, filename: str) -> str:
    url = f"{LB_BASE}/{task}/{filename}"
    resp = requests.get(url, timeout=120)
    if resp.status_code == 404:
        return ""
    resp.raise_for_status()
    return resp.text


def task_type_from_readme(readme: str) -> str:
    """Parse the README's 'Task type' line (e.g. '4-way classification')."""
    m = re.search(r"\*\*Task type\*\*:\s*(.+)", readme)
    return m.group(1).strip() if m else ""


def parse_train_tsv(task: str, raw: str) -> list[dict]:
    """Parse a LegalBench ``train.tsv`` into row dicts.

    Columns vary by task; the common ones are ``index``, ``text``, ``answer``,
    plus task-specific columns (``document_name``, ``slice``, ``option``, ...).
    """
    reader = csv.DictReader(io.StringIO(raw), delimiter="\t")
    rows = []
    for i, row in enumerate(reader):
        text = (row.get("text") or "").strip()
        answer = (row.get("answer") or "").strip()
        if not text or not answer:
            continue
        rows.append({
            "index": row.get("index", i),
            "text": text,
            "answer": answer,
            "document_name": row.get("document_name", ""),
            "slice": row.get("slice", ""),
            "option": row.get("option", ""),
            "source": row.get("source", ""),
        })
    return rows


def fetch_hf_split(task: str, split: str) -> list[dict]:
    """Fetch a task's train/test split rows from the canonical HF dataset.

    The GitHub repo ships only ``train.tsv`` per task; the authoritative
    train + test splits live in the task authors' ``nguha/legalbench`` HF
    dataset (e.g. hearsay train 5 / test 94). Paginated ``/rows`` fetch (the
    datasets-server rows endpoint caps at 100 per request). Returns the raw
    row dicts (``index``/``answer``/``text``/``slice`` + task columns).
    """
    rows: list[dict] = []
    offset = 0
    while True:
        url = (f"{HF_ROWS_API}?dataset={HF_DATASET}&config={task}&split={split}"
               f"&offset={offset}&length=100")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"HF split {task}/{split}: {data['error'][:200]}")
        batch = data.get("rows", [])
        if not batch:
            break
        rows.extend(r["row"] for r in batch)
        offset += len(batch)
        if len(batch) < 100:
            break
    return rows


def normalize_hf_rows(raw_rows: list[dict]) -> list[dict]:
    """Map HF dataset rows onto the ``train.tsv`` row shape.

    The HF release uses the same LegalBench columns (``index``/``answer``/
    ``text``/``slice`` plus task columns), so the records built from the test
    split are byte-for-byte the same format as the train split — clean,
    LegalBench-formatted inputs for the eval loop.
    """
    out: list[dict] = []
    for i, row in enumerate(raw_rows):
        text = str(row.get("text") or "").strip()
        answer = str(row.get("answer") or "").strip()
        if not text or not answer:
            continue
        out.append({
            "index": row.get("index", i),
            "text": text,
            "answer": answer,
            "document_name": row.get("document_name", ""),
            "slice": row.get("slice", ""),
            "option": row.get("option", ""),
            "source": row.get("source", ""),
        })
    return out


def build_prompt(base_prompt: str, text: str) -> str:
    """Fill the task's base_prompt with the example text."""
    if "{{text}}" in base_prompt:
        return base_prompt.replace("{{text}}", text)
    return f"{base_prompt}\n\n{text}"


def valid_classes_for(rows: list[dict], readme_type: str) -> list[str]:
    """Derive the task's answer space from the train answers.

    Ordered by first appearance in the train set (stable for eval). Binary
    tasks collapse to Yes/No; maud tasks keep their option letters.
    """
    classes: list[str] = []
    seen = set()
    for row in rows:
        answer = row["answer"].strip()
        if answer not in seen:
            seen.add(answer)
            classes.append(answer)
    if not classes:
        classes = ["Yes", "No"] if "classification" in readme_type.lower() else []
    return classes


def load_task(task: str, include_prompt: bool = True) -> dict:
    """Load one task: train rows, base prompt, README, and derived classes."""
    train_raw = fetch_task_file(task, "train.tsv")
    if not train_raw.strip():
        raise SystemExit(f"Task {task!r} has no train.tsv — is it a valid task directory?")
    rows = parse_train_tsv(task, train_raw)
    base_prompt = fetch_task_file(task, "base_prompt.txt") if include_prompt else ""
    readme = fetch_task_file(task, "README.md")
    return {
        "task": task,
        "rows": rows,
        "base_prompt": base_prompt,
        "readme": readme,
        "task_type": task_type_from_readme(readme),
        "valid_classes": valid_classes_for(rows, task_type_from_readme(readme)),
    }


def select_tasks(tasks_arg: str, all_dirs: list[str]) -> list[str]:
    """Resolve the --tasks argument into a concrete task list.

    ``maud_*`` tasks are intentionally NOT included from this source: the
    LegalBench repo's maud train.tsv files hold a single exemplar each, while
    the full 13k-row multi-class MAUD set is synced from the MAUD v1 CSV by
    ``stream_legalbench_to_bt.py`` (``mailroom-legalbench-maud-classification``).
    """
    if tasks_arg == "all":
        return [t for t in all_dirs if not any(
            t.startswith(prefix.rstrip("*")) for prefix in _NON_CLASSIFICATION)
            and not t.startswith("maud_")]
    if tasks_arg == "maud":
        print("NOTE: maud_* tasks are synced from the MAUD v1 CSV via "
              "stream_legalbench_to_bt.py; returning the GitHub exemplar datasets.",
              file=sys.stderr)
        return [t for t in all_dirs if t.startswith("maud_")]
    if tasks_arg == "cuad":
        return [t for t in all_dirs if t.startswith("cuad_")]
    if tasks_arg == "curated":
        return CURATED_OTHER_TASKS
    return [t.strip() for t in tasks_arg.split(",") if t.strip()]


def build_records(task_meta: dict) -> list[dict]:
    """Convert one task's rows into Braintrust dataset records."""
    records = []
    for row in task_meta["rows"]:
        prompt = ""
        if task_meta["base_prompt"]:
            prompt = build_prompt(task_meta["base_prompt"], row["text"])
        filename = f"{task_meta['task']}_{row['index']}.txt"
        records.append({
            "input": {
                "doc_text": row["text"],
                "prompt": prompt,
                "question": f"LegalBench task: {task_meta['task']}",
                "filename": filename,
                "metadata": {
                    "task": task_meta["task"],
                    "task_type": task_meta["task_type"],
                    "valid_classes": task_meta["valid_classes"],
                    "document_name": row["document_name"],
                    "slice": row["slice"],
                    "option": row["option"],
                    "index": row["index"],
                },
            },
            "expected": {"doc_type": row["answer"]},
            "expected_output": {"doc_type": row["answer"], "task": task_meta["task"]},
            "metadata": {
                "source": "legalbench",
                "license": "CC BY 4.0",
                "task": task_meta["task"],
                "task_type": task_meta["task_type"],
                "valid_classes": task_meta["valid_classes"],
                "answer": row["answer"],
            },
        })
    return records


def write_local_jsonl(records: list[dict], path: Path) -> int:
    """Write Braintrust record dicts to a local JSONL for the eval loop.

    Each line is flattened to the record shape ``run_classification_eval
    --task-dataset`` consumes: ``{filename, doc_text, prompt, expected,
    metadata}`` where ``expected`` is the task label (the same string the
    Braintrust rows would carry). ``metadata`` merges the input metadata
    (slice, valid_classes, task, ...) with the top-level record metadata.
    """
    import json as _json

    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            input_data = record.get("input") or {}
            expected = record.get("expected") or {}
            label = expected.get("doc_type") if isinstance(expected, dict) else expected
            row = {
                "filename": (input_data.get("filename") if isinstance(input_data, dict) else ""),
                "doc_text": (input_data.get("doc_text") if isinstance(input_data, dict) else ""),
                "prompt": (input_data.get("prompt") if isinstance(input_data, dict) else ""),
                "expected": label,
                "metadata": {
                    **(input_data.get("metadata") or {} if isinstance(input_data, dict) else {}),
                    **(record.get("metadata") or {}),
                },
            }
            fh.write(_json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Braintrust project id")
    parser.add_argument("--tasks", default="cuad,curated",
                        help="Task selection: 'cuad', 'curated', 'all', or comma-separated task names "
                             "(default: cuad,curated; the maud_* tasks are synced from the MAUD v1 "
                             "CSV by stream_legalbench_to_bt.py)")
    parser.add_argument("--classes-manifest", type=Path, default=Path("data/legalbench_classes.jsonl"),
                        help="Local JSONL with per-task valid classes (for the eval suite)")
    parser.add_argument("--skip-prompt", action="store_true",
                        help="Don't fetch base_prompt.txt (smaller, faster, no per-task prompt)")
    parser.add_argument("--test", action="store_true",
                        help="Also sync each task's TEST split (from the canonical "
                             "nguha/legalbench HF dataset — GitHub ships only train.tsv) "
                             "into a <task>-test dataset, e.g. mailroom-lb-hearsay-test "
                             "(94 rows, binary Yes/No)")
    parser.add_argument("--local-dump", type=Path, default=None,
                        help="Write the SAME LegalBench-formatted records to local JSONL "
                             "instead of Braintrust (useful when Braintrust writes are "
                             "unavailable): <dir>/<task>.jsonl (train) + <dir>/<task>-test.jsonl "
                             "(test, when --test). Each line: {filename, doc_text, prompt, "
                             "expected, metadata} — the record shape run_classification_eval "
                             "reads via --task-dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Braintrust")
    args = parser.parse_args()

    if not args.local_dump:
        (api_key,) = require_env("BRAINTRUST_API_KEY")
    else:
        api_key = None

    print("Listing LegalBench task directories...")
    all_dirs = list_task_dirs()
    tasks = select_tasks(args.tasks, all_dirs)
    unknown = [t for t in tasks if t not in all_dirs]
    if unknown:
        parser.error(f"Unknown task(s): {unknown}")
    print(f"Selected {len(tasks)} tasks: {tasks}")

    if args.classes_manifest:
        args.classes_manifest.parent.mkdir(parents=True, exist_ok=True)

    total_synced = 0
    total_failed = 0
    manifest_rows = []
    for i, task in enumerate(tasks, start=1):
        print(f"\n[{i}/{len(tasks)}] Loading task {task}...")
        meta = load_task(task, include_prompt=not args.skip_prompt)
        print(f"  rows={len(meta['rows'])} classes={meta['valid_classes']} type={meta['task_type']!r}")

        manifest_rows.append({
            "task": task,
            "valid_classes": meta["valid_classes"],
            "task_type": meta["task_type"],
            "base_prompt": meta["base_prompt"],
            "rows": len(meta["rows"]),
        })

        records = build_records(meta)
        if not records:
            print("  no records; skipping")
            continue

        test_records: list[dict] = []
        if args.test:
            test_raw = fetch_hf_split(task, "test")
            test_rows = normalize_hf_rows(test_raw)
            if test_rows:
                test_meta = {
                    **meta,
                    "rows": test_rows,
                    "valid_classes": valid_classes_for(test_rows, meta["task_type"]),
                }
                test_records = build_records(test_meta)
            else:
                print("  [test] no test rows on HF; skipping")

        if args.local_dump:
            train_path = args.local_dump / f"{task}.jsonl"
            n_train = write_local_jsonl(records, train_path)
            print(f"  -> {train_path} ({n_train} rows)")
            total_synced += n_train
            if test_records:
                test_path = args.local_dump / f"{task}-test.jsonl"
                n_test = write_local_jsonl(test_records, test_path)
                print(f"  -> {test_path} ({n_test} rows)")
                total_synced += n_test
            continue

        if test_records:
            test_dataset_name = f"{DATASET_PREFIX}-{task}-test"
            if args.dry_run:
                print(f"  would sync {len(test_records)} rows -> {test_dataset_name}")
                total_synced += len(test_records)
            else:
                test_summary = upload_text_dataset(
                    test_records,
                    project_id=args.project_id,
                    dataset_name=test_dataset_name,
                    api_key=api_key,
                    description=f"LegalBench task {task} TEST split ({meta['task_type']}, "
                                f"{len(test_records)} rows, CC BY 4.0)",
                    metadata={"source": "legalbench", "task": task, "task_type": meta["task_type"],
                              "split": "test", "valid_classes": test_meta["valid_classes"]},
                    on_progress=lambda done, n: print(f"  [test] Inserted {done}/{n}..." ),
                )
                total_synced += test_summary["inserted"]
                total_failed += test_summary["failed"]
                print(f"  -> {test_dataset_name}: {test_summary['inserted']} inserted, "
                      f"{test_summary['failed']} failed")

        dataset_name = f"{DATASET_PREFIX}-{task}"
        if args.dry_run:
            print(f"  would sync {len(records)} rows -> {dataset_name}")
            total_synced += len(records)
            continue

        summary = upload_text_dataset(
            records,
            project_id=args.project_id,
            dataset_name=dataset_name,
            api_key=api_key,
            description=f"LegalBench task {task} ({meta['task_type']}, {len(records)} rows, CC BY 4.0)",
            metadata={"source": "legalbench", "task": task, "task_type": meta["task_type"],
                      "valid_classes": meta["valid_classes"]},
            on_progress=lambda done, n: print(f"  Inserted {done}/{n}..." ),
        )
        total_synced += summary["inserted"]
        total_failed += summary["failed"]
        print(f"  -> {dataset_name}: {summary['inserted']} inserted, {summary['failed']} failed")

    if args.classes_manifest:
        with args.classes_manifest.open("w", encoding="utf-8") as fh:
            for row in manifest_rows:
                fh.write(__import__("json").dumps(row, ensure_ascii=False) + "\n")
        print(f"\nClasses manifest written to {args.classes_manifest}")

    print(f"\n{'Dry run: ' if args.dry_run else ''}Done: {total_synced} rows synced, {total_failed} failed")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
