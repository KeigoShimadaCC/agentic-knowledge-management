import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Extract text and page count from PDF. Thumbnail only if first page has embedded image."""
    from app.config import settings
    from app.models.asset import Asset

    if source.asset_id is None:
        return {"ingestion_status": "error", "error_message": "PDF source has no asset_id"}

    asset = db.get(Asset, str(source.asset_id))
    if asset is None or asset.storage_path is None:
        return {"ingestion_status": "error", "error_message": "Asset not found or no storage_path"}

    asset_path = settings.library_root / asset.storage_path
    if not asset_path.exists():
        msg = f"Asset file not found: {asset.storage_path}"
        return {"ingestion_status": "error", "error_message": msg}

    result: dict = {"ingestion_status": "ready"}

    try:
        import pypdf

        reader = pypdf.PdfReader(str(asset_path))
        result["page_count"] = len(reader.pages)

        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
        result["extracted_text"] = "\n".join(texts) if texts else None

        # Try thumbnail from first page embedded image (optional — don't fail if unavailable)
        try:
            first_page = reader.pages[0]
            if first_page.images:
                img_data = first_page.images[0].data
                from PIL import Image

                img = Image.open(BytesIO(img_data))
                img.thumbnail((512, 512))
                thumb_dir = settings.library_root / "sources" / str(source.id)
                thumb_dir.mkdir(parents=True, exist_ok=True)
                thumb_path = thumb_dir / "thumbnail.jpg"
                img.convert("RGB").save(thumb_path, "JPEG")
                result["thumbnail_path"] = f"sources/{source.id}/thumbnail.jpg"
        except Exception as e:
            logger.debug("Could not extract PDF thumbnail: %s", e)

    except Exception as e:
        logger.exception("PDF extraction failed")
        return {"ingestion_status": "error", "error_message": str(e)[:500]}

    return result
