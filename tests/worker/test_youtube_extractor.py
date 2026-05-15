"""Unit tests for the YouTube extractor — mocks safe_http_get and transcript API."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from helpers import make_source
from youtube_transcript_api import NoTranscriptFound

OEMBED_RESPONSE = {
    "title": "Test Video",
    "author_name": "Test Channel",
    "thumbnail_url": None,
}


def _fake_oembed_response(data: dict = OEMBED_RESPONSE, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.content = json.dumps(data).encode()
    return resp


def _run(source, monkeypatch, transcript_segments=None, transcript_error=None, oembed_resp=None):
    monkeypatch.setattr("app.core.url_safety.validate_safe_http_url", lambda url: None)
    monkeypatch.setattr(
        "app.core.url_safety.safe_http_get",
        lambda *a, **kw: oembed_resp or _fake_oembed_response(),
    )
    if transcript_segments is not None or transcript_error is not None:
        mock_api = MagicMock()
        if transcript_error is not None:
            mock_api.get_transcript.side_effect = transcript_error
        else:
            mock_api.get_transcript.return_value = transcript_segments
        monkeypatch.setattr("youtube_transcript_api.YouTubeTranscriptApi", mock_api)
    db = MagicMock()
    from kos_worker.extractors import youtube as extractor

    return extractor.extract(source, db)


def test_youtube_extracts_oembed_metadata(monkeypatch):
    source = make_source("src-yt-1", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    result = _run(source, monkeypatch, transcript_segments=[])

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["title"] == "Test Video"
    assert result["preview_data"]["author_name"] == "Test Channel"


def test_youtube_includes_transcript(monkeypatch):
    segments = [
        {"text": "Hello world", "start": 0.0, "duration": 1.5},
        {"text": "from YouTube", "start": 1.5, "duration": 1.0},
    ]
    source = make_source("src-yt-2", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    result = _run(source, monkeypatch, transcript_segments=segments)

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["transcript_available"] is True
    assert "Hello world" in result.get("extracted_text", "")
    assert "from YouTube" in result.get("extracted_text", "")


def test_youtube_missing_transcript_sets_flag_and_empty_text(monkeypatch):
    source = make_source("src-yt-missing", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    result = _run(
        source,
        monkeypatch,
        transcript_error=NoTranscriptFound("dQw4w9WgXcQ", ["en", "ja"], MagicMock()),
    )

    assert result["ingestion_status"] == "ready"
    assert result["preview_data"]["transcript_available"] is False
    assert not result.get("extracted_text")


def test_youtube_returns_error_when_no_url(monkeypatch):
    source = make_source("src-yt-3", url=None)
    db = MagicMock()
    from kos_worker.extractors import youtube as extractor

    result = extractor.extract(source, db)
    assert result["ingestion_status"] == "error"
