import logging

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Extract dimensions from image and generate thumbnail."""
    from app.config import settings
    from app.models.asset import Asset

    if source.asset_id is None:
        return {"ingestion_status": "error", "error_message": "Image source has no asset_id"}

    asset = db.get(Asset, str(source.asset_id))
    if asset is None or asset.storage_path is None:
        return {"ingestion_status": "error", "error_message": "Asset not found or no storage_path"}

    asset_path = settings.library_root / asset.storage_path
    if not asset_path.exists():
        msg = f"Asset file not found: {asset.storage_path}"
        return {"ingestion_status": "error", "error_message": msg}

    try:
        from PIL import Image

        img = Image.open(str(asset_path))
        width, height = img.size

        # Generate thumbnail
        thumb_img = img.copy()
        thumb_img.thumbnail((512, 512))
        thumb_dir = settings.library_root / "sources" / str(source.id)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / "thumbnail.jpg"
        thumb_img.convert("RGB").save(thumb_path, "JPEG")

        result: dict = {
            "ingestion_status": "ready",
            "thumbnail_path": f"sources/{source.id}/thumbnail.jpg",
            "preview_data": {"width": width, "height": height},
        }

        # Update asset dimensions if not already set
        if asset.width is None:
            asset.width = width
        if asset.height is None:
            asset.height = height
        db.commit()

        return result

    except Exception as e:
        logger.exception("Image extraction failed")
        return {"ingestion_status": "error", "error_message": str(e)[:500]}
