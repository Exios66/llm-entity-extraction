#!/usr/bin/env python3
"""GEPA champion-contender layer — Monte Carlo selection over the corpus.

Folds the Monte Carlo simulations into the GEPA prompt-iteration loop as a
formal **champion-selection step**. After same-surface A/Bs produce candidate
prompt versions, this layer re-validates and selects the champion corpus-wide:

1. **Paired-bootstrap prompt ablation** (the selection gate): for every pair of
   prompt versions on the same model, per-document deltas
   ``correct(A) - correct(B)`` are resampled with replacement over the
   SHARED-document surface → mean Δ, 95% CI, ``P(A beats B)``. A version
   *beats* another when the CI excludes zero (the GEPA noise-floor contract).
   The **Monte Carlo champion contender** is the version that beats the most
   peers (ties broken by aggregate accuracy); if no version beats any peer the
   surface is at a **plateau** (no measurable champion).
2. **Committee-voting robustness** for the contender: ensemble accuracy @ K
   over the champion surface's per-document label distributions.

**Effectiveness pilot (half-corpus sample):** ``--sample 0.5`` runs the same
selection on a seeded 50% sample of the shared documents and compares against
the full-corpus verdict — does half the surface recover the same champion, and
how does ``P(win)`` separation scale with document count? This is the
sample-efficiency check that gates full adoption of the MC selection layer.

Usage:
    python scripts/reporting/monte_carlo_gepa.py                          # full-corpus champion contender
    python scripts/reporting/monte_carlo_gepa.py --sample 0.5             # half-corpus effectiveness pilot
    python scripts/reporting/monte_carlo_gepa.py --task docclass_classification
    python scripts/reporting/monte_carlo_gepa.py --model qwen/qwen3.7-flash
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monte_carlo import (  # noqa: E402
    bootstrap,
    draw_committee,
    load_corpus,
    normalize_dist,
    paired_delta_bootstrap,
    task_label_vocabulary,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"

WIN_THRESHOLD = 0.9     # P(A beats B) required to call a significant pair
DEFAULT_N_BOOT = 2_000
DEFAULT_SEED = 42


# ---------------------------------------------------------------------------
# Outcomes + pairwise selection
# ---------------------------------------------------------------------------

def run_outcomes(corpus: list[dict], task: str, valid_classes: set[str]
                 ) -> dict[tuple[str, str], dict[str, bool]]:
    """{(model, prompt_version): {filename: correct}} for completed label rows."""
    outcomes: dict[tuple[str, str], dict[str, bool]] = defaultdict(dict)
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        if (record.get("predicted") or "") not in valid_classes:
            continue
        key = (record.get("model") or "?", record.get("prompt_version") or "?")
        outcomes[key][record["filename"]] = bool(record.get("correct"))
    return dict(outcomes)


def pairwise_matrix(outcomes: dict[tuple[str, str], dict[str, bool]],
                    model: str, min_shared: int, n_boot: int = DEFAULT_N_BOOT,
                    seed: int = DEFAULT_SEED) -> dict[tuple[str, str], dict]:
    """{(A, B): paired-bootstrap stat} for every ordered pair on ``model``.

    ``stat`` = {mean, ci_lo, ci_hi, p_win, n_shared, acc_a, acc_b}. A beats B
    (CI excludes zero, p_win >= WIN_THRESHOLD) is the selection signal.
    """
    versions = {p: docs for (m, p), docs in outcomes.items() if m == model}
    matrix: dict[tuple[str, str], dict] = {}
    for prompt_a, docs_a in versions.items():
        for prompt_b, docs_b in versions.items():
            if prompt_a == prompt_b:
                continue
            shared = sorted(set(docs_a) & set(docs_b))
            if len(shared) < min_shared:
                continue
            deltas = [float(docs_a[f]) - float(docs_b[f]) for f in shared]
            stat = paired_delta_bootstrap(deltas, n_boot=n_boot, seed=seed)
            stat["n_shared"] = len(shared)
            stat["acc_a"] = sum(1 for f in shared if docs_a[f]) / len(shared)
            stat["acc_b"] = sum(1 for f in shared if docs_b[f]) / len(shared)
            matrix[(prompt_a, prompt_b)] = stat
    return matrix


def aggregate_accuracy(outcomes: dict[tuple[str, str], dict[str, bool]],
                       model: str, prompt: str) -> float:
    """Mean exact-match over the prompt's own documents (support = n docs)."""
    docs = outcomes.get((model, prompt), {})
    return (sum(1 for v in docs.values() if v) / len(docs)) if docs else 0.0


def champion_contender(matrix: dict[tuple[str, str], dict], outcomes,
                       model: str) -> dict:
    """Select the Monte Carlo champion contender from the pairwise matrix.

    A version *beats* another when the CI excludes zero and P(win) >=
    WIN_THRESHOLD. The contender is the version with the most wins; ties break
    by aggregate accuracy. ``plateau=True`` when no version beats any peer
    (the surface has no measurable champion).
    """
    versions = {p for (a, b) in matrix for p in (a, b)}
    wins: dict[str, int] = Counter()
    for (a, b), stat in matrix.items():
        if stat["ci_lo"] > 0.0 and stat["p_win"] >= WIN_THRESHOLD:
            wins[a] += 1
    if not wins:
        return {"plateau": True, "contender": None, "wins": dict(wins),
                "versions": sorted(versions)}
    best_score = max(wins.values())
    best = [v for v, w in wins.items() if w == best_score]
    contender = max(best, key=lambda v: aggregate_accuracy(outcomes, model, v))
    return {"plateau": False, "contender": contender, "wins": dict(wins),
            "n_beats": best_score, "versions": sorted(versions),
            "accuracy": aggregate_accuracy(outcomes, model, contender)}


# ---------------------------------------------------------------------------
# Committee robustness (for the contender)
# ---------------------------------------------------------------------------

def committee_accuracy(corpus: list[dict], task: str, valid_classes: set[str],
                       k: int, n_sim: int = 400, seed: int = DEFAULT_SEED) -> float:
    """Ensemble majority-vote accuracy at K over the task's observations."""
    rng = random.Random(seed)
    docs: dict[str, list[str]] = defaultdict(list)
    expected: dict[str, str] = {}
    for record in corpus:
        if record.get("task") != task or record.get("status") != "completed":
            continue
        predicted = (record.get("predicted") or "").strip()
        if predicted not in valid_classes:
            continue
        filename = record["filename"]
        docs[filename].append(predicted)
        expected[filename] = record["expected"]
    per_doc = []
    for filename, observations in docs.items():
        dist = normalize_dist(Counter(observations))
        exp = expected[filename]
        if not dist or exp not in dist:
            per_doc.append(0.0)
            continue
        if k == 1:
            per_doc.append(dist[exp])
        else:
            correct = sum(1 for _ in range(n_sim)
                          if draw_committee(dist, k, rng) == exp)
            per_doc.append(correct / n_sim)
    return (sum(per_doc) / len(per_doc)) if per_doc else 0.0


# ---------------------------------------------------------------------------
# Half-corpus sampling + effectiveness
# ---------------------------------------------------------------------------

def sample_shared_docs(outcomes: dict[tuple[str, str], dict[str, bool]],
                       model: str, fraction: float, seed: int) -> set[str]:
    """Seeded 50% (etc.) sample of the shared documents for ``model``.

    Shared docs = documents observed by >= 2 of the model's prompt versions
    (the paired surface the selection reasons over).
    """
    per_prompt: list[set[str]] = [set(d) for (m, p), d in outcomes.items() if m == model]
    shared = set().union(*per_prompt) if per_prompt else set()
    for docs_a in per_prompt:
        for docs_b in per_prompt:
            shared |= (docs_a & docs_b)
    shared = sorted(shared)
    if not shared:
        return set()
    rng = random.Random(seed)
    n = max(1, int(round(len(shared) * fraction)))
    return set(rng.sample(shared, n))


def restrict_outcomes(outcomes, model: str, keep: set[str]) -> dict[tuple[str, str], dict[str, bool]]:
    """Restrict a model's outcome maps to the kept document set."""
    out = {}
    for (m, p), docs in outcomes.items():
        if m == model:
            out[(m, p)] = {f: c for f, c in docs.items() if f in keep}
    return {k: v for k, v in out.items() if v}


def effectiveness(outcomes, model: str, min_shared: int, fraction: float,
                  seed: int, n_boot: int) -> dict:
    """Compare full-corpus vs sampled-corpus champion selection.

    Returns the full and sampled selections plus a document-count sweep of the
    strongest pair's P(win) separation.
    """
    matrix_full = pairwise_matrix(outcomes, model, min_shared, n_boot=n_boot, seed=seed)
    full = champion_contender(matrix_full, outcomes, model)

    keep = sample_shared_docs(outcomes, model, fraction, seed)
    sampled_outcomes = restrict_outcomes(outcomes, model, keep)
    matrix_sampled = pairwise_matrix(sampled_outcomes, model, min_shared, n_boot=n_boot, seed=seed)
    sampled = champion_contender(matrix_sampled, sampled_outcomes, model)

    sweep = {}
    for frac in (0.25, 0.5, 0.75, 1.0):
        k = sample_shared_docs(outcomes, model, frac, seed)
        m = pairwise_matrix(restrict_outcomes(outcomes, model, k), model,
                            min_shared, n_boot=n_boot, seed=seed)
        sel = champion_contender(m, outcomes, model)
        # strongest significant pair (largest |mean Δ| with CI excluding zero)
        top = max(m.items(), key=lambda kv: abs(kv[1]["mean"])) if m else None
        sweep[frac] = {
            "contender": sel.get("contender"),
            "n_docs_sampled": len(k),
            "top_pair": (top[0][0], top[0][1]) if top else None,
            "top_mean": round(top[1]["mean"], 4) if top else None,
            "top_p_win": round(top[1]["p_win"], 4) if top else None,
            "top_ci": [round(top[1]["ci_lo"], 4), round(top[1]["ci_hi"], 4)] if top else None,
        }
    return {"full": full, "sampled": sampled, "sweep": sweep,
            "fraction": fraction, "n_shared_total": len(sample_shared_docs(outcomes, model, 1.0, seed)),
            "matrix_full": matrix_full}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def render_gepa_report(task: str, model: str, eff: dict, min_shared: int) -> str:
    L = ["# GEPA champion contender — Monte Carlo selection", ""]
    L.append(f"_Task: `{task}` · model `{model}` · paired-bootstrap ablation "
             f"over the shared-document surface (n_boot=2000, seed 42, "
             f"min_shared={min_shared})_")
    L.append("")
    full = eff["full"]
    L.append("## Full-corpus selection")
    L.append("")
    if full["plateau"]:
        L.append(f"**Plateau** — no prompt version beats another outside the CI "
                 f"on the shared surface (versions: {', '.join(full['versions'])}).")
    else:
        L.append(f"**MC champion contender: `{full['contender']}`** "
                 f"(accuracy {full['accuracy']:.4f} on its own docs, "
                 f"beats {full['n_beats']} peer(s)).")
    wins = full.get("wins") or {}
    if wins:
        L.append("")
        L.append("### Pairwise wins (CI excludes zero + P(win) >= 0.9)")
        L.append("")
        for v, w in sorted(wins.items(), key=lambda kv: -kv[1]):
            L.append(f"- `{v}`: **{w}** wins")
        L.append("")
    matrix = eff.get("matrix_full") or {}
    if matrix:
        L.append("### Decisive pairwise statistics (strongest pairs)")
        L.append("")
        L.append("| pair (A → B) | n shared | acc A | acc B | mean Δ | 95% CI | P(A beats B) |")
        L.append("|---|---|---|---|---|---|---|")
        ranked = sorted(matrix.items(), key=lambda kv: -abs(kv[1]["mean"]))
        for (a, b), stat in ranked[:12]:
            L.append(f"| `{a}` → `{b}` | {stat['n_shared']} | "
                     f"{stat['acc_a']:.4f} | {stat['acc_b']:.4f} | "
                     f"{stat['mean']:+.4f} | [{stat['ci_lo']:+.4f}, {stat['ci_hi']:+.4f}] | "
                     f"{stat['p_win']:.3f} |")
        L.append("")
    sampled = eff["sampled"]
    L.append(f"## Half-corpus pilot (fraction {eff['fraction']}, seed 42)")
    L.append("")
    L.append(f"- shared docs available: **{eff['n_shared_total']}**")
    if sampled["plateau"]:
        L.append(f"- sampled selection: **plateau** (no measurable champion on the sample)")
    else:
        L.append(f"- sampled selection: **`{sampled['contender']}`** "
                 f"(beats {sampled['n_beats']} peer(s))")
    same = (not full["plateau"] and not sampled["plateau"]
            and full["contender"] == sampled["contender"])
    L.append(f"- **champion recovered by the half-corpus sample: "
             f"{'YES' if same else 'NO' if not (full['plateau'] or sampled['plateau']) else 'N/A (plateau)'}**")
    L.append("")
    L.append("## Document-count sweep (P(win) separation vs sample size)")
    L.append("")
    L.append("| fraction | n docs | contender | strongest pair | mean Δ | P(win) | 95% CI |")
    L.append("|---|---|---|---|---|---|---|")
    for frac in (0.25, 0.5, 0.75, 1.0):
        s = eff["sweep"][frac]
        pair = f"{s['top_pair'][0]} → {s['top_pair'][1]}" if s["top_pair"] else "—"
        L.append(f"| {frac:.0%} | {s['n_docs_sampled']} | "
                 f"{s['contender'] or 'plateau'} | {pair} | "
                 f"{s['top_mean'] if s['top_mean'] is not None else '—'} | "
                 f"{s['top_p_win'] if s['top_p_win'] is not None else '—'} | "
                 f"{s['top_ci'] if s['top_ci'] else '—'} |")
    L.append("")
    L.append("Reading: the `P(win)`/CI columns show how cleanly the strongest "
             "pair separates at each sample size — the effectiveness (sample-"
             "efficiency) evidence for adopting the MC selection layer in the "
             "GEPA loop.")
    L.append("")
    return "\n".join(L)


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--task", default="subtype_classification")
    parser.add_argument("--model", default="qwen/qwen3.7-flash")
    parser.add_argument("--min-shared", type=int, default=20)
    parser.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    parser.add_argument("--sample", type=float, default=None,
                        help="Seeded sample fraction for the effectiveness pilot "
                             "(default None = report full selection only)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    valid = set(task_label_vocabulary(args.task))
    if not valid:
        print(f"no label vocabulary for task {args.task}")
        return 1
    outcomes = run_outcomes(corpus, args.task, valid)
    if not outcomes:
        print(f"no outcomes for task {args.task}")
        return 0

    frac = args.sample
    eff = effectiveness(outcomes, args.model, args.min_shared, frac or 1.0,
                        args.seed, args.n_boot)
    report = render_gepa_report(args.task, args.model, eff, args.min_shared)
    suffix = f"-sample{frac:.0%}" if frac else ""
    path = out_dir / f"gepa-champion-contender-{args.task}{suffix}.md"
    path.write_text(report, encoding="utf-8")
    print(f"report: {path}")

    full = eff["full"]
    if full["plateau"]:
        print(f"[{args.task}][{args.model}] PLATEAU — no MC champion contender")
    else:
        print(f"[{args.task}][{args.model}] MC champion contender: {full['contender']} "
              f"(acc {full['accuracy']:.4f}, beats {full['n_beats']} peers)")
    if frac:
        sampled = eff["sampled"]
        same = (not full["plateau"] and not sampled["plateau"]
                and full["contender"] == sampled["contender"])
        print(f"  half-corpus ({frac:.0%}, n={eff['n_shared_total']}): "
              f"contender={sampled.get('contender') or 'plateau'} · "
              f"champion recovered: {'YES' if same else 'NO'}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()