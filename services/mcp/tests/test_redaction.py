"""Case-insensitive redaction matrix for the MCP-side helper (PHASE-FIX-04 / S8)."""

import pytest

from kos_mcp.redaction import redact_dict

_REDACTED = "[REDACTED]"


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "API_KEY",
        "Api_Key",
        "authorization",
        "Authorization",
        "password",
        "PASSWORD_HASH",
        "session_secret",
        "Session_Secret",
        "openai_api_key",
        "OPENAI_API_KEY",
    ],
)
def test_mcp_redact_dict_case_insensitive(key: str):
    out = redact_dict({key: "leak-me", "ok_field": "fine"})
    assert out[key] == _REDACTED
    assert out["ok_field"] == "fine"


def test_mcp_redact_dict_recurses():
    nested = {"a": {"API_KEY": "x"}, "b": [{"Authorization": "y"}]}
    out = redact_dict(nested)
    assert out["a"]["API_KEY"] == _REDACTED
    assert out["b"][0]["Authorization"] == _REDACTED


def test_mcp_redact_parity_with_api_helper():
    """The MCP helper must agree with the API helper on every sensitive key.

    Imported lazily so this test can be skipped when the API package isn't on
    sys.path (e.g., minimal MCP-only test runs).
    """
    try:
        from app.core.redaction import (
            _REDACTED_KEYS as api_keys,
            _SENSITIVE_KEY_FRAGMENTS as api_fragments,
        )
    except ModuleNotFoundError:
        pytest.skip("app.core.redaction not importable in this environment")

    from kos_mcp.redaction import _REDACTED_KEYS as mcp_keys, _SENSITIVE_KEY_FRAGMENTS as mcp_fragments

    assert api_keys == mcp_keys, "Redaction key lists drifted between api and mcp"
    assert api_fragments == mcp_fragments, "Sensitive fragments drifted between api and mcp"
