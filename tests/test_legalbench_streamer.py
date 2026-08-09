"""Tests for the LegalBench tasks streamer's pure logic (no network)."""

from scripts.datasets.stream_legalbench_tasks_to_bt import (
    build_prompt,
    build_records,
    parse_train_tsv,
    task_type_from_readme,
    valid_classes_for,
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
