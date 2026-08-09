#!/usr/bin/env python3
"""Run ONE prompt-version experiment for document classification.

The core loop of the mailroom prompt-experiment environment: takes a Braintrust
dataset of legal documents, runs the SorterAgent (a LangChain chain) with
exactly ONE prompt version, and logs the full experiment — prompt text,
predictions, reasoning, confidence, and costs — to Braintrust for A/B
comparison in the UI.

Design (modeled on the RVL-CDIP classifier repo's ``braintrust_openrouter_input.py``):

- One experiment = one prompt version + one model. The experiment name is
  ``{model_slug}_p{prompt_version}`` so identical runs overwrite (never
  duplicate) and different prompt versions are directly comparable.
- Scorers are deterministic: ``exact_match``, ``failure``, ``cost``.
- A JSONL manifest checkpoint makes interrupted runs resumable; replaying a
  completed row costs nothing (no LLM call).
- ``braintrust.integrations.langchain.setup_langchain`` hooks every LangChain
  model call into the active Braintrust span, so the UI shows the full
  chain (prompt template -> model -> parser) per document.

Usage:
    python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts
    python scripts/eval/run_classification_eval.py --dataset mailroom-cuad-contracts \
        --prompt-version sorter_v0 --model qwen/qwen3.7-flash
    python scripts/eval/run_classification_eval.py --documents-dir ./docs --expected contract
    python scripts/eval/run_classification_eval.py --samples-per-class 5 --sample-seed 42
    python scripts/eval/run_classification_eval.py --manifest data/manifests/cuad_sorter_v0.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from braintrust.integrations.langchain import setup_langchain

import braintrust

from agents.sorter_agent import DOC_CLASS_KEYS, SorterAgent
from src.braintrust_config import load_braintrust_config
from src.braintrust_utils import load_braintrust_dataset
from src.env_utils import require_env
from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset
from src.prompts import DEFAULT_PROMPT_VERSION, list_prompts
from src.scorers import ERROR_PREFIX, build_scorers, exact_match, failure

_CONFIG = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"


def default_experiment_name(model: str, prompt_version: str) -> str:
    """``{model-slug}_p{prompt-version}`` — or ``{model-slug}_{prompt-version}``
    when the version already carries an agent prefix (e.g. ``sorter_v0``)."""
    slug = model.split("/")[-1]
    if prompt_version.startswith("v"):
        return f"{slug}_p{prompt_version}"
    return f"{slug}_{prompt_version}"


def parse_scorers(value: str | None) -> list[str] | None:
    """Parse the ``--scorers`` argument; None = caller default."""
    if value is None:
        return None
    names = [v.strip() for v in value.split(",") if v.strip()]
    if not names or value.strip().lower() == "none":
        return []
    return names


def sample_balanced(dataset: list[dict], samples_per_class: int, seed: int = 42) -> list[dict]:
    """Deterministically subsample ``samples_per_class`` rows per class."""
    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in dataset:
        by_class[row["expected"]].append(row)
    rng = random.Random(seed)
    sampled: list[dict] = []
    for cls in sorted(by_class):
        available = by_class[cls]
        n = min(samples_per_class, len(available))
        sampled.extend(rng.sample(available, n))
    rng.shuffle(sampled)
    return sampled


def load_local_documents(documents_dir: Path, expected: str) -> list[dict]:
    """Load local ``.txt`` documents as dataset rows (expected class override)."""
    if expected not in DOC_CLASS_KEYS:
        raise SystemExit(f"--expected must be one of {DOC_CLASS_KEYS}, got {expected!r}")
    records = []
    for path in sorted(documents_dir.glob("*.txt")):
        doc_text = path.read_text(encoding="utf-8", errors="replace")
        if doc_text.strip():
            records.append({
                "doc_text": doc_text,
                "filename": path.name,
                "expected": expected,
            })
    return records


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=_CONFIG.project_name, help="Braintrust project name")
    parser.add_argument("--project-id", default=_CONFIG.project_id, help="Braintrust project id")
    parser.add_argument("--dataset-project", default=_CONFIG.dataset_project, help="Project holding the dataset")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset name to evaluate")
    parser.add_argument("--documents-dir", type=Path, default=None,
                        help="Use local .txt documents instead of a Braintrust dataset")
    parser.add_argument("--expected", default="contract", help="Expected class for --documents-dir rows")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N documents")
    parser.add_argument("--samples-per-class", type=int, default=None,
                        help="Deterministically subsample N documents per class")
    parser.add_argument("--sample-seed", type=int, default=42, help="Seed for --samples-per-class")
    parser.add_argument("--model", default=_CONFIG.model, help=f"Model (default: {_CONFIG.model})")
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION,
                        help=f"Prompt version to test (default: {DEFAULT_PROMPT_VERSION}; one per experiment)")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max output tokens")
    parser.add_argument("--max-concurrency", type=int, default=8, help="Concurrent API calls")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_p{prompt-version})")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--scorers", default=None,
                        help="Comma-separated scorers: exact_match,failure,cost ('none' for none)")
    parser.add_argument("--no-scorers", action="store_true", help="Skip Braintrust scoring")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, and print the plan without running")
    args = parser.parse_args(argv)

    (openrouter_key,) = require_env("OPENROUTER_API_KEY")
    (braintrust_key,) = require_env("BRAINTRUST_API_KEY")

    # Fail fast: this run tests exactly one prompt.
    available = list_prompts()
    if args.prompt_version not in available:
        parser.error(f"Unknown prompt version {args.prompt_version!r}. Available: {available}")

    experiment_name = args.experiment_name or default_experiment_name(args.model, args.prompt_version)
    scorers = parse_scorers(args.scorers) if args.scorers is not None else None

    # ---- dataset ----
    if args.documents_dir:
        if not args.documents_dir.exists():
            parser.error(f"--documents-dir not found: {args.documents_dir}")
        dataset = load_local_documents(args.documents_dir, args.expected)
    else:
        dataset = load_braintrust_dataset(args.dataset_project, args.dataset)
    if args.samples_per_class:
        dataset = sample_balanced(dataset, args.samples_per_class, args.sample_seed)
        per_class = Counter(d["expected"] for d in dataset)
        print(f"Balanced subsample: {len(dataset)} documents ({args.samples_per_class} per class x {len(per_class)} classes)")
    if args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No documents found to evaluate.")
    validate_dataset(dataset)

    manifest = None
    manifest_meta = {
        "experiment_name": experiment_name,
        "dataset": args.dataset,
        "dataset_size": len(dataset),
        "dataset_fingerprint": dataset_fingerprint(dataset),
        "model": args.model,
        "prompt_version": args.prompt_version,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.manifest:
        manifest = ManifestStore(args.manifest, manifest_meta)
        manifest.initialize()

    if args.dry_run:
        print(f"Dry run: {len(dataset)} documents -> experiment '{experiment_name}'")
        print(f"  prompt_version={args.prompt_version} model={args.model} "
              f"scorers={scorers or ['exact_match', 'failure', 'cost']}")
        print(f"  classes: {dict(Counter(d['expected'] for d in dataset))}")
        return 0

    # Hook LangChain tracing into Braintrust BEFORE any model call.
    setup_langchain(api_key=braintrust_key, project_id=args.project_id, project_name=args.project)

    from src.prompts import get_prompt

    prompt_text = get_prompt(args.prompt_version)

    # Per-row actual cost, captured from the agent's last usage; read by the
    # cost scorer after the eval awaits each task.
    cost_by_index: dict[int, float] = {}
    usage_by_index: dict[int, dict] = {}

    @braintrust.traced
    def classify_document(input_data: dict) -> str:
        """Classify a single document with the LangChain SorterAgent."""
        index = input_data["index"]
        filename = input_data["filename"]
        expected = input_data["expected"]

        sorter = SorterAgent(
            model=args.model,
            api_key=openrouter_key,
            prompt_version=args.prompt_version,
        )
        sorter._max_input_chars = 12000

        if manifest:
            cached = manifest.get_completed(filename)
            if cached:
                braintrust.current_span().log(
                    metadata={"cached": True, "filename": filename,
                              "prompt_version": args.prompt_version}
                )
                return cached["predicted"]

        doc_text = input_data["doc_text"]
        try:
            result = sorter.classify_json(doc_text)
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort the eval
            msg = f"{ERROR_PREFIX}{filename}: {type(exc).__name__}: {exc}"
            print(msg, file=sys.stderr)
            if manifest:
                manifest.append({"filename": filename, "expected": expected,
                                 "status": "error", "tag": "ERROR!", "predicted": "",
                                 "error": str(exc)})
            return msg

        predicted = str(result.get("doc_type", "")).strip().lower()
        confidence = result.get("confidence")
        reasoning = str(result.get("reasoning", ""))

        usage = sorter._last_usage or {}
        usage_by_index[index] = usage
        if isinstance(usage.get("cost"), (int, float)):
            cost_by_index[index] = float(usage["cost"])

        if not predicted or predicted not in DOC_CLASS_KEYS:
            msg = f"{ERROR_PREFIX}{filename}: model returned invalid class {predicted!r}"
            print(msg, file=sys.stderr)
            if manifest:
                manifest.append({"filename": filename, "expected": expected,
                                 "status": "error", "tag": "ERROR!", "predicted": predicted,
                                 "error": f"invalid class {predicted!r}"})
            return msg

        if manifest:
            manifest.append({"filename": filename, "expected": expected,
                             "status": "completed", "tag": "OK" if predicted == expected else "MISS!",
                             "predicted": predicted, "error": "",
                             "confidence": confidence, "reasoning": reasoning,
                             "cost": cost_by_index.get(index, 0.0),
                             "usage": usage})

        braintrust.current_span().log(
            metadata={
                "filename": filename,
                "prompt_version": args.prompt_version,
                "reasoning": reasoning,
                "confidence": confidence,
                "expected": expected,
                "cost": cost_by_index.get(index, 0.0),
                "usage": usage,
            }
        )
        return predicted

    def cost(input) -> float:
        """Billed USD cost from OpenRouter's usage.cost for this row."""
        return cost_by_index.get(input.get("index", -1), 0.0)

    scorer_list = [] if args.no_scorers else build_scorers(scorers)
    if scorers and "cost" in scorers:
        scorer_list = [s for s in scorer_list if s.__name__ != "cost"]
        scorer_list.append(cost)
    elif not scorers and not args.no_scorers:
        scorer_list = [exact_match, failure, cost]

    def _report_eval(evaluator, result, verbose, jsonl):
        failures = [r for r in result.results if r.error]
        for failure_ in failures:
            print(f"ERROR {failure_.input['filename']}: {failure_.error}", file=sys.stderr)
        return not failures

    def _report_run(results, verbose, jsonl):
        return all(results)

    result = braintrust.Eval(
        args.project,
        data=lambda: [
            {"input": {"index": i, "filename": d["filename"], "expected": d["expected"],
                       "doc_text": d["doc_text"]},
             "expected": d["expected"],
             "filename": d["filename"]}
            for i, d in enumerate(dataset)
        ],
        task=classify_document,
        scores=scorer_list,
        max_concurrency=args.max_concurrency,
        reporter=braintrust.Reporter("classification-only",
                                     report_eval=_report_eval, report_run=_report_run),
        project_id=args.project_id,
        experiment_name=experiment_name,
        metadata={
            "prompt": prompt_text,
            "prompt_version": args.prompt_version,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "dataset": f"{args.dataset_project}/{args.dataset}",
            "dataset_size": len(dataset),
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "manifest": str(args.manifest) if args.manifest else None,
        },
        description=f"{args.model} | prompt {args.prompt_version} | temperature {args.temperature}",
    )

    print_classifications(result, dataset)

    braintrust.flush()
    return 0


def print_classifications(result, dataset: list[dict]) -> None:
    """Print per-class accuracy and exact-match totals."""
    by_expected: dict[str, list[tuple[str, str]]] = defaultdict(list)
    failed = 0
    for r in result.results:
        if r.error is not None:
            failed += 1
            continue
        expected = str(r.expected).lower()
        output = str(r.output)
        if output.startswith(ERROR_PREFIX):
            failed += 1
            continue
        by_expected[expected].append((output, expected))

    print("\n== Per-class accuracy ==")
    for cls in sorted(by_expected):
        rows = by_expected[cls]
        correct = sum(1 for pred, exp in rows if pred == exp)
        print(f"{cls:<24} {correct}/{len(rows)} ({correct / len(rows):.1%})")

    total = sum(len(v) for v in by_expected.values())
    correct = sum(1 for rows in by_expected.values() for pred, exp in rows if pred == exp)
    print(f"\nexact_match {correct}/{total} ({correct / total:.1%})" if total else "no results")
    if failed:
        print(f"{failed} failed rows counted as misses (tracked as `failure` metric)")


if __name__ == "__main__":
    raise SystemExit(main())
