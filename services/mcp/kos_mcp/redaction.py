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


def redact_dict(data: Any) -> Any:
    """Recursively redact sensitive keys from dicts/lists before returning to MCP caller."""
    if isinstance(data, dict):
        return {
            k: _REDACTED_SENTINEL if k in _REDACTED_KEYS else redact_dict(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [redact_dict(item) for item in data]
    return data
