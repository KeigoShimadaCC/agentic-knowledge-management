import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Fetch web article title and body text via httpx + BeautifulSoup."""
    import httpx
    from app.config import settings
    from app.core.url_safety import (
        DEFAULT_MAX_BODY_BYTES,
        UnsafeUrlError,
        safe_http_get,
        validate_safe_http_url,
    )
    from bs4 import BeautifulSoup

    if not source.url:
        return {"ingestion_status": "error", "error_message": "Web source has no URL"}

    try:
        headers = {
            "User-Agent": "KnowledgeOS/1.0 (personal knowledge base; not a crawler)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            page = safe_http_get(
                source.url,
                headers=headers,
                timeout=15.0,
                max_body_bytes=DEFAULT_MAX_BODY_BYTES,
            )
        except UnsafeUrlError as exc:
            return {"ingestion_status": "error", "error_message": str(exc)}
        except httpx.HTTPError as exc:
            logger.exception("HTTP error fetching %s", source.url)
            return {"ingestion_status": "error", "error_message": str(exc)[:500]}

        if page.status_code != 200:
            return {
                "ingestion_status": "error",
                "error_message": f"HTTP {page.status_code} fetching {source.url}",
            }

        html = page.content.decode(errors="replace")

        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""

        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        body = "\n".join(paragraphs)

        extracted_text = "\n".join(filter(None, [title, description, body])) or None

        result: dict = {
            "ingestion_status": "ready",
            "extracted_text": extracted_text,
        }

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            thumb_url = og_image["content"].strip()
            try:
                validate_safe_http_url(thumb_url)
                thumb_resp = safe_http_get(
                    thumb_url,
                    headers=headers,
                    timeout=10.0,
                    max_body_bytes=12 * 1024 * 1024,
                )
                if thumb_resp.status_code == 200:
                    from PIL import Image

                    img = Image.open(BytesIO(thumb_resp.content))
                    img.thumbnail((512, 512))
                    thumb_dir = settings.library_root / "sources" / str(source.id)
                    thumb_dir.mkdir(parents=True, exist_ok=True)
                    thumb_path = thumb_dir / "thumbnail.jpg"
                    img.convert("RGB").save(thumb_path, "JPEG")
                    result["thumbnail_path"] = f"sources/{source.id}/thumbnail.jpg"
            except (UnsafeUrlError, OSError, ValueError) as e:
                logger.debug("Could not fetch og:image thumbnail: %s", e)

        return result

    except Exception as e:
        logger.exception("Web extraction failed for %s", source.url)
        return {"ingestion_status": "error", "error_message": str(e)[:500]}
