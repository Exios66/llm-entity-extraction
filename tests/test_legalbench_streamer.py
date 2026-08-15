"""Tests for the LegalBench tasks streamer's pure logic (no network)."""

from scripts.datasets.stream_legalbench_tasks_to_bt import (
    build_prompt,
    build_records,
    normalize_hf_rows,
    parse_train_tsv,
    task_type_from_readme,
    valid_classes_for,
    write_local_jsonl,
)

MAUD_TSV = """index\tanswer\ttext
0\tA\teach Share shall be converted into the right to receive the Offer Price in cash
1\tB\tthe Merger Consideration shall consist of Company Common Stock
2\tC\teach share shall be converted into a mix of cash and stock
3\tD\teach share may be converted into cash or stock at the holder's election
"""

CUAD_TSV = """index\ttext\tanswer\tdocument_name
0\tThis AGREEMENT shall be governed by the laws of Delaware.\tYes\tDOC1.PDF
1\tThe parties agree to arbitrate in New York.\tNo\tDOC2.PDF
"""


def test_parse_train_tsv_maud():
    rows = parse_train_tsv("maud_type_of_consideration", MAUD_TSV)
    assert len(rows) == 4
    assert rows[0]["answer"] == "A"
    assert rows[0]["text"].startswith("each Share")
    assert rows[0]["index"] == "0"


def test_parse_train_tsv_cuad_extra_columns():
    rows = parse_train_tsv("cuad_governing_law", CUAD_TSV)
    assert len(rows) == 2
    assert rows[0]["document_name"] == "DOC1.PDF"
    assert rows[0]["slice"] == ""


def test_valid_classes_maud_letters():
    rows = parse_train_tsv("maud_type_of_consideration", MAUD_TSV)
    classes = valid_classes_for(rows, "4-way classification")
    assert classes == ["A", "B", "C", "D"]


def test_valid_classes_binary():
    rows = parse_train_tsv("cuad_governing_law", CUAD_TSV)
    classes = valid_classes_for(rows, "binary classification")
    assert classes == ["Yes", "No"]


def test_task_type_from_readme():
    readme = "**Task type**: 4-way classification\n\n**License**: CC By 4.0"
    assert task_type_from_readme(readme) == "4-way classification"
    assert task_type_from_readme("no type line") == ""


def test_build_prompt_fills_placeholder():
    prompt = "Question: X\n\nOption A: foo\nMerger Agreement: {{text}}\nAnswer:"
    filled = build_prompt(prompt, "some clause text")
    assert "some clause text" in filled
    assert "{{text}}" not in filled


def test_build_prompt_without_placeholder():
    filled = build_prompt("Just answer.", "clause")
    assert filled == "Just answer.\n\nclause"


def test_build_records_shape():
    rows = parse_train_tsv("cuad_governing_law", CUAD_TSV)
    meta = {
        "task": "cuad_governing_law",
        "rows": rows,
        "base_prompt": "Does the clause specify governing law?\n\nClause: {{text}}\nLabel:",
        "readme": "**Task type**: binary classification",
        "task_type": "binary classification",
        "valid_classes": valid_classes_for(rows, "binary classification"),
    }
    records = build_records(meta)
    assert len(records) == 2
    first = records[0]
    assert first["input"]["prompt"].startswith("Does the clause specify")
    assert first["input"]["prompt"].endswith("Label:")
    assert "laws of Delaware" in first["input"]["prompt"]
    assert first["expected"] == {"doc_type": "Yes"}
    assert first["metadata"]["valid_classes"] == ["Yes", "No"]
    assert first["input"]["metadata"]["task"] == "cuad_governing_law"


HF_TEST_ROWS = [
    {"index": 5, "answer": "No", "text": "On the issue of whether James is smart, the fact "
     "that James came first in his class in law school.", "slice": "Non-assertive conduct"},
    {"index": 6, "answer": "Yes", "text": "On the issue of whether Ava was angry, the fact "
     "that Ava screamed at the officer at the scene.", "slice": "Non-verbal hearsay"},
]


def test_normalize_hf_rows_maps_onto_train_shape():
    rows = normalize_hf_rows(HF_TEST_ROWS)
    assert len(rows) == 2
    assert rows[0]["answer"] == "No"
    assert rows[0]["slice"] == "Non-assertive conduct"
    assert rows[0]["document_name"] == ""
    assert rows[0]["text"].startswith("On the issue of whether James")


def test_normalize_hf_rows_drops_blank():
    rows = normalize_hf_rows(HF_TEST_ROWS + [{"index": 9, "answer": "", "text": ""}])
    assert len(rows) == 2


def test_build_records_from_hf_test_rows():
    """Test-split rows build the SAME record shape as train — clean, LegalBench-
    formatted inputs with the few-shot base_prompt filled in."""
    rows = normalize_hf_rows(HF_TEST_ROWS)
    meta = {
        "task": "hearsay",
        "rows": rows,
        "base_prompt": "Hearsay is an out-of-court statement.\n\nQ: {{text}} Is there hearsay?\nA:",
        "readme": "**Task type**: Binary classification",
        "task_type": "Binary classification",
        "valid_classes": valid_classes_for(rows, "Binary classification"),
    }
    records = build_records(meta)
    assert len(records) == 2
    assert records[0]["input"]["prompt"].endswith("Is there hearsay?\nA:")
    assert records[0]["input"]["prompt"].startswith("Hearsay is an out-of-court statement.")
    assert "Is there hearsay?" in records[0]["input"]["prompt"]
    assert records[0]["expected"] == {"doc_type": "No"}
    assert records[0]["metadata"]["valid_classes"] == ["No", "Yes"]
    assert records[0]["input"]["metadata"]["slice"] == "Non-assertive conduct"


def test_write_local_jsonl_roundtrip(tmp_path):
    """``write_local_jsonl`` (streamer --local-dump) emits exactly the record
    shape ``load_task_dataset`` (runner --task-dataset) consumes — so the local
    eval path carries the same LegalBench-formatted rows a Braintrust upload
    would, including the filled few-shot prompt."""
    rows = normalize_hf_rows(HF_TEST_ROWS)
    meta = {
        "task": "hearsay",
        "rows": rows,
        "base_prompt": "Hearsay is an out-of-court statement.\n\nQ: {{text}} Is there hearsay?\nA:",
        "readme": "**Task type**: Binary classification",
        "task_type": "Binary classification",
        "valid_classes": valid_classes_for(rows, "Binary classification"),
    }
    records = build_records(meta)
    path = tmp_path / "hearsay-test.jsonl"
    assert write_local_jsonl(records, path) == 2

    from scripts.eval.run_classification_eval import load_task_dataset

    loaded = load_task_dataset(path)
    assert len(loaded) == 2
    assert loaded[0]["filename"] == "hearsay_5.txt"
    assert loaded[0]["expected"] in ("No", "Yes")
    assert loaded[0]["prompt"].startswith("Hearsay is an out-of-court statement.")
    assert loaded[0]["prompt"].endswith("Is there hearsay?\nA:")
    assert loaded[0]["doc_text"].startswith("On the issue of whether James")
    assert loaded[0]["metadata"]["valid_classes"] == ["No", "Yes"]
    assert loaded[0]["metadata"]["slice"] == "Non-assertive conduct"

    filtered = load_task_dataset(path, valid={"Yes"})
    assert len(filtered) == 1
    assert filtered[0]["expected"] == "Yes"
