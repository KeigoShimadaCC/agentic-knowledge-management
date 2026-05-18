"""Redaction utilities for MCP tool responses.

Mirrors ``services/api/app/core/redaction.py`` so the MCP server can stay
standalone (no app dependency). Both modules share the same key list and
case-insensitive matching policy; the parity is asserted by the test in
``services/mcp/tests/test_redaction.py``.
"""

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

_REDACTED_SENTINEL = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    lower = str(key).lower()
    if lower in _REDACTED_KEYS:
        return True
    return any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_dict(data: Any) -> Any:
    """Recursively redact sensitive keys (case-insensitive) before returning to an MCP caller."""
    if isinstance(data, dict):
        return {
            k: _REDACTED_SENTINEL if _is_sensitive_key(k) else redact_dict(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data
