"""Network-free tests for the EDGAR S-1 exhibit streamer
(scripts/datasets/stream_s1_exhibits.py).

Covers the exhibit-table parser, HTML->text stripping, content-based
record-type detection (the doc_subclass GT), and the record builder. The
live EDGAR mechanics (FTS search, filing index, exhibit download) were
verified against sec.gov during development and are NOT exercised here.
"""

from __future__ import annotations

import json

from scripts.datasets.stream_s1_exhibits import (
    build_exhibit_records,
    detect_record_type,
    parse_filing_index_table,
    strip_html,
    write_local_jsonl,
)

INDEX_HTML = """
<html><body><table class="tableFile">
<tr><td>1</td><td>S-1</td><td><a href="d1.htm">d1.htm</a></td><td>S-1</td></tr>
<tr><td>2</td><td>EXHIBIT 3.1</td><td><a href="ex31.htm">ex31.htm</a></td><td>EX-3.1</td></tr>
<tr><td>3</td><td>EXHIBIT 3.2</td><td><a href="ex32.htm">ex32.htm</a></td><td>EX-3.2</td></tr>
<tr><td>4</td><td>EXHIBIT 3.3</td><td><a href="ex33.htm">ex33.htm</a></td><td>EX-3.3</td></tr>
<tr><td>5</td><td>EXHIBIT 4.1</td><td><a href="ex41.htm">ex41.htm</a></td><td>EX-4.1</td></tr>
<tr><td>6</td><td>EXHIBIT 10.1</td><td><a href="ex101.htm">ex101.htm</a></td><td>EX-10.1</td></tr>
<tr><td>7</td><td>EXHIBIT 24.1</td><td><a href="ex241.htm">ex241.htm</a></td><td>EX-24.1</td></tr>
</table></body></html>
"""


def test_parse_filing_index_table():
    rows = parse_filing_index_table(INDEX_HTML)
    # Only EXHIBIT rows are kept; the S-1 main document row is not.
    assert len(rows) == 6
    by_type = {r["exhibit_type"]: r for r in rows}
    assert by_type["EX-3.1"]["filename"] == "ex31.htm"
    assert by_type["EX-3.1"]["description"] == "EXHIBIT 3.1"
    # href preserved for archive-path-correct downloads
    assert by_type["EX-10.1"]["href"].endswith("ex101.htm")
    assert by_type["EX-3.2"]["href"]


def test_strip_html():
    html = "<html><head><style>body{}</style></head><body><p>BYLAWS&nbsp;OF</p><p>ACME&nbsp;INC.</p><script>var x=1;</script></body></html>"
    text = strip_html(html)
    assert "BYLAWS" in text and "ACME" in text
    assert "var x" not in text and "style" not in text
    assert "&nbsp;" not in text


def test_detect_record_type_content_based():
    """The record type comes from the DOCUMENT's own title — the EDGAR exhibit
    code is NOT 1:1 with the record type."""
    assert detect_record_type("EXHIBIT 3.1 Certificate of Formation of Ampex LLC under the Delaware LLC Act", "EX-3.1") == "certificate_of_formation"
    assert detect_record_type("EXHIBIT 3.2 CERTIFICATE OF INCORPORATION OF ACURX INC. The undersigned", "EX-3.2") == "articles_of_incorporation"
    assert detect_record_type("ACURX INC. BYLAWS Table of Contents ARTICLE I", "EX-3.3") == "bylaws"
    assert detect_record_type("AMENDED AND RESTATED CERTIFICATE OF INCORPORATION OF XYZ INC.", "EX-3.1") == "articles_of_incorporation"
    assert detect_record_type("CERTIFICATE OF AMENDMENT OF THE CERTIFICATE OF INCORPORATION", "EX-3.1") == "charter_amendment"
    assert detect_record_type("POWER OF ATTORNEY KNOW ALL MEN BY THESE PRESENTS", "EX-24.1") == "powers_of_attorney"
    assert detect_record_type("SUBSIDIARIES OF THE REGISTRANT", "EX-21.1") == "subsidiary_list"
    assert detect_record_type("INDENTURE between Issuer and Trustee dated as of", "EX-25.1") == "indenture"
    assert detect_record_type("INSTRUMENT DEFINING THE RIGHTS OF SECURITY HOLDERS", "EX-4.1") == "rights_instrument"
    assert detect_record_type("BYLAWS OF ACME CORPORATION", "EX-99.1") == "bylaws"  # code irrelevant
    assert detect_record_type("some unrelated letter text", "EX-99.1") == "other"


def test_build_exhibit_records():
    rows = [
        {"text": "EXHIBIT 3.2 CERTIFICATE OF INCORPORATION OF ACURX INC.", "filename": "ex32.htm",
         "exhibit_type": "EX-3.2", "description": "EXHIBIT 3.2", "href": "/x/ex32.htm",
         "accession": "0001104659-21-072553", "cik": "0001736246", "filer": "ACURX",
         "filing_date": "2021-05-27"},
    ]
    records = build_exhibit_records(rows)
    assert len(records) == 1
    r = records[0]
    assert r["expected"]["doc_type"] == "corporate_record"
    assert r["expected"]["doc_subclass"] == "articles_of_incorporation"
    assert r["metadata"]["exhibit_type"] == "EX-3.2"
    assert r["input"]["metadata"]["expected_subclass"] == "articles_of_incorporation"
    assert r["metadata"]["license"] == "public_domain"


def test_write_local_jsonl_shape(tmp_path):
    rows = [
        {"text": "BYLAWS OF ACME", "filename": "bylaws.htm", "exhibit_type": "EX-3.2",
         "description": "EXHIBIT 3.2", "href": "/x/bylaws.htm", "accession": "A",
         "cik": "C", "filer": "ACME", "filing_date": "2021-01-01"},
    ]
    path = tmp_path / "corporate-records.jsonl"
    n = write_local_jsonl(build_exhibit_records(rows), path)
    assert n == 1
    row = json.loads(path.read_text().strip())
    assert row["expected"] == "corporate_record"
    assert row["expected_subclass"] == "bylaws"
    assert row["metadata"]["exhibit_type"] == "EX-3.2"
