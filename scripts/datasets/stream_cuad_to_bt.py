#!/usr/bin/env python3
"""Stream The Atticus Project CUAD v1 contracts into a Braintrust dataset.

The canonical contract-understanding corpus (510 real SEC-exhibit contract
PDFs, CC BY 4.0). This script streams the PDFs straight from the Hugging Face
mirror (``theatticusproject/cuad``, ``CUAD_v1/full_contract_pdf``), renders
each PDF's pages to fixed-size grayscale PNGs (1024x1024, aspect-ratio
preserving — same preprocessing as the RVL-CDIP classifier repo), and uploads
each page as an IMAGE ATTACHMENT into the Braintrust dataset.

The dataset rows follow the RVL-CDIP attachment shape exactly:

    input:  {"image": braintrust.Attachment(png), "document_id": ...,
             "metadata": {page, source_file, category, placeholder: False}}
    expected: {"doc_type": "contract"}

so ``scripts/eval/run_classification_eval.py --input-mode vision`` can load the
images and classify them with a vision model (qwen) without any local files.

Nothing is committed to the repo: PDFs are streamed to a temp file, rendered,
and deleted. Reruns upsert by the deterministic item id ``cuad-<stem>-pageN``.

Prerequisites:
    pip install braintrust pyarrow Pillow pdf2image   (pdf2image needs poppler)

Usage:
    python scripts/datasets/stream_cuad_to_bt.py --limit 12          # first 12 PDFs
    python scripts/datasets/stream_cuad_to_bt.py --sample 24 --seed 42
    python scripts/datasets/stream_cuad_to_bt.py --category "Franchise"
    python scripts/datasets/stream_cuad_to_bt.py --pages-per-doc 3
    python scripts/datasets/stream_cuad_to_bt.py --dry-run
"""

from __future__ import annotations

import argparse
import io
import os
import random
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests

from src.braintrust_config import load_braintrust_config  # noqa: E402
from src.cuad_ground_truth import applicable_categories, build_expected_fields  # noqa: E402
from src.env_utils import require_env  # noqa: E402
from src.image_utils import resize_with_padding  # noqa: E402

HF_TREE_URL = "https://huggingface.co/api/datasets/theatticusproject/cuad/tree/main/CUAD_v1/full_contract_pdf"
HF_RAW_URL = "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/"
DEFAULT_TARGET_SIZE = (1024, 1024)
_USER_AGENT = "mailroom-cuad-streamer/1.0 (research sampling)"

_CUAD = load_braintrust_config()
DEFAULT_DATASET = "mailroom-cuad-contracts"
DEFAULT_PROJECT_ID = _CUAD.project_id


# ---------------------------------------------------------------------------
# PDF discovery + streaming
# ---------------------------------------------------------------------------

CUAD_JSON_URL = (
    "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/"
    "CUAD_v1/CUAD_v1.json"
)

_NORM_CACHE: dict[str, str] = {}


def _norm(s: str) -> str:
    """Normalize a title/stem for matching (lowercase alphanumeric only)."""
    key = s
    if key not in _NORM_CACHE:
        _NORM_CACHE[key] = re.sub(r"[^a-z0-9]", "", s.lower())
    return _NORM_CACHE[key]


def load_clause_labels() -> dict[str, dict]:
    """Load CUAD_v1.json clause QA annotations, keyed by normalized title.

    Each value: ``{"title": ..., "doc_text": <full contract text>,
    "clauses": [{question, answer, answer_start}]}`` — the extraction agent's
    ground truth for the Atticus corpus (41 clause categories).
    """
    resp = requests.get(CUAD_JSON_URL, headers={"User-Agent": _USER_AGENT}, timeout=600)
    resp.raise_for_status()
    data = resp.json()
    by_title: dict[str, dict] = {}
    for doc in data.get("data", []):
        title = (doc.get("title") or "").strip()
        if not title:
            continue
        seen: set[str] = set()
        parts: list[str] = []
        clauses: list[dict] = []
        for paragraph in doc.get("paragraphs", []):
            context = (paragraph.get("context") or "").strip()
            if context and context not in seen:
                seen.add(context)
                parts.append(context)
            for qa in paragraph.get("qas", []) or []:
                question = (qa.get("question") or "").strip()
                if not question:
                    continue
                answers = [a.get("text") for a in (qa.get("answers") or []) if a.get("text")]
                clauses.append({
                    "question": question,
                    "answer": answers[0] if answers else "",
                    "answer_start": (qa.get("answers") or [{}])[0].get("answer_start", -1),
                })
        by_title[_norm(title)] = {
            "title": title,
            "doc_text": "\n\n".join(parts),
            "clauses": clauses,
        }
    return by_title


def list_pdf_paths() -> list[str]:
    """List every contract PDF path in the CUAD corpus (recursive HF tree API)."""
    resp = requests.get(HF_TREE_URL, params={"recursive": "true"},
                        headers={"User-Agent": _USER_AGENT}, timeout=120)
    resp.raise_for_status()
    entries = resp.json()
    pdfs = [e["path"] for e in entries if e.get("path", "").lower().endswith(".pdf")]
    return sorted(pdfs)


def category_of(pdf_path: str) -> str:
    """Extract the agreement category from the path (e.g. 'Franchise')."""
    parts = Path(pdf_path).parts
    for part in parts:
        if part in ("Part_I", "Part_II", "Part_III"):
            continue
    # Category = the deepest directory component before the filename.
    return parts[-2] if len(parts) >= 2 else "unknown"


def stem_of(pdf_path: str) -> str:
    return Path(pdf_path).stem


def stream_pdf(pdf_path: str) -> bytes:
    """Stream one CUAD PDF into memory (small; largest is ~2 MB)."""
    url = HF_RAW_URL + pdf_path
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=300)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# PDF -> page images
# ---------------------------------------------------------------------------

def render_pdf_pages(pdf_bytes: bytes, pages_per_doc: int | str, target_size: tuple[int, int],
                     max_pages: int = 20) -> list[bytes]:
    """Render the pages of a PDF to padded grayscale PNGs.

    ``pages_per_doc``: an int (first N pages) or ``"all"`` (every page, capped
    at ``max_pages``). The FULL document is what the vision sorter evaluates;
    page 1 alone misses termination clauses, governing-law, and signature
    blocks that live on later pages.
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise SystemExit(
            "pdf2image is required to render CUAD PDFs: pip install pdf2image "
            "(plus poppler, e.g. brew install poppler)"
        )
    if pages_per_doc == "all":
        last_page = max_pages
    else:
        last_page = int(pages_per_doc)
    images = convert_from_bytes(pdf_bytes, dpi=150, first_page=1, last_page=last_page)
    pngs = []
    for img in images:
        if img.mode != "L":
            img = img.convert("L")
        padded = resize_with_padding(img, target_size, fill=255)
        buffer = io.BytesIO()
        padded.save(buffer, format="PNG", dpi=(150, 150))
        pngs.append(buffer.getvalue())
    return pngs


# ---------------------------------------------------------------------------
# Braintrust upload
# ---------------------------------------------------------------------------

def upload_dataset(
    records: list[dict],
    project_id: str,
    dataset_name: str,
    api_key: str,
    *,
    description: str,
    metadata: dict | None = None,
    on_progress=None,
) -> dict:
    """Insert image-attachment records into the dataset (RVL-CDIP shape)."""
    import braintrust

    braintrust.login(api_key=api_key)
    dataset = braintrust.init_dataset(project_id=project_id, name=dataset_name)
    metadata = dict(metadata or {})

    experiment = braintrust.init_experiment(
        project_id=project_id,
        experiment=f"create-{dataset_name}",
        description=description,
        metadata={"task": "dataset_creation", "dataset": dataset_name, **metadata},
    )

    inserted = failed = 0
    failures: list[str] = []
    for i, record in enumerate(records):
        try:
            dataset.insert(
                input=record["input"],
                expected=record["expected"],
                metadata=record.get("metadata", {}),
                id=record.get("id"),
            )
            inserted += 1
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            failed += 1
            failures.append(f"{record['input'].get('document_id', i)}: {exc}")
        if on_progress and (i + 1) % 25 == 0:
            on_progress(i + 1, len(records))

    dataset.flush()
    dataset.close()

    experiment.log(
        input={"dataset": dataset_name, "records": len(records)},
        output={"inserted": inserted, "failed": failed},
        scores={"insertion_rate": inserted / max(1, len(records)),
                "failure_rate": failed / max(1, len(records))},
        metrics={"records": inserted, "failed": failed},
        metadata={"failures": failures[:50]},
    )
    experiment.close()
    return {"inserted": inserted, "failed": failed, "failures": failures}


def build_records(
    pdf_paths: list[str],
    *,
    pages_per_doc: int | str,
    target_size: tuple[int, int],
    api_key: str,
    clause_labels: dict[str, dict] | None = None,
    max_pages: int = 20,
    text_only: bool = False,
    on_progress=None,
) -> list[dict]:
    """Stream each PDF, render pages, and build ONE record per document.

    Each record's input carries the FULL document as page-image attachments
    (``pages`` — every rendered page) plus ``image`` (page 1) for the
    single-page vision path, the full contract text, and the CUAD clause QA
    ground truth (``expected_output``) for the extraction agent.

    With ``text_only=True`` the PDFs are NOT fetched or rendered: rows carry
    the CUAD_v1.json contract text + category metadata only — the cheap,
    poppler-free path for building the full-corpus TEXT dataset (used by the
    sorter-only subtype eval, which classifies on text).
    """
    clause_labels = clause_labels or {}
    records: list[dict] = []
    failures: list[str] = []
    for i, pdf_path in enumerate(pdf_paths):
        try:
            if text_only:
                pages: list[bytes] = []
            else:
                pdf_bytes = stream_pdf(pdf_path)
                pages = render_pdf_pages(pdf_bytes, pages_per_doc, target_size, max_pages=max_pages)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{pdf_path}: {type(exc).__name__}: {exc}")
            continue
        stem = stem_of(pdf_path)
        category = category_of(pdf_path)
        labels = clause_labels.get(_norm(stem), {})
        clause_list = labels.get("clauses", [])
        doc_text = labels.get("doc_text", "")
        # Per the CUAD dataset card, NOT all expected fields map to each
        # document: the contract TYPE (folder) the document belongs to decides
        # which of the 41 clause categories are applicable. The applicable
        # category set is stamped into the row so eval loops derive
        # type-aware expected fields without re-fetching the corpus.
        expected_categories = sorted(applicable_categories(category))
        expected_fields = build_expected_fields(clause_list, doc_category=category)

        page_attachments = [
            _attachment(png_bytes, f"{stem}_page{page_num:04d}.png", api_key)
            for page_num, png_bytes in enumerate(pages, start=1)
        ]
        records.append({
            "id": f"cuad-{stem}",
            "input": {
                "image": page_attachments[0] if page_attachments else None,
                "pages": page_attachments,
                "document_id": f"cuad_{stem}",
                "doc_text": doc_text or None,
                "metadata": {
                    "placeholder": False,
                    "page_count": len(page_attachments),
                    "source_file": pdf_path,
                    "category": category,
                    "applicable_categories": expected_categories,
                    "document_id": stem,
                    "has_clause_labels": bool(clause_list),
                },
            },
            "expected": {
                "doc_type": "contract",
                "clause_labels": clause_list,
                "clause_count": len(clause_list),
                "expected_fields": expected_fields,
                "expected_categories": expected_categories,
            },
            "expected_output": {
                "doc_type": "contract",
                "clause_labels": clause_list,
                "clause_count": len(clause_list),
                "expected_fields": expected_fields,
                "expected_categories": expected_categories,
            },
            "metadata": {
                "source": "cuad_v1",
                "license": "CC BY 4.0",
                "category": category,
                "applicable_categories": expected_categories,
                "pdf_path": pdf_path,
                "page_count": len(page_attachments),
                "clause_count": len(clause_list),
            },
        })
        if on_progress:
            on_progress(i + 1, len(pdf_paths))
    if failures:
        print(f"WARNING: {len(failures)} PDFs failed:", file=sys.stderr)
        for f in failures[:10]:
            print(f"  {f}", file=sys.stderr)
    return records


_attachment_cache: dict[str, object] = {}


def _attachment(png_bytes: bytes, filename: str, api_key: str):
    """Build (and lazily cache) the braintrust.Attachment for a page image."""
    import braintrust

    key = f"{filename}:{len(png_bytes)}"
    if key not in _attachment_cache:
        _attachment_cache[key] = braintrust.Attachment(
            data=png_bytes, filename=filename, content_type="image/png"
        )
    return _attachment_cache[key]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Braintrust dataset name")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Braintrust project id")
    parser.add_argument("--limit", type=int, default=0, help="Only the first N PDFs (0 = all)")
    parser.add_argument("--sample", type=int, default=0, help="Random sample of N PDFs")
    parser.add_argument("--seed", type=int, default=42, help="Seed for --sample")
    parser.add_argument("--category", default=None,
                        help="Only PDFs in this agreement category (e.g. Franchise, IP, License_Agreements)")
    parser.add_argument("--pages-per-doc", default="all",
                        help="Pages to render per PDF: an int (first N) or 'all' (every page, "
                             "capped by --max-pages). Default: all — the sorter evaluates the "
                             "FULL document, not a page-1 stub.")
    parser.add_argument("--max-pages", type=int, default=20,
                        help="Hard cap on pages rendered per PDF when --pages-per-doc all")
    parser.add_argument("--target-size", type=int, nargs=2, default=list(DEFAULT_TARGET_SIZE),
                        metavar=("W", "H"), help=f"Output image size (default: {DEFAULT_TARGET_SIZE[0]} {DEFAULT_TARGET_SIZE[1]})")
    parser.add_argument("--no-clause-labels", action="store_true",
                        help="Skip merging CUAD_v1.json clause QA ground truth (extraction agent labels)")
    parser.add_argument("--text-only", action="store_true",
                        help="Skip PDF fetching/rendering entirely: rows carry the CUAD_v1.json "
                             "contract TEXT + category metadata only (no poppler, no images) — "
                             "the cheap path for the full-corpus text dataset")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Braintrust")
    args = parser.parse_args()

    (api_key,) = require_env("BRAINTRUST_API_KEY")
    target_size = (args.target_size[0], args.target_size[1])
    try:
        pages_per_doc: int | str = "all" if args.pages_per_doc == "all" else int(args.pages_per_doc)
    except ValueError:
        parser.error(f"--pages-per-doc must be an integer or 'all', got {args.pages_per_doc!r}")
    if pages_per_doc == "all":
        print(f"Rendering ALL pages per PDF (capped at {args.max_pages})")
    else:
        print(f"Rendering first {pages_per_doc} page(s) per PDF")

    clause_labels: dict[str, dict] | None = None
    if not args.no_clause_labels:
        print("Loading CUAD_v1.json clause QA ground truth...")
        clause_labels = load_clause_labels()
        with_clauses = sum(1 for v in clause_labels.values() if v["clauses"])
        print(f"Loaded clause labels for {len(clause_labels)} documents ({with_clauses} with clauses)")

    print("Listing CUAD contract PDFs from Hugging Face...")
    pdf_paths = list_pdf_paths()
    if args.category:
        pdf_paths = [p for p in pdf_paths if category_of(p) == args.category]
        print(f"Category '{args.category}': {len(pdf_paths)} PDFs")
    if args.sample:
        pdf_paths = random.Random(args.seed).sample(pdf_paths, min(args.sample, len(pdf_paths)))
        print(f"Sampled {len(pdf_paths)} PDFs (seed {args.seed})")
    elif args.limit:
        pdf_paths = pdf_paths[: args.limit]
        print(f"Limited to {len(pdf_paths)} PDFs")
    if not pdf_paths:
        parser.error("No PDFs matched.")

    by_category = Counter(category_of(p) for p in pdf_paths)
    print(f"Categories: {dict(by_category)}")

    if args.dry_run:
        mode = "text rows (no PDFs)" if args.text_only else "full page sets"
        print(f"\nDry run: {len(pdf_paths)} PDFs ({mode}) would sync as "
              f"{len(pdf_paths)} document rows to {args.dataset}")
        for p in pdf_paths[:8]:
            print(f"  would sync  {Path(p).name}  ({category_of(p)})")
        if len(pdf_paths) > 8:
            print(f"  ... and {len(pdf_paths) - 8} more")
        return 0

    if args.text_only:
        print(f"Building {len(pdf_paths)} TEXT-ONLY rows (no PDF fetch/render)...")
    else:
        print(f"Streaming {len(pdf_paths)} PDFs, rendering pages...")
    records = build_records(
        pdf_paths,
        pages_per_doc=pages_per_doc,
        target_size=target_size,
        api_key=api_key,
        clause_labels=clause_labels,
        max_pages=args.max_pages,
        text_only=args.text_only,
        on_progress=lambda i, n: print(f"  Processed {i}/{n} PDFs..."),
    )
    if not records:
        print("No document rows could be built.", file=sys.stderr)
        return 1

    total_pages = sum(r["metadata"]["page_count"] for r in records)
    if args.text_only:
        print(f"\n{len(records)} text documents "
              f"({total_pages / max(1, len(records)):.1f} avg pages/doc — 0 images)")
    else:
        print(f"\n{len(records)} documents, {total_pages} pages total "
              f"({total_pages / max(1, len(records)):.1f} avg pages/doc)")
    print(f"Uploading {len(records)} document rows to {args.dataset}...")
    summary = upload_dataset(
        records,
        project_id=args.project_id,
        dataset_name=args.dataset,
        api_key=api_key,
        description=f"CUAD v1 contract page images ({len(records)} rows, CC BY 4.0) — doc_type=contract",
        metadata={"source": "cuad_v1", "license": "CC BY 4.0",
                  "pdfs": len(pdf_paths), "pages_per_doc": args.pages_per_doc,
                  "target_size": list(target_size), "text_only": args.text_only},
        on_progress=lambda i, n: print(f"  Inserted {i}/{n}..."),
    )
    print(f"\nDone: {summary['inserted']} inserted, {summary['failed']} failed into {args.dataset}")
    if summary["failures"]:
        print("Failures:", *summary["failures"][:5], sep="\n  ")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
