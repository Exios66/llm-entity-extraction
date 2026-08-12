#!/usr/bin/env python3
"""Semver release workflow for llm-entity-extraction.

Performs the mechanical release steps and prints the exact commit/tag
commands — the release itself is always a human `git commit` + `git tag`
(+ the GH Pages push + the llm-mailroom mirror sync).

    python scripts/release.py --bump minor --note "issue #1 scoring suite"
    python scripts/release.py --bump patch --note "fix" --dry-run
    python scripts/release.py --check
    python scripts/release.py --help

Rules (see AGENTS.md -> "Release workflow"):
  * pyproject.toml version MUST equal the latest CHANGELOG header.
  * the tag must match the CHANGELOG header exactly (vX.Y.Z).
  * refuses to run --bump on a dirty working tree.
  * --check validates repo state without changing anything.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
REPO_URL = "https://github.com/Exios66/llm-entity-extraction"

VERSION_RE = re.compile(r'^version\s*=\s*"([0-9]+)\.([0-9]+)\.([0-9]+)"', re.M)
HEADER_RE = re.compile(r"^## \[v([0-9]+\.[0-9]+\.[0-9]+)\] - ", re.M)


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def current_version(root: Path | None = None) -> tuple[int, int, int]:
    root = root or REPO_ROOT
    m = VERSION_RE.search((root / "pyproject.toml").read_text())
    if not m:
        fail("could not find version in pyproject.toml")
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def bump_version(version: tuple[int, int, int], bump: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if bump == "major":
        return major + 1, 0, 0
    if bump == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def parse_changelog(root: Path | None = None) -> tuple[list[str], list[str]]:
    """Return (unreleased_bullets, released_headers).

    A missing `## [Unreleased]` section is normal right after a release —
    it just means there are zero pending entries."""
    root = root or REPO_ROOT
    text = (root / "CHANGELOG.md").read_text()
    m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## )", text, re.M | re.S)
    bullets = [ln for ln in m.group(1).splitlines() if ln.strip()] if m else []
    headers = HEADER_RE.findall(text)
    if not m and not headers:
        fail("CHANGELOG.md has neither an Unreleased section nor a released header")
    return bullets, headers


def write_version(version: tuple[int, int, int], root: Path | None = None) -> None:
    root = root or REPO_ROOT
    path = root / "pyproject.toml"
    text = path.read_text()
    text = VERSION_RE.sub(
        f'version = "{version[0]}.{version[1]}.{version[2]}"', text, count=1
    )
    path.write_text(text)


def release_changelog(version: tuple[int, int, int], note: str,
                     root: Path | None = None) -> None:
    """Convert `## [Unreleased]` into `## [vX.Y.Z] - <date>` and add the
    `[vX.Y.Z]:` link (tag must match this header exactly)."""
    root = root or REPO_ROOT
    changelog = root / "CHANGELOG.md"
    text = changelog.read_text()
    bullets, _ = parse_changelog(root)
    ver = f"{version[0]}.{version[1]}.{version[2]}"
    today = _dt.date.today().isoformat()
    body = "\n".join(bullets) if bullets else ""
    note_line = f"\n> {note}\n" if note else ""
    section = f"## [v{ver}] - {today}\n\n{body}\n" if body else f"## [v{ver}] - {today}\n"
    new_text = text.replace(
        "## [Unreleased]", f"## [Unreleased]\n{note_line}\n{section}", 1
    )
    if new_text == text:
        fail("failed to rewrite CHANGELOG.md")
    link = f"[v{ver}]: {REPO_URL}/releases/tag/v{ver}"
    if f"[v{ver}]: " not in new_text:
        new_text = new_text.replace(
            "[Unreleased]: ", f"[Unreleased]: {REPO_URL}\n{link}\n", 1
        )
    changelog.write_text(new_text)


def run_python(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, text=True,
        cwd=REPO_ROOT, timeout=600,
    )


def check_site_data() -> None:
    """Verify docs/data matches the JSONL (build_site.py --check)."""
    proc = run_python(REPO_ROOT / "scripts" / "site" / "build_site.py", "--check")
    if proc.returncode != 0:
        fail(f"site data is stale — run `python scripts/site/build_site.py`: "
             f"{proc.stdout.strip() or proc.stderr.strip()}")


def check_state(verbose: bool = True) -> None:
    if verbose:
        print("checking repo state...")
    if not CHANGELOG.exists():
        fail("CHANGELOG.md missing")
    bullets, headers = parse_changelog()
    ver = current_version()
    ver_s = f"{ver[0]}.{ver[1]}.{ver[2]}"
    if headers and ver_s not in headers:
        fail(f"pyproject version {ver_s} has no CHANGELOG header "
             f"(latest: {headers[0]}) — bump pyproject or release")
    if headers and ver_s in headers and bullets:
        print(f"warn: Unreleased entries remain after v{ver_s} was released")
    check_site_data()
    if verbose:
        print("running tests...")
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"], cwd=REPO_ROOT, check=True
    )
    audit = REPO_ROOT / "tests" / "assets" / "site_render_audit.js"
    if audit.exists() and subprocess.run(["node", "--version"], capture_output=True).returncode == 0:
        proc = subprocess.run(["node", str(audit)], capture_output=True, text=True,
                              cwd=REPO_ROOT, timeout=300)
        if proc.returncode != 0 or "ALL VIEWS RENDER CLEANLY" not in proc.stdout:
            fail(f"site render audit failed:\n{proc.stdout}\n{proc.stderr}")
        if verbose:
            print("site render audit: ALL VIEWS RENDER CLEANLY")
    if verbose:
        print(f"ok: version v{ver_s} · changelog entries: {len(bullets)} unreleased")


def main() -> int:
    return main_with_args(sys.argv[1:])


def main_with_args(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bump", choices=["patch", "minor", "major"],
                    help="bump the version and convert [Unreleased] into the release")
    ap.add_argument("--note", default="",
                    help="one-line summary used in the changelog, commit, and tag")
    ap.add_argument("--check", action="store_true",
                    help="validate repo state, change nothing")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan without changing anything")
    args = ap.parse_args(argv)

    if args.check:
        check_state()
        return 0
    if not args.bump:
        ap.error("nothing to do: pass --bump or --check")

    if run_git("status", "--porcelain"):
        fail("working tree is dirty — commit or stash first")
    bullets, headers = parse_changelog()
    if not bullets:
        fail("CHANGELOG.md has no Unreleased entries to release")
    version = bump_version(current_version(), args.bump)
    ver_s = f"{version[0]}.{version[1]}.{version[2]}"

    if args.dry_run:
        print(f"plan: bump pyproject.toml -> {ver_s}")
        print(f"plan: convert {len(bullets)} Unreleased entries into "
              f"`## [v{ver_s}] - {_dt.date.today().isoformat()}`")
        return 0

    print("running tests...")
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"], cwd=REPO_ROOT, check=True
    )
    check_site_data()

    write_version(version)
    release_changelog(version, args.note)
    print(f"bumped to v{ver_s}; CHANGELOG [Unreleased] moved to [v{ver_s}]")

    print("\nnext steps (release must match the changelog header exactly):")
    print(f"  git add pyproject.toml CHANGELOG.md README.md docs/ reports/ src/ scripts/ tests/")
    print(f"  git commit -m \"v{ver_s}: {args.note or 'release'}\"")
    print(f"  git tag -a v{ver_s} -m \"v{ver_s} — {args.note or 'release'}\"")
    print("  git push origin main --tags        # GH Pages serves /docs from main")
    print("  # mirror sync into llm-mailroom (synced experiment log + site data):")
    print("  cd ../llm-mailroom && PYTHONPATH=src python -c \\")
    print('    "from legalbench.experiment_log import regenerate, default_log_path; '
          'regenerate(default_log_path())"')
    print("  cd ../llm-mailroom && git add docs/ && git commit -m "
          "\"DOCS SYNC: experiment log re-synced (upstream v{ver_s})\" && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
