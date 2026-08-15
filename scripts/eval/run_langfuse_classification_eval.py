#!/usr/bin/env python3
"""LANGFUSE MIRROR of the classification evaluation (TEXT mode).

Runs the EXACT SAME experiment as ``run_classification_eval.py`` in text
mode — same Braintrust dataset, same SorterAgent task, same deterministic
scorers (exact_match, failure, cost), same manifest resume, same
append-only repo experiment log — but traces into a SEPARATE Langfuse
environment (own project keys in ``langfuse.env``; every trace tagged with
``LANGFUSE_ENVIRONMENT``).

Two prompt modes:

- ``--prompt-mode sorter`` (default): doc-type classification of full
  documents, one ``sorter`` observation per document with the sorter's task
  scores (exact_match, confidence) attached to its own observation.
- ``--prompt-mode task``: answers a LegalBench-style task question from the
  row's ``prompt`` field (base_prompt with the example filled in) with the
  versioned ``legalbench_task_v0`` system prompt constrained to
  ``--valid-classes`` — one ``legalbench_task`` observation per row.
  Example: ``--dataset mailroom-lb-hearsay --prompt-mode task
  --valid-classes Yes,No``.

Vision input is not mirrored (the Langfuse media-attachment path is a
separate mechanism).

Usage:
    python scripts/eval/run_langfuse_classification_eval.py --dry-run
    python scripts/eval/run_langfuse_classification_eval.py --sample 5 --seed 42
    python scripts/eval/run_langfuse_classification_eval.py \
        --prompt-version sorter_v6
    python scripts/eval/run_langfuse_classification_eval.py \
        --dataset mailroom-lb-hearsay --prompt-mode task \
        --valid-classes Yes,No --prompt-version legalbench_task_v0
    python scripts/eval/run_langfuse_classification_eval.py \
        --task-dataset data/legalbench_local/hearsay-test.jsonl --prompt-mode task \
        --valid-classes Yes,No --prompt-version legalbench_task_v0
"""

from __future__ import annotations

import argparse
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sorter_agent import DOC_CLASS_KEYS, SorterAgent  # noqa: E402
from scripts.eval.run_classification_eval import (  # noqa: E402
    _answer_task,
    load_local_pdfs,
    load_task_dataset,
    log_experiment_to_repo,
)
from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.braintrust_utils import load_braintrust_dataset  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.evaluation import ManifestStore, dataset_fingerprint  # noqa: E402
from src.experiment_log import default_jsonl_path, default_md_path  # noqa: E402
from src.langfuse_config import load_langfuse_config  # noqa: E402
from src.langfuse_tracing import LangfuseTracer  # noqa: E402
from src.prompts import list_prompts  # noqa: E402

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


class EvalResultShim:
    """Minimal braintrust.EvalResult-compatible row for the shared logger."""

    def __init__(self, input, expected, output, error=None):
        self.input = input
        self.expected = expected
        self.output = output
        self.error = error


class EvalRunShim:
    """Minimal braintrust.Eval-result-compatible container."""

    def __init__(self, results: list):
        self.results = results


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name, help="Braintrust project name (dataset source)")
    parser.add_argument("--project-id", default=_CONFIG.project_id, help="Braintrust project id (dataset source)")
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project, help="Project holding the dataset")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset to evaluate")
    parser.add_argument("--task-dataset", type=Path, default=None,
                        help="Local LegalBench task JSONL (streamer --local-dump output: "
                             "{filename, doc_text, prompt, expected, metadata} per line) to "
                             "evaluate instead of a Braintrust dataset")
    parser.add_argument("--pdf-dir", type=Path, default=None,
                        help="Local directory of ACTUAL PDFs to classify instead of a "
                             "Braintrust dataset (e.g. the local CUAD mirror "
                             "data/cuad_pdfs/CUAD_v1/full_contract_pdf — discovery is "
                             "recursive). Each PDF is rendered to pages and classified "
                             "by the VISION sorter, with one Langfuse trace per document.")
    parser.add_argument("--expected", default="contract",
                        help="Expected doc_type for --pdf-dir rows (default: contract)")
    parser.add_argument("--vision-pages", choices=("all", "first"), default="all",
                        help="--pdf-dir mode: 'all' sends every rendered page in one "
                             "vision call (default); 'first' sends only page 1")
    parser.add_argument("--prompt-mode", choices=("sorter", "task"), default="sorter",
                        help="sorter: classify doc_type with the sorter prompt over doc text; "
                             "task: answer a LegalBench-style task question from the row's "
                             "'prompt' field (base_prompt with the example filled in)")
    parser.add_argument("--valid-classes", default=None,
                        help="Comma-separated allowed expected labels (default: the taxonomy doc classes; "
                             "REQUIRED for --prompt-mode task, e.g. Yes,No or A,B,C,D)")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N documents")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N documents")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--prompt-version", default=None,
                        help="Sorter prompt version (default: sorter_v0 alias 'sorter')")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max output tokens")
    parser.add_argument("--max-input-chars", type=int, default=100_000,
                        help="Hard safety cap on document text fed to the sorter")
    parser.add_argument("--max-concurrency", type=int, default=8, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_classification_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/classification_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--lf-project", default=None, help="Override the Langfuse project name")
    parser.add_argument("--lf-environment", default=None, help="Override the trace environment tag")
    parser.add_argument("--lf-trace-name", default=None,
                        help="Langfuse trace name for each document "
                             "(default: doc_type_classification, or legalbench_task_classification "
                             "in --prompt-mode task)")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    if args.pdf_dir is None:
        require_env("BRAINTRUST_API_KEY")  # needed only to load a Braintrust dataset

    if args.prompt_version is None:
        args.prompt_version = "legalbench_task_v0" if args.prompt_mode == "task" else "sorter"
    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    valid_classes = None
    if args.valid_classes:
        valid_classes = {c.strip() for c in args.valid_classes.split(",") if c.strip()}
    if args.prompt_mode == "task" and not valid_classes:
        parser.error("--prompt-mode task requires --valid-classes "
                     "(the task's answer space, e.g. Yes,No)")
    if args.lf_trace_name is None:
        args.lf_trace_name = ("legalbench_task_classification" if args.prompt_mode == "task"
                              else "doc_type_classification")

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.prompt_version}_classification_langfuse"
    )

    if args.pdf_dir:
        if not args.pdf_dir.exists():
            parser.error(f"--pdf-dir not found: {args.pdf_dir}")
        dataset = load_local_pdfs(args.pdf_dir, args.expected, DOC_CLASS_KEYS)
        args.input_mode = "vision"  # local PDFs are classified by the vision sorter
    elif args.task_dataset:
        if not args.task_dataset.exists():
            parser.error(f"--task-dataset not found: {args.task_dataset}")
        dataset = load_task_dataset(args.task_dataset, valid_classes or set(DOC_CLASS_KEYS))
    else:
        dataset = load_braintrust_dataset(args.dataset_project, args.dataset,
                                          project_id=_CONFIG.project_id,
                                          valid=valid_classes or set(DOC_CLASS_KEYS))
    if args.sample:
        dataset = random.Random(args.seed).sample(dataset, min(args.sample, len(dataset)))
    if args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No documents found in the dataset.")

    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        print(f"Dry run: {len(dataset)} documents -> experiment '{experiment_name}'")
        print(f"  prompt_version={args.prompt_version} prompt_mode={args.prompt_mode} model={args.model}")
        print(f"  classes: {sorted({d['expected'] for d in dataset})}")
        print(f"  tracing=langfuse session={experiment_name} trace_name={args.lf_trace_name}")
        return 0

    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "dataset": args.dataset,
            "dataset_size": len(dataset),
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "model": args.model,
            "prompt_version": args.prompt_version,
            "prompt_mode": args.prompt_mode,
            "tracing_backend": "langfuse",
        })
        manifest.initialize()

    # ------------------------------------------------------------------
    # Langfuse tracer — separate environment from the primary project
    # ------------------------------------------------------------------
    lf_config = load_langfuse_config()
    if args.lf_project:
        lf_config = replace(lf_config, project=args.lf_project)
    if args.lf_environment:
        lf_config = replace(lf_config, environment=args.lf_environment)
    tracer = LangfuseTracer(
        config=lf_config,
        session_id=experiment_name,
        tags=[f"prompt:{args.prompt_version}", args.model.split("/")[-1]],
        trace_name=args.lf_trace_name,
    )
    if tracer.disabled:
        print("WARNING: Langfuse tracing is DISABLED (missing LANGFUSE keys in "
              "langfuse.env) — the run proceeds untraced; results still land in "
              "the repo experiment log.", file=sys.stderr)
    else:
        print(f"Tracing to Langfuse project '{lf_config.project}' "
              f"(environment '{lf_config.environment}') at {lf_config.base_url}")

    usage_by_index: dict[int, dict] = {}
    cost_by_index: dict[int, float] = {}

    def classify_one(input_data: dict) -> EvalResultShim:
        """Classify one document (doc_type or LegalBench task answer)."""
        index = input_data["index"]
        filename = input_data["filename"]
        expected = input_data["expected"]

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                return EvalResultShim(input_data, expected, cached["predicted"])

        with tracer.trace_document(
            filename, expected,
            {"dataset": args.dataset, "prompt_version": args.prompt_version,
             "model": args.model, "prompt_mode": args.prompt_mode},
        ) as trace_handle:
            observation_name = "legalbench_task" if args.prompt_mode == "task" else "sorter"
            with tracer.agent_observation(
                observation_name,
                {"prompt_version": args.prompt_version, "model": args.model,
                 "prompt_mode": args.prompt_mode},
            ) as agent_handle:
                sorter = SorterAgent(
                    model=args.model, api_key=openrouter_key,
                    prompt_version=args.prompt_version,
                    callbacks=[agent_handle.handler] if agent_handle.handler else None)
                sorter._max_input_chars = args.max_input_chars
                sorter._max_tokens = args.max_tokens
                try:
                    if args.prompt_mode == "task":
                        result = _answer_task(
                            sorter, input_data, sorted(valid_classes), args.prompt_version
                        )
                    else:
                        pages = input_data.get("pages_b64") or []
                        if pages and args.vision_pages == "all":
                            # ONE row = ONE PDF: every page in a single vision call.
                            result = sorter.classify_document(pages)
                        elif pages:
                            result = sorter.classify_image(pages[0], image_format="png")
                        else:
                            result = sorter.classify_json(input_data["doc_text"])
                except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                    msg = f"ERROR {filename}: {type(exc).__name__}: {exc}"
                    print(msg, file=sys.stderr)
                    if manifest:
                        manifest.append({"filename": filename, "expected": expected,
                                         "status": "error", "tag": "ERROR!", "predicted": "",
                                         "error": str(exc)})
                    return EvalResultShim(input_data, expected, msg, error=str(exc))

                usage_by_index[index] = sorter._last_usage or {}
                cost_by_index[index] = (sorter._last_usage or {}).get("cost") or 0.0

                if args.prompt_mode == "task":
                    # Case-preserving, validated against the task's class set.
                    predicted = str(result.get("doc_type", "")).strip()
                    allowed = sorted(valid_classes)
                    canonical = {c.lower(): c for c in allowed}
                    predicted = canonical.get(predicted.lower(), predicted)
                    if not predicted or predicted.lower() not in {c.lower() for c in allowed}:
                        msg = f"ERROR {filename}: model returned invalid class {predicted!r}"
                        print(msg, file=sys.stderr)
                        if manifest:
                            manifest.append({"filename": filename, "expected": expected,
                                             "status": "error", "tag": "ERROR!", "predicted": predicted,
                                             "error": f"invalid class {predicted!r}"})
                        return EvalResultShim(input_data, expected, msg, error=msg)
                else:
                    predicted = str(result.get("doc_type", "")).strip().lower()
                    if predicted not in DOC_CLASS_KEYS:
                        predicted = "correspondence"
                try:
                    confidence = float(result.get("confidence", 0.0))
                except (TypeError, ValueError):
                    confidence = 0.0

                agent_handle.set_output({
                    "doc_type": predicted,
                    "expected": expected,
                    "confidence": confidence,
                    "prompt_mode": args.prompt_mode,
                })
                agent_handle.score("exact_match", 1.0 if predicted == expected else 0.0,
                                   comment=f"{args.prompt_mode} == {expected}")
                agent_handle.score("confidence", confidence,
                                   comment="model-reported confidence")

                if manifest:
                    manifest.append({"filename": filename, "expected": expected,
                                     "status": "completed", "tag": "OK",
                                     "predicted": predicted, "error": ""})

            trace_handle.set_output({"doc_type": predicted, "confidence": confidence})

        return EvalResultShim(input_data, expected, predicted)

    rows = [
        {"index": i, "filename": d["filename"], "expected": d["expected"],
         "doc_text": d.get("doc_text", ""), "prompt": d.get("prompt", ""),
         "pages_b64": d.get("pages_b64", [])}
        for i, d in enumerate(dataset)
    ]
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {pool.submit(classify_one, row): i for i, row in enumerate(rows)}
        for future, i in futures.items():
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], rows[i]["expected"], None, error=str(exc))
    for failure in [r for r in results if r.error]:
        print(f"ERROR {failure.input['filename']}: {failure.error}", file=sys.stderr)

    tracer.flush()
    tracer.shutdown()

    # The shared logger reads the Braintrust runner's full flag surface; the
    # mirror records the configuration faithfully (prompt_mode is already set
    # from the CLI). Local --pdf-dir runs classify by vision; the text path
    # stays text.
    if args.pdf_dir:
        args.input_mode = "vision"
    else:
        args.input_mode = "text"
    args.vision_pages = "all"
    args.scorers = None
    args.no_scorers = True
    args.documents_dir = args.images_dir = None
    if not args.pdf_dir:
        args.pdf_dir = None
    args.samples_per_class = None
    args.sample_seed = 42

    log_experiment_to_repo(
        EvalRunShim(results), dataset, args, experiment_name,
        cost_by_index, usage_by_index, log_path, md_log_path,
        tracing_backend="langfuse",
        tracing_meta={
            "project": lf_config.project,
            "environment": lf_config.environment,
            "base_url": lf_config.base_url,
            "session_id": experiment_name,
            "trace_name": args.lf_trace_name,
            "disabled": tracer.disabled,
        },
    )
    print(f"\nExperiment logged to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
