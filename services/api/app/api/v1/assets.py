import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.storage import get_absolute_path, store_file
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import AssetOut
from app.schemas.object import ObjectOut
from app.services import asset_service

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetUploadOut:
    pass


from pydantic import BaseModel


class AssetUploadResponse(BaseModel):
    object: ObjectOut
    asset: AssetOut


@router.post("/upload", response_model=AssetUploadResponse, status_code=201)
async def upload_asset(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetUploadResponse:
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()

    existing = await asset_service.find_by_sha256(db, sha256, user.id)
    if existing:
        obj, asset = existing
        return AssetUploadResponse(
            object=ObjectOut.model_validate(obj),
            asset=AssetOut.model_validate(asset),
        )

    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"
    storage_path = store_file(content, sha256, filename)

    obj, asset = await asset_service.create_asset(
        db,
        user_id=user.id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
        storage_path=storage_path,
    )
    await db.commit()
    await db.refresh(obj)
    await db.refresh(asset)

    return AssetUploadResponse(
        object=ObjectOut.model_validate(obj),
        asset=AssetOut.model_validate(asset),
    )


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetOut:
    _, asset = await asset_service.get_asset_or_404(db, asset_id, user.id)
    return AssetOut.model_validate(asset)


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    _, asset = await asset_service.get_asset_or_404(db, asset_id, user.id)
    abs_path = get_absolute_path(asset.storage_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=str(abs_path),
        media_type=asset.content_type,
        filename=asset.filename,
    )


@router.delete("/{asset_id}", response_model=ObjectOut)
async def delete_asset(
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectOut:
    from datetime import datetime, timezone
    from app.services.object_service import get_object_or_404, soft_delete_object

    obj = await get_object_or_404(db, asset_id, user.id)
    obj = await soft_delete_object(db, obj)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)
