import socket
from unittest.mock import patch

import pytest

from app.core.redaction import redact_mapping
from app.core.url_safety import UnsafeUrlError, validate_safe_http_url


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeUrlError, match="Only http"):
        validate_safe_http_url("ftp://example.com/")


def test_rejects_credentials_in_url():
    with pytest.raises(UnsafeUrlError, match="credentials"):
        validate_safe_http_url("http://user:pass@example.com/")


def test_rejects_literal_loopback_ip():
    with pytest.raises(UnsafeUrlError):
        validate_safe_http_url("http://127.0.0.1/path")


def test_rejects_literal_private_ip():
    with pytest.raises(UnsafeUrlError):
        validate_safe_http_url("http://192.168.0.1/path")


@patch("app.core.url_safety.socket.getaddrinfo")
def test_accepts_public_resolution(mock_gai):
    mock_gai.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 443))]
    validate_safe_http_url("https://example.org/foo")


@patch("app.core.url_safety.socket.getaddrinfo")
def test_rejects_dns_that_resolves_to_private(mock_gai):
    mock_gai.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.4.4", 443)),
    ]
    with pytest.raises(UnsafeUrlError, match="globally routable"):
        validate_safe_http_url("https://evil.example/path")


def test_redact_mapping_strips_sensitive_keys():
    raw = {
        "title": "ok",
        "api_keys": "secret",
        "nested": {"password_hash": "x"},
        "list": [{"authorization": "bearer"}],
    }
    out = redact_mapping(raw)
    assert out["title"] == "ok"
    assert out["api_keys"] == "[REDACTED]"
    assert out["nested"]["password_hash"] == "[REDACTED]"
    assert out["list"][0]["authorization"] == "[REDACTED]"
