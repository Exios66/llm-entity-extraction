# CODING_GUIDELINES_PROVENANCE

Provenance for the `## Coding guidelines (adapted from Karpathy)` section in
the repo-root `AGENTS.md` (KANBAN-075, issue #35, human directive
2026-08-22).

## Upstream source

- **Repo:** https://github.com/multica-ai/andrej-karpathy-skills
- **Pinned commit:** `2c606141936f1eeef17fa3043a72095b4765b9c2`
- **License:** MIT (declared in `skills/karpathy-guidelines/SKILL.md`
  frontmatter; the repo has no separate LICENSE file — verify on re-sync)
- **Origin of the ideas:** Andrej Karpathy's observations on LLM coding
  pitfalls (https://x.com/karpathy/status/2015883857489522876), as distilled
  by the upstream repo.

## Relationship to upstream: ADAPTED, NOT VENDORED

No upstream text is copied verbatim. The four principles
(Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven
Execution) and their core bullets (surface assumptions, no speculative
abstractions, touch only what you must, verifiable success criteria, the
200→50 line test, orphan cleanup ownership) were **translated into this
repo's doctrine voice** and mapped onto house mechanics:

- "Think before coding" → card-scope + version-key + affected-surface
  declaration before first edit; governance uncertainty is stop-and-post.
- "Simplicity first" → card-scope-bounded minimum change; `.replace()`
  prompt derivation as the native simplicity mechanism.
- "Surgical changes" → every changed line traces to the card; explicit-path
  commits on shared trees; board-mention (not deletion) of pre-existing
  dead code.
- "Goal-driven execution" → Phase 4 verification; artifact-derived evidence
  numbers; suite arithmetic against the documented baseline.

**Precedence:** the governed workflow (board lifecycle, append-only prompt
versioning, release gates) always outranks these principles where they
touch. The AGENTS.md section states this explicitly.

## Upstream files consulted (at pin)

- `CLAUDE.md` — the four-principle guideline document (primary source)
- `skills/karpathy-guidelines/SKILL.md` — same four principles + license
  declaration + Karpathy attribution link (secondary source; content
  equivalent to CLAUDE.md)
- `README.md` — license note, repo purpose

Not consulted / not used: `EXAMPLES.md`, `CURSOR.md`, `.cursor/rules/`,
plugin manifests (no additional mechanics beyond the four principles).

## Re-sync protocol

```bash
git clone --depth 1 https://github.com/multica-ai/andrej-karpathy-skills /tmp/karpathy-skills
git -C /tmp/karpathy-skills rev-parse HEAD   # compare to the pin above
diff <(cat /tmp/karpathy-skills/CLAUDE.md) <(git show <pin>:CLAUDE.md) 2>/dev/null \
  || echo "upstream moved — re-check principles + license, then update AGENTS.md section, this sidecar, and tests/test_coding_guidelines_agent_file.py in ONE commit"
```

Update rule: if upstream renames or materially changes a principle, update
the AGENTS.md section + this sidecar's pin + the mechanics pins in one
commit, and note it on the board.

## Mechanics pins

`tests/test_coding_guidelines_agent_file.py` asserts the load-bearing
literals (section presence, all four principle headings, precedence clause,
upstream URL + pin, sidecar path) so a future edit cannot silently drop a
mechanic.
