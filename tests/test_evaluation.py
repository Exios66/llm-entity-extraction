"""Tests for evaluation validation, fingerprints, and manifests."""

import pytest

from src.evaluation import ManifestStore, dataset_fingerprint, validate_dataset


def test_validate_dataset_ok(sample_dataset_rows):
    validate_dataset(sample_dataset_rows)


def test_validate_dataset_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_dataset([])


def test_validate_dataset_missing_filename():
    with pytest.raises(ValueError, match="no filename"):
        validate_dataset([{"expected": "contract"}])


def test_validate_dataset_duplicate_filename(sample_dataset_rows):
    rows = sample_dataset_rows + [dict(sample_dataset_rows[0])]
    with pytest.raises(ValueError, match="duplicate"):
        validate_dataset(rows)


def test_validate_dataset_invalid_class(sample_dataset_rows):
    rows = [dict(sample_dataset_rows[0], expected="banana")]
    with pytest.raises(ValueError, match="invalid expected"):
        validate_dataset(rows)


def test_validate_dataset_custom_labels():
    rows = [{"filename": "a.txt", "expected": "positive"}]
    validate_dataset(rows, valid={"positive", "negative"})


def test_fingerprint_stable_and_distinct(sample_dataset_rows):
    fp1 = dataset_fingerprint(sample_dataset_rows)
    fp2 = dataset_fingerprint(sample_dataset_rows)
    assert fp1 == fp2
    assert len(fp1) == 64
    shuffled = list(reversed(sample_dataset_rows))
    assert dataset_fingerprint(shuffled) != fp1


def test_manifest_roundtrip(tmp_path, sample_dataset_rows):
    meta = {"experiment_name": "qwen_p_sorter_v0", "dataset_size": 4}
    path = tmp_path / "run.jsonl"
    store = ManifestStore(path, meta)
    store.initialize()
    assert path.exists()
    store.append({"filename": "a.txt", "status": "completed", "predicted": "contract"})
    store.append({"filename": "b.txt", "status": "completed", "predicted": "correspondence"})

    reloaded = ManifestStore(path, meta)
    assert reloaded.reused is True
    assert reloaded.get_completed("a.txt")["predicted"] == "contract"
    assert reloaded.get_completed("missing.txt") is None


def test_manifest_metadata_mismatch_rejected(tmp_path):
    path = tmp_path / "run.jsonl"
    ManifestStore(path, {"a": 1}).initialize()
    with pytest.raises(ValueError, match="does not match"):
        ManifestStore(path, {"a": 2})


# ---------------------------------------------------------------------------
# Adaptive concurrency (sample-size scaling) + rate-limit retry
# ---------------------------------------------------------------------------


def test_resolve_concurrency_explicit_wins():
    from src.evaluation import resolve_concurrency

    assert resolve_concurrency(676, requested=4) == 4
    assert resolve_concurrency(30, requested=64) == 64
    assert resolve_concurrency(676, requested=None) > 8


def test_resolve_concurrency_scales_with_sample_size():
    from src.evaluation import resolve_concurrency

    # auto formula: min(ceiling, max(1, min(floor + ceil(n/step), n)))
    assert resolve_concurrency(1) == 1          # never more workers than rows
    assert resolve_concurrency(5) == 5
    assert resolve_concurrency(8) == 8          # floor
    assert resolve_concurrency(30) == 10        # 8 + ceil(30/25)
    assert resolve_concurrency(50) == 10
    assert resolve_concurrency(200) == 16
    assert resolve_concurrency(500) == 28
    assert resolve_concurrency(676) == 32       # ceiling: diminishing returns
    assert resolve_concurrency(5000) == 32      # hard cap


def test_resolve_concurrency_monotonic_and_bounded():
    from src.evaluation import CONCURRENCY_MAX, resolve_concurrency

    prev = 0
    for n in range(0, 700, 25):
        w = resolve_concurrency(n)
        assert 1 <= w <= CONCURRENCY_MAX
        assert w >= prev  # more rows never yield fewer workers
        prev = w


def test_rate_limit_retry_succeeds_after_429(monkeypatch):
    import time

    from src.evaluation import call_with_rate_limit_retry

    calls = {"n": 0}
    real_sleep = time.sleep
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)
        real_sleep(0)  # do not actually wait in tests

    monkeypatch.setattr(time, "sleep", fake_sleep)

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("OpenRouter: 429 Too Many Requests - rate limit exceeded")
        return "ok"

    stats = {}
    result = call_with_rate_limit_retry(flaky, retries=4, stats=stats)
    assert result == "ok"
    assert calls["n"] == 3
    assert stats["rate_limit_retries"] == 2
    assert slept and slept[0] > 0  # exponential backoff actually waited


def test_rate_limit_retry_gives_up_and_non_rate_errors_raise():
    from src.evaluation import call_with_rate_limit_retry

    calls = {"n": 0}

    def always_429():
        calls["n"] += 1
        raise RuntimeError("Rate limit reached")

    with pytest.raises(RuntimeError, match="Rate limit"):
        call_with_rate_limit_retry(always_429, retries=2)
    assert calls["n"] == 3  # initial + 2 retries

    def other_error():
        raise ValueError("a real bug")

    with pytest.raises(ValueError, match="real bug"):
        call_with_rate_limit_retry(other_error, retries=4)
