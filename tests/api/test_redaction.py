"""Case-insensitive redaction matrix (PHASE-FIX-04 / S8)."""

import pytest
from app.core.redaction import redact_dict, redact_mapping

_REDACTED = "[REDACTED]"


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "API_KEY",
        "Api_Key",
        "ApI_KeY",
        "authorization",
        "Authorization",
        "AUTHORIZATION",
        "password",
        "Password",
        "PASSWORD_HASH",
        "session_secret",
        "Session_Secret",
        "openai_api_key",
        "OPENAI_API_KEY",
    ],
)
def test_redact_dict_case_insensitive(key: str):
    out = redact_dict({key: "leak-me", "ok_field": "fine"})
    assert out[key] == _REDACTED
    assert out["ok_field"] == "fine"


@pytest.mark.parametrize(
    "key",
    [
        "API_KEY",
        "Api_Key",
        "Authorization",
        "PASSWORD",
    ],
)
def test_redact_mapping_case_insensitive(key: str):
    out = redact_mapping({key: "leak-me", "ok_field": "fine"})
    assert out[key] == _REDACTED
    assert out["ok_field"] == "fine"


def test_redact_dict_recurses_into_nested_dicts():
    nested = {"outer": {"API_KEY": "x", "name": "ok"}, "list": [{"PASSWORD": "y"}]}
    out = redact_dict(nested)
    assert out["outer"]["API_KEY"] == _REDACTED
    assert out["outer"]["name"] == "ok"
    assert out["list"][0]["PASSWORD"] == _REDACTED
