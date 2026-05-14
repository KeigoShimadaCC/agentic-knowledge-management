import logging

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Detect file type and delegate to the appropriate extractor."""
    from app.config import settings
    from app.models.asset import Asset

    if source.asset_id is None:
        return {"ingestion_status": "error", "error_message": "File source has no asset_id"}

    asset = db.get(Asset, str(source.asset_id))
    if asset is None or asset.storage_path is None:
        return {"ingestion_status": "error", "error_message": "Asset not found or no storage_path"}

    asset_path = settings.library_root / asset.storage_path
    if not asset_path.exists():
        msg = f"Asset file not found: {asset.storage_path}"
        return {"ingestion_status": "error", "error_message": msg}

    try:
        import filetype

        kind = filetype.guess(str(asset_path))
        if kind is None:
            return {"ingestion_status": "ready"}

        mime = kind.mime
        if mime == "application/pdf":
            from kos_worker.extractors.pdf import extract as pdf_extract

            return pdf_extract(source, db)
        elif mime.startswith("image/"):
            from kos_worker.extractors.image import extract as image_extract

            return image_extract(source, db)
        elif mime.startswith("video/") or mime.startswith("audio/"):
            return {"ingestion_status": "ready"}
        else:
            return {"ingestion_status": "ready"}

    except Exception as e:
        logger.exception("File type detection failed")
        return {"ingestion_status": "error", "error_message": str(e)[:500]}
