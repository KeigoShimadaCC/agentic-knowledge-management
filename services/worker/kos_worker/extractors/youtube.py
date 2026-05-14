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
    import httpx
    from app.config import settings

    if not source.url:
        return {"ingestion_status": "error", "error_message": "YouTube source has no URL"}

    result: dict = {"ingestion_status": "ready"}

    # 1. oEmbed metadata
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={source.url}&format=json"
        resp = httpx.get(oembed_url, timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            oembed = resp.json()
            result["preview_data"] = {
                "title": oembed.get("title"),
                "author_name": oembed.get("author_name"),
                "thumbnail_url": oembed.get("thumbnail_url"),
                "oembed": oembed,
            }
            # Download thumbnail
            thumb_url = oembed.get("thumbnail_url")
            if thumb_url:
                try:
                    thumb_resp = httpx.get(thumb_url, timeout=10, follow_redirects=True)
                    if thumb_resp.status_code == 200:
                        thumb_dir = settings.library_root / "sources" / str(source.id)
                        thumb_dir.mkdir(parents=True, exist_ok=True)
                        (thumb_dir / "thumbnail.jpg").write_bytes(thumb_resp.content)
                        result["thumbnail_path"] = f"sources/{source.id}/thumbnail.jpg"
                except Exception as e:
                    logger.debug("Could not download YouTube thumbnail: %s", e)
        else:
            logger.warning("oEmbed returned status %s for %s", resp.status_code, source.url)
    except Exception as e:
        logger.warning("oEmbed fetch failed: %s", e)

    # 2. Transcript (optional — failure is not an error)
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
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.info("No transcript available for %s: %s", video_id, e)
    except Exception as e:
        logger.warning("Transcript fetch failed: %s", e)

    return result
