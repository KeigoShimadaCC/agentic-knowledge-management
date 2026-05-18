"""Redaction utilities for API responses."""

from typing import Any

_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "openai_api_key",
        "session_secret",
        "mcp_internal_token",
        "token",
        "token_hash",
        "password",
        "password_hash",
        "secret",
    }
)
_REDACTED_SENTINEL = "[REDACTED]"
_ENV_VAR_SENTINEL = "*****"
_SENSITIVE_KEY_FRAGMENTS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "secret",
        "session_secret",
        "api_key",
        "api_keys",
        "openai_api_key",
        "token_hash",
        "authorization",
    }
)


def _is_sensitive_key(key: str) -> bool:
    lower = str(key).lower()
    if lower in _REDACTED_KEYS:
        return True
    return any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_dict(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: _REDACTED_SENTINEL if _is_sensitive_key(k) else redact_dict(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data


def redact_env_vars(env_vars: dict[str, str]) -> dict[str, str]:
    return {k: _ENV_VAR_SENTINEL for k in env_vars}


def redact_mapping(value: dict[str, Any], *, depth: int = 8) -> dict[str, Any]:
    """Compatibility wrapper for earlier API unit tests."""
    if depth <= 0:
        return {"_redacted": True}

    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(str(key)):
            out[str(key)] = _REDACTED_SENTINEL
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
