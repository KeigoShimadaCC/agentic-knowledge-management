import csv
import logging

logger = logging.getLogger(__name__)


def extract(source, db) -> dict:
    """Extract first 20 rows preview from CSV."""
    from app.config import settings
    from app.models.asset import Asset

    if source.asset_id is None:
        return {"ingestion_status": "error", "error_message": "CSV source has no asset_id"}

    asset = db.get(Asset, str(source.asset_id))
    if asset is None or asset.storage_path is None:
        return {"ingestion_status": "error", "error_message": "Asset not found or no storage_path"}

    asset_path = settings.library_root / asset.storage_path
    if not asset_path.exists():
        msg = f"Asset file not found: {asset.storage_path}"
        return {"ingestion_status": "error", "error_message": msg}

    try:
        rows = []
        headers: list = []
        with open(asset_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            for i, row in enumerate(reader):
                if i >= 20:
                    break
                rows.append(dict(row))

        return {
            "ingestion_status": "ready",
            "preview_data": {"headers": headers, "rows": rows},
        }

    except Exception as e:
        logger.exception("CSV extraction failed")
        return {"ingestion_status": "error", "error_message": str(e)[:500]}
