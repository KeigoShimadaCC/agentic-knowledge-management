import logging
import re

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str | None:
    match = re.search(
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        url,
    )
    return match.group(1) if match else None


def extract(source, db) -> dict:
    """Fetch YouTube oEmbed metadata and transcript."""
    import json
    from urllib.parse import quote

    from app.config import settings
    from app.core.url_safety import (
        UnsafeUrlError,
        safe_http_get,
        validate_safe_http_url,
    )

    if not source.url:
        return {"ingestion_status": "error", "error_message": "YouTube source has no URL"}

    try:
        validate_safe_http_url(source.url)
    except UnsafeUrlError as exc:
        return {"ingestion_status": "error", "error_message": str(exc)}

    result: dict = {
        "ingestion_status": "ready",
        "preview_data": {"transcript_available": False},
    }

    headers = {
        "User-Agent": "KnowledgeOS/1.0 (personal knowledge base; not a crawler)",
        "Accept": "application/json",
    }

    try:
        oembed_url = f"https://www.youtube.com/oembed?url={quote(source.url, safe='')}&format=json"
        validate_safe_http_url(oembed_url)
        resp = safe_http_get(oembed_url, headers=headers, timeout=10.0, max_body_bytes=256 * 1024)
        if resp.status_code == 200:
            oembed = json.loads(resp.content.decode(errors="replace"))
            result["preview_data"].update(
                {
                    "title": oembed.get("title"),
                    "author_name": oembed.get("author_name"),
                    "thumbnail_url": oembed.get("thumbnail_url"),
                    "oembed": oembed,
                }
            )
            thumb_url = oembed.get("thumbnail_url")
            if thumb_url:
                try:
                    validate_safe_http_url(thumb_url)
                    thumb_resp = safe_http_get(
                        thumb_url,
                        headers=headers,
                        timeout=10.0,
                        max_body_bytes=12 * 1024 * 1024,
                    )
                    if thumb_resp.status_code == 200:
                        thumb_dir = settings.library_root / "sources" / str(source.id)
                        thumb_dir.mkdir(parents=True, exist_ok=True)
                        (thumb_dir / "thumbnail.jpg").write_bytes(thumb_resp.content)
                        result["thumbnail_path"] = f"sources/{source.id}/thumbnail.jpg"
                except (UnsafeUrlError, OSError, ValueError) as e:
                    logger.debug("Could not download YouTube thumbnail: %s", e)
        else:
            logger.warning("oEmbed returned status %s for %s", resp.status_code, source.url)
    except Exception as e:
        logger.warning("oEmbed fetch failed: %s", e)

    try:
        video_id = _extract_video_id(source.url)
        if video_id:
            from youtube_transcript_api import (
                NoTranscriptFound,
                TranscriptsDisabled,
                YouTubeTranscriptApi,
            )

            try:
                segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "ja"])
                result["extracted_text"] = " ".join(seg["text"] for seg in segments)
                result["preview_data"]["transcript_available"] = True
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.info("No transcript available for %s: %s", video_id, e)
                result["preview_data"]["transcript_available"] = False
    except Exception as e:
        logger.warning("Transcript fetch failed: %s", e)

    return result
