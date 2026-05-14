"""Strip sensitive keys from structures returned to agents or external callers."""

from __future__ import annotations

from typing import Any

_SENSITIVE_KEY_FRAGMENTS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "secret",
        "session_secret",
        "api_key",
        "openai_api_key",
        "token_hash",
        "authorization",
    }
)


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_mapping(value: dict[str, Any], *, depth: int = 8) -> dict[str, Any]:
    """Return a shallow-deep copy of *value* with sensitive keys removed or replaced."""
    if depth <= 0:
        return {"_redacted": True}

    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(str(key)):
            out[str(key)] = "[REDACTED]"
            continue
        if isinstance(item, dict):
            out[str(key)] = redact_mapping(item, depth=depth - 1)
        elif isinstance(item, list):
            out[str(key)] = [
                redact_mapping(sub, depth=depth - 1) if isinstance(sub, dict) else sub
                for sub in item
            ]
        else:
            out[str(key)] = item
    return out
