# Release Process

Every release maps to ONE tagged commit (`vX.Y.Z`) and the tag must match the
CHANGELOG header exactly. The mechanical steps are automated by
`scripts/release.py`; the commit/tag are always explicit git commands.

## Changelog discipline (automatic, per commit)

- **Every behavior-changing commit carries its `[Unreleased]` entry in the
  SAME commit** — `### Added` / `### Changed` / `### Fixed` bullets naming
  files, prompt versions, and data-backed results (accuracy numbers, sample
  sizes, seeds). Docs-only and derived-artifact regenerations skip entries.
- Bump rules (semver): **major** = breaking architecture/output-contract
  changes; **minor** = new features (prompt versions, eval runners, dataset
  modes, site capabilities); **patch** = bug fixes.

## Release steps

```bash
# 1) validate repo state (version == changelog header, site data, tests, audit)
python scripts/release.py --check

# 2) convert [Unreleased] -> [vX.Y.Z], bump pyproject.toml, add the release link
python scripts/release.py --bump minor --note "<summary>"     # --dry-run to preview

# 3) update docs the change touches (README.md, docs/README.md, docs/SCORING.md, AGENTS.md)
# 4) regenerate derived artifacts (render_experiment_log.py + build_site.py + audit)
# 5) commit everything as one release commit
git add -A
git commit -m "vX.Y.Z: <summary>"

# 6) annotated tag matching the changelog header EXACTLY, then push
#    (pushing main deploys the GH Pages site — /docs from main)
git tag -a vX.Y.Z -m "vX.Y.Z — <summary>"
git push origin main --tags

# 7) mirror sync into llm-mailroom (synced experiment log + docs)
cd ../llm-mailroom
PYTHONPATH=src python -c "from legalbench.experiment_log import regenerate, default_log_path; regenerate(default_log_path())"
git add docs/ && git commit -m "DOCS SYNC: experiment log re-synced (upstream vX.Y.Z)" && git push
```

## Wiki sync

This wiki is version-controlled in `wiki/` and pushed to the public GitHub
wiki (https://github.com/Exios66/llm-entity-extraction/wiki):

```bash
./wiki/sync-wiki.sh
```

Run it after any wiki/ edit (and after major releases when the docs changed).
