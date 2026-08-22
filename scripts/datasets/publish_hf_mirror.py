#!/usr/bin/env python3
"""Publish exported Braintrust datasets to the Hugging Face Hub (KANBAN-069).

Reads data/hf_export/<dataset>.jsonl + .manifest.json (written by
export_bt_to_hf.py) and uploads each as a public dataset repo:

    https://huggingface.co/datasets/<HF_USERNAME>/<dataset>

Each repo gets:
  - README.md dataset card (YAML frontmatter: license, task, tags, source)
  - <dataset>.jsonl (the rows)
  - manifest.json  (BT ids, sha256, provenance)

Verification: after upload the Hub's reported LFS sha256 for the jsonl is
compared against the local export manifest sha256 — byte-identity proof.

Usage:
    .venv/bin/python scripts/datasets/publish_hf_mirror.py                # all manifests
    .venv/bin/python scripts/datasets/publish_hf_mirror.py --only mailroom-cuad-contracts
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = REPO_ROOT / "data" / "hf_export"

HF_USERNAME = os.environ.get("HF_USERNAME", "Lucius-Morningstar")

CARD_TEMPLATE = """---
license: cc-by-4.0
task_categories:
- text-classification
language:
- en
tags:
- legal
- contracts
- evaluation
- llm-mailroom
- braintrust-mirror
pretty_name: "{pretty_name}"
size_categories:
- {size_category}
---

# {pretty_name}

Mirror of the Braintrust evaluation dataset `{dataset}` from the
[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)
experiment loop (llm-mailroom legal document pipeline).

| Field | Value |
|---|---|
| Rows | {rows} |
| Source script | `{source_script}` |
| Braintrust dataset id | `{bt_dataset_id}` |
| Braintrust project id | `{bt_project_id}` |
| Exported (UTC) | {exported_at} |
| Export sha256 | `{sha256}` |

## License & provenance

{license_note}

## Row shape

One JSON object per line: `id`, `input` (document payload), `expected`
(ground truth), `metadata`, `tags`, `created`. Deterministic row ids —
re-uploads upsert by id, mirroring the Braintrust upsert semantics.{images_section}

## Regenerating the export

```bash
.venv/bin/python scripts/datasets/export_bt_to_hf.py --only {dataset}
```

Braintrust stays READ-ONLY in this workflow (AGENTS.md:
`BRAINTRUST_LOGGING=disabled`); this mirror is exported, never written back.
"""

SIZE_BUCKET = [(1000, "n<1K"), (10000, "1K<n<10K"), (100000, "10K<n<100K")]


def size_category(rows: int) -> str:
    for cap, label in SIZE_BUCKET:
        if rows < cap:
            return label
    return "100K<n<1M"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publish_dataset(api, name: str) -> dict:
    jsonl = EXPORT_DIR / f"{name}.jsonl"
    manifest_path = EXPORT_DIR / f"{name}.manifest.json"
    if not jsonl.exists() or not manifest_path.exists():
        return {"dataset": name, "disposition": "skipped_missing_export"}
    manifest = json.loads(manifest_path.read_text())
    rows = manifest["rows"]
    local_sha = manifest["sha256"]
    actual_sha = sha256_file(jsonl)
    if actual_sha != local_sha:
        return {"dataset": name, "disposition": "ABORT_local_sha_mismatch",
                "manifest": local_sha[:12], "actual": actual_sha[:12]}

    repo_id = f"{HF_USERNAME}/{name}"

    # Attachment payloads (CUAD page PNGs) live beside the JSONL in the export
    # tree; row refs point at them by filename under images/.
    img_dir = EXPORT_DIR / name / "images"
    n_images = sum(1 for _ in img_dir.iterdir()) if img_dir.is_dir() else 0
    if n_images:
        images_section = (
            f"\n\nAttachment payloads ({n_images} page PNG renders) ship under "
            "`images/` in this repo; rows reference them via `input.image.file` "
            "and `input.pages[].file` (with the originating Braintrust attachment "
            "key kept in `source_ref.key`)."
        )
    else:
        images_section = ""

    card = CARD_TEMPLATE.format(
        pretty_name=name.replace("mailroom-", "Mailroom Eval: ").replace("-", " ").title(),
        dataset=name,
        rows=rows,
        source_script=manifest["source_script"],
        bt_dataset_id=manifest["braintrust_dataset_id"],
        bt_project_id=manifest["braintrust_project_id"],
        exported_at=manifest["exported_at_utc"],
        sha256=local_sha,
        license_note=manifest["license_note"],
        size_category=size_category(rows),
        images_section=images_section,
    )

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "README.md").write_text(card, encoding="utf-8")
        (tmpdir / f"{name}.jsonl").write_text(jsonl.read_text(encoding="utf-8"), encoding="utf-8")
        (tmpdir / "manifest.json").write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
        api.upload_folder(
            folder_path=str(tmpdir),
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"KANBAN-069 mirror from Braintrust ({rows} rows, sha {local_sha[:12]})",
        )

    # Attachment payloads (CUAD page PNGs) live beside the JSONL in the export
    # tree; row refs point at them by filename under images/.
    img_dir = EXPORT_DIR / name / "images"
    if img_dir.is_dir() and any(img_dir.iterdir()):
        api.upload_folder(
            folder_path=str(img_dir),
            path_in_repo="images",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"KANBAN-069 attachment payloads ({sum(1 for _ in img_dir.iterdir())} files)",
        )

    # --- verify: Hub LFS sha vs local manifest sha ---
    info = api.list_repo_tree(repo_id=repo_id, repo_type="dataset", recursive=True)
    hub_files = {f.path: getattr(f, "lfs", None) for f in info}
    jsonl_hub = hub_files.get(f"{name}.jsonl")
    hub_sha = jsonl_hub.sha256 if jsonl_hub is not None else "(non-LFS/small file)"
    verified = (hub_sha == local_sha) if isinstance(hub_sha, str) and len(hub_sha) == 64 else "(sha not exposed)"
    return {
        "dataset": name,
        "disposition": "published",
        "repo": f"https://huggingface.co/datasets/{repo_id}",
        "rows": rows,
        "sha256": local_sha[:12],
        "hub_sha256": str(hub_sha)[:12],
        "verified": verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="comma-separated dataset names")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or None
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    me = api.whoami()
    print(f"HF account: {me['name']}")

    manifests = sorted(EXPORT_DIR.glob("*.manifest.json"))
    names = [p.name[: -len(".manifest.json")] for p in manifests]
    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        names = [n for n in names if n in wanted]
    if not names:
        sys.exit("FATAL: no export manifests found (run export_bt_to_hf.py first)")

    results = []
    for name in names:
        print(f"\n== {name} ==")
        out = publish_dataset(api, name)
        print(json.dumps(out, indent=1))
        results.append(out)

    print("\n== PUBLISH SUMMARY ==")
    for r in results:
        print(f"{r['disposition']:<28} {r['dataset']}")


if __name__ == "__main__":
    main()
