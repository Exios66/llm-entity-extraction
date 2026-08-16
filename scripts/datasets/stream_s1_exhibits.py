#!/usr/bin/env python3
"""Stream EDGAR S-1 registration-statement corporate-record exhibits.

S-1 registration statements attach the registrant's corporate charter
documents as exhibits: certificate of incorporation (EX-3.1), bylaws
(EX-3.2/3.3), instruments defining rights of securityholders (EX-4.x),
subsidiary lists (EX-21.x), powers of attorney (EX-24.x) and indentures
(EX-25.x). This script discovers those exhibits, extracts their text, and
builds the ``mailroom-s1-corporate-records`` dataset: ground truth
``doc_type: corporate_record`` with a content-detected ``doc_subclass``
(record type). The EDGAR exhibit code stays in metadata — provenance, not a
classification dimension (human directive, KANBAN-033: tertiary granularity
only where the data necessitates it).

Discovery pipeline (verified live 2026-08-15):
1. SEC full-text search (``efts.sec.gov``) for S-1 exhibit documents by
   exhibit description (``q="EXHIBIT 3.1"`` etc., ``forms=S-1``).
2. Each hit -> the filing's ``-index.html`` (the human-readable filing
   index), whose table maps exhibit descriptions to files + EDGAR types.
3. Corporate-record exhibits are downloaded (the index hrefs carry the
   correct archive path — CIK folders can differ from the search hit) and
   HTML-stripped into plain text.

The S-1 exhibit texts are born-digital for modern filings; older filings may
be image scans (skipped when text extraction yields too little content).

Usage:
    python scripts/datasets/stream_s1_exhibits.py --dry-run
    python scripts/datasets/stream_s1_exhibits.py --limit 20 --local-dump data/s1_corporate_records/
    python scripts/datasets/stream_s1_exhibits.py --exhibit-types "3.x,4.x,24.x"
    python scripts/datasets/stream_s1_exhibits.py --max-filings 10 --limit 5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.env_utils import require_env  # noqa: E402

# ---------------------------------------------------------------------------
# EDGAR access (fair-access: rate limited, identifiable UA)
# ---------------------------------------------------------------------------
EDGAR_FTS = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVE = "https://www.sec.gov/Archives"
REQUEST_INTERVAL = 0.22  # SEC fair access: ~10 req/s max, stay well under

# Corporate-record exhibit families (S-1 exhibits that are corporate records).
CORPORATE_RECORD_EXHIBIT_RE = re.compile(r"^EX-(3\.\d|4\.\d|21\.\d|24\.\d|25\.\d)$")
EXHIBIT_TYPE_ALIASES = {"3.x": r"3\.\d", "4.x": r"4\.\d", "21.x": r"21\.\d",
                        "24.x": r"24\.\d", "25.x": r"25\.\d"}

# ---------------------------------------------------------------------------
# Corporate-record subclasses (content-detected record type)
# ---------------------------------------------------------------------------
RECORD_TYPE_SUBCLASSES = [
    {"key": "bylaws", "label": "Bylaws",
     "description": "Corporate bylaws (EX-3.2/3.3 conventions)"},
    {"key": "articles_of_incorporation", "label": "Articles / Certificate of Incorporation",
     "description": "Charter, incl. amended and restated certificates (EX-3.1/3.2)"},
    {"key": "certificate_of_formation", "label": "Certificate of Formation",
     "description": "LLC formation certificate (EX-3.1)"},
    {"key": "charter_amendment", "label": "Charter Amendment",
     "description": "Certificate of amendment to the charter"},
    {"key": "powers_of_attorney", "label": "Power(s) of Attorney",
     "description": "Board/officer powers of attorney authorizing filing signatures (EX-24.x)"},
    {"key": "subsidiary_list", "label": "Subsidiary List",
     "description": "List of subsidiaries of the registrant (EX-21.x)"},
    {"key": "rights_instrument", "label": "Rights Instrument",
     "description": "Instruments defining rights of securityholders (EX-4.x)"},
    {"key": "indenture", "label": "Indenture",
     "description": "Debt indentures and supplemental indentures (EX-25.x)"},
    {"key": "board_resolution", "label": "Board Resolution / Written Consent",
     "description": "Board resolutions, written consents, unanimous consents"},
    {"key": "officer_certificate", "label": "Officer Certificate",
     "description": "Officer's certificates (e.g. of incumbency)"},
    {"key": "other", "label": "Other Corporate Record",
     "description": "Corporate record not matching a listed family"},
]
RECORD_TYPE_UNKNOWN = "other"


def _session():
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": os_environ_user_agent(),
    })
    return session


def os_environ_user_agent() -> str:
    """A SEC-compliant identifying User-Agent (env override supported).

    SEC's edge rejects User-Agents with parenthetical URLs (403); the
    compliant form is ``<app> <contact>`` — keep it plain. Override with
    ``EDGAR_USER_AGENT`` for a production identity.
    """
    import os

    return os.environ.get(
        "EDGAR_USER_AGENT",
        "llm-entity-extraction research contact@example.com",
    )


class _Throttle:
    """Minimal SEC fair-access throttle: one request per interval."""

    def __init__(self, interval: float = REQUEST_INTERVAL):
        self._interval = interval
        self._last = 0.0

    @property
    def interval(self) -> float:
        """Expose the throttle interval (tests use it to bound sleeps)."""
        return self._interval

    def wait(self) -> None:
        delta = self._last + self._interval - time.time()
        if delta > 0:
            time.sleep(delta)
        self._last = time.time()


def get_with_retry(session, url: str, retries: int = 4) -> str:
    """GET with SEC fair-access backoff (403/429 -> exponential retry).

    SEC's edge rejects bursty request patterns with 403 even when the
    per-second rate is legal; a short backoff with jitter clears it. The
    caller's throttle is applied per attempt, so retries never pile up.
    """
    import random

    delay = 1.0
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code in (403, 429):
                raise requests.HTTPError(f"{resp.status_code} for {url}")
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            time.sleep(delay + random.random() * delay)
            delay *= 2
    raise RuntimeError("unreachable")


def fetch_fts_exhibit_hits(session, query: str, forms: str, size: int) -> list[dict]:
    """Query the SEC full-text search for exhibit documents in S-1 filings.

    The exhibit description is a quoted PHRASE query — SEC's search requires
    the quote (unquoted multi-word queries are rejected with 403 as a bot
    filter)."""
    url = EDGAR_FTS + "?" + urllib.parse.urlencode(
        {"q": f'"{query}"', "forms": forms, "size": size})
    data = json.loads(get_with_retry(session, url))
    return [h["_source"] for h in data.get("hits", {}).get("hits", [])]


def parse_filing_index_table(html: str) -> list[dict]:
    """Parse a filing ``-index.html`` table into exhibit rows.

    Each row: ``{description, filename, exhibit_type, href}`` where href is
    the SEC archive path for the exhibit file (the archive CIK folder can
    differ from the search hit's CIK — the href is authoritative).
    """
    import html as _html

    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [_html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 3 or not cells[1].startswith("EXHIBIT"):
            continue
        href = re.search(r'href="([^"]+)"', tr)
        rows.append({
            "description": cells[1],
            "filename": cells[2] if len(cells) > 2 else "",
            "exhibit_type": cells[3] if len(cells) > 3 else "",
            "href": href.group(1) if href else "",
        })
    return rows


def strip_html(text: str) -> str:
    """Crude-but-effective HTML -> plain text (SEC exhibits are simple HTML)."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def detect_record_type(text: str, exhibit_type: str) -> str:
    """Content-detect the corporate-record subclass from the exhibit text.

    The EDGAR exhibit code is NOT 1:1 with the record type (EX-3.2 can hold
    bylaws OR a certificate of incorporation depending on filer convention),
    so the subclass comes from the document's own title/head, with the
    exhibit type only as a fallback tie-breaker (EX-4.x -> rights instrument).
    """
    head = re.sub(r"\s+", " ", text[:3000].upper())
    body = re.sub(r"\s+", " ", text[:12000].upper())

    def has(*patterns: str) -> bool:
        return any(p in body for p in patterns)

    if has("LIST OF SUBSIDIARIES", "SUBSIDIARIES OF"):
        return "subsidiary_list"
    if has("POWER OF ATTORNEY"):
        return "powers_of_attorney"
    if has("CERTIFICATE OF AMENDMENT", "AMENDMENT TO THE CERTIFICATE OF",
           "AMENDED AND RESTATED CERTIFICATE OF INCORPORATION OF"):
        # charter amendments and restatements (the restatement itself IS a
        # charter — the head distinguishes "AMENDED AND RESTATED ... OF"
        # restatements from true amendments below).
        if "CERTIFICATE OF AMENDMENT" in body:
            return "charter_amendment"
        return "articles_of_incorporation"
    if has("CERTIFICATE OF FORMATION"):
        return "certificate_of_formation"
    if has("CERTIFICATE OF INCORPORATION", "ARTICLES OF INCORPORATION"):
        return "articles_of_incorporation"
    if re.search(r"\bBYLAWS\b", head):
        return "bylaws"
    if has("INDENTURE"):
        return "indenture"
    if exhibit_type and exhibit_type.startswith("EX-4"):
        return "rights_instrument"
    if has("WRITTEN CONSENT", "UNANIMOUS CONSENT", "BOARD RESOLUTION", "RESOLUTIONS OF"):
        return "board_resolution"
    if has("OFFICER'S CERTIFICATE", "OFFICER'S CERTIFICATES", "CERTIFICATE OF OFFICER"):
        return "officer_certificate"
    return RECORD_TYPE_UNKNOWN


def build_exhibit_records(rows: list[dict]) -> list[dict]:
    """Convert parsed exhibit dicts into Braintrust dataset records."""
    records = []
    for row in rows:
        record_type = detect_record_type(row["text"], row.get("exhibit_type", ""))
        records.append({
            "input": {
                "doc_text": row["text"],
                "filename": row["filename"],
                "metadata": {
                    "source": "edgar_s1",
                    "accession": row.get("accession", ""),
                    "cik": row.get("cik", ""),
                    "filer": row.get("filer", ""),
                    "filing_date": row.get("filing_date", ""),
                    "exhibit_type": row.get("exhibit_type", ""),
                    "exhibit_description": row.get("description", ""),
                    "expected_doc_type": "corporate_record",
                    "expected_subclass": record_type,
                    "exhibit_url": row.get("href", ""),
                    "chars": len(row["text"]),
                },
            },
            "expected": {"doc_type": "corporate_record", "doc_subclass": record_type},
            "expected_output": {"doc_type": "corporate_record", "doc_subclass": record_type},
            "metadata": {
                "source": "edgar_s1",
                "license": "public_domain",
                "accession": row.get("accession", ""),
                "exhibit_type": row.get("exhibit_type", ""),
                "expected_doc_type": "corporate_record",
                "expected_subclass": record_type,
            },
        })
    return records


def write_local_jsonl(records: list[dict], path: Path) -> int:
    """Write Braintrust record dicts to the local JSONL eval shape."""
    import json as _json

    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            input_data = record.get("input") or {}
            expected = record.get("expected") or {}
            label = expected.get("doc_type") if isinstance(expected, dict) else expected
            metadata = dict(record.get("metadata") or {})
            metadata.update(input_data.get("metadata") or {})
            row = {
                "filename": input_data.get("filename", ""),
                "doc_text": input_data.get("doc_text", ""),
                "prompt": input_data.get("prompt", ""),
                "expected": label,
                "expected_subclass": expected.get("doc_subclass") if isinstance(expected, dict) else None,
                "metadata": metadata,
            }
            fh.write(_json.dumps(row) + "\n")
            written += 1
    return written


def _queries_for_families(families: list[str]) -> list[str]:
    """Map exhibit families (3.x, 4.x, ...) to the FTS description queries."""
    family_codes = {
        "3.x": ["EXHIBIT 3.1", "EXHIBIT 3.2", "EXHIBIT 3.3", "EXHIBIT 3.4"],
        "4.x": ["EXHIBIT 4.1", "EXHIBIT 4.2"],
        "21.x": ["EXHIBIT 21.1", "EXHIBIT 21.2"],
        "24.x": ["EXHIBIT 24.1", "EXHIBIT 24.2"],
        "25.x": ["EXHIBIT 25.1", "EXHIBIT 25.2"],
    }
    queries = []
    for family in families:
        queries.extend(family_codes.get(family, []))
    return queries


def discover_and_extract(
    session,
    throttle: _Throttle,
    exhibit_types: list[str],
    max_filings: int,
    min_text_chars: int,
    cache_dir: Path,
) -> list[dict]:
    """Run discovery + extraction; return flat exhibit row dicts."""
    type_patterns = [EXHIBIT_TYPE_ALIASES[t] for t in exhibit_types]
    type_re = re.compile("^EX-(" + "|".join(type_patterns) + ")$")
    queries = _queries_for_families(exhibit_types)

    filings_seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for query in queries:
        if max_filings and len(filings_seen) >= max_filings:
            break
        throttle.wait()
        try:
            hits = fetch_fts_exhibit_hits(session, query, "S-1", size=20)
        except Exception as exc:  # noqa: BLE001 - one query must not abort the run
            print(f"WARNING: FTS query {query!r} failed: {exc}", file=sys.stderr)
            continue
        for hit in hits:
            adsh = hit.get("adsh", "")
            ciks = hit.get("ciks") or []
            if not adsh or not ciks:
                continue
            cik = ciks[0]
            filing_key = (cik, adsh)
            if filing_key in filings_seen:
                continue
            filings_seen.add(filing_key)
            if max_filings and len(filings_seen) > max_filings:
                break
            print(f"  filing {adsh} ({hit.get('file_date', '')}) {hit.get('file_type', '')}")
            throttle.wait()
            try:
                index_html = get_with_retry(session, index_url(cik, adsh))
            except Exception as exc:  # noqa: BLE001
                print(f"    WARNING: index fetch failed: {exc}", file=sys.stderr)
                continue
            exhibits = parse_filing_index_table(index_html)
            for ex in exhibits:
                if not type_re.match(ex["exhibit_type"] or ""):
                    continue
                if not ex["href"]:
                    continue
                throttle.wait()
                try:
                    raw = get_with_retry(session, "https://www.sec.gov" + ex["href"])
                except Exception as exc:  # noqa: BLE001
                    print(f"    WARNING: exhibit {ex['exhibit_type']} download failed: {exc}",
                          file=sys.stderr)
                    continue
                text = strip_html(raw)
                if len(text) < min_text_chars:
                    print(f"    skip {ex['exhibit_type']} {ex['filename']} "
                          f"({len(text)} chars — likely image scan)")
                    continue
                rows.append({
                    **ex,
                    # Namespace the filename by accession: different filings
                    # routinely carry IDENTICALLY-named exhibit files, and the
                    # eval loop keys rows by filename (dataset fingerprint +
                    # manifest resume).
                    "filename": f"{adsh}_{ex['filename']}",
                    "text": text,
                    "accession": adsh,
                    "cik": cik,
                    "filer": (hit.get("display_names") or [""])[0],
                    "filing_date": hit.get("file_date", ""),
                })
                print(f"    + {ex['exhibit_type']} {ex['filename']} ({len(text)} chars)")
    return rows


def index_url(cik: str, adsh: str) -> str:
    """The filing's human-readable index (``-index.html``)."""
    return (f"{EDGAR_ARCHIVE}/edgar/data/{cik}/{adsh.replace('-', '')}/"
            f"{adsh}-index.html")


def fetch_filing_index(session, cik: str, adsh: str) -> str:
    """Fetch a filing's human-readable index (``-index.html``)."""
    return get_with_retry(session, index_url(cik, adsh))


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="mailroom-s1-corporate-records",
                        help="Braintrust dataset name")
    parser.add_argument("--project-id", default=load_braintrust_config().project_id,
                        help="Braintrust project id")
    parser.add_argument("--exhibit-types", default="3.x,4.x,21.x,24.x,25.x",
                        help="Comma-separated exhibit families to collect (3.x,4.x,21.x,24.x,25.x)")
    parser.add_argument("--max-filings", type=int, default=40,
                        help="Cap on S-1 filings scanned (0 = unlimited)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap on final exhibit records (0 = all)")
    parser.add_argument("--min-text-chars", type=int, default=1500,
                        help="Minimum extracted text length (image scans are skipped below it)")
    parser.add_argument("--local-dump", type=Path, default=None,
                        help="Write local JSONL to <dir>/corporate-records.jsonl")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview the discovery plan without downloading exhibits")
    parser.add_argument("--cache-dir", type=Path,
                        default=Path("/tmp") / "edgar_s1_stream",
                        help="Cache dir for filing indexes")
    args = parser.parse_args(argv)

    exhibit_types = [t.strip() for t in args.exhibit_types.split(",") if t.strip()]
    for t in exhibit_types:
        if t not in EXHIBIT_TYPE_ALIASES:
            parser.error(f"Unknown exhibit family {t!r} (choose from {sorted(EXHIBIT_TYPE_ALIASES)})")

    print(f"Discovery plan: {len(exhibit_types)} exhibit families "
          f"({exhibit_types}), up to {args.max_filings or 'unlimited'} filings, "
          f"min {args.min_text_chars} chars/exhibit")
    if args.dry_run:
        print("Dry run: discovery + download skipped (--dry-run); run without it to collect.")
        return 0

    session = _session()
    throttle = _Throttle()
    rows = discover_and_extract(session, throttle, exhibit_types,
                                args.max_filings, args.min_text_chars, args.cache_dir)
    if args.limit:
        rows = rows[: args.limit]

    from collections import Counter

    by_type = Counter(r.get("exhibit_type", "") for r in rows)
    by_subclass = Counter(detect_record_type(r.get("text", ""), r.get("exhibit_type", ""))
                          for r in rows)
    print(f"\nCollected {len(rows)} corporate-record exhibits "
          f"(by exhibit type: {dict(by_type)})")
    print(f"By record subclass: {dict(by_subclass)}")

    records = build_exhibit_records(rows)
    if args.local_dump:
        n = write_local_jsonl(records, args.local_dump / "corporate-records.jsonl")
        print(f"Local dump: {n} rows -> {args.local_dump / 'corporate-records.jsonl'}")
        return 0

    if not records:
        print("No records collected — nothing to upload.", file=sys.stderr)
        return 1

    (api_key,) = require_env("BRAINTRUST_API_KEY")
    from src.braintrust_utils import upload_text_dataset

    try:
        summary = upload_text_dataset(
            records,
            project_id=args.project_id,
            dataset_name=args.dataset,
            api_key=api_key,
            description=f"EDGAR S-1 corporate-record exhibits ({len(records)} docs, public domain)",
            metadata={"source": "edgar_s1", "exhibit_types": exhibit_types},
            on_progress=lambda i, n: print(f"  Inserted {i}/{n}..."),
        )
        print(f"\n{summary['inserted']} inserted, {summary['failed']} failed into {args.dataset}")
        if summary["failures"]:
            print("Failures:", *summary["failures"][:5], sep="\n  ")
        return 0 if summary["failed"] == 0 else 1
    except Exception as exc:  # noqa: BLE001 - Braintrust row uploads are org-capped
        print(f"Braintrust upload failed ({exc}) — use --local-dump for the "
              f"reliable local JSONL path.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
