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
