"""Unit tests for the web article extractor — mocks safe_http_get."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import respx
from app.core.url_safety import SafeHttpResult, safe_http_get
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


def _fake_http_result(
    content: bytes = HTML_SAMPLE,
    status: int = 200,
    content_type: str = "text/html; charset=utf-8",
    final_url: str = "http://example.com/article",
) -> SafeHttpResult:
    return SafeHttpResult(
        status_code=status,
        content=content,
        final_url=final_url,
        content_type=content_type,
    )


def _run(source, monkeypatch, http_response: SafeHttpResult | None = None):
    monkeypatch.setattr("app.core.url_safety.validate_safe_http_url", lambda url: None)
    mock_resp = http_response or _fake_http_result()
    monkeypatch.setattr("app.core.url_safety.safe_http_get", lambda *a, **kw: mock_resp)
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
    result = _run(source, monkeypatch, http_response=_fake_http_result(status=404))
    assert result["ingestion_status"] == "error"
    assert "404" in result["error_message"]


def test_web_rejects_non_html_content_type(monkeypatch):
    source = make_source("src-web-json", url="http://example.com/data.json")
    result = _run(
        source,
        monkeypatch,
        http_response=_fake_http_result(
            content=b'{"title":"nope"}',
            content_type="application/json",
        ),
    )

    assert result["ingestion_status"] == "error"
    assert "Unsupported content-type" in result["error_message"]


@respx.mock
def test_safe_http_get_follows_redirect():
    respx.get("http://example.com/start").mock(
        return_value=httpx.Response(302, headers={"Location": "http://example.com/final"})
    )
    respx.get("http://example.com/final").mock(
        return_value=httpx.Response(
            200,
            content=HTML_SAMPLE,
            headers={"content-type": "text/html; charset=utf-8"},
        )
    )

    result = safe_http_get(
        "http://example.com/start",
        headers={"User-Agent": "KnowledgeOS-test"},
        timeout=5.0,
    )

    assert result.status_code == 200
    assert result.final_url == "http://example.com/final"
    assert b"Test Article Title" in result.content
