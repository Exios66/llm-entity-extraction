"""DMR-061 — durability gate live-or-loud static guard.

The gate script flips to exit 1 whenever a bench step fails or stays empty;
a regression to the old `set -uo pipefail` + `2>/dev/null` + silent-grep
shape must fail here before it can fake a green scoreboard on the AP.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "durability_gate.sh"


def test_gate_script_exists():
    assert GATE.is_file()


def test_gate_uses_fail_fast_shell():
    text = GATE.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text, "gate must fail fast: set -euo pipefail"


def test_gate_never_silences_bench_stderr():
    """The old shape redirected every bench's stderr to /dev/null — a crashed
    bench printed nothing and grep-empty looked like 'no results'."""
    text = GATE.read_text(encoding="utf-8")
    assert "2>/dev/null" not in text, "bench stderr must stay visible"
    assert "|| true" not in text, "a failed step must not be masked"


def test_gate_exits_nonzero_on_failure():
    text = GATE.read_text(encoding="utf-8")
    assert 'FAILED=1' in text, "the script must track per-step failures"
    assert 'exit 1' in text, "the script must exit 1 when a step failed"


def test_gate_checks_every_invocation_rc():
    """Every python3 invocation must be an rc-checked step — a bench that
    'runs' but produces no output is a failure, not a green row."""
    text = GATE.read_text(encoding="utf-8")
    assert "run_step" in text
    # gen_edge + the per-model loop bodies (4-specialist loop, judge, 2-role loop)
    assert text.count("run_step ") >= 5