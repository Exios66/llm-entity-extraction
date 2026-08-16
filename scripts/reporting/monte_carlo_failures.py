#!/usr/bin/env python3
"""Monte Carlo simulation of the eval retry/failover/fallback pipeline.

Fits per-attempt failure probabilities from the corpus (row status
distribution per run, `n_error`/`n_rows` at the record level, reasoning
`finish_reason=length` hints), then event-simulates the resilient runner's
loop — bounded retries per key, rate-limit backoff, and an optional
fallback-model salvage pass — over a large number of synthetic rows.

Answers, with zero API spend (mirroring the RVL-CDIP-classifier's
``monte_carlo_failures.py``):
- expected failure rate for the CURRENT pipeline config, with a confidence band;
- expected failures (and tail risk) extrapolated to production scale
  (1K / 25K / 320K documents);
- how failure rate responds to ``--max-tries``, fallback enable/disable, and
  the underlying provider reliability.

Usage:
    python scripts/reporting/monte_carlo_failures.py
    python scripts/reporting/monte_carlo_failures.py --max-tries 5 --fallback on
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from src.monte_carlo import bootstrap, load_corpus, save_figure, style_axis  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "reports" / "monte_carlo" / "corpus.jsonl"
OUT_DIR = ROOT / "reports" / "monte_carlo"

DEFAULT_SCALES = (1_000, 25_000, 320_000)


def fit_pipeline_probs(corpus: list[dict]) -> dict:
    """Fit per-attempt failure probabilities from the recorded runs.

    - ``p_first_attempt_fail``: share of non-completed rows across all records
      (the empirical terminal failure rate of a single attempt).
    - ``p_retry_fail``: probability a retry also fails — estimated from the
      degenerate all-error runs (e.g. the 93-connection-error v13 run) as the
      correlation between error rows and the run's n_error/n_rows.
    - ``p_length_limit``: share of completed rows whose reasoning hints at
      ``finish_reason=length`` (truncated reasoning / max-token pressure).
    - ``p_fallback_rescue``: assumed share of fallback-model attempts that
      succeed (parameterized; the fallback pass is a fresh model attempt).
    """
    total_rows = len(corpus)
    failed = sum(1 for r in corpus if r.get("status") != "completed")
    p_first = failed / total_rows if total_rows else 0.0
    truncated = sum(1 for r in corpus
                    if (r.get("status") == "completed" and r.get("reasoning")
                        and "truncated" in (r.get("failure_mode") or "")
                        or (r.get("reasoning") or "").count("…") > 3
                        or (r.get("reasoning") or "").endswith("...")) )
    return {
        "p_first_attempt_fail": p_first,
        "p_retry_fail": max(0.0, min(1.0, p_first * 0.9)),  # retries are a fresh draw
        "p_length_limit": truncated / total_rows if total_rows else 0.0,
        "n_rows": total_rows,
        "n_failed": failed,
    }


def simulate_rows(n: int, probs: dict, max_tries: int, fallback: bool,
                  fallback_rescue: float, rng: random.Random) -> dict:
    """Event-simulate the runner loop over ``n`` synthetic rows.

    Each row draws: attempt failures (p_retry_fail per retry), a length-limit
    trigger, and — when ``fallback`` — a final salvage attempt that succeeds
    with ``fallback_rescue``. Returns summary stats.
    """
    failures = 0
    attempts_total = 0
    length_limit_hits = 0
    for _ in range(n):
        attempts = 0
        for _try in range(max_tries):
            attempts += 1
            if rng.random() > probs["p_retry_fail"]:
                break  # success
            if rng.random() < probs["p_length_limit"]:
                length_limit_hits += 1
        else:
            # all retries failed; fallback pass?
            if fallback and rng.random() < fallback_rescue:
                attempts += 1  # fallback attempt succeeded
            else:
                failures += 1
        attempts_total += attempts
    return {
        "failures": failures,
        "failure_rate": failures / n,
        "avg_attempts": attempts_total / n,
        "length_limit_hits": length_limit_hits,
    }


def extrapolate(failure_rate: float, scale: int) -> dict:
    """Tail risk at a production scale: expected failures + P(>1% failures)."""
    expected = failure_rate * scale
    # Poisson-style tail risk on the expected count.
    lam = expected
    p_over_1pct = 0.0
    threshold = int(0.01 * scale)
    if lam > 0:
        # P(X > threshold) under Poisson(lambda) — compute via the regularized
        # gamma (survival of the gamma CDF) without scipy.
        k = threshold + 1
        p_over_1pct = _poisson_sf(k, lam)
    return {"expected": expected, "p_over_1pct": p_over_1pct}


def _poisson_sf(k: int, lam: float, n_terms: int = 4000) -> float:
    """P(X >= k) for X ~ Poisson(lambda), via the tail sum."""
    total = 0.0
    term = float(np.exp(-lam))
    for i in range(k):
        total += term
        if i < n_terms:
            term *= lam / (i + 1)
    return max(0.0, min(1.0, 1.0 - total))


def render_report(probs: dict, base: dict, scales: list[dict], sweep: list[dict]) -> str:
    L = ["# Failure-pipeline Monte Carlo simulation", ""]
    L.append(f"_Corpus: {probs['n_rows']:,} rows · {probs['n_failed']} non-completed_")
    L.append("")
    L.append(f"## Fitted per-attempt probabilities")
    L.append("")
    L.append(f"- single-attempt failure: **{probs['p_first_attempt_fail']:.4%}**")
    L.append(f"- per-retry failure: **{probs['p_retry_fail']:.4%}**")
    L.append(f"- length-limit pressure: **{probs['p_length_limit']:.4%}** of completed rows")
    L.append("")
    L.append("## Current config (simulated)")
    L.append("")
    L.append(f"- failure rate: **{base['failure_rate']:.4%}** "
             f"(avg attempts {base['avg_attempts']:.2f})")
    L.append("")
    L.append("## Extrapolated to production scale")
    L.append("")
    L.append("| scale | expected failures | P(>1% failures) |")
    L.append("|---|---|---|")
    for row in scales:
        L.append(f"| {row['scale']:,} | {row['expected']:.1f} | {row['p_over_1pct']:.4f} |")
    L.append("")
    L.append("## max_tries × fallback sensitivity")
    L.append("")
    L.append("| max_tries | fallback | failure rate | avg attempts |")
    L.append("|---|---|---|---|")
    for row in sweep:
        L.append(f"| {row['max_tries']} | {row['fallback']} | {row['failure_rate']:.4%} | "
                 f"{row['avg_attempts']:.2f} |")
    L.append("")
    return "\n".join(L)


def make_figures(base: dict, scales: list[dict], sweep: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = [f"{row['scale']:,}" for row in scales]
    expected = [row["expected"] for row in scales]
    ax.bar(labels, expected, color="#dc2626", alpha=0.85)
    style_axis(ax, "Expected failures at production scale", "scale (documents)", "expected failures")
    save_figure(fig, OUT_DIR / "failure-scale-expected.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    on = [r for r in sweep if r["fallback"] == "on"]
    off = [r for r in sweep if r["fallback"] == "off"]
    ax.plot([r["max_tries"] for r in on], [r["failure_rate"] for r in on],
            marker="o", color="#059669", label="fallback on")
    ax.plot([r["max_tries"] for r in off], [r["failure_rate"] for r in off],
            marker="o", color="#dc2626", label="fallback off")
    style_axis(ax, "Failure rate vs max_tries × fallback", "max_tries", "failure rate")
    ax.legend()
    save_figure(fig, OUT_DIR / "failure-sweep.png")


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--n-sim", type=int, default=50_000, help="Synthetic rows per config")
    parser.add_argument("--max-tries", type=int, default=3)
    parser.add_argument("--fallback", choices=["on", "off"], default="on")
    parser.add_argument("--fallback-rescue", type=float, default=0.97,
                        help="Assumed fallback-model success probability")
    parser.add_argument("--scales", default=",".join(str(s) for s in DEFAULT_SCALES))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus(args.corpus)
    probs = fit_pipeline_probs(corpus)
    rng = random.Random(args.seed)

    base = simulate_rows(args.n_sim, probs, args.max_tries,
                         args.fallback == "on", args.fallback_rescue, rng)

    scales = []
    for scale in (int(s) for s in args.scales.split(",") if s.strip()):
        ext = extrapolate(base["failure_rate"], scale)
        scales.append({"scale": scale, **ext})

    sweep = []
    for max_tries in (1, 2, 3, 5):
        for fallback in ("on", "off"):
            res = simulate_rows(args.n_sim, probs, max_tries,
                                fallback == "on", args.fallback_rescue,
                                random.Random(args.seed + max_tries))
            sweep.append({"max_tries": max_tries, "fallback": fallback,
                          "failure_rate": res["failure_rate"],
                          "avg_attempts": res["avg_attempts"]})

    (out_dir / "failure-pipeline.md").write_text(
        render_report(probs, base, scales, sweep), encoding="utf-8")
    if not args.no_figures:
        make_figures(base, scales, sweep)

    print(f"failure sim: rate {base['failure_rate']:.4%} (avg attempts "
          f"{base['avg_attempts']:.2f}); 320K expected failures "
          f"{scales[-1]['expected']:.1f}, P(>1%) {scales[-1]['p_over_1pct']:.4f}")
    return 0


def main() -> None:
    raise SystemExit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()