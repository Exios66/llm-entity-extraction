"""Network-free smoke tests for the same-scorer manifest re-scoring script."""

import json

from src.taxonomy import load_taxonomy


def _make_manifest(tmp_path, name, rows):
    path = tmp_path / name
    header = {"type": "header", "metadata": {"dataset": "mailroom-cuad-contracts",
                                             "dataset_fingerprint": "x" * 64,
                                             "dataset_size": len(rows)}}
    with open(path, "w") as f:
        f.write(json.dumps(header) + "\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def test_rescore_manifest_scores_rows(tmp_path, monkeypatch):
    import scripts.reporting.rescore_manifests as rm

    ct = next(dc["field_types"] for dc in load_taxonomy()["doc_classes"]
              if dc["key"] == "contract")
    path = _make_manifest(tmp_path, "extraction_ab_v18_50.jsonl", [
        {"filename": "a", "status": "completed",
         "predicted": {"parties": ["Acme, Inc."], "effective_date": "2020-01-01",
                       "key_obligations": ["Licensee shall not sublicense the Software."]},
         "expected_fields": {"parties": ["Acme, Inc."], "effective_date": "1/1/20",
                             "key_obligations": ["Licensee shall not sublicense the Software."]}},
        {"filename": "b", "status": "completed",
         "predicted": {"parties": [], "effective_date": None, "key_obligations": []},
         "expected_fields": {"parties": ["Acme, Inc."], "effective_date": "1/1/20",
                             "key_obligations": ["Licensee shall not sublicense the Software."]}},
        {"filename": "c", "status": "error", "predicted": {}, "expected_fields": {}},
    ])
    stats = rm.rescore_manifest(path, ct)
    assert stats["rows"] == 2          # the error row is skipped
    assert stats["skipped"] == 1
    assert stats["overall"] is not None
    assert 0 <= stats["overall"] <= 1
    assert stats["fields"]["parties"] == 0.5  # 1.0 (row a) + 0.0 (row b) -> mean 0.5
    assert stats["fields"]["effective_date"] == 0.5  # 1.0 (exact parse) + 0.0 (None) -> mean 0.5


def test_rescore_manifest_report_file(tmp_path, monkeypatch, capsys):
    import scripts.reporting.rescore_manifests as rm

    path = _make_manifest(tmp_path, "extraction_ab_v18_50.jsonl", [
        {"filename": "a", "status": "completed",
         "predicted": {"effective_date": "2020-01-01"},
         "expected_fields": {"effective_date": "1/1/20"}},
    ])
    out = tmp_path / "report.json"
    rc = rm.main_with_args(["--manifest", str(path), "--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert "v18" in report
    assert report["v18"]["rows"] == 1
    assert report["v18"]["fields"]["effective_date"] == 1.0
    printed = capsys.readouterr().out
    assert "overall" in printed
