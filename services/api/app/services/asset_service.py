import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.object import KosObject


async def create_asset(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
    storage_path: str,
) -> tuple[KosObject, Asset]:
    obj = KosObject(user_id=user_id, kind="asset", title=filename)
    db.add(obj)
    await db.flush()

    asset = Asset(
        id=obj.id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256,
        storage_path=storage_path,
        status="ready",
    )
    db.add(asset)
    await db.flush()
    return obj, asset


async def find_by_sha256(db: AsyncSession, sha256: str, user_id: uuid.UUID) -> tuple[KosObject, Asset] | None:
    result = await db.execute(
        select(Asset)
        .join(KosObject, KosObject.id == Asset.id)
        .where(Asset.sha256 == sha256, KosObject.user_id == user_id, KosObject.deleted_at.is_(None))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return None
    obj_result = await db.execute(select(KosObject).where(KosObject.id == asset.id))
    obj = obj_result.scalar_one()
    return obj, asset


async def get_asset_or_404(db: AsyncSession, asset_id: uuid.UUID, user_id: uuid.UUID) -> tuple[KosObject, Asset]:
    result = await db.execute(
        select(Asset)
        .join(KosObject, KosObject.id == Asset.id)
        .where(Asset.id == asset_id, KosObject.user_id == user_id, KosObject.deleted_at.is_(None))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    obj_result = await db.execute(select(KosObject).where(KosObject.id == asset_id))
    obj = obj_result.scalar_one()
    return obj, asset
