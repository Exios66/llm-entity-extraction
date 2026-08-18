#!/usr/bin/env python3
"""LANGFUSE eval runner for the directly-mirrored ContractEval task.

Replicates the ContractEval benchmark (arXiv 2508.03080,
github.com/olivialiu121/ContractEval) EXACTLY as a first-class eval task:
one LLM call per (contract, question) pair over the CUAD test split, with
ContractEval's system prompt (versioned as ``contracteval_v0``), the paper's
full-context / temperature-0 / max_tokens-5000 calling convention, and the
paper's EXACT rubric (verbatim-containment TP, F1/F2/acc/prec/recall,
token-set Jaccard over positives, false-"no related clause" rate) scored by
the canonical upstream evaluator (``llm_dojo_scoring.tasks`` v0.4.0,
``contracteval`` task kind).

Data:
    --task-dataset  pairs JSONL (data/contracteval/contracteval_test.jsonl):
                    {id, title, category, question, label_spans, n_labels}
    --contracts     contracts JSONL (data/contracteval/contracteval_contracts.jsonl):
                    {title, context} — FULL contract text (102 contracts,
                    645–300,768 chars). The paper feeds the context WHOLE in one
                    call; the runner honors that by default (--max-input-chars 0
                    = no cap). Passing a positive cap truncates the context and
                    is a documented deviation from the paper.

Scoring: per-row classification (TP/TN/FP/FN + Jaccard) is attached to each
Langfuse observation; the pooled ContractEval metrics + per-category breakdown
land in ONE append-only experiment-log record (task=contracteval).

Usage:
    python scripts/eval/run_langfuse_contracteval_eval.py --dry-run
    python scripts/eval/run_langfuse_contracteval_eval.py --sample 50 --seed 42
    python scripts/eval/run_langfuse_contracteval_eval.py \
        --model qwen3.7-flash --prompt-version contracteval_v0
    python scripts/eval/run_langfuse_contracteval_eval.py \
        --model gpt-4.1-mini --research-funding-key
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.sorter_agent import SorterAgent  # noqa: E402
from src.env_utils import (  # noqa: E402
    add_research_funding_flag,
    assert_production_run,
    resolve_openrouter_key,
)
from src.evaluation import (  # noqa: E402
    ManifestStore,
    call_with_rate_limit_retry,
    dataset_fingerprint,
    resolve_concurrency,
)
from src.experiment_log import (  # noqa: E402
    append_experiment,
    append_markdown,
    default_jsonl_path,
    default_md_path,
    git_snapshot,
    tokens_summary,
)
from src.prompts import CONTRACTEVAL_USER_TEMPLATE, get_prompt, list_prompts  # noqa: E402
from src.tracing import resolve_tracer  # noqa: E402

DEFAULT_PAIRS = Path("data/contracteval/contracteval_test.jsonl")
DEFAULT_CONTRACTS = Path("data/contracteval/contracteval_contracts.jsonl")
DEFAULT_PROMPT = "contracteval_v0"

# The canonical evaluator lives upstream (llm-dojo-scoring v0.4.0, the
# ``contracteval`` task kind) — mirrors ContractEval's Evaluation.py exactly.
from llm_dojo_scoring.tasks import (  # noqa: E402
    contracteval_classified,
    get_jaccard,
    said_no_related,
    score_task,
)


class EvalResultShim:
    """Minimal per-row result container for the local logging loop."""

    def __init__(self, input_data: dict, output: str, error=None, classification=None,
                 jaccard: float = 0.0):
        self.input = input_data
        self.output = output
        self.error = error
        self.classification = classification  # 'TP'|'TN'|'FP'|'FN'|None
        self.jaccard = jaccard


def main() -> int:
    return main_with_args(sys.argv[1:])


def _load_pairs(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_contracts(path: Path) -> dict[str, str]:
    contracts: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            contracts[row["title"]] = row["context"]
    return contracts


def load_dataset(pairs_path: Path, contracts_path: Path) -> list[dict]:
    """Join pairs with full-contract contexts (per-title, stored once)."""
    pairs = _load_pairs(pairs_path)
    contracts = _load_contracts(contracts_path)
    missing = sorted({p["title"] for p in pairs} - set(contracts))
    if missing:
        raise SystemExit(
            f"{len(missing)} pair titles have no contract text in {contracts_path}; "
            f"first: {missing[:3]}. Rebuild the dataset (build_contracteval_testset.py).")
    dataset = []
    for i, pair in enumerate(pairs):
        dataset.append({
            "index": i,
            "id": pair["id"],
            "title": pair["title"],
            "filename": pair["id"],
            "category": pair["category"],
            "question": pair["question"],
            "context": contracts[pair["title"]],
            "label_spans": list(pair.get("label_spans") or []),
            "expected": pair["category"],
        })
    return dataset


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dataset", type=Path, default=DEFAULT_PAIRS,
                        help="Pairs JSONL (id, title, category, question, label_spans)")
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS,
                        help="Contracts JSONL ({title, context} — FULL text)")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N pairs")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N pairs")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--model", default="qwen/qwen3.7-flash", help="OpenRouter model id")
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT,
                        help="ContractEval system-prompt version (default: contracteval_v0)")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Sampling temperature (ContractEval uses 0; paper parity)")
    parser.add_argument("--max-tokens", type=int, default=5000,
                        help="Max output tokens (ContractEval uses 5000; paper parity)")
    parser.add_argument("--max-input-chars", type=int, default=0,
                        help="Context cap per call; 0 (default) = UNLIMITED faithful "
                             "full-context (the paper feeds each contract whole). A "
                             "positive cap truncates and deviates from the paper.")
    parser.add_argument("--max-concurrency", type=int, default=None,
                        help="Concurrent API calls (default: AUTO, 8..32 workers)")
    parser.add_argument("--experiment-name", default=None,
                        help="Experiment name (default: {model-slug}_{prompt-version}_contracteval_langfuse)")
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/contracteval_langfuse.jsonl"),
                        help="JSONL checkpoint manifest for resuming an interrupted run")
    parser.add_argument("--tracing-backend", choices=["langfuse", "phoenix"],
                        default="langfuse",
                        help="Tracing sink: langfuse (default) or the local Arize "
                             "Phoenix server (--tracing-backend phoenix)")
    parser.add_argument("--lf-project", default=None, help="Override the Langfuse project name")
    parser.add_argument("--lf-environment", default=None, help="Override the trace environment tag")
    parser.add_argument("--lf-trace-name", default="contracteval",
                        help="Langfuse trace name for each (contract, question) pair")
    parser.add_argument("--experiment-log", type=Path, default=None,
                        help="JSONL experiment log path (default: $EXPERIMENT_LOG_PATH)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve config, load dataset, print the plan without running")
    add_research_funding_flag(parser)
    args = parser.parse_args(argv)

    openrouter_key = resolve_openrouter_key(args.research_funding_key)

    if args.prompt_version not in list_prompts():
        parser.error(f"Unknown prompt version {args.prompt_version!r}. "
                     f"Available: {list_prompts()}")

    dataset = load_dataset(args.task_dataset, args.contracts)
    total_rows = len(dataset)
    if args.sample:
        dataset = random.Random(args.seed).sample(dataset, min(args.sample, len(dataset)))
    if args.limit:
        dataset = dataset[: args.limit]
    if not dataset:
        parser.error("No (contract, question) pairs found in the dataset.")
    # Cache-friendly dispatch: run each contract's 41 pairs CONSECUTIVELY
    # (stable sort by title, then id). Every pair of a contract shares the
    # identical system prompt + full-context prefix, so OpenRouter's automatic
    # prompt cache serves the repeated prefix at ~10% of the input price —
    # a big saving on the 300k-char contexts WITHOUT deviating from the
    # paper's one-call-per-pair methodology. Deterministic, so manifest
    # fingerprints stay stable across runs.
    dataset = sorted(dataset, key=lambda d: (d["title"], d["id"]))
    assert_production_run(args.research_funding_key, dry_run=args.dry_run,
                          selected_rows=len(dataset), total_rows=total_rows)

    experiment_name = args.experiment_name or (
        f"{args.model.split('/')[-1]}_{args.prompt_version}_contracteval_langfuse"
    )
    log_path = args.experiment_log or default_jsonl_path()
    md_log_path = default_md_path()

    if args.dry_run:
        print(f"Dry run: {len(dataset)} (contract, question) pairs -> experiment '{experiment_name}'")
        print(f"  prompt_version={args.prompt_version} model={args.model}")
        print(f"  temperature={args.temperature} max_tokens={args.max_tokens} "
              f"max_input_chars={args.max_input_chars} (0 = faithful full-context)")
        print(f"  categories: {len({d['category'] for d in dataset})} | "
              f"positive pairs: {sum(1 for d in dataset if d['label_spans'])}")
        print(f"  tracing={args.tracing_backend} session={experiment_name} "
              f"trace_name={args.lf_trace_name}")
        return 0

    tracer, tracing_backend, tracing_meta = resolve_tracer(
        session_id=experiment_name,
        trace_name=args.lf_trace_name,
        tags=[f"contracteval:{args.prompt_version}", args.model.split("/")[-1]],
        prefer="phoenix" if args.tracing_backend == "phoenix" else "langfuse",
        lf_project=args.lf_project,
        lf_environment=args.lf_environment,
    )
    if tracer.disabled:
        print("WARNING: tracing is DISABLED (no Langfuse keys / no Phoenix endpoint) — "
              "the run proceeds untraced; results still land in the repo experiment log.",
              file=sys.stderr)
    else:
        print(f"Tracing to {tracing_backend}: {tracing_meta}")

    manifest = None
    if args.manifest:
        manifest = ManifestStore(args.manifest, {
            "experiment_name": experiment_name,
            "task_dataset": str(args.task_dataset),
            "contracts": str(args.contracts),
            "dataset_size": len(dataset),
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "model": args.model,
            "prompt_version": args.prompt_version,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "max_input_chars": args.max_input_chars,
            "tracing_backend": tracing_backend,
        })
        manifest.initialize()

    usage_by_index: dict[int, dict] = {}
    cost_by_index: dict[int, float] = {}

    def run_pair(input_data: dict) -> EvalResultShim:
        """One (contract, question) call with ContractEval's system prompt."""
        pair_id = input_data["id"]
        if manifest:
            cached = manifest.get_completed(pair_id)
            if cached:
                # Resume: re-derive the per-row classification/jaccard from the
                # stored output so resumed rows carry consistent per-row values
                # (the pooled metrics are recomputed from outputs regardless).
                output = (cached.get("predicted") or "").strip()
                label = input_data["label_spans"]
                no_related = said_no_related(output)
                classified = bool(label) and contracteval_classified(label, output)
                if not label:
                    cls = "TN" if no_related else "FP"
                elif classified:
                    cls = "TP"
                else:
                    cls = "FN"
                jaccard = get_jaccard(" ".join(label), output.strip(" \n`")) if label else 0.0
                return EvalResultShim(
                    input_data, output, classification=cls, jaccard=jaccard)
        context = input_data["context"]
        if args.max_input_chars > 0 and len(context) > args.max_input_chars:
            context = context[: args.max_input_chars]
        user_message = CONTRACTEVAL_USER_TEMPLATE.format(
            context=context, question=input_data["question"])
        system_prompt = get_prompt(args.prompt_version)

        with tracer.trace_document(
            pair_id, input_data["category"],
            {"dataset": "contracteval-cuad-test", "prompt_version": args.prompt_version,
             "model": args.model, "category": input_data["category"]},
        ) as trace_handle:
            with tracer.agent_observation(
                "contracteval",
                {"prompt_version": args.prompt_version, "model": args.model,
                 "category": input_data["category"]},
            ) as agent_handle:
                sorter = SorterAgent(
                    model=args.model, api_key=openrouter_key,
                    prompt_version=args.prompt_version,
                    callbacks=[agent_handle.handler] if agent_handle.handler else None)
                # The paper's calling convention is a PLAIN temp-0 completion;
                # the sorter's medium reasoning effort (thinking mode) would
                # deviate from the mirror and burn the token budget on
                # reasoning — kill it before the LLM client is built.
                sorter._reasoning_effort = None
                sorter._max_tokens = args.max_tokens
                # Trace/log label: the SorterAgent is only a plain-LLM carrier
                # here — the system prompt is the CONTRACTEVAL prompt (never
                # the sorter's); name it as such so inspection can't mistake
                # this task's calls for sorter classification calls.
                sorter.agent_name = "contracteval"
                try:
                    output = sorter._call_llm(
                        user_message, system_prompt=system_prompt,
                        temperature=args.temperature, max_tokens=args.max_tokens)
                except Exception as exc:  # noqa: BLE001 - one bad pair must not abort
                    print(f"ERROR {pair_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
                    if manifest:
                        manifest.append({"filename": pair_id, "status": "error",
                                         "tag": "ERROR!", "predicted": "", "error": str(exc)})
                    return EvalResultShim(input_data, "", error=str(exc))
                output = (output or "").strip()

                usage_by_index[input_data["index"]] = sorter._last_usage or {}
                cost_by_index[input_data["index"]] = (
                    sorter._last_usage or {}).get("cost") or 0.0

                label = input_data["label_spans"]
                no_related = said_no_related(output)
                classified = bool(label) and contracteval_classified(label, output)
                if not label:
                    cls = "TN" if no_related else "FP"
                elif classified:
                    cls = "TP"
                else:
                    cls = "FN"
                jaccard = get_jaccard(" ".join(label), output.strip(" \n`")) if label else 0.0

                agent_handle.set_output({
                    "category": input_data["category"],
                    "predicted": output,
                    "classification": cls,
                    "jaccard": round(jaccard, 4),
                    "said_no_related": no_related,
                })
                agent_handle.score("classification", {"TP": 1.0, "TN": 1.0,
                                                      "FP": 0.0, "FN": 0.0}[cls],
                                   comment=f"{cls} (ContractEval verbatim rubric)")
                agent_handle.score("jaccard", round(jaccard, 4),
                                   comment="token-set Jaccard over the positive pair")

                if manifest:
                    manifest.append({"filename": pair_id, "status": "completed",
                                     "tag": "OK", "predicted": output,
                                     "classification": cls, "error": ""})
            trace_handle.set_output({"predicted": output, "classification": cls,
                                     "jaccard": round(jaccard, 4)})
        return EvalResultShim(input_data, output, classification=cls, jaccard=jaccard)

    rows = list(dataset)
    results: list[EvalResultShim] = [None] * len(rows)  # type: ignore[list-item]
    args.max_concurrency = resolve_concurrency(len(rows), args.max_concurrency)
    retry_stats: dict = {"rate_limit_retries": 0}
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as pool:
        futures = {
            pool.submit(call_with_rate_limit_retry, run_pair, row, stats=retry_stats): i
            for i, row in enumerate(rows)
        }
        for future, i in futures.items():
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                results[i] = EvalResultShim(rows[i], "", error=str(exc))
    for failure in [r for r in results if r.error]:
        print(f"ERROR {failure.input['id']}: {failure.error}", file=sys.stderr)

    tracer.flush()
    tracer.shutdown()

    # ------------------------------------------------------------------
    # Pooled ContractEval metrics via the canonical upstream evaluator.
    # ------------------------------------------------------------------
    expected_spans = [r.input["label_spans"] for r in results]
    outputs = [r.output for r in results]
    categories = [r.input["category"] for r in results]
    metrics = score_task("contracteval", expected_spans, outputs, categories=categories)

    per_row = []
    for r in results:
        per_row.append({
            "id": r.input["id"],
            "title": r.input["title"],
            "category": r.input["category"],
            "question": r.input["question"],
            "label_spans": r.input["label_spans"],
            "predicted": r.output,
            "classification": r.classification,
            "jaccard": round(r.jaccard, 4),
            "status": "error" if r.error else "completed",
            "error": r.error,
            "cost_usd": round(cost_by_index.get(r.input["index"], 0.0), 6),
            "tokens": usage_by_index.get(r.input["index"]) or {},
        })

    record = {
        "type": "experiment",
        "task": "contracteval",
        "experiment_name": experiment_name,
        "git": git_snapshot(),
        "model": args.model,
        "prompt_version": args.prompt_version,
        "data_source": {
            "source": f"contracteval:{args.task_dataset}",
            "dataset_fingerprint": dataset_fingerprint(dataset),
            "n_samples": len(dataset),
            "n_pairs": len(dataset),
            "n_contracts": len({d["title"] for d in dataset}),
            "limit": args.limit,
            "sample": args.sample,
            "sample_seed": args.seed,
        },
        "parameters": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "max_input_chars": args.max_input_chars,
            "max_concurrency": args.max_concurrency,
            "manifest": str(args.manifest) if args.manifest else None,
            "tracing_backend": tracing_backend,
            "tracing": tracing_meta,
            "faithful_full_context": args.max_input_chars == 0,
        },
        "tokens": tokens_summary(list(usage_by_index.values()), model=args.model),
        "scores": metrics,
        "n_rows": len(per_row),
        "n_ok": len(per_row) - sum(1 for r in per_row if r["status"] == "error"),
        "n_error": sum(1 for r in per_row if r["status"] == "error"),
        "results": per_row,
    }
    jsonl_path = append_experiment(record, log_path)
    append_markdown(record, md_log_path)

    if tracing_backend == "phoenix":
        # One run = one Phoenix experiment in the llm-dojo project: per-pair
        # runs + CODE evaluations (contracteval correct/incorrect, jaccard).
        # Best-effort — never breaks the run.
        try:
            from src.phoenix_tracing import register_phoenix_experiment
        except Exception:  # noqa: BLE001
            register_phoenix_experiment = None  # type: ignore[assignment]
        if register_phoenix_experiment is not None:
            register_phoenix_experiment(
                experiment_name=experiment_name,
                model=args.model,
                prompt_version=args.prompt_version,
                dataset_name="contracteval-cuad-test",
                pairs=dataset,
                results=per_row,
                timestamp=record.get("timestamp") or "",
            )

    print(f"\nExperiment logged to {jsonl_path}")
    print(f"  ContractEval: F1 {metrics['f1']} / F2 {metrics['f2']} / "
          f"Jaccard {metrics['jaccard_mean']} / false-nr {metrics['false_no_related_rate']} "
          f"(paper {metrics['false_no_related_rate_paper']}) on {metrics['n_pairs']} pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
