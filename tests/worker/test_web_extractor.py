"""Unit tests for the web article extractor — mocks safe_http_get."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from helpers import make_source


HTML_SAMPLE = b"""
<html>
<head>
  <title>Test Article Title</title>
  <meta name="description" content="A test article about nothing.">
</head>
<body>
  <p>First paragraph with some content.</p>
  <p>Second paragraph for extraction.</p>
</body>
</html>
"""


def _fake_http_response(content: bytes = HTML_SAMPLE, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.content = content
    return resp


def _run(source, monkeypatch, http_response=None):
    monkeypatch.setattr(
        "app.core.url_safety.validate_safe_http_url", lambda url: None
    )
    mock_resp = http_response or _fake_http_response()
    monkeypatch.setattr(
        "app.core.url_safety.safe_http_get", lambda *a, **kw: mock_resp
    )
    db = MagicMock()
    from kos_worker.extractors import web as extractor
    return extractor.extract(source, db)


def test_web_extracts_title_and_body(monkeypatch):
    source = make_source("src-web-1", url="http://example.com/article")
    result = _run(source, monkeypatch)

    assert result["ingestion_status"] == "ready"
    assert "Test Article Title" in result["extracted_text"]
    assert "First paragraph" in result["extracted_text"]


def test_web_returns_error_when_no_url(monkeypatch):
    source = make_source("src-web-2", url=None)
    db = MagicMock()
    from kos_worker.extractors import web as extractor
    result = extractor.extract(source, db)
    assert result["ingestion_status"] == "error"
    assert "URL" in result["error_message"]


def test_web_returns_error_on_http_failure(monkeypatch):
    source = make_source("src-web-3", url="http://example.com/fail")
    result = _run(source, monkeypatch, http_response=_fake_http_response(status=404))
    assert result["ingestion_status"] == "error"
    assert "404" in result["error_message"]
