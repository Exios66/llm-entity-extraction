"""Release workflow tests (scripts/release.py) — no network, no git history
dependency; the pure functions operate on tmp copies."""

from __future__ import annotations

import pytest

import scripts.release as release


def _write_tmp_repo(tmp_path, version="0.14.0", unreleased=True):
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "mailroom"\nversion = "{version}"\n', encoding="utf-8"
    )
    head = (
        "# Changelog\n\n## [Unreleased]\n\n### Added\n- feature one.\n\n"
        if unreleased
        else "# Changelog\n\n"
    )
    changelog = head
    changelog += "## [v0.14.0] - 2026-08-11\n\n### Added\n- feature one.\n\n"
    changelog += "## [v0.13.0] - 2026-08-11\n\n### Fixed\n- bug one.\n"
    changelog += "\n[Unreleased]: https://github.com/Exios66/llm-entity-extraction\n"
    changelog += "[v0.14.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.14.0\n"
    changelog += "[v0.13.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.13.0\n"
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


class TestVersionMath:
    def test_current_version(self, tmp_path):
        root = _write_tmp_repo(tmp_path)
        assert release.current_version(root) == (0, 14, 0)

    def test_bump_rules(self):
        assert release.bump_version((0, 14, 0), "patch") == (0, 14, 1)
        assert release.bump_version((0, 14, 0), "minor") == (0, 15, 0)
        assert release.bump_version((0, 14, 0), "major") == (1, 0, 0)


class TestChangelog:
    def test_parse_unreleased(self, tmp_path):
        root = _write_tmp_repo(tmp_path)
        bullets, headers = release.parse_changelog(root)
        assert "feature one" in "\n".join(bullets)
        assert headers == ["0.14.0", "0.13.0"]

    def test_parse_no_unreleased_ok(self, tmp_path):
        root = _write_tmp_repo(tmp_path, unreleased=False)
        bullets, headers = release.parse_changelog(root)
        assert bullets == []
        assert headers[0] == "0.14.0"

    def test_release_changelog_converts_and_links(self, tmp_path):
        root = _write_tmp_repo(tmp_path)
        release.release_changelog((0, 15, 0), "note line", root)
        text = (root / "CHANGELOG.md").read_text()
        assert "## [v0.15.0] - " in text
        assert "> note line" in text
        assert "[v0.15.0]: https://github.com/Exios66/llm-entity-extraction/releases/tag/v0.15.0" in text
        # the bullets moved INTO the new release section, in order, and the
        # empty [Unreleased] placeholder stays for future entries.
        assert text.index("## [v0.15.0]") < text.index("## [v0.14.0]")
        assert text.index("- feature one.") < text.index("## [v0.14.0]")
        assert text.index("## [Unreleased]") < text.index("## [v0.15.0]")

    def test_write_version(self, tmp_path):
        root = _write_tmp_repo(tmp_path)
        release.write_version((0, 15, 0), root)
        assert release.current_version(root) == (0, 15, 0)


class TestBumpFlow:
    def test_dry_run_plans_without_writing(self, tmp_path, monkeypatch, capsys):
        root = _write_tmp_repo(tmp_path)
        monkeypatch.setattr(release, "REPO_ROOT", root)
        monkeypatch.setattr(release, "PYPROJECT", root / "pyproject.toml")
        monkeypatch.setattr(release, "CHANGELOG", root / "CHANGELOG.md")
        monkeypatch.setattr(release, "run_git", lambda *a: "")
        rc = release.main_with_args(["--bump", "minor", "--dry-run"])
        assert rc == 0
        assert "0.15.0" in capsys.readouterr().out
        assert release.current_version(root) == (0, 14, 0)  # untouched
        assert "## [Unreleased]" in (root / "CHANGELOG.md").read_text()

    def test_dirty_tree_refuses(self, tmp_path, monkeypatch):
        root = _write_tmp_repo(tmp_path)
        monkeypatch.setattr(release, "REPO_ROOT", root)
        monkeypatch.setattr(release, "PYPROJECT", root / "pyproject.toml")
        monkeypatch.setattr(release, "CHANGELOG", root / "CHANGELOG.md")
        monkeypatch.setattr(release, "run_git", lambda *a: " M CHANGELOG.md")
        with pytest.raises(SystemExit):
            release.main_with_args(["--bump", "minor"])

    def test_no_unreleased_entries_refuses(self, tmp_path, monkeypatch):
        root = _write_tmp_repo(tmp_path, unreleased=False)
        monkeypatch.setattr(release, "REPO_ROOT", root)
        monkeypatch.setattr(release, "PYPROJECT", root / "pyproject.toml")
        monkeypatch.setattr(release, "CHANGELOG", root / "CHANGELOG.md")
        monkeypatch.setattr(release, "run_git", lambda *a: "")
        with pytest.raises(SystemExit):
            release.main_with_args(["--bump", "minor"])
