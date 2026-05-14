import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Fetch web article title and body text via httpx + BeautifulSoup."""
    import httpx
    from app.config import settings

    if not source.url:
        return {"ingestion_status": "error", "error_message": "Web source has no URL"}

    try:
        headers = {
            "User-Agent": "KnowledgeOS/1.0 (personal knowledge base; not a crawler)",
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = httpx.get(source.url, headers=headers, timeout=15, follow_redirects=True)

        if resp.status_code != 200:
            return {
                "ingestion_status": "error",
                "error_message": f"HTTP {resp.status_code} fetching {source.url}",
            }

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")

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

        # Try og:image for thumbnail
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            try:
                thumb_resp = httpx.get(og_image["content"], timeout=10, follow_redirects=True)
                if thumb_resp.status_code == 200:
                    from PIL import Image

                    img = Image.open(BytesIO(thumb_resp.content))
                    img.thumbnail((512, 512))
                    thumb_dir = settings.library_root / "sources" / str(source.id)
                    thumb_dir.mkdir(parents=True, exist_ok=True)
                    thumb_path = thumb_dir / "thumbnail.jpg"
                    img.convert("RGB").save(thumb_path, "JPEG")
                    result["thumbnail_path"] = f"sources/{source.id}/thumbnail.jpg"
            except Exception as e:
                logger.debug("Could not fetch og:image thumbnail: %s", e)

        return result

    except Exception as e:
        logger.exception("Web extraction failed for %s", source.url)
        return {"ingestion_status": "error", "error_message": str(e)[:500]}
