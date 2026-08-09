"""Tests for full-document (multi-page) vision classification.

One dataset row = ONE PDF with ALL its pages; the sorter sends every page to
the model in a SINGLE vision call (no per-page calls, no voting).
"""

from agents.sorter_agent import SorterAgent


def test_classify_document_sends_all_pages_in_one_call(mocker):
    sorter = SorterAgent(prompt_version="sorter_vision_v0")
    mock = mocker.patch.object(
        sorter,
        "_call_vision_multi",
        return_value="<label>contract</label>\n<confidence>94</confidence>\n"
                     "<reasoning>full agreement visible across pages</reasoning>",
    )
    result = sorter.classify_document(["page1", "page2", "page3"], image_format="png")
    assert result["doc_type"] == "contract"
    assert result["confidence"] == 0.94
    assert "full agreement" in result["reasoning"]
    # All three pages in ONE call.
    assert len(mock.call_args.kwargs["images"]) == 3
    assert mock.call_args.kwargs["images"][0] == ("page1", "png")
    assert mock.call_args.kwargs["images"][2] == ("page3", "png")


def test_classify_document_prompt_split(mocker):
    sorter = SorterAgent(prompt_version="sorter_vision_v0")
    mock = mocker.patch.object(
        sorter,
        "_call_vision_multi",
        return_value="<label>contract</label>\n<confidence>90</confidence>\n<reasoning>ok</reasoning>",
    )
    sorter.classify_document(["p1"])
    kwargs = mock.call_args.kwargs
    assert "Scratchpad" in kwargs["system_prompt"]  # the checks/scratchpad intro
    assert "Worked example" in kwargs["user_text"]  # the output contract + examples


def test_classify_document_empty_input():
    sorter = SorterAgent(prompt_version="sorter_vision_v0")
    result = sorter.classify_document([])
    assert result["doc_type"] == "correspondence"
    assert result["confidence"] == 0.0


def test_classify_document_invalid_label_falls_back(mocker):
    sorter = SorterAgent(prompt_version="sorter_vision_v0")
    mocker.patch.object(
        sorter, "_call_vision_multi", return_value="<label>banana</label>\n<confidence>80</confidence>"
    )
    result = sorter.classify_document(["p1"])
    assert result["doc_type"] == "correspondence"


def test_classify_document_missing_confidence_defaults(mocker):
    sorter = SorterAgent(prompt_version="sorter_vision_v0")
    mocker.patch.object(
        sorter, "_call_vision_multi", return_value="<label>court_opinion</label>\nno confidence here"
    )
    result = sorter.classify_document(["p1"])
    assert result["doc_type"] == "court_opinion"
    assert result["confidence"] == 0.5


def test_pdf_dir_loader_renders_all_pages(monkeypatch, tmp_path):
    import base64

    from scripts.eval.run_classification_eval import load_local_pdfs

    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "a.pdf").write_bytes(b"fake-pdf-1")
    (pdfs / "b.pdf").write_bytes(b"fake-pdf-2")

    def fake_pdf_to_png(pdf_bytes, page_num=0, target_size=(1024, 1024)):
        if page_num >= 2:
            raise ValueError("no more pages")
        return b"\x89PNG-page" + bytes([page_num])

    monkeypatch.setattr("src.image_utils.pdf_to_png_bytes", fake_pdf_to_png)
    records = load_local_pdfs(pdfs, "contract")
    assert len(records) == 2  # one row per PDF, no matter its size
    first = records[0]
    assert first["filename"] == "a.pdf"
    assert first["expected"] == "contract"
    assert first["page_count"] == 2
    decoded = [base64.b64decode(p) for p in first["pages_b64"]]
    assert decoded[0].endswith(b"\x00")
    assert decoded[1].endswith(b"\x01")
