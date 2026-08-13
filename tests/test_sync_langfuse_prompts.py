"""Network-free smoke tests for the Langfuse prompt-sync script."""

from pathlib import Path

import pytest

from src.prompts import PROMPT_VERSIONS


@pytest.fixture
def fake_env_file(tmp_path: Path) -> Path:
    env_file = tmp_path / "langfuse.env"
    env_file.write_text(
        "LANGFUSE_PUBLIC_KEY=pk-lf-fake-public\n"
        "LANGFUSE_SECRET_KEY=sk-lf-fake-secret\n"
        "LANGFUSE_PROJECT=llm-dojo\n"
        "LANGFUSE_BASE_URL=https://us.cloud.langfuse.com\n"
    )
    return env_file


def _run_sync(argv, monkeypatch, responses):
    import scripts.eval.sync_langfuse_prompts as sync

    calls = {"get": 0, "post": 0}

    class FakeResponse:
        def __init__(self, status, payload=None, text=""):
            self.status_code = status
            self._payload = payload
            self.text = text

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, **kwargs):
        calls["get"] += 1
        name = (kwargs.get("params") or {}).get("name")
        if name not in responses:
            return FakeResponse(404, text="not found")
        return FakeResponse(200, {"name": name, "prompt": responses[name]})

    def fake_post(url, **kwargs):
        calls["post"] += 1
        return FakeResponse(200, kwargs.get("json"))

    monkeypatch.setattr(sync.requests, "get", fake_get)
    monkeypatch.setattr(sync.requests, "post", fake_post)
    rc = sync.main_with_args(argv)
    return rc, calls


def test_sync_dry_run_reports_creates(fake_env_file, monkeypatch, capsys):
    rc, calls = _run_sync(["--env-file", str(fake_env_file), "--dry-run"], monkeypatch, {})
    assert rc == 0
    assert calls["post"] == 0  # dry-run never writes
    out = capsys.readouterr().out
    assert f"would create {len(PROMPT_VERSIONS)}" in out
    assert "llm-dojo" in out


def test_sync_creates_absent_prompts_and_skips_unchanged(fake_env_file, monkeypatch):
    import scripts.eval.sync_langfuse_prompts as sync

    versions = dict(PROMPT_VERSIONS)
    first = next(iter(versions))
    # Simulate: every prompt absent locally -> all created.
    rc, calls = _run_sync(["--env-file", str(fake_env_file)], monkeypatch, {})
    assert rc == 0
    assert calls["post"] == len(versions)

    # Second run: the project already holds every prompt with matching
    # content -> nothing is created (idempotency).
    rc, calls = _run_sync(["--env-file", str(fake_env_file)], monkeypatch, versions)
    assert rc == 0
    assert calls["post"] == 0
    assert calls["get"] == len(versions)

    # A prompt whose content CHANGED locally gets re-created; identical
    # ones are skipped (the server holds the old content).
    changed = dict(versions)
    changed[first] = changed[first] + "\n(changed)"
    monkeypatch.setattr(sync, "PROMPT_VERSIONS", changed)
    rc, calls = _run_sync(["--env-file", str(fake_env_file)], monkeypatch, versions)
    assert rc == 0
    assert calls["post"] == 1


def test_sync_missing_env_file_warns(tmp_path, monkeypatch, capsys):
    rc, calls = _run_sync(["--env-file", str(tmp_path / "nope.env")], monkeypatch, {})
    assert rc == 0
    out = capsys.readouterr().out
    assert "not found" in out


def test_sync_without_keys_skips_project(tmp_path, monkeypatch, capsys):
    # The script falls back to real shell env vars — clear them so the
    # no-keys fixture is authoritative (tests must be network-free).
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    env_file = tmp_path / "no-keys.env"
    env_file.write_text("LANGFUSE_PROJECT=llm-dojo\n")
    rc, calls = _run_sync(["--env-file", str(env_file)], monkeypatch, {})
    assert rc == 0
    assert calls["get"] == 0
    out = capsys.readouterr().out
    assert "no Langfuse keys" in out
