"""Environment variable helpers.

Require specific env vars are set, with helpful error messages.
"""

from __future__ import annotations

import os


def require_env(*names: str) -> tuple[str, ...]:
    """Validate that all given environment variables are set and non-empty.

    Returns the resolved values as a tuple. Exits with a helpful message if any are missing.
    """
    values = []
    missing = []
    for name in names:
        value = os.environ.get(name, "").strip()
        if not value:
            missing.append(name)
        else:
            values.append(value)
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    return tuple(values)


def get_env(name: str, default: str = "") -> str:
    """Get an environment variable with a default fallback."""
    return os.environ.get(name, default).strip()


def bool_env(name: str, default: bool = False) -> bool:
    """Get a boolean environment variable."""
    value = os.environ.get(name, str(default)).lower()
    return value in ("true", "1", "yes", "on")
