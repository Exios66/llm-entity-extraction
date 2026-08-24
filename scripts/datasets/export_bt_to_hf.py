#!/usr/bin/env python3
"""Export Braintrust evaluation datasets to gitignored staging for HF mirroring.

KANBAN-069. STRICTLY READ-ONLY against Braintrust:
- dataset names are parsed programmatically from scripts/datasets/stream_*.py
  defaults (never hand-typed);
- names are resolved against the LIVE CATALOG via GET /v1/dataset?project_id=
  (a pure read — never api/dataset/register, which is get-or-CREATE);
- streamer defaults absent from the catalog are recorded as skipped, never
  created;
- rows are fetched via the BTQL query endpoint exactly as
  braintrust.logger.ObjectFetcher._refetch does (pure read);
- image attachments (CUAD page PNGs) are downloaded via the SDK's own
  ReadonlyAttachment reader into images/ — resumable: existing non-empty
  files are skipped, so interrupted runs continue where they left off.

Outputs under data/hf_export/ (gitignored):
  <dataset>.jsonl          one row per line: id, input, expected, metadata, tags, created
  <dataset>.manifest.json  counts, sha256, BT ids, source script, license note
  <dataset>/images/*.png   downloaded attachment payloads (cuad page images)
  EXPORT_SUMMARY.json      one-line-per-dataset disposition incl. skips

Usage:
    .venv/bin/python scripts/datasets/export_bt_to_hf.py [--limit N] [--only name,name] [--no-images]
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.braintrust_config import load_braintrust_config  # noqa: E402

os.environ.setdefault("BRAINTRUST_LOGGING", "disabled")

DATASETS_DIR = REPO_ROOT / "scripts" / "datasets"
OUT_DIR = REPO_ROOT / "data" / "hf_export"

# Line-boundary hazard characters: JSON-legal inside strings, but any loader
# that parses line-by-line via str.splitlines() treats these as record breaks
# INSIDE a row (bytes.splitlines() only knows \n/\r, so this is
# version/platform-dependent). The Hub datasets-server worker shreds such rows
# into invalid JSON fragments -> DatasetGenerationError "Expected object or
# value" (KANBAN-087: 16 literal U+2028 chars in one CUAD doc_text). JSONL
# writers must neutralize them; \\u2028 escapes round-trip losslessly.
LINE_BOUNDARY_HAZARDS = {
    "\u2028": "\\u2028",  # LINE SEPARATOR
    "\u2029": "\\u2029",  # PARAGRAPH SEPARATOR
    "\x85": "\\u0085",    # NEL (str.splitlines boundary on some platforms)
}


def sanitize_line_boundary_chars(text: str) -> str:
    """Escape str.splitlines() hazard characters so one JSONL record can never
    be split mid-row by a line-oriented parser. Lossless: json.loads decodes
    the escapes back to the original characters."""
    for ch, esc in LINE_BOUNDARY_HAZARDS.items():
        text = text.replace(ch, esc)
    return text


LICENSE_NOTES = {
    "mailroom-cuad-contracts": "CUAD v1 (The Atticus Project), CC BY 4.0 — page-image rows are DERIVED artifacts; regenerate via scripts/datasets/stream_cuad_to_bt.py",
    "mailroom-cuad-contracts-full": "CUAD v1 (The Atticus Project), CC BY 4.0 — text rows derived from theatticusproject/cuad",
    "mailroom-legalbench-contracts": "LegalBench (nguha/legalbench), CC BY 4.0",
    "mailroom-legalbench-maud-classification": "MAUD questions via LegalBench mirror, CC BY 4.0",
    "mailroom-lb-hearsay": "LegalBench hearsay task (nguha/legalbench), CC BY 4.0",
    "mailroom-maud-contracts": "MAUD v1 merger-agreement corpus, per MAUD project terms",
    "mailroom-maud-classification": "MAUD per-question classification suite",
    "mailroom-s1-corporate-records": "SEC EDGAR S-1 exhibits — public-domain filings, curated selection",
}

SOURCE_SCRIPTS = {
    "mailroom-cuad-contracts": "stream_cuad_to_bt.py",
    "mailroom-cuad-contracts-full": "stream_cuad_to_bt.py",
    "mailroom-legalbench-contracts": "stream_legalbench_to_bt.py",
    "mailroom-legalbench-maud-classification": "stream_legalbench_to_bt.py",
    "mailroom-lb-hearsay": "stream_legalbench_tasks_to_bt.py",
    "mailroom-maud-contracts": "stream_maud_to_bt.py",
    "mailroom-maud-classification": "stream_maud_to_bt.py",
    "mailroom-s1-corporate-records": "stream_s1_exhibits.py",
}


def discover_dataset_names() -> list[str]:
    """Parse dataset-name defaults out of the streamer sources (AST walk)."""
    names: set[str] = set()
    for py in sorted(DATASETS_DIR.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and re.fullmatch(r"[A-Z_]*DATASET[A-Z_]*", tgt.id):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            names.add(node.value.value)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument":
                opts = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                if any(o.startswith("--") and "dataset" in o for o in opts):
                    for kw in node.keywords:
                        if kw.arg == "default" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            names.add(kw.value.value)
    return sorted(names)


# Per-task datasets are built with f-strings (mailroom-lb-{task}) and are
# therefore invisible to the AST walk above. Names here were VERIFIED LIVE in
# the project catalog (GET /v1/dataset) before inclusion — never guesses.
# Verified 2026-08-21: mailroom-lb-hearsay (id 33b5771b-..., 5 rows).
EXPLICIT_INCLUDES = ["mailroom-lb-hearsay"]


def fetch_catalog(api_conn, project_id: str, retries: int = 3, backoff: float = 5.0) -> dict[str, dict]:
    """READ-ONLY dataset catalog: GET /v1/dataset (name -> info).

    Transient-failure hardening (2026-08-21): under load this endpoint has
    returned 200 with an EMPTY objects list (twice, from background shells,
    while foreground reads succeeded seconds later). Retry, and let the
    caller's empty-catalog abort catch a genuine persistent empty.
    """
    import time  # noqa: PLC0415

    last: dict[str, dict] = {}
    for attempt in range(1, retries + 1):
        r = api_conn.get_json("/v1/dataset", {"project_id": project_id})
        last = {o["name"]: o for o in r.get("objects", [])}
        if last:
            return last
        print(f"  catalog read {attempt}/{retries}: 0 objects — retrying in {backoff}s")
        time.sleep(backoff)
    return last


def fetch_rows(api_conn, ds_id: str, limit: int = 0) -> list[dict]:
    """Read rows via BTQL exactly as ObjectFetcher._refetch does."""
    rows: list[dict] = []
    cursor = None
    while True:
        body = {
            "query": {
                "select": [{"op": "star"}],
                "from": {
                    "op": "function",
                    "name": {"op": "ident", "name": ["dataset"]},
                    "args": [{"op": "literal", "value": ds_id}],
                },
                "cursor": cursor,
                "limit": 1000,
            },
            "use_columnstore": False,
            "brainstore_realtime": True,
            "query_source": "py_sdk_hermes_kanban069_export",
        }
        r = api_conn.post("btql", json=body)
        r.raise_for_status()
        j = r.json()
        rows.extend(j.get("data", []))
        if limit and len(rows) >= limit:
            return rows[:limit]
        cursor = j.get("cursor")
        if not cursor:
            return rows


def safe_name(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:180]


def collect_attachments(obj, found: list):
    if isinstance(obj, dict):
        if obj.get("type") == "braintrust_attachment":
            found.append(obj)
        else:
            for v in obj.values():
                collect_attachments(v, found)
    elif isinstance(obj, list):
        for v in obj:
            collect_attachments(v, found)


def materialize_images(rec_input, img_dir: Path) -> tuple[int, int]:
    """Download unique attachments into img_dir (resumable); replace refs
    with {type: image_file, file: <name>} markers. Returns (files_written,
    files_already_present)."""
    import braintrust  # noqa: PLC0415 — local import keeps login lazy

    refs: list[dict] = []
    collect_attachments(rec_input, refs)
    written = already = 0
    seen_keys: set[str] = set()
    for ref in refs:
        key = ref.get("key") or ""
        fname = safe_name(ref.get("filename") or key.split("/")[-1] or "attachment.bin")
        marker = {"type": "image_file", "file": fname,
                  "source_ref": {"key": key, "content_type": ref.get("content_type"),
                                 "filename": ref.get("filename")}}
        ref.clear()
        ref.update(marker)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        dest = img_dir / fname
        if dest.exists() and dest.stat().st_size > 0:
            already += 1
            continue
        readonly = braintrust.logger.ReadonlyAttachment({
            "type": "braintrust_attachment", "key": key,
            "filename": ref["source_ref"]["filename"],
            "content_type": ref["source_ref"]["content_type"]})
        dest.write_bytes(readonly.data)
        written += 1
        print(f"    img {fname} ({dest.stat().st_size} B)")
    return written, already


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="cap rows per dataset (0 = all)")
    parser.add_argument("--only", default="", help="comma-separated subset of dataset names")
    parser.add_argument("--no-images", action="store_true",
                        help="skip downloading attachment payloads (refs only)")
    args = parser.parse_args()

    cfg = load_braintrust_config()
    if not cfg.api_key:
        sys.exit("FATAL: BRAINTRUST_API_KEY unresolved")

    from braintrust.logger import login_to_state  # noqa: PLC0415

    state = login_to_state(api_key=cfg.api_key)
    api_conn = state.api_conn()

    discovered = sorted(set(discover_dataset_names()) | set(EXPLICIT_INCLUDES))
    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        discovered = [n for n in discovered if n in wanted]
    if not discovered:
        sys.exit("FATAL: no dataset names discovered from streamer sources")

    catalog = fetch_catalog(api_conn, cfg.project_id)
    if not catalog:
        # A 0-catalog read is a transient BT failure (seen 2026-08-21 ~23:47:
        # same endpoint returned 6 datasets before and after). Never trust it —
        # aborting beats overwriting a truthful summary with bogus skips.
        sys.exit(
            "ABORT: live catalog returned 0 datasets — transient Braintrust read "
            "failure. Re-run when the catalog read succeeds; nothing was written."
        )
    print(f"live catalog: {len(catalog)} datasets; discovered {len(discovered)} names from streamers")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for name in discovered:
        info = catalog.get(name)
        if info is None:
            summary.append({"dataset": name, "disposition": "skipped_not_in_project",
                            "note": "streamer default absent from live BT catalog — never created"})
            print(f"[{name}] SKIP: not in live catalog (would-be-create refused)")
            continue
        ds_id = info["id"]
        rows = fetch_rows(api_conn, ds_id, limit=args.limit)
        if not rows:
            summary.append({"dataset": name, "disposition": "skipped_empty",
                            "bt_dataset_id": ds_id, "rows": 0,
                            "note": "exists in BT but holds zero rows"})
            print(f"[{name}] SKIP: 0 rows in BT (empty shell)")
            continue

        img_dir = OUT_DIR / name / "images"
        n_written = n_cached = 0
        rows_out = []
        for row in rows:
            rec = {
                "id": row.get("id"),
                "input": row.get("input"),
                "expected": row.get("expected"),
                "metadata": row.get("metadata"),
                "tags": row.get("tags"),
                "created": row.get("created"),
            }
            if not args.no_images:
                img_dir.mkdir(parents=True, exist_ok=True)
                w, c = materialize_images(rec["input"], img_dir)
                n_written += w
                n_cached += c
            rows_out.append(
                sanitize_line_boundary_chars(json.dumps(rec, default=str, ensure_ascii=False))
            )

        jsonl_path = OUT_DIR / f"{name}.jsonl"
        payload = "\n".join(rows_out) + "\n"
        jsonl_path.write_text(payload, encoding="utf-8")

        manifest = {
            "dataset": name,
            "braintrust_project_id": cfg.project_id,
            "braintrust_dataset_id": ds_id,
            "braintrust_org_id": cfg.org_id,
            "rows": len(rows_out),
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "images_downloaded_this_run": n_written,
            "images_already_on_disk": n_cached,
            "exported_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source_script": SOURCE_SCRIPTS.get(name, "(unknown)"),
            "license_note": LICENSE_NOTES.get(name, "provenance TBD"),
            "row_limit_applied": args.limit or None,
        }
        (OUT_DIR / f"{name}.manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        summary.append({"dataset": name, "disposition": "exported", **manifest})
        print(f"[{name}] wrote {len(rows_out)} rows (sha {manifest['sha256'][:12]}), "
              f"images: {n_written} new / {n_cached} cached")

    (OUT_DIR / "EXPORT_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                 encoding="utf-8")
    print("\n== DISPOSITION ==")
    for s in summary:
        print(f"{s['disposition']:24s} {s['dataset']}")


if __name__ == "__main__":
    main()
