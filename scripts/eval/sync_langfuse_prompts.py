#!/usr/bin/env python3
"""Sync every prompt version from ``src/prompts.py`` into Langfuse projects.

The versioned prompt constants in ``src/prompts.py`` are the source of truth;
this script mirrors each version (name = the version key, content = the
template text) into the configured Langfuse project(s) so prompt iterations
stay synced between environments (llm-dojo, the experiment project, and any
additional project whose keys are provided).

Usage:
    python scripts/eval/sync_langfuse_prompts.py --dry-run
    python scripts/eval/sync_langfuse_prompts.py            # sync llm-dojo (langfuse.env)
    python scripts/eval/sync_langfuse_prompts.py --env-file langfuse.env \\
        --env-file langfuse-primary.env                     # sync multiple projects

Each ``--env-file`` contributes one project: its LANGFUSE_PUBLIC_KEY /
LANGFUSE_SECRET_KEY route the write (keys are project-scoped), and its
LANGFUSE_PROJECT value names the project in the report. The default is
``langfuse.env`` (the llm-dojo experiment environment). A missing env file
is skipped with a warning — so adding a second project is a drop-in: create
``langfuse-<project>.env`` with that project's keys and pass it on the
command line (or add it to the default list).

Idempotency: a prompt whose latest version content already equals the local
constant is skipped; only changed/absent versions are created. New versions
are created with the ``production`` label (Langfuse applies it by default on
create). Template variables (``{{var}}``) pass through untouched — the
prompts already use Langfuse-compatible double-brace syntax.

Run after every prompt iteration (per AGENTS.md "After every run").
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402

from src.prompts import PROMPT_VERSIONS  # noqa: E402

DEFAULT_ENV_FILES = ["langfuse.env"]
DEFAULT_BASE_URL = "https://us.cloud.langfuse.com"


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE dotenv file (no interpolation, no export)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _auth_header(public_key: str, secret_key: str) -> str:
    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    return f"Basic {token}"


def _latest_content(name: str, base_url: str, auth: str) -> str | None:
    """Return the latest version's content, or None when the prompt is absent.

    The public API returns the latest version directly for
    ``GET /api/public/prompts?name=<name>`` (a 404 means the prompt does not
    exist in this project yet).
    """
    resp = requests.get(f"{base_url}/api/public/prompts", params={"name": name},
                        headers={"Authorization": auth}, timeout=60)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return (resp.json() or {}).get("prompt")


def _create_prompt(name: str, content: str, base_url: str, auth: str) -> None:
    resp = requests.post(
        f"{base_url}/api/public/prompts",
        headers={"Authorization": auth, "Content-Type": "application/json"},
        json={"name": name, "type": "text", "prompt": content, "isActive": True},
        timeout=120,
    )
    if resp.status_code == 200:
        return
    if resp.status_code == 409:
        return  # concurrent create — content already exists
    resp.raise_for_status()


def _sync_project(env_file: Path, prompts: dict[str, str], dry_run: bool) -> dict:
    env = _load_env_file(env_file)
    public = env.get("LANGFUSE_PUBLIC_KEY") or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret = env.get("LANGFUSE_SECRET_KEY") or os.environ.get("LANGFUSE_SECRET_KEY", "")
    project = env.get("LANGFUSE_PROJECT") or os.environ.get("LANGFUSE_PROJECT", "unknown-project")
    base_url = (env.get("LANGFUSE_BASE_URL") or env.get("LANGFUSE_HOST") or DEFAULT_BASE_URL).rstrip("/")
    if not public or not secret:
        return {"project": project, "skipped_env": True, "created": 0, "unchanged": 0, "total": len(prompts)}

    auth = _auth_header(public, secret)
    created: list[str] = []
    unchanged: list[str] = []
    for name, content in prompts.items():
        latest = _latest_content(name, base_url, auth)
        if latest == content:
            unchanged.append(name)
            continue
        if dry_run:
            created.append(name)
            continue
        _create_prompt(name, content, base_url, auth)
        created.append(name)
    return {"project": project, "created": len(created), "unchanged": len(unchanged), "total": len(prompts),
            "created_names": created, "unchanged_names": unchanged}


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", action="append", default=[],
                        help="Langfuse env file with keys + project label (repeatable). "
                             f"Defaults to {DEFAULT_ENV_FILES}")
    parser.add_argument("--dry-run", action="store_true", help="Report what would sync without writing")
    args = parser.parse_args(argv)

    env_files = [Path(p) for p in (args.env_file or DEFAULT_ENV_FILES)]
    prompts = dict(PROMPT_VERSIONS)
    print(f"Syncing {len(prompts)} prompt versions from src/prompts.py")
    for env_file in env_files:
        if not env_file.exists():
            print(f"  [warn] {env_file} not found — skipped (add it with --env-file to sync that project)")
            continue
        report = _sync_project(env_file, prompts, args.dry_run)
        if report.get("skipped_env"):
            print(f"  [warn] {env_file}: no Langfuse keys found — skipped")
            continue
        mode = "would create" if args.dry_run else "created"
        print(f"  {report['project']}: {mode} {report['created']}, unchanged {report['unchanged']} "
              f"(of {report['total']})")
        if args.dry_run and report["created_names"]:
            print("    " + ", ".join(report["created_names"][:8]) + ("..." if len(report["created_names"]) > 8 else ""))
    return 0


def main() -> None:
    sys.exit(main_with_args(sys.argv[1:]))


if __name__ == "__main__":
    main()
