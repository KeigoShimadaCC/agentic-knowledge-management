"""Worker-side URL safety checks for network-backed extractors."""

from __future__ import annotations

from helpers import make_source


def test_youtube_extractor_rejects_loopback_url_before_fetching(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("unsafe URL should be rejected before HTTP fetch")

    monkeypatch.setattr("app.core.url_safety.safe_http_get", fail_if_called)

    from kos_worker.extractors import youtube as extractor

    source = make_source("src-youtube-unsafe", url="http://127.0.0.1/watch?v=dQw4w9WgXcQ")
    result = extractor.extract(source, db=None)

    assert result["ingestion_status"] == "error"
    assert "not allowed" in result["error_message"]
