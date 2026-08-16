# Failure-pipeline Monte Carlo simulation

_Corpus: 17,691 rows · 42 non-completed_

## Fitted per-attempt probabilities

- single-attempt failure: **0.2374%**
- per-retry failure: **0.2137%**
- length-limit pressure: **0.0057%** of completed rows

## Current config (simulated)

- failure rate: **0.0000%** (avg attempts 1.00)

## Extrapolated to production scale

| scale | expected failures | P(>1% failures) |
|---|---|---|
| 1,000 | 0.0 | 0.0000 |
| 25,000 | 0.0 | 0.0000 |
| 320,000 | 0.0 | 0.0000 |

## max_tries × fallback sensitivity

| max_tries | fallback | failure rate | avg attempts |
|---|---|---|---|
| 1 | on | 0.0040% | 1.00 |
| 1 | off | 0.2020% | 1.00 |
| 2 | on | 0.0000% | 1.00 |
| 2 | off | 0.0000% | 1.00 |
| 3 | on | 0.0000% | 1.00 |
| 3 | off | 0.0000% | 1.00 |
| 5 | on | 0.0000% | 1.00 |
| 5 | off | 0.0000% | 1.00 |
