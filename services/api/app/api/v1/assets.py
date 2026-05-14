import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.storage import get_absolute_path, store_file
from app.db.session import get_db
from app.models.edge import Edge
from app.models.object import KosObject
from app.models.source import Source
from app.models.user import User
from app.schemas.asset import AssetOut
from app.schemas.object import ObjectOut
from app.schemas.source import SourceCreate, SourceOut
from app.services import asset_service, source_service

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetUploadOut:
    pass


class AssetUploadResponse(BaseModel):
    object: ObjectOut
    asset: AssetOut


class AssetSourceUploadResponse(BaseModel):
    object: AssetOut
    source: SourceOut


def infer_source_type(content_type: str) -> str:
    if content_type == "application/pdf":
        return "pdf"
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    if content_type in {"text/csv", "application/csv"}:
        return "csv"
    return "file"


def build_source_out(obj: KosObject, source: Source) -> SourceOut:
    return SourceOut(
        id=obj.id,
        user_id=obj.user_id,
        kind=obj.kind,
        title=obj.title,
        description=obj.description,
        tags=obj.tags,
        is_pinned=obj.is_pinned,
        is_archived=obj.is_archived,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        deleted_at=obj.deleted_at,
        source_type=source.source_type,
        url=source.url,
        asset_id=source.asset_id,
        ingestion_status=source.ingestion_status,
        extracted_text=source.extracted_text,
        page_count=source.page_count,
        thumbnail_path=source.thumbnail_path,
        preview_data=source.preview_data,
        error_message=source.error_message,
    )


@router.post(
    "/upload",
    response_model=AssetUploadResponse | AssetSourceUploadResponse,
    status_code=201,
)
async def upload_asset(
    file: UploadFile,
    create_source: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetUploadResponse | AssetSourceUploadResponse:
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()

    existing = await asset_service.find_by_sha256(db, sha256, user.id)
    if existing and not create_source:
        obj, asset = existing
        return AssetUploadResponse(
            object=ObjectOut.model_validate(obj),
            asset=AssetOut.model_validate(asset),
        )

    if existing:
        obj, asset = existing
    else:
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

    if create_source:
        source_data = SourceCreate(
            source_type=infer_source_type(asset.content_type),
            asset_id=obj.id,
            title=obj.title,
        )
        src_obj, src = await source_service.create_source(db, user.id, source_data)
        db.add(
            Edge(
                user_id=user.id,
                source_id=src_obj.id,
                target_id=obj.id,
                kind="derives_from",
            )
        )
        await db.commit()
        await db.refresh(src_obj)
        await db.refresh(src)

        return AssetSourceUploadResponse(
            object=AssetOut.model_validate(asset),
            source=build_source_out(src_obj, src),
        )

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
    from app.services.object_service import get_object_or_404, soft_delete_object

    obj = await get_object_or_404(db, asset_id, user.id)
    obj = await soft_delete_object(db, obj)
    await db.commit()
    await db.refresh(obj)
    return ObjectOut.model_validate(obj)
